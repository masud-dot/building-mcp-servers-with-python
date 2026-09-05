"""The MCP server mounted beside ordinary routes."""

from mcp.server.transport_security import TransportSecuritySettings
from productivity.server import server
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route

security = TransportSecuritySettings(
    allowed_hosts=["127.0.0.1:8010", "mcp.internal"],
    allowed_origins=["https://app.example"],
)

mcp_app = server.streamable_http_app(
    streamable_http_path="/",
    json_response=True,
    transport_security=security,
)


async def health(request):
    return PlainTextResponse("ok")


async def version(request):
    return JSONResponse(
        {"service": "productivity", "version": "1.0.0"}
    )


app = Starlette(
    routes=[
        Route("/healthz", health),
        Route("/version", version),
        Mount("/mcp", app=mcp_app),
    ],
    # The MCP app owns a lifespan. A parent application must
    # hand it through, or the server's startup never runs.
    lifespan=lambda _: mcp_app.router.lifespan_context(mcp_app),
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8010, log_level="error")
