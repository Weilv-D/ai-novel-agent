"""Tests for Dependency API endpoints."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.models.dependency import Dependency
from app.schemas.dependency import DependencyResponse, ImpactAnalysisResponse


class TestListDependencies:
    """Tests for GET /api/v1/dependencies."""

    def test_list_dependencies_empty(self):
        """Test listing dependencies when none exist."""
        client = TestClient(app)

        with patch("app.api.v1.dependencies.dependency_service.query_dependencies", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/dependencies?project_id={uuid.uuid4()}")

            assert response.status_code == status.HTTP_200_OK
            assert response.json() == []

    def test_list_dependencies_with_data(self):
        """Test listing dependencies with existing data."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_response = DependencyResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            source_type="chapter",
            source_id=source_id,
            target_type="character",
            target_id=target_id,
            dependency_type="references",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.dependencies.dependency_service.query_dependencies", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [mock_response]

            response = client.get(f"/api/v1/dependencies?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["source_type"] == "chapter"

    def test_list_dependencies_missing_project_id(self):
        """Test listing dependencies without project_id raises error."""
        client = TestClient(app)

        response = client.get("/api/v1/dependencies")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCreateDependency:
    """Tests for POST /api/v1/dependencies."""

    def test_create_dependency_valid(self):
        """Test creating a dependency with valid data."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        dependency_data = {
            "project_id": str(project_id),
            "source_type": "chapter",
            "source_id": str(source_id),
            "target_type": "character",
            "target_id": str(target_id),
            "dependency_type": "references",
        }

        mock_response = DependencyResponse(
            id=uuid.uuid4(),
            project_id=project_id,
            source_type="chapter",
            source_id=source_id,
            target_type="character",
            target_id=target_id,
            dependency_type="references",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "app.api.v1.dependencies.dependency_service.create_with_project", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            response = client.post("/api/v1/dependencies", json=dependency_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["source_type"] == "chapter"
            assert data["dependency_type"] == "references"

    def test_create_dependency_invalid_schema(self):
        """Test creating a dependency with invalid schema."""
        client = TestClient(app)

        # Missing required fields
        dependency_data = {"source_type": "chapter"}

        response = client.post("/api/v1/dependencies", json=dependency_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetDependency:
    """Tests for GET /api/v1/dependencies/{id}."""

    def test_get_dependency_found(self):
        """Test getting an existing dependency."""
        client = TestClient(app)
        dependency_id = uuid.uuid4()
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_response = DependencyResponse(
            id=dependency_id,
            project_id=project_id,
            source_type="chapter",
            source_id=source_id,
            target_type="character",
            target_id=target_id,
            dependency_type="references",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.dependencies.dependency_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            response = client.get(f"/api/v1/dependencies/{dependency_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(dependency_id)
            assert data["source_type"] == "chapter"

    def test_get_dependency_not_found(self):
        """Test getting a non-existent dependency."""
        client = TestClient(app)
        dependency_id = uuid.uuid4()

        from app.core.exceptions import NotFoundException

        with patch("app.api.v1.dependencies.dependency_service.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = NotFoundException("Dependency not found")

            response = client.get(f"/api/v1/dependencies/{dependency_id}")

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateDependency:
    """Tests for PATCH /api/v1/dependencies/{id}."""

    def test_update_dependency_valid(self):
        """Test updating a dependency with valid data."""
        client = TestClient(app)
        dependency_id = uuid.uuid4()
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_response = DependencyResponse(
            id=dependency_id,
            project_id=project_id,
            source_type="chapter",
            source_id=source_id,
            target_type="character",
            target_id=target_id,
            dependency_type="influences",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.dependencies.dependency_service.get", new_callable=AsyncMock) as mock_get:
            with patch("app.api.v1.dependencies.dependency_service.update", new_callable=AsyncMock) as mock_update:
                mock_get.return_value = mock_response
                mock_update.return_value = mock_response

                response = client.patch(
                    f"/api/v1/dependencies/{dependency_id}", json={"dependency_type": "influences"}
                )

                assert response.status_code == status.HTTP_200_OK


class TestDeleteDependency:
    """Tests for DELETE /api/v1/dependencies/{id}."""

    def test_delete_dependency_success(self):
        """Test deleting a dependency successfully."""
        client = TestClient(app)
        dependency_id = uuid.uuid4()
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_response = DependencyResponse(
            id=dependency_id,
            project_id=project_id,
            source_type="chapter",
            source_id=source_id,
            target_type="character",
            target_id=target_id,
            dependency_type="references",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("app.api.v1.dependencies.dependency_service.delete", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = mock_response

            response = client.delete(f"/api/v1/dependencies/{dependency_id}")

            assert response.status_code == status.HTTP_200_OK


class TestListSourceDependencies:
    """Tests for GET /api/v1/dependencies/source/{source_type}/{source_id}."""

    def test_list_source_dependencies(self):
        """Test listing dependencies for a specific source."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()

        with patch(
            "app.api.v1.dependencies.dependency_service.get_by_source", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/dependencies/source/chapter/{source_id}?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            mock_get.assert_called_once()


class TestListTargetDependencies:
    """Tests for GET /api/v1/dependencies/target/{target_type}/{target_id}."""

    def test_list_target_dependencies(self):
        """Test listing dependencies pointing to a specific target."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()

        with patch(
            "app.api.v1.dependencies.dependency_service.get_by_target", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = []

            response = client.get(f"/api/v1/dependencies/target/character/{target_id}?project_id={project_id}")

            assert response.status_code == status.HTTP_200_OK
            mock_get.assert_called_once()


class TestAnalyzeImpact:
    """Tests for POST /api/v1/dependencies/analyze."""

    def test_analyze_impact(self):
        """Test analyzing impact of modifying a source object."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        from app.schemas import ImpactDetail

        mock_impacts = [
            ImpactDetail(
                target_type="chapter",
                target_id=target_id,
                dependency_type="references",
                description="Character appears in this chapter",
            )
        ]

        with patch(
            "app.api.v1.dependencies.dependency_service.analyze_impact", new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = mock_impacts

            response = client.post(
                f"/api/v1/dependencies/analyze?project_id={project_id}",
                json={"source_type": "character", "source_id": str(source_id)},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["source_type"] == "character"
            assert data["total_count"] == 1
            assert len(data["impacted_objects"]) == 1

    def test_analyze_impact_empty(self):
        """Test analyzing impact when no dependencies exist."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        source_id = uuid.uuid4()

        with patch(
            "app.api.v1.dependencies.dependency_service.analyze_impact", new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = []

            response = client.post(
                f"/api/v1/dependencies/analyze?project_id={project_id}",
                json={"source_type": "character", "source_id": str(source_id)},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_count"] == 0
            assert len(data["impacted_objects"]) == 0


class TestAnalyzeReverseImpact:
    """Tests for POST /api/v1/dependencies/analyze/reverse/{target_type}/{target_id}."""

    def test_analyze_reverse_impact(self):
        """Test analyzing reverse impact (what depends on this target)."""
        client = TestClient(app)
        project_id = uuid.uuid4()
        target_id = uuid.uuid4()
        source_id = uuid.uuid4()

        from app.schemas import ImpactDetail

        mock_impacts = [
            ImpactDetail(
                target_type="chapter",
                target_id=source_id,
                dependency_type="references",
                description="Chapter references this character",
            )
        ]

        with patch(
            "app.api.v1.dependencies.dependency_service.analyze_reverse_impact", new_callable=AsyncMock
        ) as mock_analyze:
            mock_analyze.return_value = mock_impacts

            response = client.post(
                f"/api/v1/dependencies/analyze/reverse/character/{target_id}?project_id={project_id}"
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["source_type"] == "character"
            assert data["total_count"] == 1
            assert len(data["impacted_objects"]) == 1
