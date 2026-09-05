"""Server construction and lifespan."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer
from mcp_types import (
    Completion,
    PromptReference,
    ResourceTemplateReference,
)

from productivity import prompts, resources, store, tools
from productivity.store import Store


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[Store]:
    """Create state on startup, discard it on shutdown."""
    current = Store()
    store.set_active(current)
    try:
        yield current
    finally:
        store.set_active(None)


server = MCPServer(
    name="productivity",
    version="1.0.0",
    lifespan=lifespan,
    instructions=(
        "Tracks tasks and short notes. Create tasks with "
        "create_task and review them with list_tasks. Read "
        "task://{id} for one task and notes://recent for "
        "recent notes."
    ),
)

tools.register(server)
resources.register(server)
prompts.register(server)


@server.completion()
async def complete_argument(ref, argument, context):
    """Suggest values while a user fills in a template."""
    current = store.active()
    if isinstance(ref, PromptReference):
        if ref.name == "weekly_review" and argument.name == "focus":
            options = ["overdue", "high priority", "notes only"]
            hits = [
                o for o in options if o.startswith(argument.value)
            ]
            return Completion(values=hits, total=len(hits))
        return None
    if not isinstance(ref, ResourceTemplateReference):
        return None
    if ref.uri == "task://{task_id}":
        ids = [str(t.id) for t in current.tasks]
    elif ref.uri == "note://{note_id}":
        ids = [str(n.id) for n in current.notes]
    else:
        return None
    hits = [i for i in ids if i.startswith(argument.value)]
    return Completion(values=hits[:20], total=len(hits))
