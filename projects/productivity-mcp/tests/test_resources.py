"""Resources, templates, and the miss path."""

import json

import pytest

from mcp import Client
from mcp.shared.exceptions import MCPError

pytestmark = pytest.mark.anyio


async def test_fixed_and_templated_are_listed_separately(
    client: Client,
):
    fixed = await client.list_resources()
    templates = await client.list_resource_templates()
    assert {str(r.uri) for r in fixed.resources} == {
        "tasks://all",
        "notes://recent",
    }
    assert {t.uri_template for t in templates.resource_templates} == {
        "task://{task_id}",
        "note://{note_id}",
    }


async def test_template_serves_declared_mime_type(seeded: Client):
    result = await seeded.read_resource("task://1")
    assert result.contents[0].mime_type == "application/json"
    body = json.loads(result.contents[0].text)
    assert body["id"] == 1


async def test_static_resource_reads_lifespan_state(
    seeded: Client,
):
    result = await seeded.read_resource("tasks://all")
    assert "Ship it" in result.contents[0].text


async def test_reading_a_missing_resource_raises(client: Client):
    with pytest.raises(MCPError, match="No task with identifier"):
        await client.read_resource("task://99")


async def test_empty_store_reads_cleanly(client: Client):
    result = await client.read_resource("tasks://all")
    assert result.contents[0].text == "No tasks yet."
