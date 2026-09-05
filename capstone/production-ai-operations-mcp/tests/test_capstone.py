"""One test per boundary this server relies on."""

import pytest
from mcp import Client
from mcp.shared.exceptions import MCPError

from aiops import auth, server
from aiops.services.diagnostics import DiagnosticRunner
from aiops.services.runbooks import RunbookStore
from tests.conftest import answering

pytestmark = pytest.mark.anyio


async def test_catalogue_is_the_entry_point(client: Client):
    result = await client.call_tool("list_services", {})
    names = {s["name"] for s in result.structured_content["result"]}
    assert names == {"billing", "checkout", "search"}


async def test_incidents_report_truncation(client: Client):
    result = await client.call_tool(
        "query_incidents", {"status": "all", "limit": 1}
    )
    page = result.structured_content
    assert page["returned"] == 1
    assert page["truncated"] is True


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (404, "No such service"),
        (401, "operator must check"),
        (500, "returned an error"),
    ],
)
async def test_monitoring_failures_are_translated(
    status: int, expected: str
):
    """Chapter 21: the upstream is injected, never reached.

    This suite runs with no network and no stub.
    """
    import httpx2
    from mcp.server.mcpserver.exceptions import ToolError

    from aiops.services.monitoring import MonitoringService

    def responder(request):
        return httpx2.Response(status, json={})

    service = MonitoringService(
        httpx2.AsyncClient(
            base_url="http://monitoring.test",
            transport=httpx2.MockTransport(responder),
        ),
        max_retries=0,
    )
    with pytest.raises(ToolError, match=expected):
        await service.health("checkout")


async def test_monitoring_timeout_is_translated():
    import httpx2
    from mcp.server.mcpserver.exceptions import ToolError

    from aiops.services.monitoring import MonitoringService

    def times_out(request):
        raise httpx2.TimeoutException("slow")

    service = MonitoringService(
        httpx2.AsyncClient(
            base_url="http://monitoring.test",
            transport=httpx2.MockTransport(times_out),
        ),
        max_retries=0,
    )
    with pytest.raises(ToolError, match="did not respond in time"):
        await service.health("checkout")


async def test_unknown_diagnostic_lists_the_real_ones(
    client: Client,
):
    result = await client.call_tool(
        "run_diagnostic", {"name": "; id"}
    )
    assert result.is_error is True
    assert "Available:" in result.content[0].text


async def test_command_injection_is_inexpressible():
    """No shell, and the name must be in the registry."""
    runner = DiagnosticRunner(timeout_s=5)
    assert "; id" not in runner.names
    assert set(runner.names) == {
        "disk-free",
        "dns-check",
        "python-version",
    }


def test_runbook_symlink_escape_is_refused(tmp_path):
    """Only safe_join catches this. Chapter 14."""
    (tmp_path / "ok.md").write_text("inside")
    outside = tmp_path.parent / "secret.md"
    outside.write_text("outside")
    (tmp_path / "escape.md").symlink_to(outside)
    store = RunbookStore(tmp_path, max_bytes=1024)
    assert store.names() == ["ok.md"]
    with pytest.raises(Exception):
        store.read("escape.md")


def test_runbook_refusal_hides_the_root(tmp_path):
    store = RunbookStore(tmp_path, max_bytes=1024)
    with pytest.raises(Exception) as raised:
        store.read("../secret.md")
    assert str(tmp_path) not in str(raised.value)


async def test_missing_resource_raises(client: Client):
    with pytest.raises(MCPError):
        await client.read_resource("incident://99999")


async def test_write_requires_confirmation(client: Client):
    """Declining changes nothing."""
    async with Client(
        server, elicitation_callback=answering("decline")
    ) as writer:
        result = await writer.call_tool(
            "acknowledge_incident", {"incident_id": 3}
        )
    assert result.is_error is True
    detail = await client.call_tool(
        "query_incidents", {"status": "all", "limit": 50}
    )
    third = [
        i
        for i in detail.structured_content["incidents"]
        if i["id"] == 3
    ][0]
    assert third["status"] == "open"


# Builds its own client rather than using the fixture, so the
# automatic marking in conftest cannot see it.
@pytest.mark.integration
async def test_mismatched_confirmation_changes_nothing():
    async with Client(
        server, elicitation_callback=answering("accept", "999")
    ) as writer:
        result = await writer.call_tool(
            "acknowledge_incident", {"incident_id": 3}
        )
    assert result.is_error is True
    assert "did not match" in result.content[0].text


async def test_scan_handle_round_trip(client: Client):
    started = await client.call_tool(
        "start_log_scan", {"service": "checkout"}
    )
    handle = started.structured_content["handle"]
    assert len(handle) >= 16
    result = await client.call_tool(
        "get_scan_result", {"handle": handle}
    )
    assert result.structured_content["service"] == "checkout"


async def test_unknown_handle_reveals_nothing(client: Client):
    result = await client.call_tool(
        "get_scan_result", {"handle": "not-a-real-handle"}
    )
    assert result.is_error is True
    assert "No scan with that handle" in result.content[0].text


def test_enforcement_is_off_by_default():
    """HTTP refuses to start in this state."""
    assert auth.enforcing() is False


async def test_prompt_assembles_live_context(client: Client):
    result = await client.get_prompt(
        "investigate_incident", {"incident_id": "1"}
    )
    bodies = [m.content.text for m in result.messages]
    assert any("checkout" in b for b in bodies)
    assert result.messages[-1].role == "user"
