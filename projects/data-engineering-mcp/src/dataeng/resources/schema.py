"""Schema discovery as a resource."""

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

from dataeng.db import Database


def register(server: MCPServer) -> None:
    @server.resource(
        "schema://{table}",
        name="table_schema",
        description=(
            "The columns of one allow-listed table, as JSON. "
            "Use the qualified name, such as analytics.orders."
        ),
        mime_type="application/json",
    )
    async def table_schema(ctx: Context, table: str) -> str:
        database: Database = ctx.request_context.lifespan_context
        described = await database.describe(table)
        return described.model_dump_json(indent=2)
