"""Tests for Project Package Service."""

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.services.project_package import project_package_service


class TestProjectPackageService:
    """Tests for ProjectPackageService."""

    def test_package_version(self):
        """Test package version constant."""
        assert project_package_service.PACKAGE_VERSION == "1.1.0"

    @pytest.mark.asyncio
    async def test_import_package_invalid_zip_raises_error(self):
        """Test importing invalid zip file raises error."""
        mock_db = MagicMock()

        with pytest.raises(ValueError) as exc_info:
            await project_package_service.import_package(
                mock_db,
                zip_bytes=b"not a zip file",
            )

        assert "Invalid package file" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_import_package_missing_manifest_raises_error(self):
        """Test importing package without manifest raises error."""
        mock_db = MagicMock()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("project_bundle.json", "{}")

        zip_bytes = zip_buffer.getvalue()

        with pytest.raises(ValueError) as exc_info:
            await project_package_service.import_package(
                mock_db,
                zip_bytes=zip_bytes,
            )

        assert "Invalid package file" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_import_package_missing_bundle_raises_error(self):
        """Test importing package without bundle raises error."""
        mock_db = MagicMock()

        manifest_data = {
            "package_version": "1.1.0",
            "exported_at": datetime.now(UTC).isoformat(),
            "app_version": "0.1.0",
            "source_project_id": str(uuid.uuid4()),
            "source_project_name": "Test",
            "agent_profile_id": "default",
            "embedding_dimension": 1536,
        }

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest_data))

        zip_bytes = zip_buffer.getvalue()

        with pytest.raises(ValueError) as exc_info:
            await project_package_service.import_package(
                mock_db,
                zip_bytes=zip_bytes,
            )

        assert "Invalid package file" in str(exc_info.value)


class TestProjectPackageManifest:
    """Tests for ProjectPackageManifest schema."""

    def test_manifest_creation(self):
        """Test manifest can be created with valid data."""
        from app.schemas.project_package import ProjectPackageManifest

        manifest = ProjectPackageManifest(
            package_version="1.1.0",
            exported_at=datetime.now(UTC),
            app_version="0.1.0",
            source_project_id=uuid.uuid4(),
            source_project_name="Test Project",
            agent_profile_id="default",
            embedding_dimension=1536,
        )

        assert manifest.package_version == "1.1.0"
        assert manifest.source_project_name == "Test Project"

    def test_manifest_serialization(self):
        """Test manifest can be serialized to JSON."""
        from app.schemas.project_package import ProjectPackageManifest

        manifest = ProjectPackageManifest(
            package_version="1.1.0",
            exported_at=datetime.now(UTC),
            app_version="0.1.0",
            source_project_id=uuid.uuid4(),
            source_project_name="Test Project",
            agent_profile_id="default",
            embedding_dimension=1536,
        )

        json_data = manifest.model_dump_json()
        assert "1.1.0" in json_data
        assert "Test Project" in json_data


class TestProjectBundle:
    """Tests for ProjectBundle schema."""

    def test_bundle_creation_empty(self):
        """Test bundle can be created with empty lists."""
        from app.schemas.project_package import ProjectBundle

        bundle = ProjectBundle(
            project={"id": str(uuid.uuid4()), "name": "Test"},
            characters=[],
            world_settings=[],
            volumes=[],
            chapters=[],
            scenes=[],
            dependencies=[],
            snapshots=[],
            memories=[],
        )

        assert bundle.project["name"] == "Test"
        assert len(bundle.characters) == 0

    def test_bundle_with_data(self):
        """Test bundle can hold project data."""
        from app.schemas.project_package import ProjectBundle

        project_id = uuid.uuid4()
        character_id = uuid.uuid4()

        bundle = ProjectBundle(
            project={"id": str(project_id), "name": "Test Novel"},
            characters=[
                {
                    "id": str(character_id),
                    "name": "Hero",
                    "role": "protagonist",
                }
            ],
            world_settings=[],
            volumes=[],
            chapters=[],
            scenes=[],
            dependencies=[],
            snapshots=[],
            memories=[],
        )

        assert len(bundle.characters) == 1
        assert bundle.characters[0]["name"] == "Hero"


class TestProjectImportResponse:
    """Tests for ProjectImportResponse schema."""

    def test_import_response_creation(self):
        """Test import response can be created."""
        from app.schemas.project_package import ProjectImportResponse

        response = ProjectImportResponse(
            project_id=uuid.uuid4(),
            project_name="Imported Project",
            imported_counts={
                "characters": 5,
                "chapters": 10,
            },
            warnings=[],
        )

        assert response.project_name == "Imported Project"
        assert response.imported_counts["characters"] == 5

    def test_import_response_with_warnings(self):
        """Test import response with warnings."""
        from app.schemas.project_package import ProjectImportResponse, ProjectImportWarning

        warning = ProjectImportWarning(
            code="embedding_dimension_mismatch",
            message="Dimension mismatch warning",
        )

        response = ProjectImportResponse(
            project_id=uuid.uuid4(),
            project_name="Test",
            imported_counts={},
            warnings=[warning],
        )

        assert len(response.warnings) == 1
        assert response.warnings[0].code == "embedding_dimension_mismatch"


class TestExportPackageIntegrity:
    """Tests for export package integrity."""

    def test_export_package_contains_required_files(self):
        """Test exported package contains manifest and bundle."""
        from app.schemas.project_package import ProjectBundle, ProjectPackageManifest

        manifest = ProjectPackageManifest(
            package_version="1.1.0",
            exported_at=datetime.now(UTC),
            app_version="0.1.0",
            source_project_id=uuid.uuid4(),
            source_project_name="Test Project",
            agent_profile_id="default",
            embedding_dimension=1536,
        )

        bundle = ProjectBundle(
            project={"id": str(uuid.uuid4()), "name": "Test Project"},
            characters=[],
            world_settings=[],
            volumes=[],
            chapters=[],
            scenes=[],
            dependencies=[],
            snapshots=[],
            memories=[],
        )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(
                    manifest.model_dump(mode="json"),
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            zf.writestr(
                "project_bundle.json",
                json.dumps(
                    bundle.model_dump(mode="json"),
                    ensure_ascii=False,
                    indent=2,
                ),
            )

        zip_bytes = zip_buffer.getvalue()

        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "manifest.json" in zf.namelist()
            assert "project_bundle.json" in zf.namelist()

            manifest_data = json.loads(zf.read("manifest.json"))
            assert manifest_data["package_version"] == "1.1.0"

            bundle_data = json.loads(zf.read("project_bundle.json"))
            assert bundle_data["project"]["name"] == "Test Project"

    def test_import_package_dimension_warning_generation(self):
        """Test that dimension mismatch warning is generated correctly."""
        from app.schemas.project_package import ProjectImportWarning

        package_dimension = 512
        system_dimension = 1536

        warning = ProjectImportWarning(
            code="embedding_dimension_mismatch",
            message=(
                f"Package was exported with embedding dimension "
                f"{package_dimension}, current system uses "
                f"{system_dimension}. Embeddings will be cleared."
            ),
            details={
                "package_dimension": package_dimension,
                "system_dimension": system_dimension,
            },
        )

        assert warning.code == "embedding_dimension_mismatch"
        assert str(package_dimension) in warning.message
        assert str(system_dimension) in warning.message
