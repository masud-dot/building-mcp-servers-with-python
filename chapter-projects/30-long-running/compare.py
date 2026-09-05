"""Three ways to handle work that takes a while.

Progress notifications, an explicit handle, and the Tasks
extension. The same scan, three interfaces, so the trade-offs
are visible side by side.
"""

from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import anyio
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

from tasks_extension import TaskStore, TasksExtension, run_scan

store = TaskStore()
tasks = TasksExtension(store)


@dataclass
class Background:
    """Somewhere for work that outlives its request to live.

    The SDK gives a handler no task group of its own, so one is
    opened in the lifespan. Chapter 11 established that this is
    where things needing startup and shutdown belong.
    """

    group: anyio.abc.TaskGroup
    handles: dict[str, dict] = field(default_factory=dict)


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[Background]:
    async with anyio.create_task_group() as group:
        yield Background(group=group)
        # Cancel anything still running, so shutdown does not
        # wait on work nobody is coming back for.
        group.cancel_scope.cancel()


server = MCPServer(
    name="long-running", extensions=[tasks], lifespan=lifespan
)


def _bg(ctx: Context) -> Background:
    return ctx.request_context.lifespan_context


@server.tool()
async def scan_with_progress(ctx: Context, steps: int) -> str:
    """Short work. Reports progress and blocks until done."""
    for index in range(steps):
        await anyio.sleep(0.02)
        await ctx.report_progress(
            progress=index + 1, total=steps, message="scanning"
        )
    return f"scanned {steps * 100} rows"


@server.tool()
async def scan_by_handle(
    ctx: Context, steps: int
) -> dict[str, str]:
    """Medium work. Returns a handle; poll get_by_handle.

    Note the parameterised return type. A bare `dict` produces
    no output schema and no structured content at all.
    """
    background = _bg(ctx)
    handle = secrets.token_urlsafe(8)
    background.handles[handle] = {"status": "working"}

    async def work() -> None:
        await anyio.sleep(0.02 * steps)
        background.handles[handle] = {
            "status": "complete",
            "rows": str(steps * 100),
        }

    background.group.start_soon(work)
    return {"handle": handle, "poll": "get_by_handle"}


@server.tool()
def get_by_handle(
    ctx: Context, handle: str
) -> dict[str, str]:
    """Retrieve work started by scan_by_handle."""
    return _bg(ctx).handles.get(handle, {"status": "unknown"})


@server.tool()
async def scan_as_task(
    ctx: Context, steps: int
) -> dict[str, str]:
    """Long work. Poll with the extension's tasks/get.

    The tool cannot declare `execution.task_support`: the field
    exists in mcp_types.Tool, and MCPServer.add_tool has no
    parameter for it in 2.1.1. A client discovers task support
    from the extension capability instead.
    """
    task_id = secrets.token_urlsafe(8)
    store.create(task_id)
    _bg(ctx).group.start_soon(run_scan, store, task_id, steps)
    return {"taskId": task_id, "poll": "tasks/get"}
