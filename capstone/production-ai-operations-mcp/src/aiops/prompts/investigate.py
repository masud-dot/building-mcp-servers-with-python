"""User-selected workflows. Chapter 10."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.prompts.base import (
    AssistantMessage,
    Message,
    UserMessage,
)
from pydantic import Field


async def _read(ctx: Context, uri: str) -> str:
    parts = list(await ctx.read_resource(uri))
    return str(parts[0].content) if parts else ""


def register(server: MCPServer) -> None:
    @server.prompt(
        title="Investigate incident",
        description=(
            "Walk through an incident investigation. Loads the "
            "service catalogue and the incident, then asks for "
            "a structured assessment. Choose this rather than "
            "asking freely when you want the same shape every "
            "time."
        ),
    )
    async def investigate_incident(
        ctx: Context,
        incident_id: Annotated[
            str,
            Field(
                description=(
                    "The incident to investigate, as shown by "
                    "query_incidents, for example 1."
                )
            ),
        ],
    ) -> list[Message]:
        """Structured incident investigation."""
        catalogue = await _read(ctx, "catalogue://services")
        detail = await _read(ctx, f"incident://{incident_id}")
        return [
            UserMessage(f"Incident {incident_id} is open."),
            UserMessage(f"Services:\n{catalogue}"),
            UserMessage(f"Incident:\n{detail}"),
            AssistantMessage(
                "I have the incident and the catalogue."
            ),
            UserMessage(
                "Assess it in four parts: what is affected, "
                "what changed recently, what to check first, "
                "and whether to acknowledge. Use "
                "get_service_health and "
                "get_deployment_history before answering."
            ),
        ]

    @server.prompt(
        title="Postmortem draft",
        description=(
            "Draft a postmortem for a resolved incident, from "
            "its record and the deployments around it."
        ),
    )
    async def postmortem_draft(
        ctx: Context,
        incident_id: Annotated[
            str, Field(description="The incident, for example 1.")
        ],
    ) -> list[Message]:
        """Draft a postmortem."""
        detail = await _read(ctx, f"incident://{incident_id}")
        return [
            UserMessage(f"Incident:\n{detail}"),
            UserMessage(
                "Draft a postmortem: summary, timeline, impact, "
                "root cause if known, and follow-up actions. "
                "Mark anything you are inferring."
            ),
        ]
