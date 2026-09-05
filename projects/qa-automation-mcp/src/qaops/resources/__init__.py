"""Resource registration for the QA automation server."""

from mcp.server.mcpserver import MCPServer

from qaops.resources import artifacts
from qaops.services.artifacts import ArtifactStore


def register(server: MCPServer, store: ArtifactStore) -> None:
    artifacts.register(server, store)
