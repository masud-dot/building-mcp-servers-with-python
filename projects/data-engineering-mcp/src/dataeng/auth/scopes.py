"""The permissions this server understands.

Two scopes. Read covers everything that cannot change data;
write covers the one operation that can.
"""

from mcp.server.auth.middleware.auth_context import (
    get_access_token,
)
from mcp.server.mcpserver.exceptions import ToolError

READ = "warehouse:read"
WRITE = "warehouse:write"
ALL = frozenset({READ, WRITE})

# Set once at server construction. When there is no token
# verifier there is no identity, so there is nothing to check
# and require() cannot mean anything. Chapter 24 explains why
# that is honest rather than a loophole, and why an HTTP
# deployment refuses to start in this state.
_enforcing = False


def configure(enforcing: bool) -> None:
    """Called by server.py. Not by tools."""
    global _enforcing
    _enforcing = enforcing


def enforcing() -> bool:
    return _enforcing


def require(scope: str) -> None:
    """Refuse unless the caller's token carries `scope`.

    Called at the top of every tool. There is no decorator,
    deliberately: a decorator can be forgotten silently, and a
    missing call here is visible in the body.
    """
    if not _enforcing:
        return
    token = get_access_token()
    if token is None:
        raise ToolError(
            "This server requires authentication."
        )
    if scope not in token.scopes:
        raise ToolError(
            f"Your access does not include {scope!r}. "
            f"Granted: {', '.join(sorted(token.scopes)) or 'none'}."
        )


def caller() -> str:
    """Who is calling, for logs and audit."""
    token = get_access_token()
    if token is None:
        return "anonymous"
    return token.subject or token.client_id
