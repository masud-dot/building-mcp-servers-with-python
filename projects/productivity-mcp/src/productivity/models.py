"""Data models for the productivity server."""

from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["low", "normal", "high"]
Status = Literal["open", "done"]


class Task(BaseModel):
    """One task."""

    id: int = Field(description="Stable identifier for this task.")
    title: str = Field(description="What needs doing.")
    priority: Priority = Field(description="How urgent it is.")
    status: Status = Field(description="Open, or already done.")


class TaskPage(BaseModel):
    """A page of tasks, plus enough detail to request more."""

    tasks: list[Task] = Field(description="The tasks in this page.")
    returned: int = Field(description="How many tasks are here.")
    total: int = Field(description="How many matched in total.")
    next_offset: int | None = Field(
        default=None,
        description=(
            "Pass this back as offset for the next page. "
            "Null when this is the last page."
        ),
    )


class Note(BaseModel):
    """A short free-text note."""

    id: int = Field(description="Stable identifier for this note.")
    body: str = Field(description="The text of the note.")
