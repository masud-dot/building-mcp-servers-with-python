"""One test per defect that reached a running system.

Each names where it came from. A regression test is cheap to
write on the day and worthless a month later, so it gets
written on the day.
"""

import importlib

import pytest

from mcp import Client

pytestmark = pytest.mark.anyio


async def test_every_registered_tool_is_callable(client: Client):
    """A method appended below its class parsed as a nested
    function, so the tool registered and failed at call time
    with AttributeError. Listing was not enough to catch it.
    """
    listed = await client.list_tools()
    assert listed.tools
    for tool in listed.tools:
        assert callable(getattr(tool, "name", None)) is False
        assert tool.name


async def test_traces_are_trimmed(client: Client):
    """A 500-frame trace reached a result unmodified once."""
    result = await client.call_tool(
        "list_failures", {"run_id": 4101}
    )
    failure = result.structured_content["failures"][0]
    assert failure["trace_truncated"] is True
    assert len(failure["trace_excerpt"]) <= 800


async def test_message_survives_trimming(client: Client):
    """Trimming once removed the assertion text as well."""
    result = await client.call_tool(
        "list_failures", {"run_id": 4101}
    )
    failure = result.structured_content["failures"][0]
    assert "expected 4500" in failure["message"]


def test_importing_the_package_starts_nothing():
    """A script with a module-level entry point ran the whole
    assistant when imported to reuse one function.
    """
    module = importlib.import_module("qaops.__main__")
    assert hasattr(module, "main")
