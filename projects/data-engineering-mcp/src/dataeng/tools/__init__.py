"""Tool registration for the data engineering server."""

from mcp.server.mcpserver import MCPServer

from dataeng.tools import pipelines, quality, warehouse


def register(server: MCPServer) -> None:
    warehouse.register(server)
    pipelines.register(server)
    quality.register(server)
