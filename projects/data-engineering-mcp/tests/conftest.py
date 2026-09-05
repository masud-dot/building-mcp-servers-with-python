"""Fixtures for the data engineering server.

Two client fixtures. `client` connects with the default mode.
`era_client` is parametrised over both protocol eras, so a test
using it runs twice.
"""

from collections.abc import AsyncIterator

import pytest

from mcp import Client
from dataeng import server

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[Client]:
    async with Client(server) as connected:
        yield connected


@pytest.fixture(
    params=["auto", "legacy"], ids=["modern", "handshake"]
)
async def era_client(request) -> AsyncIterator[Client]:
    """One test, both protocol eras."""
    async with Client(server, mode=request.param) as connected:
        yield connected

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
