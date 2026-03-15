"""Unit tests for the agent risk classifier service."""

from app.services.agent_risk import RISK_POLICY_VERSION, agent_risk_service


class TestAgentRiskService:
    """Covers registry exposure and deterministic risk classification."""

    def test_registry_response_exposes_expected_policies(self) -> None:
        """The public registry should expose the full policy set."""
        registry = agent_risk_service.get_registry_response()

        assert registry.policy_version == RISK_POLICY_VERSION
        policy_ids = {policy.policy_id for policy in registry.policies}
        assert {
            "create_only",
            "standard_updates",
            "content_append",
            "content_rewrite",
            "long_form_overwrite",
            "multi_object_write",
        } <= policy_ids

    def test_registry_response_reflects_xianxia_threshold_override(self) -> None:
        """Profile-specific registry views should expose stricter thresholds without changing the schema."""
        registry = agent_risk_service.get_registry_response(profile_id="xianxia_intrigue")

        long_form = next(policy for policy in registry.policies if policy.policy_id == "long_form_overwrite")
        assert "180" in long_form.description

    def test_classify_operations_marks_long_form_overwrite(self) -> None:
        """Long-form replace writes should require high-risk confirmation."""
        long_content = " ".join(["夜色沉坠，皇城如渊。"] * 40)
        classified = agent_risk_service.classify_operations(
            [
                {
                    "tool_name": "write_chapter_content",
                    "description": "重写章节正文",
                    "payload": {
                        "chapter_number": 1,
                        "mode": "replace",
                        "content": long_content,
                    },
                }
            ]
        )

        assert classified[0]["position"] == 1
        assert classified[0]["permission_level"] == "high_risk_write"
        assert classified[0]["risk_level"] == "high"
        assert classified[0]["requires_secondary_confirmation"] is True

    def test_build_run_risk_summary_marks_multi_object_batch(self) -> None:
        """Multiple rewrite operations should trigger the batch overwrite policy."""
        classified = agent_risk_service.classify_operations(
            [
                {
                    "tool_name": "write_chapter_content",
                    "description": "改写第一章",
                    "payload": {
                        "chapter_number": 1,
                        "mode": "replace",
                        "content": "新正文一",
                    },
                },
                {
                    "tool_name": "write_scene_content",
                    "description": "改写第二章场景",
                    "payload": {
                        "scene_order": 1,
                        "mode": "replace",
                        "content": "新正文二",
                    },
                },
            ]
        )
        summary = agent_risk_service.build_run_risk_summary(classified)

        assert summary.policy_version == RISK_POLICY_VERSION
        assert summary.overall_risk_level == "high"
        assert summary.confirmation_gate == "double"
        assert summary.high_risk_operation_positions == [1, 2]
        assert summary.secondary_confirmation_operation_positions == [1, 2]
        assert {policy.policy_id for policy in summary.applied_policies} == {
            "content_rewrite",
            "multi_object_write",
        }

    def test_xianxia_profile_lowers_long_form_overwrite_threshold(self) -> None:
        """The xianxia profile should classify shorter overwrite content as high-risk."""
        medium_content = " ".join(["夜色沉坠，皇城如渊。"] * 18)

        default_classified = agent_risk_service.classify_operations(
            [
                {
                    "tool_name": "write_chapter_content",
                    "description": "默认 profile 下重写章节正文",
                    "payload": {
                        "chapter_number": 1,
                        "mode": "replace",
                        "content": medium_content,
                    },
                }
            ]
        )
        xianxia_classified = agent_risk_service.classify_operations(
            [
                {
                    "tool_name": "write_chapter_content",
                    "description": "仙侠 profile 下重写章节正文",
                    "payload": {
                        "chapter_number": 1,
                        "mode": "replace",
                        "content": medium_content,
                    },
                }
            ],
            profile_id="xianxia_intrigue",
        )

        assert default_classified[0]["permission_level"] == "standard_write"
        assert default_classified[0]["risk_level"] == "medium"
        assert xianxia_classified[0]["permission_level"] == "high_risk_write"
        assert xianxia_classified[0]["risk_level"] == "high"
        assert xianxia_classified[0]["requires_secondary_confirmation"] is True
