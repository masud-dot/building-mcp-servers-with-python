"""Run the server. Chapter 25 adds the other transports."""

import sys

from dataeng import auth
from dataeng.server import server


def main() -> None:
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    if transport != "stdio" and not auth.enforcing():
        raise SystemExit(
            "Refusing to serve over HTTP without authentication. "
            "Set DATAENG_AUTH_ENABLED=true and supply "
            "DATAENG_AUTH_PUBLIC_KEY."
        )
    if transport == "stdio":
        server.run(transport="stdio")
    else:
        import os

        server.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=int(os.environ.get("DATAENG_PORT", "8000")),
        )


if __name__ == "__main__":
    main()
