"""Read-only tools an on-call engineer's assistant uses."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp_types import ToolAnnotations
from pydantic import Field

from aiops import auth
from aiops.models import (
    Deployment,
    DiagnosticResult,
    Health,
    IncidentPage,
    Service,
)

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True
)
EXTERNAL = ToolAnnotations(
    read_only_hint=True,
    idempotent_hint=True,
    open_world_hint=True,
)


def register(server: MCPServer) -> None:
    @server.tool(annotations=READ_ONLY)
    async def list_services(ctx: Context) -> list[Service]:
        """List every service this server knows about.

        Start here. Other tools take a service name from this
        list and refuse anything else.
        """
        auth.require(auth.READ)
        state = ctx.request_context.lifespan_context
        return await state.db.services()

    @server.tool(annotations=EXTERNAL)
    async def get_service_health(
        ctx: Context,
        service: Annotated[
            str, Field(description="Name from list_services.")
        ],
    ) -> Health:
        """Current health of one service, from monitoring.

        Live data, so it changes between calls.
        """
        auth.require(auth.READ)
        state = ctx.request_context.lifespan_context
        return await state.monitoring.health(service)

    @server.tool(annotations=READ_ONLY)
    async def query_incidents(
        ctx: Context,
        service: Annotated[
            str | None,
            Field(
                default=None,
                description="Restrict to one service. Optional.",
            ),
        ] = None,
        status: Annotated[
            str,
            Field(
                description=(
                    "open, acknowledged or all. Defaults to open."
                )
            ),
        ] = "open",
        limit: Annotated[
            int, Field(ge=1, le=100, description="Rows, 1 to 100.")
        ] = 20,
    ) -> IncidentPage:
        """Incidents, most severe first.

        Returns identifiers that acknowledge_incident accepts.
        """
        auth.require(auth.READ)
        state = ctx.request_context.lifespan_context
        return await state.db.incidents(service, status, limit)

    @server.tool(annotations=READ_ONLY)
    async def get_deployment_history(
        ctx: Context,
        service: Annotated[
            str, Field(description="Name from list_services.")
        ],
        limit: Annotated[
            int, Field(ge=1, le=50, description="Rows, 1 to 50.")
        ] = 10,
    ) -> list[Deployment]:
        """Recent deploys for one service, newest first.

        Useful for correlating an incident with a change.
        """
        auth.require(auth.READ)
        state = ctx.request_context.lifespan_context
        return await state.db.deployments(service, limit)

    @server.tool(annotations=READ_ONLY)
    async def run_diagnostic(
        ctx: Context,
        name: Annotated[
            str,
            Field(
                description=(
                    "One of a fixed set. Anything else is "
                    "refused; the message lists them."
                )
            ),
        ],
    ) -> DiagnosticResult:
        """Run one named diagnostic and return its output.

        Only diagnostics defined in this server can run. There
        is no way to pass a command or an argument.
        """
        auth.require(auth.READ)
        state = ctx.request_context.lifespan_context
        return await state.diagnostics.run(name)
