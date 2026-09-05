"""Writes, and work that outlives its request."""

from typing import Annotated

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.resolve import (
    CancelledElicitation,
    DeclinedElicitation,
    Elicit,
    ElicitationResult,
    Resolve,
)
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field

from aiops import auth
from aiops.models import Incident, ScanReport, ScanStarted

ACKNOWLEDGE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
)
STARTS_WORK = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
)
READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True
)


class AcknowledgeConfirmation(BaseModel):
    """What the user is asked before an incident changes."""

    incident_id: str = Field(
        description=(
            "Type the incident identifier again to confirm. "
            "Anything else cancels."
        )
    )


def confirm_acknowledge(
    incident_id: int,
) -> Elicit[AcknowledgeConfirmation]:
    """Resolved before the tool body runs. Chapter 18."""
    return Elicit(
        message=(
            f"Acknowledge incident {incident_id}? This records "
            "your name against it and pages nobody else."
        ),
        schema=AcknowledgeConfirmation,
    )


def register(server: MCPServer) -> None:
    @server.tool(annotations=ACKNOWLEDGE)
    async def acknowledge_incident(
        ctx: Context,
        incident_id: Annotated[
            int,
            Field(ge=1, description="Id from query_incidents."),
        ],
        approval: Annotated[
            ElicitationResult[AcknowledgeConfirmation],
            Resolve(confirm_acknowledge),
        ],
    ) -> Incident:
        """Acknowledge an incident, after confirmation.

        Records who acknowledged it. Acknowledging twice is
        not an error.
        """
        auth.require(auth.WRITE)
        if isinstance(approval, DeclinedElicitation):
            raise ToolError("Nothing changed: declined.")
        if isinstance(approval, CancelledElicitation):
            raise ToolError("Nothing changed: cancelled.")
        if approval.data.incident_id != str(incident_id):
            raise ToolError(
                "Nothing changed: the confirmation did not match."
            )
        state = ctx.request_context.lifespan_context
        return await state.db.acknowledge(
            incident_id, auth.caller()
        )

    @server.tool(annotations=STARTS_WORK)
    async def start_log_scan(
        ctx: Context,
        service: Annotated[
            str, Field(description="Name from list_services.")
        ],
    ) -> ScanStarted:
        """Start a log scan and return a handle.

        The scan outlives this call. Any instance of this
        server can answer get_scan_result.
        """
        auth.require(auth.READ)
        state = ctx.request_context.lifespan_context
        handle = await state.db.start_scan(service)

        async def work() -> None:
            await anyio.sleep(0.05)
            await state.db.finish_scan(handle, 42)

        state.background.start_soon(work)
        return ScanStarted(handle=handle, service=service)

    @server.tool(annotations=READ_ONLY)
    async def get_scan_result(
        ctx: Context,
        handle: Annotated[
            str,
            Field(
                min_length=8,
                max_length=64,
                description="Handle from start_log_scan.",
            ),
        ],
    ) -> ScanReport:
        """Retrieve a log scan by its handle."""
        auth.require(auth.READ)
        state = ctx.request_context.lifespan_context
        return await state.db.scan(handle)
