"""Database access, with every limit enforced in one place."""

import time
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError
from psycopg import sql
from psycopg_pool import AsyncConnectionPool

from dataeng.config import Settings
from dataeng.state import ScanStore
from dataeng.models import (
    Column,
    DeletedRun,
    QueryResult,
    TableSchema,
)

COLUMN_QUERY = """
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    ORDER BY ordinal_position
"""


class Database:
    """A read-only view of an allow-listed set of tables."""

    def __init__(
        self,
        pool: AsyncConnectionPool,
        writer_pool: AsyncConnectionPool,
        settings: Settings,
    ) -> None:
        self._pool = pool
        self._writer_pool = writer_pool
        self._settings = settings
        self.scans = ScanStore(writer_pool, pool)

    @property
    def tables(self) -> list[str]:
        return sorted(self._settings.table_set)

    def _split(self, qualified: str) -> tuple[str, str]:
        """Check the allow-list, then split schema from table.

        The allow-list is checked before anything reaches SQL, so
        an unknown name never becomes an identifier.
        """
        if qualified not in self._settings.table_set:
            raise ToolError(
                f"Table {qualified!r} is not available. "
                f"Available tables: {', '.join(self.tables)}."
            )
        schema, _, table = qualified.partition(".")
        return schema, table

    async def describe(self, qualified: str) -> TableSchema:
        """Return the columns of one allow-listed table."""
        schema, table = self._split(qualified)
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(COLUMN_QUERY, (schema, table))
                rows = await cur.fetchall()
        return TableSchema(
            schema_name=schema,
            table=table,
            columns=[
                Column(
                    name=name,
                    type=data_type,
                    nullable=(is_nullable == "YES"),
                )
                for name, data_type, is_nullable in rows
            ],
        )

    async def sample(
        self, qualified: str, limit: int
    ) -> QueryResult:
        """Return up to `limit` rows from an allow-listed table.

        The table name is composed with psycopg's Identifier, so
        it is quoted as an identifier and can never be read as
        SQL, whatever it contains.
        """
        schema, table = self._split(qualified)
        capped = min(limit, self._settings.max_rows)
        statement = sql.SQL(
            "SELECT * FROM {}.{} LIMIT %s"
        ).format(sql.Identifier(schema), sql.Identifier(table))
        return await self._run(statement, (capped + 1,), capped)

    async def _run(
        self,
        statement: Any,
        params: tuple[Any, ...],
        capped: int,
    ) -> QueryResult:
        started = time.monotonic()
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                # SET takes no bound parameters, so the value
                # is composed with Literal rather than being
                # formatted into the string by hand.
                await cur.execute(
                    sql.SQL(
                        "SET LOCAL statement_timeout = {}"
                    ).format(
                        sql.Literal(
                            self._settings.statement_timeout_ms
                        )
                    )
                )
                await cur.execute(statement, params)
                names = [d.name for d in cur.description or []]
                fetched = await cur.fetchall()
        truncated = len(fetched) > capped
        rows = fetched[:capped]
        return QueryResult(
            columns=names,
            rows=[[_render(v) for v in row] for row in rows],
            returned=len(rows),
            truncated=truncated,
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )

    async def delete_pipeline_run(self, run_id: int) -> DeletedRun:
        """Delete one pipeline run.

        The only method that touches the writer pool. Its role
        can delete from pipeline_runs and nothing else, so a
        mistake here cannot reach any other table.
        """
        async with self._writer_pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT pipeline FROM analytics.pipeline_runs "
                    "WHERE id = %s",
                    (run_id,),
                )
                row = await cur.fetchone()
                if row is None:
                    raise ToolError(
                        f"No pipeline run with identifier {run_id}."
                    )
                await cur.execute(
                    "DELETE FROM analytics.pipeline_runs "
                    "WHERE id = %s",
                    (run_id,),
                )
                removed = cur.rowcount
        return DeletedRun(
            id=run_id, pipeline=row[0], deleted=removed == 1
        )

    async def profile(
        self, qualified: str
    ) -> tuple[int, dict[str, int]]:
        """Count rows and nulls per column, bounded."""
        schema, table = self._split(qualified)
        described = await self.describe(qualified)
        counts = sql.SQL(", ").join(
            sql.SQL("count(*) - count({})").format(
                sql.Identifier(column.name)
            )
            for column in described.columns
        )
        statement = sql.SQL(
            "SELECT count(*), {} FROM {}.{}"
        ).format(
            counts, sql.Identifier(schema), sql.Identifier(table)
        )
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    sql.SQL(
                        "SET LOCAL statement_timeout = {}"
                    ).format(
                        sql.Literal(
                            self._settings.statement_timeout_ms
                        )
                    )
                )
                await cur.execute(statement)
                row = await cur.fetchone()
        assert row is not None
        names = [c.name for c in described.columns]
        return int(row[0]), {
            name: int(value)
            for name, value in zip(names, row[1:])
        }


def _render(value: Any) -> str:
    """Values become text, so a result is always displayable."""
    return "" if value is None else str(value)

