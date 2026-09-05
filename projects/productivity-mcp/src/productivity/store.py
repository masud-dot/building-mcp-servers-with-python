"""Mutable state, owned by the server lifespan.

One Store is created when the server starts and discarded when
it stops. Nothing here outlives a server run, which is what
Chapter 11 explains.
"""

from mcp.server.mcpserver.exceptions import ResourceError, ToolError

from productivity.models import Note, Priority, Task


class Store:
    """Everything the server remembers while it is running."""

    def __init__(self) -> None:
        self.tasks: list[Task] = []
        self.notes: list[Note] = []
        self._next_task_id = 1
        self._next_note_id = 1

    def add_task(self, title: str, priority: Priority) -> Task:
        task = Task(
            id=self._next_task_id,
            title=title,
            priority=priority,
            status="open",
        )
        self.tasks.append(task)
        self._next_task_id += 1
        return task

    def add_note(self, body: str) -> Note:
        note = Note(id=self._next_note_id, body=body)
        self.notes.append(note)
        self._next_note_id += 1
        return note

    def find_task(self, task_id: int) -> Task:
        """Look up a task for a tool. Raises ToolError."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise ToolError(f"No task with identifier {task_id}.")

    def read_task(self, task_id: int) -> Task:
        """Look up a task for a resource. Raises ResourceError."""
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise ResourceError(f"No task with identifier {task_id}.")

    def read_note(self, note_id: int) -> Note:
        for note in self.notes:
            if note.id == note_id:
                return note
        raise ResourceError(f"No note with identifier {note_id}.")


# Static resources cannot receive a Context, so they need another
# route to the running store. The lifespan sets this on startup
# and clears it on shutdown, so its lifetime is still managed.
_active: Store | None = None


def set_active(store: Store | None) -> None:
    global _active
    _active = store


def active() -> Store:
    if _active is None:
        raise ResourceError("The server is not running.")
    return _active
