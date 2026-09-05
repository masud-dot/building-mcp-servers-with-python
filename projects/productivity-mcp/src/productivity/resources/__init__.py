"""Resource registration for the productivity server."""

from mcp.server.mcpserver import MCPServer

from productivity.resources import notes, tasks


def register(server: MCPServer) -> None:
    """Attach every resource to the server."""
    tasks.register(server)
    notes.register(server)
