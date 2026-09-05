"""Run it. HTTP requires authentication. Chapter 24."""

import sys

from aiops import auth
from aiops.server import server


def main() -> None:
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport != "stdio" and not auth.enforcing():
        raise SystemExit(
            "Refusing to serve over HTTP without "
            "authentication. Set AIOPS_AUTH_ENABLED=true and "
            "supply AIOPS_AUTH_PUBLIC_KEY."
        )
    if transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="streamable-http", host="127.0.0.1")


if __name__ == "__main__":
    main()
