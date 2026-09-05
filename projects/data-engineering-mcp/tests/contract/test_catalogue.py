"""The published surface, defended against accidental change.

The snapshot in snapshots/catalogue.json is committed. A
change to any tool's name, description, schema or annotations
fails these tests, which forces the change to be a decision
rather than a side effect.

To accept a deliberate change:

    uv run python tests/contract/refresh.py

then read the diff before committing it.
"""

import json
import pathlib

import pytest

from mcp import Client

pytestmark = pytest.mark.anyio

SNAPSHOT = (
    pathlib.Path(__file__).parent / "snapshots" / "catalogue.json"
)


def committed() -> dict:
    return json.loads(SNAPSHOT.read_text())


async def live(client: Client) -> dict:
    listed = await client.list_tools()
    return {
        tool.name: {
            "description": tool.description,
            "input_schema": tool.input_schema,
            "output_schema": tool.output_schema,
            "annotations": (
                tool.annotations.model_dump(
                    by_alias=True, exclude_none=True
                )
                if tool.annotations
                else None
            ),
        }
        for tool in listed.tools
    }


async def test_no_tool_appeared_or_vanished(client: Client):
    assert set(await live(client)) == set(committed())


async def test_every_tool_matches_its_snapshot(client: Client):
    current = await live(client)
    expected = committed()
    for name in sorted(expected):
        assert current[name] == expected[name], (
            f"{name} has drifted from its committed contract"
        )


async def test_required_parameters_did_not_grow(client: Client):
    """Adding a required parameter breaks existing callers."""
    current = await live(client)
    for name, expected in committed().items():
        was = set(expected["input_schema"].get("required", []))
        now = set(current[name]["input_schema"].get("required", []))
        assert now <= was, (
            f"{name} now requires {sorted(now - was)}, "
            "which existing callers do not send"
        )


async def test_every_tool_has_a_description(client: Client):
    """Chapter 6: an empty description is silent and useless."""
    for name, entry in (await live(client)).items():
        assert entry["description"], f"{name} has no description"
