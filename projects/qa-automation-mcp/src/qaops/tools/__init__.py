"""Tool registration for the QA automation server."""

from mcp.server.mcpserver import MCPServer

from qaops.tools import runs


def register(server: MCPServer) -> None:
    runs.register(server)
