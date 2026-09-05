"""Context the application loads, rather than the model asks for."""

import json

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context


def register(server: MCPServer, state_ref) -> None:
    @server.resource(
        "catalogue://services",
        name="service_catalogue",
        description="Every service, as plain text.",
        mime_type="text/plain",
    )
    async def catalogue() -> str:
        # Static resources get no Context. Chapter 11.
        state = state_ref()
        services = await state.db.services()
        return "\n".join(
            f"{s.name} (tier {s.tier}, {s.team})" for s in services
        )

    @server.resource(
        "incident://{incident_id}",
        name="incident_detail",
        description="One incident as JSON, by identifier.",
        mime_type="application/json",
    )
    async def incident_detail(
        ctx: Context, incident_id: int
    ) -> str:
        state = ctx.request_context.lifespan_context
        page = await state.db.incidents(None, "all", 100)
        for incident in page.incidents:
            if incident.id == incident_id:
                return incident.model_dump_json(indent=2)
        from mcp.server.mcpserver.exceptions import ResourceError

        raise ResourceError(
            f"No incident with identifier {incident_id}."
        )

    @server.resource(
        "service://{name}/runbook",
        name="service_runbook",
        description=(
            "The runbook for one service, from a jailed "
            "directory. Long files are truncated."
        ),
        mime_type="text/markdown",
    )
    def runbook(ctx: Context, name: str) -> str:
        state = ctx.request_context.lifespan_context
        text, truncated = state.runbooks.read(f"{name}.md")
        if truncated:
            text += "\n[truncated]"
        return text
