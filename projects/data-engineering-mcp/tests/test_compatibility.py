"""The same assertions, against both protocol eras.

One server serves handshake-era and modern clients. Chapter 4
showed that; these tests keep it true.
"""

import pytest

from mcp import Client

pytestmark = pytest.mark.anyio


async def test_negotiates_the_expected_era(era_client: Client):
    negotiated = str(era_client.protocol_version)
    assert negotiated in {"2026-07-28", "2025-11-25"}


async def test_catalogue_is_identical_across_eras(
    era_client: Client,
):
    listed = await era_client.list_tools()
    assert {t.name for t in listed.tools} == {
        "list_tables",
        "describe_table",
        "sample_table",
        "delete_pipeline_run",
        "start_quality_scan",
        "get_scan_result",
    }


async def test_tools_work_across_eras(era_client: Client):
    result = await era_client.call_tool("list_tables", {})
    assert result.is_error is False
    assert "analytics.orders" in result.structured_content["result"]


async def test_resources_work_across_eras(era_client: Client):
    contents = await era_client.read_resource(
        "schema://analytics.customers"
    )
    assert contents.contents[0].mime_type == "application/json"


async def test_refusals_hold_across_eras(era_client: Client):
    result = await era_client.call_tool(
        "sample_table", {"table": "analytics.api_credentials"}
    )
    assert result.is_error is True
    assert "not available" in result.content[0].text
