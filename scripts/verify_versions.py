"""Verify the environment this book was written against.

Run this before Chapter 5 and again after any SDK upgrade:

    uv run python scripts/verify_versions.py

Every check prints PASS or FAIL. The script exits non-zero if any
check fails, so it works as a CI step as well as a manual one.

This is a tripwire, not a test suite. It answers one question:
"is the SDK on this machine the one the book was written for?"
The real tests live in each project's tests/ directory.
"""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version

from pydantic import BaseModel

EXPECTED_SDK = "2.1.1"
EXPECTED_PROTOCOL = "2026-07-28"
MINIMUM_PYTHON = (3, 10)

results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str) -> None:
    results.append((name, passed, detail))


def check_python() -> None:
    v = sys.version_info
    found = f"{v.major}.{v.minor}.{v.micro}"
    record("Python version", v[:2] >= MINIMUM_PYTHON, found)


def check_sdk_version() -> None:
    try:
        found = version("mcp")
    except PackageNotFoundError:
        record("mcp installed", False, "not installed")
        return
    record("mcp version", found == EXPECTED_SDK, found)


def check_fastmcp_is_gone() -> None:
    """The v1 import must fail. If it succeeds, this is mcp 1.x."""
    try:
        import mcp.server.fastmcp  # noqa: F401
    except ModuleNotFoundError:
        record("FastMCP removed", True, "import raises as expected")
    else:
        record("FastMCP removed", False, "mcp 1.x is installed")


def check_imports() -> None:
    try:
        from mcp import Client  # noqa: F401
        from mcp.server.mcpserver import MCPServer  # noqa: F401
    except ImportError as exc:
        record("Core imports", False, str(exc))
        return
    record("Core imports", True, "Client, MCPServer")


def check_protocol_version() -> None:
    """mcp 1.x has no mcp_types, so this must not assume it."""
    try:
        from mcp_types.version import LATEST_PROTOCOL_VERSION
    except ImportError:
        record("Protocol version", False, "mcp_types missing")
        return
    found = str(LATEST_PROTOCOL_VERSION)
    record("Protocol version", found == EXPECTED_PROTOCOL, found)


class Reading(BaseModel):
    """Kept at module level on purpose.

    This file uses `from __future__ import annotations`, so every
    annotation is a string the SDK resolves against module globals.
    A model defined inside a function is not in those globals, and
    registering the tool fails with InvalidSignature. Chapter 7
    covers this; the fix is to keep the model at module level.
    """

    label: str
    value: int


async def _round_trip() -> tuple[bool, str]:
    """Build a server, call it in memory, inspect the result."""
    from mcp import Client
    from mcp.server.mcpserver import MCPServer

    server = MCPServer(name="verify", version="0.1.0")

    @server.tool()
    def sample(label: str) -> Reading:
        """Return a fixed reading for the given label."""
        return Reading(label=label, value=42)

    async with Client(server) as client:
        negotiated = str(client.protocol_version)
        result = await client.call_tool("sample", {"label": "x"})

    if negotiated != EXPECTED_PROTOCOL:
        return False, f"negotiated {negotiated}"
    if hasattr(result, "isError"):
        return False, "camelCase fields present (mcp 1.x?)"
    if result.is_error:
        return False, "tool call returned an error"
    if result.structured_content != {"label": "x", "value": 42}:
        return False, f"unexpected: {result.structured_content}"
    return True, "call ok, structured output ok"


def check_round_trip() -> None:
    import anyio

    try:
        passed, detail = anyio.run(_round_trip)
    except Exception as exc:  # surfaced, never swallowed
        passed, detail = False, f"{type(exc).__name__}: {exc}"
    record("Live round trip", passed, detail)


def main() -> int:
    check_python()
    check_sdk_version()
    check_fastmcp_is_gone()
    check_imports()
    check_protocol_version()
    check_round_trip()

    width = max(len(name) for name, _, _ in results)
    for name, passed, detail in results:
        flag = "PASS" if passed else "FAIL"
        print(f"{flag}  {name:<{width}}  {detail}")

    failed = [name for name, passed, _ in results if not passed]
    if failed:
        print(f"\n{len(failed)} check(s) failed. The book's examples "
              f"assume mcp=={EXPECTED_SDK}.")
        return 1
    print("\nEnvironment matches the book.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
