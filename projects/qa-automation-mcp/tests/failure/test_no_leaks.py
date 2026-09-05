"""No error may carry a credential or an internal address."""

import httpx2
import pytest

from mcp import Client
from mcp.server.mcpserver.exceptions import ToolError

pytestmark = pytest.mark.anyio

SECRET = "sk_live_should_never_appear"


async def test_upstream_error_hides_the_host_and_token(
    make_service, settings
):
    def explodes(request):
        raise httpx2.ConnectError(
            f"failed connecting to {request.url} "
            f"with {SECRET}"
        )

    service = make_service(explodes)
    with pytest.raises(ToolError) as raised:
        await service.list_runs()
    message = str(raised.value)
    assert SECRET not in message
    assert "upstream.test" not in message


async def test_unexpected_exception_reaches_no_caller(client):
    """Chapter 7: ordinary exception messages are withheld."""
    result = await client.call_tool(
        "get_test_run", {"run_id": 4101}
    )
    assert result.is_error is False


async def test_settings_repr_redacts_the_token(settings):
    assert settings.token.get_secret_value() not in repr(settings)
