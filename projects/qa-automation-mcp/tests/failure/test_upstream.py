"""What the caller is told when the upstream misbehaves."""

import httpx2
import pytest

from mcp.server.mcpserver.exceptions import ToolError

pytestmark = pytest.mark.anyio


async def test_timeout_becomes_a_useful_message(make_service):
    def times_out(request):
        raise httpx2.TimeoutException("too slow")

    service = make_service(times_out)
    with pytest.raises(ToolError, match="did not respond in time"):
        await service.list_runs()


async def test_connection_failure_is_translated(make_service):
    def refuses(request):
        raise httpx2.ConnectError("no route")

    service = make_service(refuses)
    with pytest.raises(ToolError, match="could not be reached"):
        await service.list_runs()


async def test_rate_limit_reports_the_wait(make_service):
    def throttled(request):
        return httpx2.Response(
            429, json={}, headers={"Retry-After": "30"}
        )

    service = make_service(throttled)
    with pytest.raises(ToolError, match="Wait 30 seconds"):
        await service.list_runs()


async def test_not_found_uses_domain_language(make_service):
    def missing(request):
        return httpx2.Response(404, json={})

    service = make_service(missing)
    with pytest.raises(ToolError, match="No such test run"):
        await service.get_run(9999)


async def test_server_error_is_retried_then_reported(
    make_service,
):
    attempts = {"n": 0}

    def flaky(request):
        attempts["n"] += 1
        return httpx2.Response(503, json={})

    service = make_service(flaky)
    with pytest.raises(ToolError, match="returned an error"):
        await service.list_runs()
    assert attempts["n"] == 2, "one retry, per max_retries=1"


async def test_client_error_is_not_retried(make_service):
    attempts = {"n": 0}

    def bad_request(request):
        attempts["n"] += 1
        return httpx2.Response(400, json={})

    service = make_service(bad_request)
    with pytest.raises(ToolError):
        await service.list_runs()
    assert attempts["n"] == 1, "4xx must not be retried"
