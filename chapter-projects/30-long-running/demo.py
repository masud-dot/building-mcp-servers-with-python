"""Run all three approaches and compare what a caller sees."""

import anyio
from mcp import Client
from mcp_types import (
    CancelTaskRequest,
    CancelTaskRequestParams,
    GetTaskRequest,
    GetTaskRequestParams,
)
from pydantic import TypeAdapter

from compare import server


async def main() -> None:
    async with Client(server) as client:
        # 1. progress: blocks, reports as it goes
        seen: list[int] = []

        async def on_progress(progress, total, message):
            seen.append(int(progress))

        result = await client.call_tool(
            "scan_with_progress",
            {"steps": 4},
            progress_callback=on_progress,
        )
        print(f"  progress  -> {result.content[0].text}")
        print(f"               reported {seen}")

        # 2. handle: returns immediately, poll a tool
        started = await client.call_tool(
            "scan_by_handle", {"steps": 4}
        )
        handle = started.structured_content["handle"]
        print(f"  handle    -> {handle}")
        for _ in range(20):
            got = await client.call_tool(
                "get_by_handle", {"handle": handle}
            )
            if got.structured_content["status"] == "complete":
                break
            await anyio.sleep(0.02)
        print(f"               {got.structured_content}")

        # 3. task: returns immediately, poll tasks/get
        started = await client.call_tool(
            "scan_as_task", {"steps": 4}
        )
        task_id = started.structured_content["taskId"]
        print(f"  task      -> {task_id}")
        for _ in range(20):
            # The high-level Client has no generic request
            # method; an extension's own method goes through
            # the session.
            # A typed request. A plain Request built with a
            # dict for params serialises params as {} and the
            # server reports a missing field.
            task = await client.session.send_request(
                GetTaskRequest(
                    params=GetTaskRequestParams(taskId=task_id)
                ),
                TypeAdapter(dict),
            )
            if task.get("status") != "working":
                break
            await anyio.sleep(0.02)
        print(f"               status={task['status']} "
              f"poll={task['pollInterval']}ms")

        # cancellation
        started = await client.call_tool(
            "scan_as_task", {"steps": 200}
        )
        long_id = started.structured_content["taskId"]
        cancelled = await client.session.send_request(
            CancelTaskRequest(
                params=CancelTaskRequestParams(taskId=long_id)
            ),
            TypeAdapter(dict),
        )
        print(f"  cancelled -> status={cancelled['status']}")


anyio.run(main)
