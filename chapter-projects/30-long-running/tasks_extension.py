"""Tasks, built on the extension framework.

`mcp` 2.1.1 ships every Tasks type in `mcp_types` and no
server-side helper: there is no `mcp.server.tasks` to import,
the way there is `mcp.server.apps`. So this is what building an
extension yourself looks like, and Chapter 29's four
contribution points are exactly the tools for it.

This is a teaching implementation. It stores tasks in memory,
which Chapter 26 established is wrong for anything behind a
load balancer; a real one persists them.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import anyio
from mcp.server.extension import Extension, MethodBinding
from mcp_types import (
    CancelTaskRequestParams,
    GetTaskRequestParams,
    Task,
    TaskStatus,
)

EXTENSION_ID = "io.modelcontextprotocol/tasks"
DEFAULT_TTL_MS = 3_600_000
POLL_INTERVAL_MS = 1_000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStore:
    """Tasks and the work behind them."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._results: dict[str, Any] = {}
        self._cancelled: set[str] = set()

    def create(self, task_id: str) -> Task:
        task = Task(
            taskId=task_id,
            status="working",
            createdAt=_now(),
            lastUpdatedAt=_now(),
            ttl=DEFAULT_TTL_MS,
            pollInterval=POLL_INTERVAL_MS,
        )
        self._tasks[task_id] = task
        return task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def cancelled(self, task_id: str) -> bool:
        return task_id in self._cancelled

    def cancel(self, task_id: str) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None or task.status != "working":
            return task
        self._cancelled.add(task_id)
        return self._settle(task_id, "cancelled", "Cancelled.")

    def finish(self, task_id: str, result: Any) -> None:
        self._results[task_id] = result
        self._settle(task_id, "completed", "Done.")

    def fail(self, task_id: str, reason: str) -> None:
        self._settle(task_id, "failed", reason)

    def result(self, task_id: str) -> Any:
        return self._results.get(task_id)

    def _settle(
        self, task_id: str, status: TaskStatus, message: str
    ) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        updated = task.model_copy(
            update={
                "status": status,
                "status_message": message,
                "last_updated_at": _now(),
            }
        )
        self._tasks[task_id] = updated
        return updated


class TasksExtension(Extension):
    """Serves tasks/get and tasks/cancel."""

    identifier = EXTENSION_ID

    def __init__(self, store: TaskStore) -> None:
        self._store = store

    def settings(self) -> dict[str, Any]:
        """Advertise what this implementation supports.

        No `list`: enumerating other callers' tasks needs the
        identity from Chapter 24, and without it the honest
        answer is not to offer it.
        """
        return {"cancel": True, "list": False}

    def methods(self) -> tuple[MethodBinding, ...]:
        # The runner calls handlers as (ctx, params), not the
        # (params, ctx) that intercept_tool_call uses.
        async def get_task(
            ctx, params: GetTaskRequestParams
        ) -> dict[str, Any]:
            task = self._store.get(params.task_id)
            if task is None:
                return {"error": "no such task"}
            return task.model_dump(by_alias=True, mode="json")

        async def cancel_task(
            ctx, params: CancelTaskRequestParams
        ) -> dict[str, Any]:
            task = self._store.cancel(params.task_id)
            if task is None:
                return {"error": "no such task"}
            return task.model_dump(by_alias=True, mode="json")

        return (
            MethodBinding(
                method="tasks/get",
                params_type=GetTaskRequestParams,
                handler=get_task,
                protocol_versions=None,
            ),
            MethodBinding(
                method="tasks/cancel",
                params_type=CancelTaskRequestParams,
                handler=cancel_task,
                protocol_versions=None,
            ),
        )


async def run_scan(
    store: TaskStore, task_id: str, steps: int
) -> None:
    """Pretend work that checks for cancellation between steps.

    Cancellation is cooperative: nothing interrupts a running
    step, so a step that takes a minute delays a cancel by up
    to a minute.
    """
    seen = 0
    for _ in range(steps):
        if store.cancelled(task_id):
            return
        await anyio.sleep(0.05)
        seen += 1
    store.finish(task_id, {"rows_seen": seen * 100})
