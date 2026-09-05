"""The one destructive tool, behind a typed confirmation."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.resolve import (
    CancelledElicitation,
    DeclinedElicitation,
    Elicit,
    ElicitationResult,
    Resolve,
)
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field

from dataeng import auth
from dataeng.db import Database
from dataeng.models import DeletedRun

DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
)


class DeleteConfirmation(BaseModel):
    """What the user is asked before anything is removed."""

    run_id: str = Field(
        description=(
            "Type the run identifier again to confirm. "
            "Anything else cancels the deletion."
        )
    )


def confirm_deletion(run_id: int) -> Elicit[DeleteConfirmation]:
    """Ask before the tool body runs.

    The framework calls this while resolving the tool's
    parameters. If the answer is not already recorded for this
    call, it returns an input_required result instead of
    running the body.
    """
    return Elicit(
        message=(
            f"Permanently delete pipeline run {run_id}? "
            "This cannot be undone."
        ),
        schema=DeleteConfirmation,
    )


def register(server: MCPServer) -> None:
    @server.tool(annotations=DESTRUCTIVE)
    async def delete_pipeline_run(
        ctx: Context,
        run_id: Annotated[
            int,
            Field(ge=1, description="Identifier of the run."),
        ],
        approval: Annotated[
            ElicitationResult[DeleteConfirmation],
            Resolve(confirm_deletion),
        ],
    ) -> DeletedRun:
        """Delete one pipeline run, after confirmation.

        The user is asked to retype the identifier. Nothing is
        removed unless they do. Only pipeline runs can be
        deleted; no other table is reachable.
        """
        auth.require(auth.WRITE)
        if isinstance(approval, DeclinedElicitation):
            raise_declined("declined")
        if isinstance(approval, CancelledElicitation):
            raise_declined("cancelled")
        if approval.data.run_id != str(run_id):
            raise_declined("the confirmation did not match")
        database: Database = ctx.request_context.lifespan_context
        return await database.delete_pipeline_run(run_id)


def raise_declined(reason: str) -> None:
    from mcp.server.mcpserver.exceptions import ToolError

    raise ToolError(f"Nothing was deleted: {reason}.")
