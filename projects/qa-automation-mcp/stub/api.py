"""A stand-in test-management API.

Real enough to exercise every failure path in Chapter 13, and
small enough to read. Run it with:

    uv run python stub/api.py
"""

import asyncio
import time

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

TOKEN = "stub-token"
_calls: dict[str, int] = {}

RUNS = [
    {
        "id": 4101,
        "suite": "checkout",
        "status": "failed",
        "passed": 118,
        "failed": 3,
        "started_at": "2026-09-01T09:14:00Z",
    },
    {
        "id": 4102,
        "suite": "search",
        "status": "passed",
        "passed": 64,
        "failed": 0,
        "started_at": "2026-09-01T10:02:00Z",
    },
]

FAILURES = {
    4101: [
        {
            "test": "test_apply_discount_code",
            "message": "AssertionError: expected 4500, got 5000",
            "trace": "long stack trace " * 400,
        },
        {
            "test": "test_guest_checkout",
            "message": "TimeoutError: locator not visible",
            "trace": "long stack trace " * 400,
        },
    ],
    4102: [],
}


def _auth_ok(request) -> bool:
    header = request.headers.get("authorization", "")
    return header == f"Bearer {TOKEN}"


async def list_runs(request):
    if not _auth_ok(request):
        return JSONResponse(
            {"error": "unauthorised"}, status_code=401
        )
    return JSONResponse({"runs": RUNS})


async def get_run(request):
    if not _auth_ok(request):
        return JSONResponse(
            {"error": "unauthorised"}, status_code=401
        )
    run_id = int(request.path_params["run_id"])
    for run in RUNS:
        if run["id"] == run_id:
            return JSONResponse(run)
    return JSONResponse({"error": "not found"}, status_code=404)


async def get_failures(request):
    if not _auth_ok(request):
        return JSONResponse(
            {"error": "unauthorised"}, status_code=401
        )
    run_id = int(request.path_params["run_id"])
    if run_id not in FAILURES:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse({"failures": FAILURES[run_id]})


async def flaky(request):
    """Fails twice, then succeeds. For the retry section."""
    key = request.client.host if request.client else "x"
    _calls[key] = _calls.get(key, 0) + 1
    if _calls[key] % 3 != 0:
        return JSONResponse({"error": "upstream"}, status_code=503)
    return JSONResponse({"ok": True, "attempts": _calls[key]})


async def slow(request):
    await asyncio.sleep(5)
    return JSONResponse({"ok": True})


async def redirect_inward(request):
    """A permitted host that redirects somewhere else."""
    return JSONResponse(
        {}, status_code=302,
        headers={"Location": "http://127.0.0.1:8944/creds"},
    )


async def throttled(request):
    return JSONResponse(
        {"error": "too many requests"},
        status_code=429,
        headers={"Retry-After": "30"},
    )


app = Starlette(
    routes=[
        Route("/runs", list_runs),
        Route("/runs/{run_id:int}", get_run),
        Route("/runs/{run_id:int}/failures", get_failures),
        Route("/flaky", flaky),
        Route("/slow", slow),
        Route("/throttled", throttled),
        Route("/redirect", redirect_inward),
    ]
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="127.0.0.1", port=8931, log_level="warning"
    )
