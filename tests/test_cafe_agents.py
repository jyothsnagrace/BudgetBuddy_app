"""Tests for Pet Community Cafe multi-agent orchestration."""

from __future__ import annotations

from pathlib import Path

from backend.cafe_agents import run_cafe_group_chat


def test_cafe_agents_multi_step_tool_and_quest(tmp_path: Path) -> None:
    """
    Validate the required milestone behaviors:
    1) Multi-step conversation happened.
    2) Tool orchestration happened (fetch_budget_data used).
    3) Task completion happened (quest output present).
    """
    memory_file = tmp_path / "cafe_memory.json"

    history = run_cafe_group_chat(
        user_id="integration_test_user",
        memory_path=str(memory_file),
        max_round=6,
    )

    # 1) Multi-step reasoning across multiple agents.
    assert len(history) >= 4, "Expected at least 4 messages in the cafe chat."
    speakers = {entry.get("speaker") for entry in history}
    assert len(speakers.intersection({"user_pet", "npc_pet_1", "npc_pet_2", "barista_planner"})) >= 3

    # 2) Tool orchestration was recorded.
    used_budget_tool = any(
        entry.get("meta", {}).get("tool") == "fetch_budget_data" for entry in history
    )
    assert used_budget_tool, "Expected barista planner to fetch budget data via tool orchestration."

    # 3) Final task completion includes a quest.
    assert history, "Chat history should not be empty."
    final_content = str(history[-1].get("content", ""))
    assert "quest" in final_content.lower(), "Expected final message to include a Cafe Budget Quest."
