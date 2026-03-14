"""Tests for dependency schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas import (
    DependencyCreate,
    DependencyQueryRequest,
    DependencyType,
    DependencyUpdate,
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
)


class TestDependencySchemas:
    """Tests for Dependency schemas."""

    def test_dependency_create_valid(self):
        """Test valid DependencyCreate schema."""
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        data = {
            "project_id": project_id,
            "source_type": "chapter",
            "source_id": source_id,
            "target_type": "character",
            "target_id": target_id,
            "dependency_type": "references",
        }
        schema = DependencyCreate(**data)
        assert schema.project_id == project_id
        assert schema.source_type == "chapter"
        assert schema.source_id == source_id
        assert schema.target_type == "character"
        assert schema.target_id == target_id
        assert schema.dependency_type == "references"

    def test_dependency_create_without_type(self):
        """Test DependencyCreate without dependency_type."""
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        schema = DependencyCreate(
            project_id=project_id,
            source_type="volume",
            source_id=source_id,
            target_type="chapter",
            target_id=target_id,
        )
        assert schema.dependency_type is None

    def test_dependency_update(self):
        """Test DependencyUpdate schema."""
        data = {
            "dependency_type": "influences",
        }
        schema = DependencyUpdate(**data)
        assert schema.dependency_type == "influences"

    def test_dependency_update_empty(self):
        """Test DependencyUpdate with no fields."""
        schema = DependencyUpdate()
        assert schema.dependency_type is None

    def test_dependency_type_valid_values(self):
        """Test valid dependency_type values."""
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        for dep_type in ["references", "influences", "contains", "precedes"]:
            schema = DependencyCreate(
                project_id=project_id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id,
                dependency_type=dep_type,
            )
            assert schema.dependency_type == dep_type

    def test_dependency_type_constants(self):
        """Test DependencyType constants."""
        assert DependencyType.REFERENCES == "references"
        assert DependencyType.INFLUENCES == "influences"
        assert DependencyType.CONTAINS == "contains"
        assert DependencyType.PRECEDES == "precedes"

    def test_entity_type_valid_values(self):
        """Test valid source_type and target_type values."""
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        valid_types = ["project", "character", "world_setting", "volume", "chapter", "scene", "suggestion"]
        for entity_type in valid_types:
            schema = DependencyCreate(
                project_id=project_id,
                source_type=entity_type,
                source_id=source_id,
                target_type="character",
                target_id=target_id,
            )
            assert schema.source_type == entity_type

    def test_dependency_query_request_empty(self):
        """Test DependencyQueryRequest with no filters."""
        schema = DependencyQueryRequest()
        assert schema.source_type is None
        assert schema.source_id is None
        assert schema.target_type is None
        assert schema.target_id is None
        assert schema.dependency_type is None

    def test_dependency_query_request_with_filters(self):
        """Test DependencyQueryRequest with filters."""
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        schema = DependencyQueryRequest(
            source_type="chapter",
            source_id=source_id,
            target_type="character",
            target_id=target_id,
            dependency_type="references",
        )
        assert schema.source_type == "chapter"
        assert schema.source_id == source_id
        assert schema.target_type == "character"
        assert schema.target_id == target_id
        assert schema.dependency_type == "references"

    def test_impact_analysis_request(self):
        """Test ImpactAnalysisRequest schema."""
        source_id = uuid.uuid4()
        schema = ImpactAnalysisRequest(
            source_type="character",
            source_id=source_id,
        )
        assert schema.source_type == "character"
        assert schema.source_id == source_id

    def test_impact_analysis_response(self):
        """Test ImpactAnalysisResponse schema."""
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        data = {
            "source_type": "character",
            "source_id": source_id,
            "impacted_objects": [
                {
                    "target_type": "chapter",
                    "target_id": target_id,
                    "dependency_type": "references",
                    "description": "Character appears in this chapter",
                }
            ],
            "total_count": 1,
            "analysis_summary": "Modifying this character affects 1 object(s)",
        }
        schema = ImpactAnalysisResponse(**data)
        assert schema.source_type == "character"
        assert schema.source_id == source_id
        assert len(schema.impacted_objects) == 1
        assert schema.total_count == 1
        assert schema.analysis_summary == "Modifying this character affects 1 object(s)"
        assert schema.impacted_objects[0].target_type == "chapter"

    def test_impact_detail(self):
        """Test ImpactDetail schema."""
        target_id = uuid.uuid4()
        from app.schemas import ImpactDetail

        data = {
            "target_type": "chapter",
            "target_id": target_id,
            "dependency_type": "references",
            "description": "Character appears in this chapter",
        }
        schema = ImpactDetail(**data)
        assert schema.target_type == "chapter"
        assert schema.target_id == target_id
        assert schema.dependency_type == "references"
        assert schema.description == "Character appears in this chapter"

    def test_impact_detail_without_description(self):
        """Test ImpactDetail without description."""
        target_id = uuid.uuid4()
        from app.schemas import ImpactDetail

        schema = ImpactDetail(
            target_type="chapter",
            target_id=target_id,
            dependency_type="contains",
        )
        assert schema.description is None

    def test_dependency_type_invalid_value(self):
        """Test invalid dependency_type value raises ValidationError."""
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            DependencyCreate(
                project_id=project_id,
                source_type="chapter",
                source_id=source_id,
                target_type="character",
                target_id=target_id,
                dependency_type="invalid_type",
            )
        assert "dependency_type" in str(exc_info.value).lower()

    def test_entity_type_invalid_value(self):
        """Test invalid source_type value raises ValidationError."""
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        with pytest.raises(ValidationError) as exc_info:
            DependencyCreate(
                project_id=project_id,
                source_type="invalid_entity",
                source_id=source_id,
                target_type="character",
                target_id=target_id,
            )
        assert "source_type" in str(exc_info.value).lower()
