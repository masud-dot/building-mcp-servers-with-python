"""A minimal productivity server: one tool, one resource, one prompt."""

from mcp.server.mcpserver import MCPServer

server = MCPServer(
    name="productivity",
    version="0.1.0",
    instructions=(
        "Tracks a short list of tasks. Use create_task to add one, "
        "and read tasks://all to see the current list."
    ),
)

# Temporary storage. Chapter 11 explains why this is a bug.
_tasks: list[str] = []


@server.tool()
def create_task(title: str) -> str:
    """Add a task to the list and return a confirmation."""
    _tasks.append(title)
    return f"Added task: {title}"


@server.resource("tasks://all")
def all_tasks() -> str:
    """The current task list, one per line."""
    if not _tasks:
        return "No tasks yet."
    return "\n".join(f"- {t}" for t in _tasks)


@server.prompt()
def summarise_tasks() -> str:
    """Ask for a short summary of the outstanding tasks."""
    return (
        "Read the tasks://all resource and summarise what is "
        "outstanding in two or three sentences."
    )


if __name__ == "__main__":
    server.run(transport="stdio")
