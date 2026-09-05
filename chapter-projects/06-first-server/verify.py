"""Call the server in memory, without a host or a transport."""

import anyio

from mcp import Client

from server import server


async def main() -> None:
    async with Client(server) as client:
        tools = await client.list_tools()
        print("tools:", [t.name for t in tools.tools])

        result = await client.call_tool(
            "create_task", {"title": "Write chapter 6"}
        )
        print("is_error:", result.is_error)
        print("text:", result.content[0].text)

        resource = await client.read_resource("tasks://all")
        print("resource:", resource.contents[0].text)

        prompt = await client.get_prompt("summarise_tasks")
        print("prompt role:", prompt.messages[0].role)


anyio.run(main)
