"""Exercise the QA tools against the stub, including failures."""

import anyio

from mcp import Client

from qaops import server


async def show(client, name, args):
    result = await client.call_tool(name, args)
    flag = "ERROR" if result.is_error else "ok   "
    print(f"  {flag} {name}{args}")
    body = (
        result.content[0].text
        if result.is_error
        else str(result.structured_content)
    )
    print(f"        {body[:96]}")


async def main() -> None:
    async with Client(server) as client:
        await show(client, "list_test_runs", {})
        await show(client, "get_test_run", {"run_id": 4101})
        await show(client, "list_failures", {"run_id": 4101})
        await show(client, "list_failures", {"run_id": 4102})
        await show(client, "get_test_run", {"run_id": 9999})


anyio.run(main)
