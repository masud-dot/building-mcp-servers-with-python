"""Choosing and configuring a transport.

One entry point, two transports. The choice is an operator's,
made on the command line, and nothing above this module knows
which was taken.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HttpOptions:
    """Everything the HTTP transport needs."""

    host: str = "127.0.0.1"
    port: int = 8000
    path: str = "/mcp"
    json_response: bool = False
    allowed_hosts: tuple[str, ...] = ()
    allowed_origins: tuple[str, ...] = ()


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="productivity")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio for a desktop host, http for a service.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--path", default="/mcp")
    parser.add_argument(
        "--json-response",
        action="store_true",
        help="Answer with one JSON body instead of a stream.",
    )
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        metavar="HOST:PORT",
        help="Repeatable. Required for --transport http.",
    )
    parser.add_argument(
        "--allow-origin",
        action="append",
        default=[],
        metavar="ORIGIN",
        help="Repeatable. Required for --transport http.",
    )
    return parser.parse_args(argv)


def serve(server: MCPServer, args: argparse.Namespace) -> None:
    """Run the server on the transport the operator chose."""
    if args.transport == "stdio":
        # Diagnostics must not reach stdout: it is the protocol.
        logging.basicConfig(stream=sys.stderr, level=logging.INFO)
        server.run(transport="stdio")
        return

    if not args.allow_host or not args.allow_origin:
        raise SystemExit(
            "HTTP needs --allow-host and --allow-origin. "
            "Leaving them open would disable the transport's "
            "DNS-rebinding protection."
        )

    logging.basicConfig(level=logging.INFO)
    logger.warning(
        "This server has no authentication. Chapter 24 adds it. "
        "Do not expose this beyond localhost."
    )
    security = TransportSecuritySettings(
        allowed_hosts=list(args.allow_host),
        allowed_origins=list(args.allow_origin),
    )
    # host and port are transport arguments, not server
    # settings: run() forwards its kwargs to the transport.
    server.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
        json_response=args.json_response,
        transport_security=security,
    )
