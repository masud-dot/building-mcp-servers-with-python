"""Construction, lifespan and everything wired together."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import anyio
import httpx2
from mcp.server.auth.settings import AuthSettings
from mcp.server.caching import CacheHint
from mcp.server.mcpserver import MCPServer
from psycopg_pool import AsyncConnectionPool
from pydantic import AnyHttpUrl

from aiops import auth, prompts, resources, tools
from aiops.config import Settings, warn_unknown_env
from aiops.db import Database
from aiops.observability import MetricsMiddleware, configure_logging
from aiops.ratelimit import RateLimiter
from aiops.services.diagnostics import DiagnosticRunner
from aiops.services.monitoring import MonitoringService
from aiops.services.runbooks import RunbookStore

logger = logging.getLogger(__name__)
settings = Settings()
configure_logging()

for unknown in warn_unknown_env():
    logger.warning("ignoring unknown setting %s", unknown)

auth.configure(settings.auth_enabled)


@dataclass
class State:
    """Everything a handler reaches, built once at startup."""

    db: Database
    monitoring: MonitoringService
    diagnostics: DiagnosticRunner
    runbooks: RunbookStore
    background: anyio.abc.TaskGroup


# Static resources get no Context (Chapter 11), so they need
# another route to the running state. A stack rather than a
# single slot, because a test may connect twice at once and a
# nested lifespan closing would otherwise clear the outer
# one's state. Two *different* servers in one process would
# still need a per-server key.
_states: list[State] = []


def current_state() -> State:
    if not _states:
        raise RuntimeError("The server is not running.")
    return _states[-1]


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[State]:
    """Open everything, then close it in reverse."""
    pool = AsyncConnectionPool(
        settings.dsn.get_secret_value(),
        min_size=1,
        max_size=4,
        open=False,
    )
    writer = AsyncConnectionPool(
        settings.writer_dsn.get_secret_value(),
        min_size=0,
        max_size=1,
        open=False,
    )
    # A short timeout so a missing database fails in
    # seconds with a clear error, rather than blocking
    # on the pool's default wait.
    await pool.open(wait=True, timeout=5.0)
    await writer.open(wait=True, timeout=5.0)
    client = httpx2.AsyncClient(
        base_url=settings.monitoring_url,
        headers={
            "Authorization": (
                f"Bearer "
                f"{settings.monitoring_token.get_secret_value()}"
            )
        },
        timeout=httpx2.Timeout(
            connect=2.0, read=5.0, write=5.0, pool=2.0
        ),
        follow_redirects=False,
    )
    async with anyio.create_task_group() as background:
        state = State(
            db=Database(pool, writer, settings),
            monitoring=MonitoringService(client),
            diagnostics=DiagnosticRunner(
                settings.diagnostic_timeout_s
            ),
            runbooks=RunbookStore(
                settings.runbook_root, settings.max_runbook_bytes
            ),
            background=background,
        )
        _states.append(state)
        try:
            yield state
        finally:
            _states.remove(state)
            background.cancel_scope.cancel()
            await client.aclose()
            await writer.close()
            await pool.close()


_auth = (
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
        settings.auth_public_key,
        settings.auth_issuer,
        settings.auth_audience,
    )
    if settings.auth_enabled
    else None
)

# Held by name so tests can reset it. A limiter shared
# across a suite makes the suite order-dependent.
limiter = RateLimiter()

server = MCPServer(
    name="ai-operations",
    version="1.0.0",
    lifespan=lifespan,
    auth=_auth,
    token_verifier=_verifier,
    middleware=[MetricsMiddleware(), limiter],
    instructions=(
        "Investigate incidents. Call list_services first, then "
        "query_incidents. Use get_service_health and "
        "get_deployment_history to correlate. Only "
        "acknowledge_incident changes anything, and it asks "
        "for confirmation."
    ),
    cache_hints={
        # Identical for every caller and changes on deploy.
        "tools/list": CacheHint(ttl_ms=300_000, scope="public"),
        "prompts/list": CacheHint(ttl_ms=300_000, scope="public"),
        "server/discover": CacheHint(
            ttl_ms=300_000, scope="public"
        ),
        "resources/list": CacheHint(
            ttl_ms=300_000, scope="public"
        ),
        "resources/templates/list": CacheHint(
            ttl_ms=300_000, scope="public"
        ),
        # Private: incident detail may become caller-scoped,
        # and a public entry would outlive that decision.
        "resources/read": CacheHint(
            ttl_ms=30_000, scope="private"
        ),
    },
)

tools.register(server)
resources.register(server, current_state)
prompts.register(server)
