"""Print the MCP traffic passing between a host and a server.

Sits between an MCP client and a stdio server, forwarding every
byte unchanged and writing an annotated copy to stderr. Point it
at any stdio MCP server, including ones you did not write:

    python scripts/inspect_wire.py -- python -m my_server
    python scripts/inspect_wire.py --summary -- uv run server.py

Everything after `--` is the command that launches the server.

To use it with a host, put this script where the server command
used to go in the host's configuration, with the real command
after `--`. The host talks to the proxy, the proxy talks to the
server, and the traffic appears on stderr.

Diagnostics go to stderr on purpose. Under stdio, stdout carries
the protocol, and a stray print there corrupts the stream.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

CLIENT_TO_SERVER = "-->"
SERVER_TO_CLIENT = "<--"


def summarise(message: dict[str, Any]) -> str:
    """One line describing a JSON-RPC message."""
    if "method" in message and "id" in message:
        return f"request  id={message['id']} {message['method']}"
    if "method" in message:
        return f"notify   {message['method']}"
    if "error" in message:
        err = message["error"]
        code = err.get("code")
        return f"error    id={message.get('id')} code={code}"
    if "result" in message:
        result = message["result"]
        kind = ""
        if isinstance(result, dict):
            kind = result.get("resultType", "")
        suffix = f" [{kind}]" if kind else ""
        return f"response id={message.get('id')}{suffix}"
    return "unrecognised message"


def log(direction: str, raw: bytes, full: bool) -> None:
    text = raw.decode("utf-8", errors="replace").rstrip()
    if not text:
        return
    try:
        message = json.loads(text)
    except json.JSONDecodeError:
        print(f"{direction} <non-JSON> {text}", file=sys.stderr)
        return
    print(f"{direction} {summarise(message)}", file=sys.stderr)
    if full:
        body = json.dumps(message, indent=2)
        for line in body.splitlines():
            print(f"    {line}", file=sys.stderr)
    sys.stderr.flush()


async def open_stdin() -> asyncio.StreamReader:
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader


async def pump(
    source: asyncio.StreamReader,
    sink: Any,
    direction: str,
    full: bool,
) -> None:
    """Forward newline-delimited JSON, logging each message."""
    while True:
        line = await source.readline()
        if not line:
            break
        log(direction, line, full)
        sink.write(line)
        if hasattr(sink, "drain"):
            await sink.drain()
        else:
            sink.flush()


async def relay_stderr(source: asyncio.StreamReader) -> None:
    """Pass the server's own diagnostics through untouched."""
    while True:
        line = await source.readline()
        if not line:
            break
        sys.stderr.buffer.write(line)
        sys.stderr.buffer.flush()


async def run(command: list[str], full: bool) -> int:
    child = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert child.stdin and child.stdout and child.stderr

    stdin = await open_stdin()
    tasks = [
        asyncio.create_task(
            pump(stdin, child.stdin, CLIENT_TO_SERVER, full)
        ),
        asyncio.create_task(
            pump(
                child.stdout,
                sys.stdout.buffer,
                SERVER_TO_CLIENT,
                full,
            )
        ),
        asyncio.create_task(relay_stderr(child.stderr)),
    ]
    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in tasks:
        task.cancel()
    if child.returncode is None:
        child.terminate()
    return await child.wait()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Log MCP traffic to and from a stdio server.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print one line per message instead of full bodies",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("give the server command after --")

    return asyncio.run(run(command, full=not args.summary))


if __name__ == "__main__":
    raise SystemExit(main())
