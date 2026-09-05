"""Work that outlives a request.

Chapter 11 put state in the lifespan, which is per instance.
Anything a caller expects to come back to must live somewhere
all instances can reach, and must travel as a value the caller
holds rather than as something the server remembers about them.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import timedelta

from mcp.server.mcpserver.exceptions import ToolError
from psycopg_pool import AsyncConnectionPool

HANDLE_BYTES = 16
DEFAULT_TTL = timedelta(hours=1)


@dataclass(frozen=True)
class ScanResult:
    """The outcome of one data-quality scan."""

    handle: str
    table_name: str
    status: str
    rows_seen: int | None
    null_counts: dict[str, int] | None


def mint() -> str:
    """A handle a caller could not have guessed.

    Chapter 9 warned that sequential identifiers build
    enumeration into an interface. A handle names work somebody
    started, so it gets 128 bits of randomness rather than a
    counter.
    """
    return secrets.token_urlsafe(HANDLE_BYTES)


class ScanStore:
    """Handles and their results, shared by every instance."""

    def __init__(
        self,
        writer_pool: AsyncConnectionPool,
        reader_pool: AsyncConnectionPool,
        ttl: timedelta = DEFAULT_TTL,
    ) -> None:
        self._writer = writer_pool
        self._reader = reader_pool
        self._ttl = ttl

    async def start(self, table_name: str) -> str:
        """Record that a scan was requested. Returns its handle."""
        handle = mint()
        async with self._writer.connection() as conn:
            await conn.execute(
                "INSERT INTO analytics.scan_results "
                "(handle, table_name, status, expires_at) "
                "VALUES (%s, %s, 'running', now() + %s)",
                (handle, table_name, self._ttl),
            )
        return handle

    async def finish(
        self,
        handle: str,
        rows_seen: int,
        null_counts: dict[str, int],
    ) -> None:
        async with self._writer.connection() as conn:
            await conn.execute(
                "UPDATE analytics.scan_results "
                "SET status = 'complete', rows_seen = %s, "
                "    null_counts = %s "
                "WHERE handle = %s",
                (rows_seen, json.dumps(null_counts), handle),
            )

    async def get(self, handle: str) -> ScanResult:
        """Retrieve by handle. Any instance can answer this."""
        async with self._reader.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT handle, table_name, status, rows_seen, "
                    "       null_counts "
                    "FROM analytics.scan_results "
                    "WHERE handle = %s AND expires_at > now()",
                    (handle,),
                )
                row = await cur.fetchone()
        if row is None:
            # Expired and unknown are the same answer on
            # purpose: neither confirms a handle ever existed.
            raise ToolError(
                "No scan with that handle. Handles expire after "
                "an hour; start a new scan."
            )
        return ScanResult(
            handle=row[0],
            table_name=row[1],
            status=row[2],
            rows_seen=row[3],
            null_counts=row[4],
        )
