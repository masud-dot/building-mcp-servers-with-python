"""A round-robin balancer, for demonstrating statelessness.

Not a production load balancer. It exists to prove one thing:
consecutive requests from one client land on different server
instances and everything still works.

    python scripts/roundrobin.py 8100 8101 8102 8103
"""

from __future__ import annotations

import itertools
import sys

import httpx2
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

BACKENDS: list[str] = []
_next = itertools.cycle([0])


async def proxy(request: Request) -> Response:
    index = next(_next)
    backend = BACKENDS[index]
    body = await request.body()
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }
    async with httpx2.AsyncClient(timeout=30.0) as client:
        upstream = await client.post(
            f"{backend}{request.url.path}",
            content=body,
            headers=headers,
        )
    out = dict(upstream.headers)
    out.pop("content-length", None)
    out.pop("content-encoding", None)
    # So the demonstration can show where each request went.
    out["X-Served-By"] = backend
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=out,
    )


app = Starlette(routes=[Route("/mcp", proxy, methods=["POST"])])


def main() -> None:
    global _next
    port = int(sys.argv[1])
    BACKENDS.extend(f"http://127.0.0.1:{p}" for p in sys.argv[2:])
    _next = itertools.cycle(range(len(BACKENDS)))
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")


if __name__ == "__main__":
    main()
