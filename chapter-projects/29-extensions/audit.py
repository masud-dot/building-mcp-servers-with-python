"""A small extension, using all four contribution points.

Not a real audit system. It exists to show the shape: an
identifier, advertised settings, a tool, a resource, a new
method, and an interceptor.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from mcp.server.extension import (
    Extension,
    MethodBinding,
    ResourceBinding,
    ToolBinding,
)
from mcp_types import Resource
from pydantic import BaseModel


class AuditQuery(BaseModel):
    """Params for the extension's own request method."""

    tool: str | None = None


class AuditExtension(Extension):
    """Counts tool calls and exposes the tally three ways."""

    # Reverse-DNS, and validated at subclass definition time.
    identifier = "com.example/audit"

    def __init__(self) -> None:
        self._calls: Counter[str] = Counter()

    def settings(self) -> dict[str, Any]:
        """Advertised at capabilities.extensions[identifier]."""
        return {"version": "1", "counts": "per-tool"}

    async def intercept_tool_call(self, params, ctx, call_next):
        """Wrap every tools/call. Observe, do not change."""
        self._calls[params.name] += 1
        return await call_next(ctx)

    def tools(self) -> tuple[ToolBinding, ...]:
        def audit_summary() -> dict[str, int]:
            """How many times each tool has been called."""
            return dict(self._calls)

        return (ToolBinding(fn=audit_summary, meta=None, kwargs={}),)

    def resources(self) -> tuple[ResourceBinding, ...]:
        return (
            ResourceBinding(
                resource=Resource(
                    uri="audit://summary",
                    name="audit_summary",
                    description="Tool call counts, as text.",
                    mimeType="text/plain",
                )
            ),
        )

    def methods(self) -> tuple[MethodBinding, ...]:
        async def handle(params: AuditQuery, ctx) -> dict[str, Any]:
            if params.tool:
                return {"tool": params.tool,
                        "calls": self._calls[params.tool]}
            return {"total": sum(self._calls.values())}

        return (
            MethodBinding(
                method="com.example/audit.query",
                params_type=AuditQuery,
                handler=handle,
                protocol_versions=None,
            ),
        )
