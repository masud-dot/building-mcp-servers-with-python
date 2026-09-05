"""Every tool, on its happy path and its failure paths."""

import pytest

from mcp import Client

pytestmark = pytest.mark.anyio


async def test_create_task_returns_the_task(client: Client):
    result = await client.call_tool(
        "create_task", {"title": "Write tests", "priority": "high"}
    )
    assert result.is_error is False
    assert result.structured_content == {
        "id": 1,
        "title": "Write tests",
        "priority": "high",
        "status": "open",
    }


async def test_create_task_rejects_an_empty_title(client: Client):
    result = await client.call_tool("create_task", {"title": ""})
    assert result.is_error is True
    assert "validation error" in result.content[0].text


async def test_list_tasks_paginates(seeded: Client):
    result = await seeded.call_tool("list_tasks", {"limit": 2})
    page = result.structured_content
    assert page["returned"] == 2
    assert page["total"] == 3
    assert page["next_offset"] == 2


async def test_list_tasks_last_page_has_no_next(seeded: Client):
    result = await seeded.call_tool(
        "list_tasks", {"limit": 2, "offset": 2}
    )
    assert result.structured_content["next_offset"] is None


async def test_complete_task_is_idempotent(seeded: Client):
    first = await seeded.call_tool("complete_task", {"task_id": 1})
    second = await seeded.call_tool("complete_task", {"task_id": 1})
    assert first.structured_content == second.structured_content
    assert first.structured_content["status"] == "done"


async def test_missing_task_reports_a_useful_message(
    client: Client,
):
    result = await client.call_tool("get_task", {"task_id": 99})
    assert result.is_error is True
    assert "No task with identifier 99" in result.content[0].text


@pytest.mark.parametrize(
    "arguments",
    [
        {"task_id": 0},
        {"task_id": -1},
        {},
        {"task_id": "not a number"},
    ],
)
async def test_get_task_rejects_bad_arguments(
    client: Client, arguments: dict
):
    result = await client.call_tool("get_task", arguments)
    assert result.is_error is True


async def test_bulk_create_reports_progress(client: Client):
    seen: list[tuple] = []

    async def on_progress(progress, total, message):
        seen.append((progress, total, message))

    await client.call_tool(
        "bulk_create_tasks",
        {"titles": ["one", "two", "three"]},
        progress_callback=on_progress,
    )
    assert [p for p, _, _ in seen] == [1, 2, 3]
    assert all(total == 3 for _, total, _ in seen)
