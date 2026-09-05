"""Prompt registration."""

from mcp.server.mcpserver import MCPServer

from aiops.prompts import investigate


def register(server: MCPServer) -> None:
    investigate.register(server)
