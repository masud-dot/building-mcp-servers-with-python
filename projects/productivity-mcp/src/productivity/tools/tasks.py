"""Task and note tools."""

from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp_types import ToolAnnotations
from pydantic import Field

from productivity.models import Note, Priority, Task, TaskPage
from productivity.store import Store

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True
)
WRITES = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
)
IDEMPOTENT_WRITE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
)


def _store(ctx: Context) -> Store:
    """The store this request belongs to."""
    return ctx.request_context.lifespan_context


def register(server: MCPServer) -> None:
    @server.tool(annotations=WRITES)
    async def create_task(
        ctx: Context,
        title: Annotated[
            str,
            Field(
                min_length=1,
                max_length=200,
                description="What needs doing, as a short phrase.",
            ),
        ],
        priority: Annotated[
            Priority,
            Field(description="How urgent. Defaults to normal."),
        ] = "normal",
    ) -> Task:
        """Create a task and return it."""
        task = _store(ctx).add_task(title, priority)
        await ctx.notify_resources_changed()
        return task

    @server.tool(annotations=WRITES)
    async def bulk_create_tasks(
        ctx: Context,
        titles: Annotated[
            list[str],
            Field(
                min_length=1,
                max_length=50,
                description="One title per task, 1 to 50 of them.",
            ),
        ],
    ) -> TaskPage:
        """Create several tasks at once and return them.

        Reports progress as it goes, so a host can show how far
        through it has got.
        """
        store = _store(ctx)
        created: list[Task] = []
        total = len(titles)
        for index, title in enumerate(titles, start=1):
            created.append(store.add_task(title, "normal"))
            await ctx.report_progress(
                progress=index, total=total, message=title
            )
        await ctx.notify_resources_changed()
        return TaskPage(
            tasks=created,
            returned=len(created),
            total=len(created),
        )

    @server.tool(annotations=WRITES)
    async def create_note(
        ctx: Context,
        body: Annotated[
            str,
            Field(
                min_length=1,
                max_length=2000,
                description="The text of the note.",
            ),
        ],
    ) -> Note:
        """Record a short note and return it."""
        note = _store(ctx).add_note(body)
        await ctx.notify_resources_changed()
        return note

    @server.tool(annotations=READ_ONLY)
    def get_task(
        ctx: Context,
        task_id: Annotated[
            int,
            Field(
                ge=1,
                description="Identifier shown by list_tasks.",
            ),
        ],
    ) -> Task:
        """Return one task by its identifier."""
        return _store(ctx).find_task(task_id)

    @server.tool(annotations=READ_ONLY)
    def list_tasks(
        ctx: Context,
        status: Annotated[
            Literal["open", "done", "all"],
            Field(
                description=(
                    "Which tasks to return. Defaults to open."
                )
            ),
        ] = "open",
        limit: Annotated[
            int,
            Field(ge=1, le=50, description="Page size, 1 to 50."),
        ] = 20,
        offset: Annotated[
            int,
            Field(ge=0, description="How many to skip."),
        ] = 0,
    ) -> TaskPage:
        """List tasks, most recently created first."""
        store = _store(ctx)
        matched = [
            t for t in reversed(store.tasks)
            if status == "all" or t.status == status
        ]
        page = matched[offset : offset + limit]
        consumed = offset + len(page)
        return TaskPage(
            tasks=page,
            returned=len(page),
            total=len(matched),
            next_offset=(
                consumed if consumed < len(matched) else None
            ),
        )

    @server.tool(annotations=IDEMPOTENT_WRITE)
    async def complete_task(
        ctx: Context,
        task_id: Annotated[
            int,
            Field(
                ge=1,
                description=(
                    "Identifier shown by create_task or "
                    "list_tasks."
                ),
            ),
        ],
    ) -> Task:
        """Mark a task as done and return its new state.

        Completing an already-completed task is not an error.
        """
        task = _store(ctx).find_task(task_id)
        task.status = "done"
        await ctx.notify_resource_updated(f"task://{task_id}")
        return task
