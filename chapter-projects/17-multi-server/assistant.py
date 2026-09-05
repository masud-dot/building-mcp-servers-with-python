"""Connect several MCP servers and drive them from one loop.

Run it:

    uv run python assistant.py

Each server runs in its own environment, as a subprocess, which
is how a desktop host does it. A server that fails to start is
reported and skipped; the rest still work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import anyio
from mcp import StdioServerParameters
from mcp.client.session_group import ClientSessionGroup
from mcp_types import Implementation, Tool


@dataclass(frozen=True)
class ServerSpec:
    """One server this assistant knows how to launch."""

    label: str
    command: str
    args: list[str]


SERVERS = [
    ServerSpec(
        "productivity",
        "/home/claude/p1c11/.venv/bin/python",
        ["-m", "productivity"],
    ),
    ServerSpec(
        "warehouse",
        "/home/claude/p2/.venv/bin/python",
        ["-m", "dataeng"],
    ),
    ServerSpec(
        "qa",
        "/home/claude/p3/.venv/bin/python",
        ["-m", "qaops"],
    ),
    ServerSpec("broken", "/nonexistent/python", ["-m", "nothing"]),
]


def namespaced(name: str, server_info: Implementation) -> str:
    """Prefix every component with the server that offered it.

    Without this, two servers offering `list_tables` cannot be
    connected to the same group at all.
    """
    return f"{server_info.name}.{name}"


def to_model_format(name: str, tool: Tool) -> dict[str, Any]:
    """Map one MCP tool onto the shape a model API expects.

    Most vendors accept this shape or something within a rename
    of it: a name, a description, and a JSON Schema.
    """
    return {
        "type": "function",
        "function": {
            "name": name.replace(".", "__"),
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


async def connect_all(
    group: ClientSessionGroup, specs: list[ServerSpec]
) -> list[str]:
    """Connect each server, reporting rather than raising."""
    failures = []
    for spec in specs:
        params = StdioServerParameters(
            command=spec.command, args=spec.args
        )
        try:
            await group.connect_to_server(params)
        except Exception as exc:
            failures.append(f"{spec.label}: {type(exc).__name__}")
    return failures


def choose(question: str, catalogue: list[dict]) -> dict | None:
    """Stand in for the model.

    A real assistant sends `question` and `catalogue` to a model
    API and receives a tool call back. The mapping either side
    of that call is the part this chapter is about, so the
    choice here is scripted to keep the example runnable.
    """
    wanted = {
        "what tables can you read": "data-engineering__list_tables",
        "what tests failed": "qa-automation__list_test_runs",
        "add a task": "productivity__create_task",
    }
    for phrase, tool_name in wanted.items():
        if phrase in question.lower():
            for entry in catalogue:
                if entry["function"]["name"] == tool_name:
                    return entry
    return None


async def main() -> None:
    async with ClientSessionGroup(
        component_name_hook=namespaced
    ) as group:
        failures = await connect_all(group, SERVERS)
        for failure in failures:
            print(f"unavailable  {failure}")

        catalogue = [
            to_model_format(name, tool)
            for name, tool in sorted(group.tools.items())
        ]
        print(f"connected    {len(group.sessions)} servers")
        print(f"tools        {len(catalogue)} in the catalogue")
        for entry in catalogue[:4]:
            print(f"  {entry['function']['name']}")
        print("  ...")

        for question in [
            "what tables can you read",
            "what tests failed",
        ]:
            chosen = choose(question, catalogue)
            if chosen is None:
                print(f"\n{question!r} -> no tool matched")
                continue
            mcp_name = chosen["function"]["name"].replace("__", ".")
            result = await group.call_tool(mcp_name, {})
            body = json.dumps(result.structured_content)
            print(f"\n{question!r}")
            print(f"  tool     {mcp_name}")
            print(f"  is_error {result.is_error}")
            print(f"  result   {body[:66]}")


if __name__ == "__main__":
    anyio.run(main)
