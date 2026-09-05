"""Tool registration for the productivity server."""

from mcp.server.mcpserver import MCPServer

from productivity.tools import tasks


def register(server: MCPServer) -> None:
    """Attach every tool to the server."""
    tasks.register(server)
