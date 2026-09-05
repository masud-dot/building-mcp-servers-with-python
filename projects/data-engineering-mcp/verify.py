"""Exercise the warehouse tools, including refusals."""

import anyio

from mcp import Client

from dataeng import server


async def show(client, name, args):
    result = await client.call_tool(name, args)
    flag = "ERROR" if result.is_error else "ok   "
    print(f"  {flag} {name}{args}")
    if result.is_error:
        print(f"        {result.content[0].text[:88]}")
    else:
        print(f"        {str(result.structured_content)[:88]}")


async def main() -> None:
    async with Client(server) as client:
        await show(client, "list_tables", {})
        await show(
            client, "describe_table", {"table": "analytics.orders"}
        )
        await show(
            client,
            "sample_table",
            {"table": "analytics.orders", "limit": 2},
        )
        await show(
            client,
            "describe_table",
            {"table": "analytics.api_credentials"},
        )
        await show(
            client,
            "sample_table",
            {"table": "analytics.orders; DROP TABLE x --"},
        )
        await show(
            client,
            "sample_table",
            {"table": "analytics.orders", "limit": 999},
        )
        contents = await client.read_resource(
            "schema://analytics.customers"
        )
        first = contents.contents[0].text.splitlines()[1]
        print("  ok    schema://analytics.customers")
        print(f"        {first}")


anyio.run(main)
