"""An MCP Apps UI that degrades to text.

SEP-1865, extension id io.modelcontextprotocol/ui. A host that
negotiated the extension renders the HTML; one that did not
gets the same information as prose.
"""

from __future__ import annotations

import anyio
from mcp import Client
from mcp.client.extension import advertise
from mcp.server.apps import (
    APP_MIME_TYPE,
    Apps,
    client_supports_apps,
)
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

TASKS = [
    {"id": 1, "title": "Write chapter 29", "status": "open"},
    {"id": 2, "title": "Review extensions", "status": "done"},
]

BOARD_HTML = """<!doctype html>
<meta charset="utf-8">
<style>
 body { font: 14px system-ui; margin: 0; padding: 12px; }
 li { margin: 4px 0; }
 .done { opacity: .5; text-decoration: line-through; }
</style>
<h3>Tasks</h3>
<ul id="items"></ul>
<script>
  // App-initiated tool calls travel the ordinary tools/call
  // path, so the host applies the same consent it always does.
  const data = JSON.parse(
    document.currentScript.dataset.tasks || "[]");
  document.getElementById("items").innerHTML = data
    .map(t => `<li class="${t.status}">${t.title}</li>`)
    .join("");
</script>
"""

apps = Apps()
apps.add_html_resource(
    "ui://productivity/board",
    BOARD_HTML,
    name="task_board",
    title="Task board",
    description="The current tasks, rendered.",
)



# The extension's tools are collected when the server is
# constructed, so everything must be registered on the
# extension first. Decorating after construction registers a
# tool nobody ever sees.
@apps.tool(
    resource_uri="ui://productivity/board",
    visibility=["model", "app"],
)
def show_board(ctx: Context) -> str:
    """Show the current tasks.

    Renders a board in hosts that support MCP Apps, and
    returns the same information as text in hosts that do not.
    """
    if client_supports_apps(ctx):
        # The host will render ui://productivity/board. The
        # text is still returned, because the model reads it.
        return "Rendered the task board."
    return "\n".join(
        f"{t['id']}. {t['title']} ({t['status']})" for t in TASKS
    )


server = MCPServer(name="productivity-ui", extensions=[apps])


async def main() -> None:
    # Advertising the identifier is not enough. A host must
    # also list the MIME types it can render, which is how a
    # server knows the UI will really be shown.
    renders = advertise(
        Apps.identifier, {"mimeTypes": [APP_MIME_TYPE]}
    )
    for label, extensions in (
        ("renders apps", [renders]),
        ("advertises only", [advertise(Apps.identifier, {})]),
        ("no extension", None),
    ):
        async with Client(server, extensions=extensions) as client:
            result = await client.call_tool("show_board", {})
            first = result.content[0].text.splitlines()[0]
            print(f"  {label:20} -> {first}")


if __name__ == "__main__":
    anyio.run(main)
