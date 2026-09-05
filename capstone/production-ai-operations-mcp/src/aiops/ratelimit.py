"""Rate limiting, per caller and per method.

A token bucket refilled continuously. Cheap methods cost one
token; anything that touches the database costs more, because
the thing worth protecting is the database rather than the
request count.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from mcp.server.auth.middleware.auth_context import (
    get_access_token,
)
from mcp.shared.exceptions import MCPError
from mcp_types import INVALID_REQUEST

logger = logging.getLogger(__name__)

# Listing is cheap and cacheable. Sampling and profiling read
# rows. Deleting writes. The costs are a policy, not a fact.
COSTS: dict[str, int] = {
    "tools/call:query_incidents": 3,
    "tools/call:get_service_health": 5,
    "tools/call:run_diagnostic": 15,
    "tools/call:start_log_scan": 10,
    "tools/call:acknowledge_incident": 5,
}
DEFAULT_COST = 1


@dataclass
class Bucket:
    """One caller's allowance."""

    capacity: float
    refill_per_second: float
    tokens: float = field(init=False)
    updated: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = self.capacity
        self.updated = time.monotonic()

    def take(self, cost: float, now: float) -> bool:
        elapsed = now - self.updated
        self.updated = now
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_per_second,
        )
        if self.tokens < cost:
            return False
        self.tokens -= cost
        return True


class RateLimiter:
    """Server middleware: (ctx, call_next) -> result."""

    def __init__(
        self,
        capacity: float = 60,
        refill_per_second: float = 1.0,
        max_callers: int = 10_000,
    ) -> None:
        self._capacity = capacity
        self._refill = refill_per_second
        self._max_callers = max_callers
        self._buckets: dict[str, Bucket] = {}

    def _caller(self) -> str:
        """Identity when authenticated, otherwise one shared
        bucket. An unauthenticated deployment is local, and a
        single bucket is the honest answer there."""
        token = get_access_token()
        if token is None:
            return "anonymous"
        return token.subject or token.client_id

    def _cost(self, ctx) -> int:
        method = ctx.method or ""
        if method == "tools/call":
            name = (ctx.params or {}).get("name", "")
            return COSTS.get(f"tools/call:{name}", DEFAULT_COST)
        return COSTS.get(method, DEFAULT_COST)

    async def __call__(self, ctx, call_next):
        # Notifications carry no request id and get no answer,
        # so there is nothing useful to refuse them with.
        if ctx.request_id is None:
            return await call_next(ctx)

        caller = self._caller()
        bucket = self._buckets.get(caller)
        if bucket is None:
            if len(self._buckets) >= self._max_callers:
                # Bounded, so a flood of identities cannot
                # exhaust memory. Chapter 27 explains.
                self._buckets.clear()
            bucket = Bucket(self._capacity, self._refill)
            self._buckets[caller] = bucket

        cost = self._cost(ctx)
        if not bucket.take(cost, time.monotonic()):
            logger.warning(
                "rate limited %s on %s (cost %d)",
                caller,
                ctx.method,
                cost,
            )
            raise MCPError(
                code=INVALID_REQUEST,
                message=(
                    "Rate limit exceeded. Wait a few seconds "
                    "and try again."
                ),
            )
        return await call_next(ctx)
