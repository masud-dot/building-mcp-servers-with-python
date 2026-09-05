"""Read-only warehouse tools."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp_types import ToolAnnotations
from pydantic import Field

from dataeng import auth
from dataeng.db import Database
from dataeng.models import QueryResult, TableSchema

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True
)


def _db(ctx: Context) -> Database:
    return ctx.request_context.lifespan_context


def register(server: MCPServer) -> None:
    @server.tool(annotations=READ_ONLY)
    def list_tables(ctx: Context) -> list[str]:
        """List the tables this server can read.

        Only these tables are available. Anything else is
        refused, including tables that exist in the database.
        """
        auth.require(auth.READ)
        return _db(ctx).tables

    @server.tool(annotations=READ_ONLY)
    async def describe_table(
        ctx: Context,
        table: Annotated[
            str,
            Field(
                description=(
                    "Qualified name from list_tables, such as "
                    "analytics.orders."
                )
            ),
        ],
    ) -> TableSchema:
        """Return the columns and types of one table.

        Call this before sample_table so you know what the
        columns are.
        """
        auth.require(auth.READ)
        return await _db(ctx).describe(table)

    @server.tool(annotations=READ_ONLY)
    async def sample_table(
        ctx: Context,
        table: Annotated[
            str,
            Field(description="Qualified name from list_tables."),
        ],
        limit: Annotated[
            int,
            Field(
                ge=1,
                le=200,
                description="Rows to return, 1 to 200.",
            ),
        ] = 20,
    ) -> QueryResult:
        """Return a sample of rows from one table.

        Rows are capped. When truncated is true, more rows
        matched than were returned.
        """
        auth.require(auth.READ)
        return await _db(ctx).sample(table, limit)
