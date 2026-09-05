"""Fixtures for the QA automation server.

Nothing here reaches the network. The upstream is replaced by
a transport that returns whatever the test asks for, so an
outage is a fixture rather than an unplugged cable.
"""

from collections.abc import AsyncIterator, Callable
from pathlib import Path

import httpx2
import pytest

from mcp import Client
from mcp.server.mcpserver import MCPServer

from qaops import resources, tools
from qaops.config import Settings
from qaops.services.artifacts import ArtifactStore
from qaops.services.testruns import TestRunService

pytestmark = pytest.mark.anyio

RUNS = [
    {
        "id": 4101,
        "suite": "checkout",
        "status": "failed",
        "passed": 118,
        "failed": 3,
        "started_at": "2026-09-01T09:14:00Z",
    }
]
FAILURES = [
    {
        "test": "test_apply_discount_code",
        "message": "AssertionError: expected 4500, got 5000",
        "trace": "frame " * 500,
    }
]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings pointed at a temporary artefact root."""
    return Settings(
        base_url="http://upstream.test",
        artifact_root=tmp_path,
        max_artifact_bytes=1024,
        max_retries=1,
    )


def responding(handler: Callable) -> httpx2.MockTransport:
    """Wrap a handler as a transport the service can use."""
    return httpx2.MockTransport(handler)


def healthy(request: httpx2.Request) -> httpx2.Response:
    if request.url.path == "/runs":
        return httpx2.Response(200, json={"runs": RUNS})
    if request.url.path.endswith("/failures"):
        return httpx2.Response(200, json={"failures": FAILURES})
    return httpx2.Response(200, json=RUNS[0])


@pytest.fixture
def make_service(settings: Settings):
    """Build a service whose upstream behaves as the test says."""

    def build(handler: Callable) -> TestRunService:
        client = httpx2.AsyncClient(
            base_url=settings.base_url,
            transport=responding(handler),
            timeout=httpx2.Timeout(1.0),
        )
        return TestRunService(client, settings)

    return build


@pytest.fixture
async def client(
    settings: Settings, make_service
) -> AsyncIterator[Client]:
    """A server whose upstream is healthy."""
    service = make_service(healthy)

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(_server):
        yield service

    server = MCPServer(name="qa-test", lifespan=lifespan)
    tools.register(server)
    resources.register(
        server,
        ArtifactStore(
            settings.artifact_root, settings.max_artifact_bytes
        ),
    )
    async with Client(server) as connected:
        yield connected
