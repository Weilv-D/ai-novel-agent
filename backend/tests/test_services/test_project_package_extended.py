"""Extended coverage for project package export/import helpers."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.chapter import Chapter, Scene, Volume
from app.models.character import Character
from app.models.dependency import Dependency
from app.models.memory import Memory
from app.models.project import Project
from app.models.snapshot import Snapshot
from app.models.world_setting import WorldSetting
from app.schemas.project_package import ProjectBundle, ProjectPackageManifest
from app.services.project_package import project_package_service


class ScalarResult:
    """Mimic SQLAlchemy scalar result access used in the service."""

    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class SingleResult:
    """Mimic scalar_one_or_none() for project root lookup."""

    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


def _project(project_id: uuid.UUID) -> Project:
    project = Project(
        id=project_id,
        name="测试项目",
        genre="Fantasy",
        summary="项目简介",
        story_outline="项目大纲",
        notes="项目备注",
        meta={},
    )
    project.agent_profile_id = "xianxia_intrigue"
    project.created_at = datetime.now(UTC)
    project.updated_at = datetime.now(UTC)
    return project


class TestProjectPackageServiceExtended:
    """Covers export/import paths and helper routines."""

    @pytest.mark.asyncio
    async def test_export_package_writes_manifest_and_bundle(self) -> None:
        """export_package() should emit a complete manifest + bundle zip."""
        project_id = uuid.uuid4()
        project = _project(project_id)
        character = Character(
            id=uuid.uuid4(),
            project_id=project_id,
            name="主角",
            role="protagonist",
            profile={"age": 18},
            relationships={},
            arc_state={},
            notes="人物备注",
        )
        character.created_at = datetime.now(UTC)
        character.updated_at = datetime.now(UTC)

        empty_groups = ([], [], [], [], [], [], [], [])
        records = ([character], *empty_groups[1:])
        mock_db = MagicMock()

        with patch.object(project_package_service, "_get_project_with_relations", new_callable=AsyncMock) as mock_project:
            with patch.object(project_package_service, "_list_project_records", new_callable=AsyncMock) as mock_records:
                mock_project.return_value = project
                mock_records.return_value = records

                zip_bytes, filename = await project_package_service.export_package(
                    mock_db,
                    project_id=project_id,
                )

        assert filename.startswith("测试项目_package_")
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))
            bundle = json.loads(zf.read("project_bundle.json"))

        assert manifest["source_project_id"] == str(project_id)
        assert manifest["agent_profile_id"] == "xianxia_intrigue"
        assert bundle["project"]["name"] == "测试项目"
        assert bundle["characters"][0]["name"] == "主角"
        assert bundle["characters"][0]["id"] == str(character.id)

    @pytest.mark.asyncio
    async def test_get_project_with_relations_returns_and_raises(self) -> None:
        """_get_project_with_relations() should return the project or raise ValueError."""
        project_id = uuid.uuid4()
        project = _project(project_id)
        db = MagicMock()
        db.execute = AsyncMock(return_value=SingleResult(project))

        loaded = await project_package_service._get_project_with_relations(db, project_id=project_id)
        assert loaded.id == project_id

        db.execute = AsyncMock(return_value=SingleResult(None))
        with pytest.raises(ValueError, match="Project not found"):
            await project_package_service._get_project_with_relations(db, project_id=project_id)

    @pytest.mark.asyncio
    async def test_list_project_records_loads_all_tables_and_scenes(self) -> None:
        """_list_project_records() should query all project tables and related scenes."""
        project_id = uuid.uuid4()
        chapter_id = uuid.uuid4()
        character = Character(id=uuid.uuid4(), project_id=project_id, name="主角", role=None, profile={}, relationships={}, arc_state={}, notes=None)
        world_setting = WorldSetting(id=uuid.uuid4(), project_id=project_id, category="history", name="王朝", content="设定", meta={})
        volume = Volume(id=uuid.uuid4(), project_id=project_id, volume_number=1, title="卷一", outline=None, notes=None)
        chapter = Chapter(id=chapter_id, project_id=project_id, volume_id=volume.id, chapter_number=1, title="第一章", outline=None, content=None, status="draft", notes=None)
        scene = Scene(id=uuid.uuid4(), chapter_id=chapter_id, scene_order=1, pov_character_id=None, location="客栈", content="场景", meta={})
        dependency = Dependency(id=uuid.uuid4(), project_id=project_id, source_type="character", source_id=character.id, target_type="world_setting", target_id=world_setting.id, dependency_type="references")
        snapshot = Snapshot(id=uuid.uuid4(), project_id=project_id, target_type="character", target_id=character.id, data={"name": "主角"})
        memory = Memory(id=uuid.uuid4(), project_id=project_id, memory_type="fact", content="记忆", embedding=None, meta={})

        db = MagicMock()
        db.execute = AsyncMock(
            side_effect=[
                ScalarResult([character]),
                ScalarResult([world_setting]),
                ScalarResult([volume]),
                ScalarResult([chapter]),
                ScalarResult([scene]),
                ScalarResult([dependency]),
                ScalarResult([snapshot]),
                ScalarResult([memory]),
            ]
        )

        records = await project_package_service._list_project_records(db, project_id=project_id)

        assert records == ([character], [world_setting], [volume], [chapter], [scene], [dependency], [snapshot], [memory])
        assert db.execute.await_count == 8

    @pytest.mark.asyncio
    async def test_import_package_rebuilds_project_graph(self) -> None:
        """import_package() should recreate the full object graph and preserve mappings."""
        settings = SimpleNamespace(embedding_dimension=1536)
        old_project_id = uuid.uuid4()
        old_character_id = uuid.uuid4()
        old_world_setting_id = uuid.uuid4()
        old_volume_id = uuid.uuid4()
        old_chapter_id = uuid.uuid4()
        old_scene_id = uuid.uuid4()
        old_dependency_id = uuid.uuid4()
        old_snapshot_id = uuid.uuid4()
        old_memory_id = uuid.uuid4()

        manifest = ProjectPackageManifest(
            package_version="1.1.0",
            exported_at=datetime.now(UTC),
            app_version="0.1.0",
            source_project_id=old_project_id,
            source_project_name="旧项目",
            agent_profile_id="default",
            embedding_dimension=1536,
        )
        bundle = ProjectBundle(
            project={
                "id": str(old_project_id),
                "name": "旧项目",
                "genre": "Fantasy",
                "summary": "摘要",
                "story_outline": "总纲",
                "notes": "备注",
                "meta": {"agent_profile_id": "default"},
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
            characters=[
                {
                    "id": str(old_character_id),
                    "project_id": str(old_project_id),
                    "name": "主角",
                    "role": "hero",
                    "profile": {},
                    "relationships": {},
                    "arc_state": {},
                    "notes": None,
                }
            ],
            world_settings=[
                {
                    "id": str(old_world_setting_id),
                    "project_id": str(old_project_id),
                    "category": "history",
                    "name": "王朝",
                    "content": "设定",
                    "meta": {},
                }
            ],
            volumes=[
                {
                    "id": str(old_volume_id),
                    "project_id": str(old_project_id),
                    "volume_number": 1,
                    "title": "卷一",
                    "outline": None,
                    "notes": None,
                }
            ],
            chapters=[
                {
                    "id": str(old_chapter_id),
                    "project_id": str(old_project_id),
                    "volume_id": str(old_volume_id),
                    "chapter_number": 1,
                    "title": "第一章",
                    "outline": None,
                    "content": "章节内容",
                    "status": "draft",
                    "notes": None,
                }
            ],
            scenes=[
                {
                    "id": str(old_scene_id),
                    "chapter_id": str(old_chapter_id),
                    "scene_order": 1,
                    "pov_character_id": str(old_character_id),
                    "location": "客栈",
                    "content": "场景内容",
                    "meta": {},
                }
            ],
            dependencies=[
                {
                    "id": str(old_dependency_id),
                    "project_id": str(old_project_id),
                    "source_type": "character",
                    "source_id": str(old_character_id),
                    "target_type": "world_setting",
                    "target_id": str(old_world_setting_id),
                    "dependency_type": "references",
                }
            ],
            snapshots=[
                {
                    "id": str(old_snapshot_id),
                    "project_id": str(old_project_id),
                    "target_type": "character",
                    "target_id": str(old_character_id),
                    "data": {"name": "主角"},
                }
            ],
            memories=[
                {
                    "id": str(old_memory_id),
                    "project_id": str(old_project_id),
                    "memory_type": "fact",
                    "content": "记忆",
                    "embedding": [0.1, 0.2],
                    "meta": {},
                }
            ],
        )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest.model_dump(mode="json")))
            zf.writestr("project_bundle.json", json.dumps(bundle.model_dump(mode="json")))

        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        with patch("app.services.project_package.get_settings", return_value=settings):
            response = await project_package_service.import_package(
                db,
                zip_bytes=zip_buffer.getvalue(),
                new_name="导入副本",
            )

        assert response.project_name == "导入副本"
        assert response.imported_counts == {
            "characters": 1,
            "world_settings": 1,
            "volumes": 1,
            "chapters": 1,
            "scenes": 1,
            "dependencies": 1,
            "snapshots": 1,
            "memories": 1,
        }
        db.commit.assert_awaited_once()

        added_models = [call.args[0] for call in db.add.call_args_list]
        imported_project = next(model for model in added_models if isinstance(model, Project))
        imported_volume = next(model for model in added_models if isinstance(model, Volume))
        imported_chapter = next(model for model in added_models if isinstance(model, Chapter))
        imported_scene = next(model for model in added_models if isinstance(model, Scene))
        imported_dependency = next(model for model in added_models if isinstance(model, Dependency))
        imported_snapshot = next(model for model in added_models if isinstance(model, Snapshot))
        imported_memory = next(model for model in added_models if isinstance(model, Memory))

        assert imported_project.name == "导入副本"
        assert imported_chapter.project_id == imported_project.id
        assert imported_chapter.volume_id == imported_volume.id
        assert imported_scene.chapter_id == imported_chapter.id
        assert imported_dependency.project_id == imported_project.id
        assert imported_snapshot.project_id == imported_project.id
        assert imported_memory.project_id == imported_project.id
        assert imported_memory.embedding == [0.1, 0.2]

    @pytest.mark.asyncio
    async def test_import_package_emits_dimension_warning_and_clears_memory_embedding(self) -> None:
        """Embedding mismatches should produce a warning and clear imported memory vectors."""
        db = MagicMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        old_memory_id = uuid.uuid4()
        new_project_id = uuid.uuid4()
        id_mapping: dict[str, uuid.UUID] = {}

        old_id, memory = await project_package_service._import_memory(
            db,
            mem_data={
                "id": str(old_memory_id),
                "project_id": str(uuid.uuid4()),
                "memory_type": "fact",
                "content": "记忆",
                "embedding": [0.1, 0.2, 0.3],
                "meta": {},
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
            new_project_id=new_project_id,
            id_mapping=id_mapping,
            embedding_dimension=1536,
            manifest_dimension=512,
        )

        assert old_id == str(old_memory_id)
        assert memory.project_id == new_project_id
        assert memory.embedding is None

    def test_serialize_model_converts_uuid_and_datetime(self) -> None:
        """_serialize_model() should emit JSON-friendly UUID and datetime values."""
        project_id = uuid.uuid4()
        created_at = datetime.now(UTC)
        project = Project(
            id=project_id,
            name="测试项目",
            genre="Fantasy",
            summary=None,
            story_outline=None,
            notes=None,
            meta={},
        )
        project.created_at = created_at
        project.updated_at = created_at

        serialized = project_package_service._serialize_model(project)

        assert serialized["id"] == str(project_id)
        assert serialized["created_at"] == created_at.isoformat()
