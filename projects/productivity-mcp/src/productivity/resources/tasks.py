"""Task resources: the whole list, and one task by identifier."""

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

from productivity import store


def register(server: MCPServer) -> None:
    @server.resource(
        "tasks://all",
        name="all_tasks",
        description="Every task, newest first, as plain text.",
        mime_type="text/plain",
    )
    def all_tasks() -> str:
        # Static resources get no Context, so they reach the
        # running store through the lifespan-managed accessor.
        current = store.active()
        if not current.tasks:
            return "No tasks yet."
        return "\n".join(
            f"{t.id}. [{t.priority}] {t.title} ({t.status})"
            for t in reversed(current.tasks)
        )

    @server.resource(
        "task://{task_id}",
        name="task_detail",
        description=(
            "One task as JSON. The identifier is the number "
            "shown by list_tasks."
        ),
        mime_type="application/json",
    )
    def task_detail(ctx: Context, task_id: int) -> str:
        current = ctx.request_context.lifespan_context
        return current.read_task(task_id).model_dump_json(indent=2)
