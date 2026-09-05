"""Prompts, arguments and completion."""

import pytest

from mcp import Client
from mcp_types import PromptReference

pytestmark = pytest.mark.anyio


async def test_prompt_arguments_are_advertised(client: Client):
    listed = await client.list_prompts()
    review = next(
        p for p in listed.prompts if p.name == "weekly_review"
    )
    required = {a.name for a in review.arguments if a.required}
    assert required == {"week"}


async def test_weekly_review_assembles_live_context(
    seeded: Client,
):
    result = await seeded.get_prompt(
        "weekly_review", {"week": "2026-W36"}
    )
    bodies = [m.content.text for m in result.messages]
    assert any("2026-W36" in b for b in bodies)
    assert any("Ship it" in b for b in bodies)
    assert result.messages[-1].role == "user"


async def test_completion_filters_on_the_typed_prefix(
    client: Client,
):
    suggestions = await client.complete(
        PromptReference(type="ref/prompt", name="weekly_review"),
        {"name": "focus", "value": "h"},
    )
    assert suggestions.completion.values == ["high priority"]
