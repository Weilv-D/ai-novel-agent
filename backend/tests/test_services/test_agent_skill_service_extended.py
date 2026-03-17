"""Extended tests for the file-backed agent skill registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import BadRequestException
from app.services.agent_skill import AgentProfile, AgentSkill, AgentSkillBundle, AgentSkillService


def _write_skill(
    path: Path,
    *,
    name: str,
    description: str,
    kind: str,
    tool_name: str | None = None,
    payload_contract: str | None = None,
    keywords: list[str] | None = None,
    references: list[str] | None = None,
    body: str = "Use this skill.",
) -> None:
    """Write a minimal skill file with YAML frontmatter."""
    lines = [
        "---",
        f"name: {name}",
        f"description: {description}",
        f"kind: {kind}",
    ]
    if tool_name is not None:
        lines.append(f"tool_name: {tool_name}")
    if payload_contract is not None:
        lines.append(f'payload_contract: "{payload_contract}"')
    if keywords:
        lines.append("keywords:")
        lines.extend(f"  - {keyword}" for keyword in keywords)
    if references:
        lines.append("references:")
        lines.extend(f"  - {reference}" for reference in references)
    lines.extend(["---", body])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


class TestAgentSkillServiceExtended:
    """Covers prompt rendering, selection, custom profiles, and validation errors."""

    def test_agent_skill_prompt_block_and_reference_resolution(self, tmp_path: Path) -> None:
        reference = tmp_path / "notes.txt"
        reference.write_text("reference body", encoding="utf-8")
        skill_path = tmp_path / "skill" / "SKILL.md"
        _write_skill(
            skill_path,
            name="custom-skill",
            description="desc",
            kind="operation",
            tool_name="create_character",
            payload_contract="{name}",
            references=["../notes.txt"],
            body="Do the thing.",
        )

        service = AgentSkillService()
        skill = service._load_skill(skill_path)

        prompt = skill.prompt_block()
        assert "Skill: custom-skill" in prompt
        assert "Tool: create_character" in prompt
        assert "Payload: {name}" in prompt
        assert skill.resolve_reference("../notes.txt") == reference.resolve()

    def test_bundle_select_operations_reference_blocks_and_catalog(self, tmp_path: Path) -> None:
        reference = tmp_path / "shared.txt"
        reference.write_text("shared reference", encoding="utf-8")
        planner = AgentSkill(
            name="planner",
            description="desc",
            kind="planner",
            body="plan",
            source_path=tmp_path / "planner" / "SKILL.md",
        )
        create_skill = AgentSkill(
            name="create",
            description="desc",
            kind="operation",
            body="body",
            source_path=tmp_path / "operations" / "create" / "SKILL.md",
            tool_name="create_character",
            keywords=("人物", "角色"),
            references=("../../shared.txt",),
        )
        update_skill = AgentSkill(
            name="update",
            description="desc",
            kind="operation",
            body="body",
            source_path=tmp_path / "operations" / "update" / "SKILL.md",
            tool_name="update_world_setting",
            keywords=("设定",),
            references=("../../shared.txt",),
        )
        bundle = AgentSkillBundle(
            profile=AgentProfile(id="custom", name="Custom", description="desc", builtin=False, root=tmp_path),
            planner=planner,
            operations={
                "update_world_setting": update_skill,
                "create_character": create_skill,
            },
            roots=(tmp_path,),
        )

        selected = bundle.select_operations(
            user_message="请创建一个新人物",
            context_data={"chapter_id": "1"},
            prior_summary=None,
        )
        fallback = bundle.select_operations(
            user_message="无关键词命中",
            context_data={"chapter_id": "1"},
            prior_summary=None,
        )
        reference_blocks = bundle.load_reference_blocks([create_skill, update_skill])
        catalog = bundle.catalog()

        assert [skill.tool_name for skill in selected] == ["create_character"]
        assert [skill.tool_name for skill in fallback] == ["create_character", "update_world_setting"]
        assert reference_blocks == ["Reference: shared\nshared reference"]
        assert catalog[0].kind == "planner"
        assert catalog[1].tool_name == "create_character"

    def test_list_profiles_and_load_bundle_from_custom_override(self, tmp_path: Path) -> None:
        custom_root = tmp_path / "custom-profile"
        _write_skill(
            custom_root / "planner" / "SKILL.md",
            name="custom-planner",
            description="custom profile",
            kind="planner",
        )
        _write_skill(
            custom_root / "operations" / "rewrite" / "SKILL.md",
            name="custom-rewrite",
            description="rewrite",
            kind="operation",
            tool_name="write_scene_content",
        )

        service = AgentSkillService()
        profiles = service.list_profiles(override_root=tmp_path)
        bundle = service.load_bundle(profile_id="custom-profile", override_root=tmp_path)

        assert any(profile.id == "custom-profile" and not profile.builtin for profile in profiles)
        assert bundle.profile.id == "custom-profile"
        assert bundle.planner.name == "custom-planner"
        assert bundle.operations["write_scene_content"].name == "custom-rewrite"

    def test_skill_service_rejects_invalid_override_roots_and_frontmatter(self, tmp_path: Path) -> None:
        service = AgentSkillService()

        with pytest.raises(BadRequestException, match="does not exist"):
            service.list_profiles(override_root=tmp_path / "missing")

        bad_frontmatter = tmp_path / "operations" / "broken" / "SKILL.md"
        bad_frontmatter.parent.mkdir(parents=True, exist_ok=True)
        bad_frontmatter.write_text("name: missing-frontmatter", encoding="utf-8")
        with pytest.raises(BadRequestException, match="must start with YAML frontmatter"):
            service._load_skill(bad_frontmatter)

        unterminated = tmp_path / "operations" / "unterminated" / "SKILL.md"
        unterminated.parent.mkdir(parents=True, exist_ok=True)
        unterminated.write_text("---\nname: broken", encoding="utf-8")
        with pytest.raises(BadRequestException, match="not terminated"):
            service._load_skill(unterminated)

        missing_tool_root = tmp_path / "missing-tool"
        _write_skill(
            missing_tool_root / "planner" / "SKILL.md",
            name="planner",
            description="desc",
            kind="planner",
        )
        _write_skill(
            missing_tool_root / "operations" / "broken" / "SKILL.md",
            name="broken-op",
            description="desc",
            kind="operation",
        )
        with pytest.raises(BadRequestException, match="missing tool_name"):
            service.load_bundle(override_root=missing_tool_root)

        invalid_metadata = tmp_path / "invalid-metadata" / "planner" / "SKILL.md"
        invalid_metadata.parent.mkdir(parents=True, exist_ok=True)
        invalid_metadata.write_text("---\nname:\ndescription: ok\nkind: planner\n---\nbody", encoding="utf-8")
        with pytest.raises(BadRequestException, match="metadata 'name' is required"):
            service._load_skill(invalid_metadata)
