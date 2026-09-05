"""Prompt registration for the productivity server."""

from mcp.server.mcpserver import MCPServer

from productivity.prompts import review


def register(server: MCPServer) -> None:
    """Attach every prompt to the server."""
    review.register(server)
