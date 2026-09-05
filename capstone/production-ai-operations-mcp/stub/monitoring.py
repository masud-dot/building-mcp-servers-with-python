"""A stand-in monitoring API, so the capstone runs offline."""

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

TOKEN = "stub-token"
HEALTH = {
    "checkout": {"status": "degraded", "error_rate": 0.07,
                 "p95_ms": 2400},
    "search": {"status": "healthy", "error_rate": 0.001,
               "p95_ms": 180},
    "billing": {"status": "healthy", "error_rate": 0.002,
                "p95_ms": 240},
}


async def health(request):
    if request.headers.get("authorization") != f"Bearer {TOKEN}":
        return JSONResponse({"error": "unauthorised"},
                            status_code=401)
    name = request.path_params["service"]
    if name not in HEALTH:
        return JSONResponse({"error": "not found"},
                            status_code=404)
    return JSONResponse({"service": name, **HEALTH[name]})


app = Starlette(
    routes=[Route("/health/{service}", health)]
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8955,
                log_level="error")
