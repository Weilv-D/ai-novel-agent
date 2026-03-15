"""Unit tests for the execution contract assembly service."""

from app.services.agent_contract import agent_contract_service


class TestAgentContractService:
    """Covers stable phase and child-unit contract assembly."""

    def test_build_execution_contract_payload_keeps_plan_units_explicit(self) -> None:
        """Plan phase should expose planner and researcher child units."""
        payload = agent_contract_service.build_execution_contract_payload(
            operations=[
                {
                    "position": 1,
                    "tool_name": "create_character",
                    "permission_level": "standard_write",
                }
            ],
            subtasks=[
                {
                    "role": "planner",
                    "title": "Planner unit",
                    "summary": "Compose a visible run blueprint.",
                    "status": "completed",
                    "meta": {
                        "child_trace": {
                            "unit_id": "planner-plan-1",
                            "tool_scope": ["compose_run_blueprint"],
                        }
                    },
                },
                {
                    "role": "researcher",
                    "title": "Research unit",
                    "summary": "Resolve project inventory and focused objects.",
                    "status": "completed",
                    "meta": {
                        "child_trace": {
                            "unit_id": "researcher-plan-1",
                            "tool_scope": ["list_project_characters", "resolve_current_character"],
                        }
                    },
                },
            ],
            plan_capabilities=[
                {"capability_id": "project_inventory"},
                {"capability_id": "focused_object_resolution"},
                {"capability_id": "checkpoint_context"},
            ],
            build_capabilities=[],
            registry_version="2026-03-15.1",
            internal_read_search_tools=["list_project_characters", "resolve_current_character"],
        )

        assert payload["registry_version"] == "2026-03-15.1"
        plan_phase = payload["phases"][0]
        assert plan_phase["phase"] == "plan"
        assert plan_phase["allowed_permission_levels"] == ["read_search"]
        assert [unit["role"] for unit in plan_phase["child_units"]] == ["planner", "researcher"]
        assert plan_phase["child_units"][1]["capability_ids"] == [
            "project_inventory",
            "focused_object_resolution",
            "checkpoint_context",
        ]

    def test_build_execution_contract_payload_marks_high_risk_build_gate(self) -> None:
        """Build phase should enforce double confirmation for high-risk writes."""
        payload = agent_contract_service.build_execution_contract_payload(
            operations=[
                {
                    "position": 1,
                    "tool_name": "write_chapter_content",
                    "permission_level": "high_risk_write",
                }
            ],
            subtasks=[
                {
                    "role": "writer",
                    "title": "Writer unit",
                    "summary": "Draft replacement prose.",
                    "status": "completed",
                    "meta": {
                        "child_trace": {
                            "unit_id": "writer-build-1",
                            "tool_scope": ["write_chapter_content"],
                            "operation_positions": [1],
                        }
                    },
                },
                {
                    "role": "continuity",
                    "title": "Continuity unit",
                    "summary": "Validate preview consistency.",
                    "status": "completed",
                    "meta": {
                        "child_trace": {
                            "unit_id": "continuity-build-1",
                            "tool_scope": ["load_latest_checkpoint"],
                        }
                    },
                },
            ],
            plan_capabilities=[],
            build_capabilities=[
                {
                    "capability_id": "operation_execution",
                    "execution_record": {"record_id": "cap-op-exec-1"},
                }
            ],
            registry_version="2026-03-15.1",
            internal_read_search_tools=[],
        )

        build_phase = payload["phases"][1]
        assert build_phase["phase"] == "build"
        assert build_phase["confirmation_gate"] == "double"
        assert build_phase["requires_secondary_confirmation"] is True
        assert [unit["role"] for unit in build_phase["child_units"]] == ["writer", "continuity", "executor"]
        assert build_phase["child_units"][1]["confirmation_gate"] == "double"
        assert build_phase["child_units"][1]["operation_positions"] == [1]
        assert build_phase["child_units"][2]["unit_id"] == "cap-op-exec-1"
        assert build_phase["child_units"][2]["capability_ids"] == ["operation_execution"]
