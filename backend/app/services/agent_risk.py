"""Risk classification service for the agent workflow."""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, Field

from app.models.agent_workflow import AgentOperation, AgentPermissionLevel, AgentRiskLevel
from app.schemas.agent import (
    AgentAppliedRiskPolicyResponse,
    AgentRiskPolicyRegistryResponse,
    AgentRiskPolicyResponse,
    AgentRunRiskSummaryResponse,
)

RISK_POLICY_VERSION = "2026-03-15.2"


class RiskProfileSettings(BaseModel):
    """Profile-specific override settings for the risk classifier."""

    profile_id: str
    long_form_overwrite_min_chars: int = 280


class RiskPolicyDefinition(BaseModel):
    """Stable risk policy definition used by the classifier."""

    policy_id: Literal[
        "create_only",
        "standard_updates",
        "content_append",
        "content_rewrite",
        "long_form_overwrite",
        "multi_object_write",
    ]
    name: str
    scope: Literal["operation", "run"]
    description: str
    risk_level: Literal["low", "medium", "high"]
    confirmation_gate: Literal["none", "single", "double"]
    requires_secondary_confirmation: bool = False
    tool_scope: list[str] = Field(default_factory=list)


class NormalizedRiskOperation(BaseModel):
    """Minimal operation snapshot used by the risk classifier."""

    position: int
    tool_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    permission_level: Literal["read_search", "standard_write", "high_risk_write"] = (
        AgentPermissionLevel.STANDARD_WRITE.value
    )
    risk_level: Literal["low", "medium", "high"] = AgentRiskLevel.LOW.value
    requires_secondary_confirmation: bool = False


class AgentRiskService:
    """Encapsulate risk policy registry, operation classification, and run summaries."""

    def get_registry_response(
        self,
        *,
        profile_id: str = "default",
    ) -> AgentRiskPolicyRegistryResponse:
        """Return the stable risk policy registry."""
        return AgentRiskPolicyRegistryResponse(
            policy_version=RISK_POLICY_VERSION,
            policies=[
                self._risk_policy_response(policy)
                for policy in self._policy_registry(profile_id=profile_id).values()
            ],
        )

    def classify_operations(
        self,
        operations: list[dict[str, Any]],
        *,
        profile_id: str = "default",
    ) -> list[dict[str, Any]]:
        """Attach permission and risk metadata to planner operations."""
        classified: list[dict[str, Any]] = []
        for position, operation in enumerate(operations, start=1):
            enriched = dict(operation)
            permission_level, risk_level, requires_secondary_confirmation = self._classify_single_operation(
                enriched,
                profile_id=profile_id,
            )
            enriched["position"] = position
            enriched["permission_level"] = permission_level
            enriched["risk_level"] = risk_level
            enriched["requires_secondary_confirmation"] = requires_secondary_confirmation
            classified.append(enriched)

        self._apply_multi_object_write_policy(classified)
        return classified

    def build_run_risk_summary(
        self,
        operations: list[dict[str, Any]] | list[AgentOperation],
        *,
        profile_id: str = "default",
    ) -> AgentRunRiskSummaryResponse:
        """Aggregate operation-level risk into a stable run-level contract."""
        normalized_inputs = cast(list[AgentOperation | dict[str, Any]], operations)
        normalized = [
            self._normalize_operation(operation, fallback_position=index)
            for index, operation in enumerate(normalized_inputs, start=1)
        ]
        if not normalized:
            return AgentRunRiskSummaryResponse(
                policy_version=RISK_POLICY_VERSION,
                overall_risk_level=AgentRiskLevel.LOW.value,
                confirmation_gate="none",
                requires_confirmation=False,
                requires_secondary_confirmation=False,
                summary="当前 run 不包含可执行写入步骤。",
            )

        registry = self._policy_registry(profile_id=profile_id)
        low_count = sum(1 for operation in normalized if operation.risk_level == AgentRiskLevel.LOW.value)
        medium_count = sum(1 for operation in normalized if operation.risk_level == AgentRiskLevel.MEDIUM.value)
        high_positions = [
            operation.position for operation in normalized if operation.risk_level == AgentRiskLevel.HIGH.value
        ]
        secondary_positions = [
            operation.position for operation in normalized if operation.requires_secondary_confirmation
        ]

        create_positions = [
            operation.position
            for operation in normalized
            if operation.tool_name.startswith("create_")
        ]
        standard_update_positions = [
            operation.position
            for operation in normalized
            if self._is_standard_update_operation(operation)
        ]
        append_positions = [
            operation.position
            for operation in normalized
            if self._is_append_operation(operation)
        ]
        rewrite_positions = [
            operation.position
            for operation in normalized
            if self._is_content_rewrite_operation(operation)
        ]
        long_form_positions = [
            operation.position
            for operation in normalized
            if self._is_long_form_overwrite_operation(operation, profile_id=profile_id)
        ]

        applied_policies: list[AgentAppliedRiskPolicyResponse] = []
        policy_matches: list[tuple[str, list[int]]] = []
        if len(create_positions) == len(normalized):
            policy_matches.append(("create_only", create_positions))
        if standard_update_positions:
            policy_matches.append(("standard_updates", standard_update_positions))
        if append_positions:
            policy_matches.append(("content_append", append_positions))
        if rewrite_positions:
            policy_matches.append(("content_rewrite", rewrite_positions))
        if long_form_positions:
            policy_matches.append(("long_form_overwrite", long_form_positions))
        if len(rewrite_positions) > 1:
            policy_matches.append(("multi_object_write", rewrite_positions))

        for policy_id, matched_positions in policy_matches:
            applied_policies.append(
                self._applied_risk_policy_response(
                    policy=registry[policy_id],
                    matched_positions=matched_positions,
                )
            )

        overall_risk = (
            AgentRiskLevel.HIGH.value
            if high_positions
            else AgentRiskLevel.MEDIUM.value
            if medium_count > 0
            else AgentRiskLevel.LOW.value
        )
        confirmation_gate: Literal["none", "single", "double"] = (
            "double" if secondary_positions else "single"
        )

        summary_parts = [f"当前计划包含 {len(normalized)} 个写入步骤"]
        risk_fragments: list[str] = []
        if high_positions:
            risk_fragments.append(f"{len(high_positions)} 个高风险正文覆盖")
        if medium_count > 0:
            risk_fragments.append(f"{medium_count} 个标准写入")
        if low_count > 0:
            risk_fragments.append(f"{low_count} 个低风险创建或补充")
        if risk_fragments:
            summary_parts.append("，其中" + "、".join(risk_fragments))
        if len(normalized) > 1:
            summary_parts.append("，涉及多步骤联动修改")
        if applied_policies:
            summary_parts.append("；命中策略：" + "、".join(policy.name for policy in applied_policies))
        summary_parts.append(
            "；需要二次确认后执行。"
            if confirmation_gate == "double"
            else "；需要一次确认后执行。"
        )

        return AgentRunRiskSummaryResponse(
            policy_version=RISK_POLICY_VERSION,
            overall_risk_level=cast(Any, overall_risk),
            confirmation_gate=confirmation_gate,
            requires_confirmation=True,
            requires_secondary_confirmation=bool(secondary_positions),
            total_operations=len(normalized),
            low_risk_operation_count=low_count,
            medium_risk_operation_count=medium_count,
            high_risk_operation_count=len(high_positions),
            high_risk_operation_positions=high_positions,
            secondary_confirmation_operation_positions=secondary_positions,
            applied_policies=applied_policies,
            summary="".join(summary_parts),
        )

    def _policy_registry(self, *, profile_id: str = "default") -> dict[str, RiskPolicyDefinition]:
        """Return the stable risk policy registry."""
        settings = self._profile_settings(profile_id=profile_id)
        return {
            "create_only": RiskPolicyDefinition(
                policy_id="create_only",
                name="Create Only",
                scope="operation",
                description="仅包含创建或补充类写入，不涉及既有正文覆盖。",
                risk_level=AgentRiskLevel.LOW.value,
                confirmation_gate="single",
                tool_scope=[
                    "create_character",
                    "create_world_setting",
                    "create_volume",
                    "create_chapter",
                    "create_scene",
                ],
            ),
            "standard_updates": RiskPolicyDefinition(
                policy_id="standard_updates",
                name="Standard Updates",
                scope="operation",
                description="标准字段更新，不包含长正文覆盖。",
                risk_level=AgentRiskLevel.MEDIUM.value,
                confirmation_gate="single",
                tool_scope=[
                    "update_project_outline",
                    "update_character",
                    "update_world_setting",
                    "update_volume",
                    "update_chapter",
                    "update_scene",
                ],
            ),
            "content_append": RiskPolicyDefinition(
                policy_id="content_append",
                name="Content Append",
                scope="operation",
                description="对既有正文做续写或追加，不直接覆盖原文。",
                risk_level=AgentRiskLevel.MEDIUM.value,
                confirmation_gate="single",
                tool_scope=["write_chapter_content", "write_scene_content"],
            ),
            "content_rewrite": RiskPolicyDefinition(
                policy_id="content_rewrite",
                name="Content Rewrite",
                scope="operation",
                description="对章节或场景正文做改写或替换。",
                risk_level=AgentRiskLevel.MEDIUM.value,
                confirmation_gate="single",
                tool_scope=[
                    "write_chapter_content",
                    "write_scene_content",
                    "update_chapter",
                    "update_scene",
                ],
            ),
            "long_form_overwrite": RiskPolicyDefinition(
                policy_id="long_form_overwrite",
                name="Long Form Overwrite",
                scope="operation",
                description=(
                    f"长文本正文覆盖，超过 {settings.long_form_overwrite_min_chars} 字后必须二次确认才能执行。"
                ),
                risk_level=AgentRiskLevel.HIGH.value,
                confirmation_gate="double",
                requires_secondary_confirmation=True,
                tool_scope=[
                    "write_chapter_content",
                    "write_scene_content",
                    "update_chapter",
                    "update_scene",
                ],
            ),
            "multi_object_write": RiskPolicyDefinition(
                policy_id="multi_object_write",
                name="Multi Object Rewrite",
                scope="run",
                description="同一 run 内存在多个正文重写步骤，统一按联动高风险处理。",
                risk_level=AgentRiskLevel.HIGH.value,
                confirmation_gate="double",
                requires_secondary_confirmation=True,
                tool_scope=[
                    "write_chapter_content",
                    "write_scene_content",
                    "update_chapter",
                    "update_scene",
                ],
            ),
        }

    def _risk_policy_response(self, policy: RiskPolicyDefinition) -> AgentRiskPolicyResponse:
        """Serialize one policy definition to the public contract."""
        return AgentRiskPolicyResponse(
            policy_id=cast(Any, policy.policy_id),
            name=policy.name,
            scope=cast(Any, policy.scope),
            description=policy.description,
            risk_level=cast(Any, policy.risk_level),
            confirmation_gate=cast(Any, policy.confirmation_gate),
            requires_secondary_confirmation=policy.requires_secondary_confirmation,
            tool_scope=policy.tool_scope,
        )

    def _applied_risk_policy_response(
        self,
        *,
        policy: RiskPolicyDefinition,
        matched_positions: list[int],
    ) -> AgentAppliedRiskPolicyResponse:
        """Serialize one applied policy snapshot."""
        return AgentAppliedRiskPolicyResponse(
            policy_id=cast(Any, policy.policy_id),
            name=policy.name,
            scope=cast(Any, policy.scope),
            description=policy.description,
            risk_level=cast(Any, policy.risk_level),
            confirmation_gate=cast(Any, policy.confirmation_gate),
            requires_secondary_confirmation=policy.requires_secondary_confirmation,
            matched_operation_positions=matched_positions,
        )

    def _normalize_operation(
        self,
        operation: AgentOperation | dict[str, Any],
        *,
        fallback_position: int,
    ) -> NormalizedRiskOperation:
        """Normalize planned or persisted operations for classifier use."""
        if isinstance(operation, AgentOperation):
            return NormalizedRiskOperation(
                position=operation.position or fallback_position,
                tool_name=operation.tool_name,
                payload=operation.payload or {},
                permission_level=cast(Any, operation.permission_level),
                risk_level=cast(Any, operation.risk_level),
                requires_secondary_confirmation=operation.requires_secondary_confirmation,
            )
        return NormalizedRiskOperation(
            position=int(operation.get("position", fallback_position)),
            tool_name=str(operation["tool_name"]),
            payload=cast(dict[str, Any], operation.get("payload", {})),
            permission_level=cast(
                Any,
                operation.get("permission_level", AgentPermissionLevel.STANDARD_WRITE.value),
            ),
            risk_level=cast(Any, operation.get("risk_level", AgentRiskLevel.LOW.value)),
            requires_secondary_confirmation=bool(
                operation.get("requires_secondary_confirmation", False)
            ),
        )

    def _operation_content_candidate(self, operation: NormalizedRiskOperation) -> str | None:
        """Return the content candidate represented by an operation, if any."""
        if operation.tool_name in {"write_chapter_content", "write_scene_content"}:
            return cast(str | None, operation.payload.get("content"))
        if operation.tool_name in {"create_chapter", "create_scene", "create_world_setting"}:
            return cast(str | None, operation.payload.get("content"))
        if operation.tool_name in {"update_chapter", "update_scene", "update_world_setting"}:
            updates = cast(dict[str, Any], operation.payload.get("updates", {}))
            return cast(str | None, updates.get("content"))
        return None

    def _is_append_operation(self, operation: NormalizedRiskOperation) -> bool:
        """Return whether a content write uses append mode."""
        if operation.tool_name not in {"write_chapter_content", "write_scene_content"}:
            return False
        return str(operation.payload.get("mode", "replace")) == "append"

    def _is_content_rewrite_operation(self, operation: NormalizedRiskOperation) -> bool:
        """Return whether the operation rewrites chapter or scene content."""
        if operation.tool_name in {"write_chapter_content", "write_scene_content"}:
            return not self._is_append_operation(operation)
        if operation.tool_name in {"update_chapter", "update_scene"}:
            updates = operation.payload.get("updates")
            return isinstance(updates, dict) and "content" in updates
        return False

    def _is_long_form_overwrite_operation(
        self,
        operation: NormalizedRiskOperation,
        *,
        profile_id: str,
    ) -> bool:
        """Return whether a rewrite crosses the long-form overwrite threshold."""
        if not self._is_content_rewrite_operation(operation):
            return False
        settings = self._profile_settings(profile_id=profile_id)
        return len(self._operation_content_candidate(operation) or "") >= settings.long_form_overwrite_min_chars

    def _is_standard_update_operation(self, operation: NormalizedRiskOperation) -> bool:
        """Return whether the operation is a non-content update."""
        if operation.tool_name in {"update_character", "update_world_setting"}:
            return True
        if operation.tool_name in {"update_chapter", "update_scene"}:
            return not self._is_content_rewrite_operation(operation)
        return False

    def _classify_single_operation(
        self,
        operation: dict[str, Any],
        *,
        profile_id: str,
    ) -> tuple[str, str, bool]:
        """Classify one operation before any cross-operation escalation is applied."""
        normalized = self._normalize_operation(operation, fallback_position=1)
        settings = self._profile_settings(profile_id=profile_id)
        permission_level = AgentPermissionLevel.STANDARD_WRITE.value
        content_candidate = self._operation_content_candidate(normalized)
        touches_content = content_candidate is not None

        if normalized.tool_name in {"write_chapter_content", "write_scene_content"}:
            if self._is_append_operation(normalized):
                return permission_level, AgentRiskLevel.MEDIUM.value, False
            if len(content_candidate or "") >= settings.long_form_overwrite_min_chars:
                return (
                    AgentPermissionLevel.HIGH_RISK_WRITE.value,
                    AgentRiskLevel.HIGH.value,
                    True,
                )
            return permission_level, AgentRiskLevel.MEDIUM.value, False

        if normalized.tool_name in {"update_chapter", "update_scene"} and touches_content:
            if len(content_candidate or "") >= settings.long_form_overwrite_min_chars:
                return (
                    AgentPermissionLevel.HIGH_RISK_WRITE.value,
                    AgentRiskLevel.HIGH.value,
                    True,
                )
            return permission_level, AgentRiskLevel.MEDIUM.value, False

        if normalized.tool_name in {"create_chapter", "create_scene"} and touches_content:
            return permission_level, AgentRiskLevel.MEDIUM.value, False

        if normalized.tool_name in {"update_project_outline", "update_character", "update_world_setting", "update_volume"}:
            return permission_level, AgentRiskLevel.MEDIUM.value, False

        return permission_level, AgentRiskLevel.LOW.value, False

    def _apply_multi_object_write_policy(self, classified: list[dict[str, Any]]) -> None:
        """Escalate multiple rewrite operations into one explicit high-risk batch."""
        rewrite_indexes = [
            index
            for index, operation in enumerate(classified)
            if self._is_content_rewrite_operation(
                self._normalize_operation(operation, fallback_position=index + 1)
            )
        ]
        if len(rewrite_indexes) <= 1:
            return
        for index in rewrite_indexes:
            classified[index]["permission_level"] = AgentPermissionLevel.HIGH_RISK_WRITE.value
            classified[index]["risk_level"] = AgentRiskLevel.HIGH.value
            classified[index]["requires_secondary_confirmation"] = True

    def _profile_settings(self, *, profile_id: str) -> RiskProfileSettings:
        """Resolve risk override settings for one project profile."""
        if profile_id == "xianxia_intrigue":
            return RiskProfileSettings(
                profile_id=profile_id,
                long_form_overwrite_min_chars=180,
            )
        return RiskProfileSettings(profile_id="default")


agent_risk_service = AgentRiskService()
