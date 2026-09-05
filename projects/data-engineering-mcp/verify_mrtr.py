"""Exercise the confirmed destructive tool, every outcome."""

import anyio

from mcp import Client
from mcp_types import ElicitResult

from dataeng import server


def answering(action, value=None):
    """A client-side elicitation callback."""

    async def callback(ctx, params):
        if value is None:
            return ElicitResult(action=action)
        return ElicitResult(
            action=action, content={"run_id": value}
        )

    return callback


async def attempt(label, run_id, callback):
    try:
        async with Client(
            server, elicitation_callback=callback
        ) as client:
            result = await client.call_tool(
                "delete_pipeline_run", {"run_id": run_id}
            )
            body = (
                result.content[0].text
                if result.is_error
                else str(result.structured_content)
            )
            print(
                f"  {label:12} run={run_id} "
                f"error={result.is_error} {body[:40]}"
            )
    except Exception as exc:
        print(f"  {label:12} run={run_id} {type(exc).__name__}")


async def ids():
    async with Client(server) as client:
        result = await client.call_tool(
            "sample_table",
            {"table": "analytics.pipeline_runs", "limit": 50},
        )
        return [int(r[0]) for r in result.structured_content["rows"]]


async def main() -> None:
    before = await ids()
    print(f"  before: {before}")
    first, second = before[0], before[1]

    await attempt("declined", first, answering("decline"))
    await attempt("cancelled", first, answering("cancel"))
    await attempt("mismatch", first, answering("accept", "99999"))
    await attempt(
        "confirmed", first, answering("accept", str(first))
    )
    await attempt(
        "already gone", first, answering("accept", str(first))
    )
    await attempt("no callback", second, None)
    print(f"  after : {await ids()}")


anyio.run(main)
