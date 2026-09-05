"""DELIBERATELY VULNERABLE. See README.md. Never imported."""

from typing import Annotated

import httpx2
from mcp.server.mcpserver import MCPServer
from pydantic import Field

server = MCPServer(name="ssrf-insecure")


@server.tool()
async def check_endpoint(
    url: Annotated[
        str, Field(description="Endpoint to probe.")
    ],
) -> str:
    """Fetch a URL and report what came back.

    VULNERABLE: the caller chooses the host, and redirects are
    followed.
    """
    async with httpx2.AsyncClient(follow_redirects=True) as c:
        response = await c.get(url, timeout=5.0)
        return f"{response.status_code} {response.text[:200]}"
