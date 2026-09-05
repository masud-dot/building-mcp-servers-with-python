"""Resource registration."""

from mcp.server.mcpserver import MCPServer

from aiops.resources import ops


def register(server: MCPServer, state_ref) -> None:
    ops.register(server, state_ref)
