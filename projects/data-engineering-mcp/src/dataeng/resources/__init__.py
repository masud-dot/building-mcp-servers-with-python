"""Resource registration for the data engineering server."""

from mcp.server.mcpserver import MCPServer

from dataeng.resources import schema


def register(server: MCPServer) -> None:
    schema.register(server)
