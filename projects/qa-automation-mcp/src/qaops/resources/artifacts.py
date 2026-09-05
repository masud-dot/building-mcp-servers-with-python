"""Test artefacts and logs, served from a jailed directory."""

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

from qaops.services.artifacts import ArtifactStore


def register(server: MCPServer, store: ArtifactStore) -> None:
    @server.resource(
        "artifacts://all",
        name="artifact_index",
        description=(
            "Names of the test artefacts and logs available "
            "to read. Use one with artifact://{name}."
        ),
        mime_type="text/plain",
    )
    def artifact_index() -> str:
        names = store.list_names()
        if not names:
            return "No artefacts."
        return "\n".join(names)

    @server.resource(
        "artifact://{name}",
        name="artifact",
        description=(
            "The contents of one artefact, by the name shown "
            "in artifacts://all. Long files are truncated."
        ),
        mime_type="text/plain",
    )
    def artifact(ctx: Context, name: str) -> str:
        text, truncated = store.read_text(name)
        if truncated:
            text += "\n[truncated: file is longer than the cap]"
        return text
