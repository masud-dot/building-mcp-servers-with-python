"""Note resources: the recent list, and one note by identifier."""

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

from productivity import store
from productivity.config import Settings

RECENT_LIMIT = Settings().recent_notes


def register(server: MCPServer) -> None:
    @server.resource(
        "notes://recent",
        name="recent_notes",
        description=(
            f"The {RECENT_LIMIT} most recent notes, newest first."
        ),
        mime_type="text/plain",
    )
    def recent_notes() -> str:
        current = store.active()
        recent = list(reversed(current.notes))[:RECENT_LIMIT]
        if not recent:
            return "No notes yet."
        return "\n".join(f"{n.id}. {n.body}" for n in recent)

    @server.resource(
        "note://{note_id}",
        name="note_detail",
        description="One note as JSON, by identifier.",
        mime_type="application/json",
    )
    def note_detail(ctx: Context, note_id: int) -> str:
        current = ctx.request_context.lifespan_context
        return current.read_note(note_id).model_dump_json(indent=2)
