"""Profile-aware skill registry for the planner/executor agent workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import BadRequestException
from app.models.project import DEFAULT_AGENT_PROFILE_ID

XIANXIA_INTRIGUE_PROFILE_ID = "xianxia_intrigue"


@dataclass(frozen=True)
class AgentSkill:
    """Single file-backed skill."""

    name: str
    description: str
    kind: str
    body: str
    source_path: Path
    tool_name: str | None = None
    payload_contract: str | None = None
    keywords: tuple[str, ...] = ()
    references: tuple[str, ...] = ()

    def prompt_block(self) -> str:
        """Render this skill into a prompt-safe text block."""
        lines = [
            f"Skill: {self.name}",
            f"Description: {self.description}",
        ]
        if self.tool_name:
            lines.append(f"Tool: {self.tool_name}")
        if self.payload_contract:
            lines.append(f"Payload: {self.payload_contract}")
        lines.append("Instructions:")
        lines.append(self.body.strip())
        return "\n".join(lines).strip()

    def resolve_reference(self, reference: str) -> Path:
        """Resolve a reference path relative to the skill file."""
        return (self.source_path.parent / reference).resolve()


@dataclass(frozen=True)
class AgentProfile:
    """Profile metadata for project-level agent behavior."""

    id: str
    name: str
    description: str
    builtin: bool
    root: Path


@dataclass(frozen=True)
class AgentSkillSummary:
    """Small serializable view of a skill."""

    name: str
    description: str
    kind: str
    tool_name: str | None
    source: str
    payload_contract: str | None
    references: list[str]


@dataclass(frozen=True)
class AgentSkillBundle:
    """Loaded planner and operation skills for one profile."""

    profile: AgentProfile
    planner: AgentSkill
    operations: dict[str, AgentSkill]
    roots: tuple[Path, ...]

    def ordered_operations(self) -> list[AgentSkill]:
        """Return operation skills in stable tool order."""
        return [self.operations[key] for key in sorted(self.operations)]

    def select_operations(
        self,
        *,
        user_message: str,
        context_data: dict[str, Any],
        prior_summary: str | None,
    ) -> list[AgentSkill]:
        """Select likely-relevant operations for prompt enrichment."""
        haystacks = [
            user_message.lower(),
            prior_summary.lower() if prior_summary else "",
            " ".join(str(value).lower() for value in context_data.keys()),
        ]
        selected: list[tuple[int, AgentSkill]] = []
        for skill in self.ordered_operations():
            score = 0
            for keyword in skill.keywords:
                keyword_lc = keyword.lower()
                if any(keyword_lc in haystack for haystack in haystacks):
                    score += 1
            if score > 0:
                selected.append((score, skill))
        if not selected:
            return self.ordered_operations()
        selected.sort(key=lambda item: (-item[0], item[1].tool_name or item[1].name))
        return [skill for _, skill in selected]

    def load_reference_blocks(self, skills: list[AgentSkill]) -> list[str]:
        """Load unique reference texts required by selected skills."""
        blocks: list[str] = []
        seen_paths: set[Path] = set()
        for skill in skills:
            for reference in skill.references:
                path = skill.resolve_reference(reference)
                if path in seen_paths or not path.exists():
                    continue
                seen_paths.add(path)
                blocks.append(f"Reference: {path.stem}\n{path.read_text(encoding='utf-8').strip()}")
        return blocks

    def catalog(self) -> list[AgentSkillSummary]:
        """Return serializable skill metadata."""
        summaries = [
            AgentSkillSummary(
                name=self.planner.name,
                description=self.planner.description,
                kind=self.planner.kind,
                tool_name=self.planner.tool_name,
                source=str(self.planner.source_path),
                payload_contract=self.planner.payload_contract,
                references=list(self.planner.references),
            )
        ]
        summaries.extend(
            AgentSkillSummary(
                name=skill.name,
                description=skill.description,
                kind=skill.kind,
                tool_name=skill.tool_name,
                source=str(skill.source_path),
                payload_contract=skill.payload_contract,
                references=list(skill.references),
            )
            for skill in self.ordered_operations()
        )
        return summaries


class AgentSkillService:
    """Load packaged profile-aware skills and optional local overrides."""

    def __init__(self) -> None:
        service_root = Path(__file__).resolve().parent.parent
        self.default_profile_root = service_root / "agent_skills"
        self.profile_root = service_root / "agent_profiles"
        self.builtin_profiles: dict[str, AgentProfile] = {
            DEFAULT_AGENT_PROFILE_ID: AgentProfile(
                id=DEFAULT_AGENT_PROFILE_ID,
                name="Default",
                description="General-purpose long-form novel planning profile.",
                builtin=True,
                root=self.default_profile_root,
            ),
            XIANXIA_INTRIGUE_PROFILE_ID: AgentProfile(
                id=XIANXIA_INTRIGUE_PROFILE_ID,
                name="仙侠权谋",
                description="Grounded in the canonical prompts under others/ for outline, chapter design, and prose.",
                builtin=True,
                root=self.profile_root / XIANXIA_INTRIGUE_PROFILE_ID,
            ),
        }

    def list_profiles(self, *, override_root: Path | None = None) -> list[AgentProfile]:
        """List builtin profiles and any custom profiles from the override root."""
        configured_root = self._resolve_override_root(override_root)
        profiles = dict(self.builtin_profiles)
        if configured_root is not None:
            for candidate in configured_root.iterdir():
                if not candidate.is_dir():
                    continue
                planner_path = candidate / "planner" / "SKILL.md"
                if not planner_path.exists():
                    continue
                profile_id = candidate.name
                if profile_id in profiles:
                    continue
                planner_skill = self._load_skill(planner_path)
                profiles[profile_id] = AgentProfile(
                    id=profile_id,
                    name=planner_skill.name,
                    description=planner_skill.description,
                    builtin=False,
                    root=candidate.resolve(),
                )
        return [profiles[key] for key in sorted(profiles)]

    def load_bundle(
        self,
        *,
        profile_id: str = DEFAULT_AGENT_PROFILE_ID,
        override_root: Path | None = None,
    ) -> AgentSkillBundle:
        """Load the default profile and overlay a project-selected profile."""
        configured_root = self._resolve_override_root(override_root)
        profile = self._resolve_profile(profile_id, configured_root=configured_root)

        roots: list[Path] = [self.default_profile_root]
        planner = self._load_skill(self.default_profile_root / "planner" / "SKILL.md")
        operations = self._load_operation_skills(self.default_profile_root)

        if profile.id != DEFAULT_AGENT_PROFILE_ID:
            profile_planner_path = profile.root / "planner" / "SKILL.md"
            if profile_planner_path.exists():
                planner = self._load_skill(profile_planner_path)
            operations.update(self._load_operation_skills(profile.root))
            roots.append(profile.root)

        if configured_root is not None:
            override_profile_root = self._resolve_override_profile_root(
                profile_id=profile.id,
                override_root=configured_root,
            )
            if override_profile_root is not None:
                planner_override = override_profile_root / "planner" / "SKILL.md"
                if planner_override.exists():
                    planner = self._load_skill(planner_override)
                operations.update(self._load_operation_skills(override_profile_root))
                roots.append(override_profile_root)

        return AgentSkillBundle(profile=profile, planner=planner, operations=operations, roots=tuple(roots))

    def _resolve_override_root(self, override_root: Path | None) -> Path | None:
        configured_root = override_root
        if configured_root is None:
            configured_value = get_settings().agent_skills_dir.strip()
            configured_root = Path(configured_value).expanduser().resolve() if configured_value else None
        if configured_root is None:
            return None
        if not configured_root.exists():
            raise BadRequestException(f"Configured agent skills directory does not exist: {configured_root}")
        return configured_root

    def _resolve_profile(self, profile_id: str, *, configured_root: Path | None) -> AgentProfile:
        normalized = profile_id.strip() or DEFAULT_AGENT_PROFILE_ID
        builtin = self.builtin_profiles.get(normalized)
        if builtin is not None:
            return builtin
        if configured_root is None:
            raise BadRequestException(f"Unknown agent profile '{normalized}'")
        custom_root = self._resolve_override_profile_root(profile_id=normalized, override_root=configured_root)
        if custom_root is None:
            raise BadRequestException(f"Unknown agent profile '{normalized}'")
        planner_skill = self._load_skill(custom_root / "planner" / "SKILL.md")
        return AgentProfile(
            id=normalized,
            name=planner_skill.name,
            description=planner_skill.description,
            builtin=False,
            root=custom_root,
        )

    def _resolve_override_profile_root(
        self,
        *,
        profile_id: str,
        override_root: Path,
    ) -> Path | None:
        direct_planner = override_root / "planner" / "SKILL.md"
        direct_operations = override_root / "operations"
        if profile_id == DEFAULT_AGENT_PROFILE_ID and (direct_planner.exists() or direct_operations.exists()):
            return override_root
        candidate = override_root / profile_id
        if (candidate / "planner" / "SKILL.md").exists():
            return candidate.resolve()
        return None

    def _load_operation_skills(self, root: Path) -> dict[str, AgentSkill]:
        operation_root = root / "operations"
        if not operation_root.exists():
            return {}
        skills: dict[str, AgentSkill] = {}
        for skill_path in sorted(operation_root.glob("*/SKILL.md")):
            skill = self._load_skill(skill_path)
            if skill.kind != "operation":
                continue
            if skill.tool_name is None:
                raise BadRequestException(f"Operation skill is missing tool_name: {skill_path}")
            skills[skill.tool_name] = skill
        return skills

    def _load_skill(self, path: Path) -> AgentSkill:
        if not path.exists():
            raise BadRequestException(f"Agent skill file not found: {path}")
        raw = path.read_text(encoding="utf-8")
        metadata, body = self._split_frontmatter(raw, path)
        name = self._require_string(metadata, "name", path)
        description = self._require_string(metadata, "description", path)
        kind = self._require_string(metadata, "kind", path)
        tool_name = metadata.get("tool_name")
        payload_contract = metadata.get("payload_contract")
        keywords = tuple(self._normalize_list(metadata.get("keywords", [])))
        references = tuple(self._normalize_list(metadata.get("references", [])))
        return AgentSkill(
            name=name,
            description=description,
            kind=kind,
            body=body.strip(),
            source_path=path.resolve(),
            tool_name=str(tool_name) if tool_name else None,
            payload_contract=str(payload_contract) if payload_contract else None,
            keywords=keywords,
            references=references,
        )

    def _split_frontmatter(self, raw: str, path: Path) -> tuple[dict[str, Any], str]:
        if not raw.startswith("---\n"):
            raise BadRequestException(f"Skill file must start with YAML frontmatter: {path}")
        parts = raw.split("\n---\n", 1)
        if len(parts) != 2:
            raise BadRequestException(f"Skill file frontmatter is not terminated: {path}")
        header = parts[0][4:]
        body = parts[1]
        return self._parse_frontmatter(header, path), body

    def _parse_frontmatter(self, header: str, path: Path) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        active_list_key: str | None = None
        for raw_line in header.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                continue
            if active_list_key is not None and stripped.startswith("- "):
                metadata.setdefault(active_list_key, []).append(self._parse_scalar(stripped[2:].strip()))
                continue
            active_list_key = None
            if ":" not in line:
                raise BadRequestException(f"Invalid skill frontmatter line in {path}: {line}")
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if not value:
                metadata[key] = []
                active_list_key = key
                continue
            metadata[key] = self._parse_scalar(value)
        return metadata

    def _parse_scalar(self, value: str) -> Any:
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            return value[1:-1]
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
        return value

    def _normalize_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if value in {"", None}:
            return []
        return [str(value)]

    def _require_string(self, metadata: dict[str, Any], key: str, path: Path) -> str:
        value = metadata.get(key)
        if not isinstance(value, str) or not value.strip():
            raise BadRequestException(f"Skill metadata '{key}' is required in {path}")
        return value.strip()


agent_skill_service = AgentSkillService()
