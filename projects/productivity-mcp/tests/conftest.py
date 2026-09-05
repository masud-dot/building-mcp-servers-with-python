"""Fixtures shared by every test in this project.

The client connects straight to the server object, so there is
no subprocess and no socket. Each test gets a connection, and
because the lifespan builds a new Store per connection, each
test also gets empty data.
"""

from collections.abc import AsyncIterator

import pytest

from mcp import Client
from productivity import server

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    """One backend, so tests do not run twice."""
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[Client]:
    """A connected client, with a store of its own."""
    async with Client(server) as connected:
        yield connected


@pytest.fixture
async def seeded(client: Client) -> Client:
    """A client whose store already has three tasks."""
    for title in ("Write tests", "Read the schema", "Ship it"):
        await client.call_tool("create_task", {"title": title})
    return client
