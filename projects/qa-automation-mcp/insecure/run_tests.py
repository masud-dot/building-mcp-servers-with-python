"""DELIBERATELY VULNERABLE. See README.md. Never imported.

Chapter 23 breaks each of these and then rebuilds them.
"""

import asyncio
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

server = MCPServer(name="qa-insecure")


@server.tool()
async def run_tests(
    target: Annotated[
        str, Field(description="Test file or directory to run.")
    ],
) -> str:
    """Run a test suite and return its output.

    VULNERABLE: `target` is interpolated into a shell string.
    """
    command = f"python -m pytest {target}"
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await process.communicate()
    return out.decode()[:2000]
