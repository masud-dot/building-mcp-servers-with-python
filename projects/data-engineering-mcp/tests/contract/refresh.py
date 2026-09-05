"""Rewrite the committed catalogue snapshot.

Run this only when a contract change is deliberate, then read
the diff before committing.
"""

import anyio

from tests.contract.test_catalogue import SNAPSHOT, live
from mcp import Client
from dataeng import server
import json


async def main() -> None:
    async with Client(server) as client:
        catalogue = await live(client)
    SNAPSHOT.write_text(
        json.dumps(catalogue, indent=2, sort_keys=True) + "\n"
    )
    print(f"wrote {len(catalogue)} tools to {SNAPSHOT}")


if __name__ == "__main__":
    anyio.run(main)
