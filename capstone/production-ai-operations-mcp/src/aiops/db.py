"""Every database limit, in one place. Chapter 12."""

import json
import secrets
from datetime import timedelta
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError
from psycopg import sql
from psycopg_pool import AsyncConnectionPool

from aiops.config import Settings
from aiops.models import (
    Deployment,
    Incident,
    IncidentPage,
    ScanReport,
    Service,
)

# Read paths touch these and nothing else. ops.services is
# joined implicitly; ops.oncall_pager_tokens is granted to
# nobody, so a mistake here still cannot reach it.
INCIDENT_COLUMNS = (
    "id, service, severity, summary, status, "
    "acknowledged_by, opened_at"
)


class Database:
    """Read-only, except for two writes on separate pools."""

    def __init__(
        self,
        pool: AsyncConnectionPool,
        writer_pool: AsyncConnectionPool,
        settings: Settings,
    ) -> None:
        self._pool = pool
        self._writer = writer_pool
        self._settings = settings

    async def _timeout(self, cur) -> None:
        # SET takes no bound parameters. Chapter 12.
        await cur.execute(
            sql.SQL("SET LOCAL statement_timeout = {}").format(
                sql.Literal(self._settings.statement_timeout_ms)
            )
        )

    async def services(self) -> list[Service]:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await self._timeout(cur)
                await cur.execute(
                    "SELECT name, team, tier FROM ops.services "
                    "ORDER BY tier, name"
                )
                rows = await cur.fetchall()
        return [
            Service(name=r[0], team=r[1], tier=r[2]) for r in rows
        ]

    async def incidents(
        self, service: str | None, status: str, limit: int
    ) -> IncidentPage:
        capped = min(limit, self._settings.max_rows)
        clauses = ["1 = 1"]
        params: list[Any] = []
        if service:
            clauses.append("service = %s")
            params.append(service)
        if status != "all":
            clauses.append("status = %s")
            params.append(status)
        where = " AND ".join(clauses)
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await self._timeout(cur)
                await cur.execute(
                    f"SELECT count(*) FROM ops.incidents "
                    f"WHERE {where}",
                    params,
                )
                total = (await cur.fetchone())[0]
                await cur.execute(
                    f"SELECT {INCIDENT_COLUMNS} FROM ops.incidents "
                    f"WHERE {where} ORDER BY severity, id "
                    f"LIMIT %s",
                    [*params, capped],
                )
                rows = await cur.fetchall()
        found = [
            Incident(
                id=r[0],
                service=r[1],
                severity=r[2],
                summary=r[3],
                status=r[4],
                acknowledged_by=r[5],
                opened_at=r[6].isoformat(),
            )
            for r in rows
        ]
        return IncidentPage(
            incidents=found,
            returned=len(found),
            total=total,
            truncated=total > len(found),
        )

    async def deployments(
        self, service: str, limit: int
    ) -> list[Deployment]:
        capped = min(limit, self._settings.max_rows)
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await self._timeout(cur)
                await cur.execute(
                    "SELECT id, service, version, deployed_at "
                    "FROM ops.deployments WHERE service = %s "
                    "ORDER BY deployed_at DESC, id DESC LIMIT %s",
                    (service, capped),
                )
                rows = await cur.fetchall()
        return [
            Deployment(
                id=r[0],
                service=r[1],
                version=r[2],
                deployed_at=r[3].isoformat(),
            )
            for r in rows
        ]

    async def acknowledge(
        self, incident_id: int, who: str
    ) -> Incident:
        """The only write to ops.incidents, on the writer pool."""
        async with self._writer.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE ops.incidents SET status = "
                    "'acknowledged', acknowledged_by = %s "
                    f"WHERE id = %s RETURNING {INCIDENT_COLUMNS}",
                    (who, incident_id),
                )
                row = await cur.fetchone()
        if row is None:
            raise ToolError(
                f"No incident with identifier {incident_id}."
            )
        return Incident(
            id=row[0],
            service=row[1],
            severity=row[2],
            summary=row[3],
            status=row[4],
            acknowledged_by=row[5],
            opened_at=row[6].isoformat(),
        )

    async def start_scan(self, service: str) -> str:
        handle = secrets.token_urlsafe(16)
        async with self._writer.connection() as conn:
            await conn.execute(
                "INSERT INTO ops.scan_results "
                "(handle, service, status, expires_at) "
                "VALUES (%s, %s, 'running', now() + %s)",
                (handle, service, timedelta(hours=1)),
            )
        return handle

    async def finish_scan(
        self, handle: str, matches: int
    ) -> None:
        async with self._writer.connection() as conn:
            await conn.execute(
                "UPDATE ops.scan_results SET status = 'complete', "
                "matches = %s WHERE handle = %s",
                (matches, handle),
            )

    async def scan(self, handle: str) -> ScanReport:
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT handle, service, status, matches "
                    "FROM ops.scan_results "
                    "WHERE handle = %s AND expires_at > now()",
                    (handle,),
                )
                row = await cur.fetchone()
        if row is None:
            # Unknown and expired answer identically.
            raise ToolError(
                "No scan with that handle. Handles last an hour."
            )
        return ScanReport(
            handle=row[0],
            service=row[1],
            status=row[2],
            matches=row[3],
        )
