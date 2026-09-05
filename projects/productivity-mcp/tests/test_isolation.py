"""The property the whole suite depends on."""

import pytest

from mcp import Client
from productivity import server

pytestmark = pytest.mark.anyio


async def test_each_connection_gets_an_empty_store():
    """Chapter 11's lifespan is what makes tests independent.

    If this fails, every other test in the suite becomes
    order-dependent.
    """
    async with Client(server) as first:
        await first.call_tool("create_task", {"title": "leaky"})
        listed = await first.call_tool("list_tasks", {})
        assert listed.structured_content["total"] == 1

    async with Client(server) as second:
        listed = await second.call_tool("list_tasks", {})
        assert listed.structured_content["total"] == 0
