"""Server construction and lifespan."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.auth.settings import AuthSettings
from mcp.server.caching import CacheHint
from mcp.server.mcpserver import MCPServer
from pydantic import AnyHttpUrl
from psycopg_pool import AsyncConnectionPool

from dataeng import auth, resources, tools
from dataeng.config import Settings
from dataeng.db import Database
from dataeng.observability import MetricsMiddleware
from dataeng.ratelimit import RateLimiter
from dataeng.state import ScanStore

settings = Settings()


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[Database]:
    """Open the pool on startup, close it on shutdown."""
    pool = AsyncConnectionPool(
        settings.dsn.get_secret_value(),
        min_size=settings.pool_min,
        max_size=settings.pool_max,
        open=False,
    )
    writer_pool = AsyncConnectionPool(
        settings.writer_dsn.get_secret_value(),
        min_size=0,
        max_size=1,
        open=False,
    )
    # A short timeout so a missing database fails in
    # seconds with a clear error, rather than blocking
    # on the pool's default wait.
    await pool.open(wait=True, timeout=5.0)
    await writer_pool.open(wait=True, timeout=5.0)
    try:
        yield Database(pool, writer_pool, settings)
    finally:
        await writer_pool.close()
        await pool.close()


auth.configure(settings.auth_enabled)

_auth_settings = (
    AuthSettings(
        issuer_url=AnyHttpUrl(settings.auth_issuer),
        resource_server_url=AnyHttpUrl(settings.auth_audience),
        required_scopes=[auth.READ],
    )
    if settings.auth_enabled
    else None
)

_verifier = (
    auth.JWTVerifier(
        public_key=settings.auth_public_key,
        issuer=settings.auth_issuer,
        audience=settings.auth_audience,
    )
    if settings.auth_enabled
    else None
)

server = MCPServer(
    name="data-engineering",
    version="0.2.0",
    lifespan=lifespan,
    auth=_auth_settings,
    token_verifier=_verifier,
    # Outermost first: trace everything, including
    # requests the limiter refuses.
    middleware=[MetricsMiddleware(), RateLimiter()],
    cache_hints={
        # Catalogues change when the server is redeployed, and
        # are identical for every caller.
        "tools/list": CacheHint(ttl_ms=300_000, scope="public"),
        "prompts/list": CacheHint(ttl_ms=300_000, scope="public"),
        "server/discover": CacheHint(
            ttl_ms=300_000, scope="public"
        ),
        # The resource list is public too: it names tables, and
        # every caller sees the same three.
        "resources/list": CacheHint(
            ttl_ms=300_000, scope="public"
        ),
        "resources/templates/list": CacheHint(
            ttl_ms=300_000, scope="public"
        ),
        # Schemas change with migrations. Private, because a
        # future release may filter them by scope, and a public
        # entry would then outlive that decision.
        "resources/read": CacheHint(
            ttl_ms=60_000, scope="private"
        ),
    },
    instructions=(
        "Read-only access to a small set of warehouse tables. "
        "Call list_tables first, then describe_table, then "
        "sample_table. Nothing here can modify data."
    ),
)

tools.register(server)
resources.register(server)
