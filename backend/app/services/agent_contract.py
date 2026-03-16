"""Execution contract assembly service for the agent workflow."""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, Field

from app.models.agent_workflow import AgentSubtaskRole, AgentSubtaskStatus


class ChildUnitContractSummary(BaseModel):
    """Stable contract for one internal child unit within a phase."""

    unit_id: str
    role: Literal["planner", "researcher", "writer", "editor", "continuity", "executor"]
    phase: Literal["plan", "build"]
    stage: Literal["preview", "pre_execution", "execution"]
    mode: Literal["restricted", "gated"]
    title: str
    description: str
    tool_scope: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    operation_positions: list[int] = Field(default_factory=list)
    confirmation_gate: Literal["none", "single", "double"] = "none"
    requires_confirmation: bool = False
    internal_only: bool = True


class PermissionPhaseSummary(BaseModel):
    """Serializable summary for one workflow permission phase."""

    phase: Literal["plan", "build"]
    mode: Literal["restricted", "gated"]
    allowed_permission_levels: list[str] = Field(default_factory=list)
    tool_scope: list[str] = Field(default_factory=list)
    role_scope: list[str] = Field(default_factory=list)
    confirmation_gate: Literal["none", "single", "double"] = "none"
    requires_confirmation: bool = False
    requires_secondary_confirmation: bool = False
    operation_count: int = 0
    child_units: list[ChildUnitContractSummary] = Field(default_factory=list)
    capabilities: list[dict[str, Any]] = Field(default_factory=list)


class ExecutionContractPayload(BaseModel):
    """Serialized execution contract stored with a run."""

    registry_version: str
    phases: list[PermissionPhaseSummary] = Field(default_factory=list)


class AgentContractService:
    """Build explicit phase contracts and child unit contracts from workflow inputs."""

    def build_execution_contract_payload(
        self,
        *,
        operations: list[dict[str, Any]],
        subtasks: list[dict[str, Any]],
        plan_capabilities: list[dict[str, Any]],
        build_capabilities: list[dict[str, Any]],
        registry_version: str,
        internal_read_search_tools: list[str],
    ) -> dict[str, Any]:
        """Assemble the serialized execution contract stored on a run."""
        build_levels = sorted({str(operation["permission_level"]) for operation in operations})
        high_risk_count = sum(1 for operation in operations if str(operation["permission_level"]) == "high_risk_write")
        role_scope = [str(subtask["role"]) for subtask in subtasks]
        confirmation_gate: Literal["none", "single", "double"] = "double" if high_risk_count > 0 else "single"

        plan_phase = PermissionPhaseSummary(
            phase="plan",
            mode="restricted",
            allowed_permission_levels=["read_search"],
            tool_scope=list(internal_read_search_tools),
            role_scope=role_scope,
            confirmation_gate="none",
            requires_confirmation=False,
            requires_secondary_confirmation=False,
            operation_count=0,
            child_units=self._build_plan_child_units(
                subtasks=subtasks,
                plan_capabilities=plan_capabilities,
            ),
            capabilities=plan_capabilities,
        )
        build_phase = PermissionPhaseSummary(
            phase="build",
            mode="gated",
            allowed_permission_levels=build_levels,
            tool_scope=[str(operation["tool_name"]) for operation in operations],
            role_scope=role_scope,
            confirmation_gate=confirmation_gate,
            requires_confirmation=bool(operations),
            requires_secondary_confirmation=high_risk_count > 0,
            operation_count=len(operations),
            child_units=self._build_build_child_units(
                subtasks=subtasks,
                operations=operations,
                confirmation_gate=confirmation_gate,
                build_capabilities=build_capabilities,
            ),
            capabilities=build_capabilities,
        )
        return ExecutionContractPayload(
            registry_version=registry_version,
            phases=[plan_phase, build_phase],
        ).model_dump(mode="json")

    def _child_trace_payload(self, subtask: dict[str, Any]) -> dict[str, Any] | None:
        """Return the raw child trace payload from a serialized subtask if present."""
        meta = cast(dict[str, Any], subtask.get("meta", {}))
        raw = meta.get("child_trace")
        return raw if isinstance(raw, dict) else None

    def _child_unit_description(self, *, role: str, subtask: dict[str, Any] | None = None) -> str:
        """Return a stable description for one child unit role."""
        summary = str(subtask.get("summary") or "").strip() if subtask is not None else ""
        if summary:
            return summary
        descriptions = {
            AgentSubtaskRole.PLANNER.value: "整理用户指令，生成可确认的 run blueprint。",
            AgentSubtaskRole.RESEARCHER.value: "解析项目上下文、聚焦对象与最近 checkpoint。",
            AgentSubtaskRole.WRITER.value: "为正文型 operation 生成候选内容与预览。",
            AgentSubtaskRole.EDITOR.value: "为结构化修改生成 patch 与字段级 diff 预览。",
            AgentSubtaskRole.CONTINUITY.value: "在执行前检查对象命中、预览一致性与多步冲突。",
            "executor": "执行已确认 operation，并更新执行期 capability record。",
        }
        return descriptions.get(role, "内部 child unit。")

    def _subtask_tool_scope(self, *, role: str) -> list[str]:
        """Return the internal tool scope fallback for one child unit role."""
        if role == AgentSubtaskRole.RESEARCHER.value:
            return [
                "resolve_current_project",
                "list_project_characters",
                "list_project_world_settings",
                "list_project_volumes",
                "list_project_chapters",
                "list_project_scenes",
                "resolve_current_character",
                "resolve_current_world_setting",
                "resolve_current_volume",
                "resolve_current_chapter",
                "resolve_current_scene",
                "load_latest_checkpoint",
            ]
        if role == AgentSubtaskRole.WRITER.value:
            return ["write_chapter_content", "write_scene_content", "create_chapter", "create_scene"]
        if role == AgentSubtaskRole.EDITOR.value:
            return [
                "update_project_outline",
                "create_volume",
                "update_volume",
                "update_character",
                "update_world_setting",
                "update_chapter",
                "update_scene",
            ]
        if role == AgentSubtaskRole.CONTINUITY.value:
            return ["load_latest_checkpoint"]
        return []

    def _child_unit_from_subtask(
        self,
        *,
        subtask: dict[str, Any],
        phase: Literal["plan", "build"],
        stage: Literal["preview", "pre_execution", "execution"],
        mode: Literal["restricted", "gated"],
        confirmation_gate: Literal["none", "single", "double"],
        requires_confirmation: bool,
        capability_ids: list[str] | None = None,
    ) -> ChildUnitContractSummary:
        """Build one child unit contract from a serialized subtask."""
        role = str(subtask["role"])
        child_trace = self._child_trace_payload(subtask) or {}
        unit_id = str(child_trace.get("unit_id") or f"{role}-{phase}")
        depends_on = [str(item) for item in cast(list[Any], child_trace.get("depends_on", []))]
        operation_positions = [
            int(item)
            for item in cast(list[Any], child_trace.get("operation_positions", []))
            if isinstance(item, int)
        ]
        tool_scope = [str(item) for item in cast(list[Any], child_trace.get("tool_scope", []))]
        if not tool_scope:
            tool_scope = self._subtask_tool_scope(role=role)
        return ChildUnitContractSummary(
            unit_id=unit_id,
            role=cast(Any, role),
            phase=phase,
            stage=stage,
            mode=mode,
            title=str(subtask.get("title") or role),
            description=self._child_unit_description(role=role, subtask=subtask),
            tool_scope=tool_scope,
            capability_ids=list(capability_ids or []),
            depends_on=depends_on,
            operation_positions=operation_positions,
            confirmation_gate=confirmation_gate,
            requires_confirmation=requires_confirmation,
            internal_only=True,
        )

    def _build_plan_child_units(
        self,
        *,
        subtasks: list[dict[str, Any]],
        plan_capabilities: list[dict[str, Any]],
    ) -> list[ChildUnitContractSummary]:
        """Build explicit child unit contracts for the plan phase."""
        subtask_by_role = {str(subtask["role"]): subtask for subtask in subtasks}
        units: list[ChildUnitContractSummary] = []

        planner = subtask_by_role.get(AgentSubtaskRole.PLANNER.value)
        if planner is not None:
            units.append(
                self._child_unit_from_subtask(
                    subtask=planner,
                    phase="plan",
                    stage="preview",
                    mode="restricted",
                    confirmation_gate="none",
                    requires_confirmation=False,
                )
            )

        researcher = subtask_by_role.get(AgentSubtaskRole.RESEARCHER.value)
        if researcher is not None:
            units.append(
                self._child_unit_from_subtask(
                    subtask=researcher,
                    phase="plan",
                    stage="preview",
                    mode="restricted",
                    confirmation_gate="none",
                    requires_confirmation=False,
                    capability_ids=[
                        str(capability["capability_id"])
                        for capability in plan_capabilities
                        if "capability_id" in capability
                    ],
                )
            )
        return units

    def _build_build_child_units(
        self,
        *,
        subtasks: list[dict[str, Any]],
        operations: list[dict[str, Any]],
        confirmation_gate: Literal["none", "single", "double"],
        build_capabilities: list[dict[str, Any]],
    ) -> list[ChildUnitContractSummary]:
        """Build explicit child unit contracts for the build phase."""
        if not operations:
            return []

        subtask_by_role = {str(subtask["role"]): subtask for subtask in subtasks}
        operation_positions = [int(operation["position"]) for operation in operations if "position" in operation]
        units: list[ChildUnitContractSummary] = []

        for role in (AgentSubtaskRole.WRITER.value, AgentSubtaskRole.EDITOR.value):
            subtask = subtask_by_role.get(role)
            if subtask is None or str(subtask.get("status")) == AgentSubtaskStatus.SKIPPED.value:
                continue
            units.append(
                self._child_unit_from_subtask(
                    subtask=subtask,
                    phase="build",
                    stage="preview",
                    mode="gated",
                    confirmation_gate="none",
                    requires_confirmation=False,
                )
            )

        continuity = subtask_by_role.get(AgentSubtaskRole.CONTINUITY.value)
        if continuity is not None:
            child_unit = self._child_unit_from_subtask(
                subtask=continuity,
                phase="build",
                stage="pre_execution",
                mode="gated",
                confirmation_gate=confirmation_gate,
                requires_confirmation=True,
            )
            if not child_unit.operation_positions:
                child_unit.operation_positions = list(operation_positions)
            units.append(child_unit)

        executor_capability_ids = [
            str(capability["capability_id"])
            for capability in build_capabilities
            if "capability_id" in capability
        ]
        executor_record_id = ""
        if build_capabilities:
            execution_record = cast(dict[str, Any] | None, build_capabilities[0].get("execution_record"))
            if execution_record is not None:
                executor_record_id = str(execution_record.get("record_id") or "")
        units.append(
            ChildUnitContractSummary(
                unit_id=executor_record_id or f"executor-build-{len(operation_positions)}",
                role="executor",
                phase="build",
                stage="execution",
                mode="gated",
                title="Executor unit",
                description=self._child_unit_description(role="executor"),
                tool_scope=[str(operation["tool_name"]) for operation in operations],
                capability_ids=executor_capability_ids,
                depends_on=[AgentSubtaskRole.CONTINUITY.value],
                operation_positions=list(operation_positions),
                confirmation_gate=confirmation_gate,
                requires_confirmation=True,
                internal_only=True,
            )
        )
        return units


agent_contract_service = AgentContractService()
