"""Connect to any MCP server and describe what it offers.

Four ways to name a target:

    python cli.py object productivity:server
    python cli.py stdio -- uv run python -m productivity
    python cli.py url http://127.0.0.1:8000/mcp
    python cli.py object productivity:server --call list_tasks

The first three are the connection forms Client accepts. The
fourth argument shape, a custom Transport, is covered in the
chapter and needs no command-line form.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys

import anyio
from mcp import Client, StdioServerParameters


def build_target(args: argparse.Namespace):
    """Turn command-line arguments into something Client accepts."""
    if args.kind == "url":
        return args.target
    if args.kind == "stdio":
        command, *rest = args.command
        return StdioServerParameters(command=command, args=rest)
    module_name, _, attribute = args.target.partition(":")
    module = importlib.import_module(module_name)
    return getattr(module, attribute or "server")


async def describe(client: Client) -> None:
    info = client.server_info
    print(f"server            {info.name} {info.version}")
    print(f"protocol          {client.protocol_version}")

    capabilities = client.server_capabilities
    if capabilities is not None:
        offered = [
            name
            for name in (
                "tools", "resources", "prompts", "completions"
            )
            if getattr(capabilities, name, None) is not None
        ]
        print(f"capabilities      {', '.join(offered) or 'none'}")

    if client.instructions:
        first = client.instructions.split(". ")[0]
        print(f"instructions      {first}.")

    tools = await client.list_tools()
    print(f"\ntools ({len(tools.tools)})")
    for tool in tools.tools:
        summary = (tool.description or "").splitlines()[0]
        print(f"  {tool.name:22} {summary[:44]}")

    resources = await client.list_resources()
    templates = await client.list_resource_templates()
    total = len(resources.resources) + len(
        templates.resource_templates
    )
    print(f"\nresources ({total})")
    for resource in resources.resources:
        print(f"  {str(resource.uri):22} fixed")
    for template in templates.resource_templates:
        print(f"  {template.uri_template:22} template")

    prompts = await client.list_prompts()
    print(f"\nprompts ({len(prompts.prompts)})")
    for prompt in prompts.prompts:
        required = [
            a.name for a in (prompt.arguments or []) if a.required
        ]
        needs = f"requires {', '.join(required)}" if required else ""
        print(f"  {prompt.name:22} {needs}")


async def run(args: argparse.Namespace) -> int:
    target = build_target(args)
    async with Client(target, mode=args.mode) as client:
        await describe(client)
        if args.call:
            arguments = json.loads(args.arguments)
            result = await client.call_tool(args.call, arguments)
            print(f"\ncall {args.call}")
            print(f"  is_error  {result.is_error}")
            print(f"  content   {result.content[0].text[:60]}")
            if result.structured_content is not None:
                body = json.dumps(result.structured_content)
                print(f"  structured {body[:60]}")
    return 0


def main() -> int:
    # Split on the first `--` ourselves. argparse.REMAINDER
    # interacts badly with optional arguments and would swallow
    # --mode and --call into the server command.
    argv = sys.argv[1:]
    command: list[str] = []
    if "--" in argv:
        index = argv.index("--")
        argv, command = argv[:index], argv[index + 1 :]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["object", "stdio", "url"])
    parser.add_argument("target", nargs="?", default="")
    parser.add_argument("--mode", default="auto")
    parser.add_argument("--call", default=None)
    parser.add_argument("--arguments", default="{}")
    args = parser.parse_args(argv)
    args.command = command

    if args.kind == "stdio" and not args.command:
        parser.error("stdio needs a command after --")
    if args.kind in {"object", "url"} and not args.target:
        parser.error(f"{args.kind} needs a target")

    try:
        return anyio.run(run, args)
    except Exception as exc:
        print(f"failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
