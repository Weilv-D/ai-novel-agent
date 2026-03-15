"""Tests for the file-backed agent skill registry."""

from pathlib import Path

from app.services.agent_skill import agent_skill_service


def test_load_default_skill_bundle() -> None:
    """Default packaged skills should load successfully."""
    bundle = agent_skill_service.load_bundle()

    assert bundle.planner.name == "novel-agent-planner"
    assert "create_character" in bundle.operations
    assert "write_scene_content" in bundle.operations
    assert bundle.operations["create_character"].payload_contract is not None


def test_override_skill_directory_replaces_matching_tool(tmp_path: Path) -> None:
    """A custom skill directory can override one tool while keeping the rest."""
    override_skill = tmp_path / "operations" / "create-character"
    override_skill.mkdir(parents=True)
    (override_skill / "SKILL.md").write_text(
        """---
name: custom-create-character
description: Custom character creation skill.
kind: operation
tool_name: create_character
payload_contract: "{name}"
keywords:
  - 人物
---
Use the custom skill body.
""",
        encoding="utf-8",
    )

    bundle = agent_skill_service.load_bundle(override_root=tmp_path)

    assert bundle.operations["create_character"].name == "custom-create-character"
    assert bundle.operations["update_character"].name == "update-character"


def test_load_xianxia_profile_bundle() -> None:
    """The builtin xianxia profile should overlay the default skills."""
    bundle = agent_skill_service.load_bundle(profile_id="xianxia_intrigue")

    assert bundle.profile.id == "xianxia_intrigue"
    assert bundle.planner.name == "xianxia-intrigue-planner"
    assert bundle.operations["write_chapter_content"].name == "xianxia-write-chapter-content"
    assert any(reference.endswith("写作提示词.txt") for reference in bundle.operations["write_chapter_content"].references)
