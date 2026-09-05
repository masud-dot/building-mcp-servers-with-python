"""Health and readiness, which are different questions.

Liveness: is this process working? Restart it if not.
Readiness: should it receive traffic right now? Take it out of
rotation if not, without restarting it.

The distinction matters during a rolling deploy: readiness goes
false first, the balancer stops sending work, in-flight requests
finish, and only then does the process stop.
"""

from __future__ import annotations

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from dataeng.observability import METRICS

logger = logging.getLogger(__name__)

# Flipped to False on shutdown, before the server stops
# accepting. Nothing else writes it.
_accepting = True


def stop_accepting() -> None:
    _accepting = False  # noqa: F841
    globals()["_accepting"] = False
    logger.info("readiness withdrawn")


async def livez(request: Request) -> PlainTextResponse:
    """The process is running. Cheap and dependency-free."""
    return PlainTextResponse("ok")


async def readyz(request: Request) -> JSONResponse:
    """Ready only if we are accepting and the pool answers."""
    if not globals()["_accepting"]:
        return JSONResponse(
            {"ready": False, "reason": "draining"},
            status_code=503,
        )
    pool = request.app.state.pool
    try:
        async with pool.connection(timeout=1.0) as conn:
            await conn.execute("SELECT 1")
    except Exception:
        # The reason goes to the log, not the response: a
        # readiness probe is reachable from more places than
        # a tool call is.
        logger.exception("readiness check failed")
        return JSONResponse(
            {"ready": False, "reason": "dependency"},
            status_code=503,
        )
    return JSONResponse({"ready": True})


async def metrics(request: Request) -> JSONResponse:
    """Per-tool counts, error counts and percentiles."""
    return JSONResponse(METRICS.snapshot())
