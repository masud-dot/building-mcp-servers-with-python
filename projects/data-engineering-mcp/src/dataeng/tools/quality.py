"""A scan that outlives the request that started it."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field

from dataeng import auth
from dataeng.state import ScanStore

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True
)
STARTS_WORK = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
)


class ScanStarted(BaseModel):
    """What a caller needs to come back for the result."""

    handle: str = Field(
        description=(
            "Pass this to get_scan_result. Valid for one hour."
        )
    )
    table: str = Field(description="The table being scanned.")


class ScanReport(BaseModel):
    """A finished, or still running, scan."""

    handle: str = Field(description="The handle you asked for.")
    table: str = Field(description="The table scanned.")
    status: str = Field(description="running, or complete.")
    rows_seen: int | None = Field(
        default=None, description="Rows examined, when complete."
    )
    null_counts: dict[str, int] | None = Field(
        default=None,
        description="Null count per column, when complete.",
    )


def _store(ctx: Context) -> ScanStore:
    """Built from the same pools the lifespan opened."""
    database = ctx.request_context.lifespan_context
    return database.scans


def register(server: MCPServer) -> None:
    @server.tool(annotations=STARTS_WORK)
    async def start_quality_scan(
        ctx: Context,
        table: Annotated[
            str,
            Field(description="Qualified name from list_tables."),
        ],
    ) -> ScanStarted:
        """Start a data-quality scan and return a handle.

        The scan may outlive this call. Come back with
        get_scan_result, which any instance of this server can
        answer.
        """
        auth.require(auth.READ)
        database = ctx.request_context.lifespan_context
        store = _store(ctx)
        handle = await store.start(table)
        # Small enough to finish here. Chapter 30 covers the
        # case where it is not.
        rows, nulls = await database.profile(table)
        await store.finish(handle, rows, nulls)
        return ScanStarted(handle=handle, table=table)

    @server.tool(annotations=READ_ONLY)
    async def get_scan_result(
        ctx: Context,
        handle: Annotated[
            str,
            Field(
                min_length=8,
                max_length=64,
                description="Handle from start_quality_scan.",
            ),
        ],
    ) -> ScanReport:
        """Retrieve a scan by its handle."""
        auth.require(auth.READ)
        result = await _store(ctx).get(handle)
        return ScanReport(
            handle=result.handle,
            table=result.table_name,
            status=result.status,
            rows_seen=result.rows_seen,
            null_counts=result.null_counts,
        )
