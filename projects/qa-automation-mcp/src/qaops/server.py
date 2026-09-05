"""Server construction and lifespan."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx2
from mcp.server.mcpserver import MCPServer

from qaops import resources, tools
from qaops.config import Settings, warn_unknown_env
from qaops.services.artifacts import ArtifactStore
from qaops.services.testruns import TestRunService

logger = logging.getLogger(__name__)

settings = Settings()

for unknown in warn_unknown_env():
    logger.warning("ignoring unknown setting %s", unknown)


@asynccontextmanager
async def lifespan(
    server: MCPServer,
) -> AsyncIterator[TestRunService]:
    """One HTTP client for the server's whole life."""
    async with httpx2.AsyncClient(
        base_url=settings.base_url,
        headers={
            "Authorization": (
                f"Bearer {settings.token.get_secret_value()}"
            )
        },
        timeout=httpx2.Timeout(
            connect=settings.connect_timeout,
            read=settings.read_timeout,
            write=settings.read_timeout,
            pool=settings.connect_timeout,
        ),
        limits=httpx2.Limits(max_connections=10),
        follow_redirects=False,
    ) as client:
        yield TestRunService(client, settings)


server = MCPServer(
    name="qa-automation",
    version="0.1.0",
    lifespan=lifespan,
    instructions=(
        "Read-only access to test runs and their failures. "
        "Call list_test_runs first, then list_failures with a "
        "run identifier. Nothing here starts or changes a run."
    ),
)

tools.register(server)
resources.register(
    server,
    ArtifactStore(
        settings.artifact_root, settings.max_artifact_bytes
    ),
)
