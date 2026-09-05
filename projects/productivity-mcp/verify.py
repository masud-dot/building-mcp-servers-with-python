"""Exercise the server, including lifespan isolation."""

import anyio

from mcp import Client

from productivity import server


async def main() -> None:
    async with Client(server) as client:
        seen: list[tuple[float, float | None, str | None]] = []

        async def on_progress(progress, total, message):
            seen.append((progress, total, message))

        await client.call_tool(
            "bulk_create_tasks",
            {"titles": ["Restructure", "Add lifespan", "Verify"]},
            progress_callback=on_progress,
        )
        print("progress  :", seen)

        listed = await client.call_tool("list_tasks", {})
        print("total     :", listed.structured_content["total"])

        detail = await client.read_resource("task://2")
        print("task://2  :", detail.contents[0].mime_type)

        static = await client.read_resource("tasks://all")
        print("static    :", static.contents[0].text.splitlines()[0])

    # A second connection gets a brand new store.
    async with Client(server) as client:
        again = await client.call_tool("list_tasks", {})
        print("after new connection, total:",
              again.structured_content["total"])


anyio.run(main)
