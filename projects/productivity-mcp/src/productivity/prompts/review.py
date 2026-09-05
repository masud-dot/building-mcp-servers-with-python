"""User-selected review workflows."""

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
    """Read one resource and return its text."""
    parts = list(await ctx.read_resource(uri))
    return str(parts[0].content) if parts else ""


def register(server: MCPServer) -> None:
    @server.prompt(title="Summarise tasks")
    def summarise_tasks() -> str:
        """Ask for a short summary of the outstanding tasks."""
        return (
            "Read the tasks://all resource and summarise what "
            "is outstanding in two or three sentences."
        )

    @server.prompt(
        title="Weekly review",
        description=(
            "Walk through a weekly review of tasks and notes. "
            "Reads the current tasks and recent notes, then "
            "asks for a written review. Choose this rather "
            "than asking freely when you want the same "
            "structure every week."
        ),
    )
    async def weekly_review(
        ctx: Context,
        week: Annotated[
            str,
            Field(
                description=(
                    "The week being reviewed, as an ISO week "
                    "such as 2026-W36."
                )
            ),
        ],
        focus: Annotated[
            str,
            Field(
                description=(
                    "Optional area to emphasise, such as "
                    "'overdue' or 'high priority'. Leave "
                    "empty for a general review."
                )
            ),
        ] = "",
    ) -> list[Message]:
        """Walk through a weekly review of tasks and notes.

        Reads the current tasks and recent notes, then asks for
        a written review. Choose this rather than asking freely
        when you want the same structure every week.
        """
        tasks = await _read(ctx, "tasks://all")
        notes = await _read(ctx, "notes://recent")
        emphasis = focus or "no particular area"

        return [
            UserMessage(
                f"I am reviewing week {week}, emphasising "
                f"{emphasis}."
            ),
            UserMessage(f"Current tasks:\n{tasks}"),
            UserMessage(f"Recent notes:\n{notes}"),
            AssistantMessage(
                "I have the tasks and notes. I will write the "
                "review now."
            ),
            UserMessage(
                "Write the review in three parts: what closed "
                "this week, what is still open and why it "
                "matters, and the single thing to do first "
                "next week."
            ),
        ]
