"""Fixtures. anyio's plugin, not pytest-asyncio. Chapter 19."""

from collections.abc import AsyncIterator

import pytest
from mcp import Client
from mcp_types import ElicitResult

from aiops.server import limiter, server

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def fresh_limiter():
    """The limiter is real. Without this, tests that spend
    tokens make later tests fail depending on order."""
    limiter._buckets.clear()
    yield
    limiter._buckets.clear()


@pytest.fixture
async def client() -> AsyncIterator[Client]:
    async with Client(server) as connected:
        yield connected


def answering(action: str, value: str | None = None):
    """A client-side elicitation callback."""

    async def callback(ctx, params):
        if value is None:
            return ElicitResult(action=action)
        return ElicitResult(
            action=action, content={"incident_id": value}
        )

    return callback

# --- test classification -------------------------------------------
# Tests that open the server lifespan need PostgreSQL, because the
# lifespan opens a connection pool. They are marked `integration`
# automatically so a reader without a database can run:
#
#     uv run pytest -m "not integration"
#
DB_FIXTURES = {"client", "era_client", "seeded"}


def pytest_collection_modifyitems(config, items):
    import pytest

    for item in items:
        if DB_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.integration)
