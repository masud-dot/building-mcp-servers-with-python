"""Results must match the schema the server published.

Chapter 8 showed the SDK validates a return value against the
declared output schema. These tests assert it from outside,
using the schema the client actually received.
"""

import pytest
from jsonschema import Draft202012Validator

from mcp import Client

pytestmark = pytest.mark.anyio


async def schema_for(client: Client, name: str) -> dict:
    listed = await client.list_tools()
    tool = next(t for t in listed.tools if t.name == name)
    assert tool.output_schema is not None, (
        f"{name} declares no output schema"
    )
    return tool.output_schema


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("list_tables", {}),
        ("describe_table", {"table": "analytics.orders"}),
        (
            "sample_table",
            {"table": "analytics.orders", "limit": 2},
        ),
    ],
)
async def test_result_matches_declared_schema(
    client: Client, tool: str, arguments: dict
):
    schema = await schema_for(client, tool)
    result = await client.call_tool(tool, arguments)
    assert result.is_error is False
    assert result.structured_content is not None
    Draft202012Validator(schema).validate(result.structured_content)


async def test_declared_schemas_are_themselves_valid(
    client: Client,
):
    """A malformed schema breaks callers before any call."""
    listed = await client.list_tools()
    for tool in listed.tools:
        Draft202012Validator.check_schema(tool.input_schema)
        if tool.output_schema is not None:
            Draft202012Validator.check_schema(tool.output_schema)
