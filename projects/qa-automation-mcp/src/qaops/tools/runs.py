"""Read-only tools over the test-management API."""

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp_types import ToolAnnotations
from pydantic import Field

from qaops.models import FailureReport, TestRun
from qaops.services.testruns import TestRunService

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, open_world_hint=True
)


def _service(ctx: Context) -> TestRunService:
    return ctx.request_context.lifespan_context


def register(server: MCPServer) -> None:
    @server.tool(annotations=READ_ONLY)
    async def list_test_runs(ctx: Context) -> list[TestRun]:
        """List recent test runs, newest first.

        Returns run identifiers that get_test_run and
        list_failures accept.
        """
        return await _service(ctx).list_runs()

    @server.tool(annotations=READ_ONLY)
    async def get_test_run(
        ctx: Context,
        run_id: Annotated[
            int,
            Field(
                ge=1,
                description="Identifier from list_test_runs.",
            ),
        ],
    ) -> TestRun:
        """Return the summary of one test run."""
        return await _service(ctx).get_run(run_id)

    @server.tool(annotations=READ_ONLY)
    async def list_failures(
        ctx: Context,
        run_id: Annotated[
            int,
            Field(
                ge=1,
                description="Identifier from list_test_runs.",
            ),
        ],
    ) -> FailureReport:
        """Return the failing tests of one run.

        Stack traces are trimmed. When trace_truncated is true,
        the full trace is longer than what is shown here.
        """
        return await _service(ctx).failures(run_id)
