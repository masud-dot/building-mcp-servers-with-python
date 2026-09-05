"""Tool registration."""

from mcp.server.mcpserver import MCPServer

from aiops.tools import incidents, investigate


def register(server: MCPServer) -> None:
    investigate.register(server)
    incidents.register(server)
