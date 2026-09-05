"""Two scopes. Read investigates; write changes an incident."""

from mcp.server.auth.middleware.auth_context import (
    get_access_token,
)
from mcp.server.mcpserver.exceptions import ToolError

READ = "ops:read"
WRITE = "ops:write"

_enforcing = False


def configure(enforcing_now: bool) -> None:
    global _enforcing
    _enforcing = enforcing_now


def enforcing() -> bool:
    return _enforcing


def require(scope: str) -> None:
    """Called at the top of every tool, visibly."""
    if not _enforcing:
        return
    token = get_access_token()
    if token is None:
        raise ToolError("This server requires authentication.")
    if scope not in token.scopes:
        raise ToolError(
            f"Your access does not include {scope!r}. "
            f"Granted: {', '.join(sorted(token.scopes)) or 'none'}."
        )


def caller() -> str:
    """Who is asking. Recorded on writes."""
    token = get_access_token()
    if token is None:
        return "anonymous"
    return token.subject or token.client_id
