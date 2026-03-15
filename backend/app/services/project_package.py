"""Project package export/import service."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.chapter import Chapter, Scene, Volume
from app.models.character import Character
from app.models.dependency import Dependency
from app.models.memory import Memory
from app.models.project import Project
from app.models.snapshot import Snapshot
from app.models.world_setting import WorldSetting
from app.schemas.project_package import (
    ProjectBundle,
    ProjectImportResponse,
    ProjectImportWarning,
    ProjectPackageManifest,
)


class ProjectPackageService:
    """Service for exporting and importing project packages."""

    PACKAGE_VERSION = "1.0.0"

    async def export_package(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
    ) -> tuple[bytes, str]:
        """Export a project as a zip package.

        Returns the zip bytes and suggested filename.
        """
        project = await self._get_project_with_relations(db, project_id=project_id)

        settings = get_settings()

        manifest = ProjectPackageManifest(
            package_version=self.PACKAGE_VERSION,
            exported_at=datetime.now(UTC),
            app_version=settings.app_version,
            source_project_id=project.id,
            source_project_name=project.name,
            agent_profile_id=project.agent_profile_id,
            embedding_dimension=settings.embedding_dimension,
        )

        bundle = ProjectBundle(
            project=self._serialize_model(project),
            characters=[self._serialize_model(c) for c in project.characters],  # type: ignore[attr-defined]
            world_settings=[self._serialize_model(ws) for ws in project.world_settings],  # type: ignore[attr-defined]
            volumes=[self._serialize_model(v) for v in project.volumes],  # type: ignore[attr-defined]
            chapters=[],
            scenes=[],
            dependencies=[self._serialize_model(d) for d in project.dependencies],  # type: ignore[attr-defined]
            snapshots=[self._serialize_model(s) for s in project.snapshots],  # type: ignore[attr-defined]
            memories=[self._serialize_model(m) for m in project.memories],  # type: ignore[attr-defined]
        )

        for volume in project.volumes:  # type: ignore[attr-defined]
            for chapter in volume.chapters:
                bundle.chapters.append(self._serialize_model(chapter))
                for scene in chapter.scenes:
                    bundle.scenes.append(self._serialize_model(scene))

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

        filename = f"{project.name}_package_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.zip"
        return zip_buffer.getvalue(), filename

    async def import_package(
        self,
        db: AsyncSession,
        *,
        zip_bytes: bytes,
        new_name: str | None = None,
    ) -> ProjectImportResponse:
        """Import a project from a zip package.

        Creates a new project as a copy of the exported project.
        """
        warnings: list[ProjectImportWarning] = []
        id_mapping: dict[str, uuid.UUID] = {}

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
                manifest_data = json.loads(zf.read("manifest.json"))
                bundle_data = json.loads(zf.read("project_bundle.json"))
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid package file: {e}") from e

        manifest = ProjectPackageManifest.model_validate(manifest_data)
        bundle = ProjectBundle.model_validate(bundle_data)

        settings = get_settings()
        if manifest.embedding_dimension != settings.embedding_dimension:
            warnings.append(
                ProjectImportWarning(
                    code="embedding_dimension_mismatch",
                    message=(
                        f"Package was exported with embedding dimension "
                        f"{manifest.embedding_dimension}, current system uses "
                        f"{settings.embedding_dimension}. Embeddings will be cleared."
                    ),
                    details={
                        "package_dimension": manifest.embedding_dimension,
                        "system_dimension": settings.embedding_dimension,
                    },
                )
            )

        project_data = dict(bundle.project)
        new_project_id = uuid.uuid4()
        id_mapping[str(project_data["id"])] = new_project_id

        project_data["id"] = new_project_id
        project_data["name"] = new_name or f"{project_data['name']} (导入副本)"
        for field in ("created_at", "updated_at"):
            if field in project_data:
                del project_data[field]

        new_project = Project(**project_data)
        db.add(new_project)
        await db.flush()

        imported_counts: dict[str, int] = {}

        for char_data in bundle.characters:
            old_id, new_char = await self._import_character(
                db,
                char_data=char_data,
                new_project_id=new_project_id,
                id_mapping=id_mapping,
            )
            id_mapping[old_id] = new_char.id
            imported_counts["characters"] = imported_counts.get("characters", 0) + 1

        for ws_data in bundle.world_settings:
            old_id, new_ws = await self._import_world_setting(
                db,
                ws_data=ws_data,
                new_project_id=new_project_id,
                id_mapping=id_mapping,
            )
            id_mapping[old_id] = new_ws.id
            imported_counts["world_settings"] = imported_counts.get("world_settings", 0) + 1

        for vol_data in bundle.volumes:
            old_id, new_vol = await self._import_volume(
                db,
                vol_data=vol_data,
                new_project_id=new_project_id,
                id_mapping=id_mapping,
            )
            id_mapping[old_id] = new_vol.id
            imported_counts["volumes"] = imported_counts.get("volumes", 0) + 1

        for ch_data in bundle.chapters:
            old_id, new_ch = await self._import_chapter(
                db,
                ch_data=ch_data,
                id_mapping=id_mapping,
            )
            id_mapping[old_id] = new_ch.id
            imported_counts["chapters"] = imported_counts.get("chapters", 0) + 1

        for scene_data in bundle.scenes:
            old_id, new_scene = await self._import_scene(
                db,
                scene_data=scene_data,
                id_mapping=id_mapping,
                embedding_dimension=settings.embedding_dimension,
                manifest_dimension=manifest.embedding_dimension,
            )
            id_mapping[old_id] = new_scene.id
            imported_counts["scenes"] = imported_counts.get("scenes", 0) + 1

        for dep_data in bundle.dependencies:
            old_id, new_dep = await self._import_dependency(
                db,
                dep_data=dep_data,
                new_project_id=new_project_id,
                id_mapping=id_mapping,
            )
            id_mapping[old_id] = new_dep.id
            imported_counts["dependencies"] = imported_counts.get("dependencies", 0) + 1

        for snap_data in bundle.snapshots:
            old_id, new_snap = await self._import_snapshot(
                db,
                snap_data=snap_data,
                id_mapping=id_mapping,
            )
            id_mapping[old_id] = new_snap.id
            imported_counts["snapshots"] = imported_counts.get("snapshots", 0) + 1

        for mem_data in bundle.memories:
            old_id, new_mem = await self._import_memory(
                db,
                mem_data=mem_data,
                new_project_id=new_project_id,
                id_mapping=id_mapping,
                embedding_dimension=settings.embedding_dimension,
                manifest_dimension=manifest.embedding_dimension,
            )
            id_mapping[old_id] = new_mem.id
            imported_counts["memories"] = imported_counts.get("memories", 0) + 1

        await db.commit()

        return ProjectImportResponse(
            project_id=new_project_id,
            project_name=new_project.name,
            imported_counts=imported_counts,
            warnings=warnings,
        )

    async def _get_project_with_relations(
        self,
        db: AsyncSession,
        *,
        project_id: uuid.UUID,
    ) -> Project:
        """Load a project with all related objects."""
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.characters),  # type: ignore[attr-defined]
                selectinload(Project.world_settings),  # type: ignore[attr-defined]
                selectinload(Project.volumes).selectinload(  # type: ignore[attr-defined]
                    Volume.chapters  # type: ignore[attr-defined]
                ).selectinload(Chapter.scenes),  # type: ignore[attr-defined]
                selectinload(Project.dependencies),  # type: ignore[attr-defined]
                selectinload(Project.snapshots),  # type: ignore[attr-defined]
                selectinload(Project.memories),  # type: ignore[attr-defined]
            )
        )
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        if project is None:
            raise ValueError(f"Project not found: {project_id}")
        return project

    def _serialize_model(self, model: Any) -> dict[str, Any]:
        """Serialize a SQLAlchemy model to a dictionary."""
        result = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            if isinstance(value, uuid.UUID):
                result[column.name] = str(value)
            elif isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result

    async def _import_character(
        self,
        db: AsyncSession,
        *,
        char_data: dict[str, Any],
        new_project_id: uuid.UUID,
        id_mapping: dict[str, uuid.UUID],
    ) -> tuple[str, Character]:
        """Import a character record."""
        data = dict(char_data)
        old_id = str(data["id"])
        data["id"] = uuid.uuid4()
        data["project_id"] = new_project_id
        for field in ("created_at", "updated_at"):
            if field in data:
                del data[field]

        char = Character(**data)
        db.add(char)
        await db.flush()
        return old_id, char

    async def _import_world_setting(
        self,
        db: AsyncSession,
        *,
        ws_data: dict[str, Any],
        new_project_id: uuid.UUID,
        id_mapping: dict[str, uuid.UUID],
    ) -> tuple[str, WorldSetting]:
        """Import a world setting record."""
        data = dict(ws_data)
        old_id = str(data["id"])
        data["id"] = uuid.uuid4()
        data["project_id"] = new_project_id
        for field in ("created_at", "updated_at"):
            if field in data:
                del data[field]

        ws = WorldSetting(**data)
        db.add(ws)
        await db.flush()
        return old_id, ws

    async def _import_volume(
        self,
        db: AsyncSession,
        *,
        vol_data: dict[str, Any],
        new_project_id: uuid.UUID,
        id_mapping: dict[str, uuid.UUID],
    ) -> tuple[str, Volume]:
        """Import a volume record."""
        data = dict(vol_data)
        old_id = str(data["id"])
        data["id"] = uuid.uuid4()
        data["project_id"] = new_project_id
        for field in ("created_at", "updated_at"):
            if field in data:
                del data[field]

        vol = Volume(**data)
        db.add(vol)
        await db.flush()
        return old_id, vol

    async def _import_chapter(
        self,
        db: AsyncSession,
        *,
        ch_data: dict[str, Any],
        id_mapping: dict[str, uuid.UUID],
    ) -> tuple[str, Chapter]:
        """Import a chapter record."""
        data = dict(ch_data)
        old_id = str(data["id"])
        data["id"] = uuid.uuid4()
        data["project_id"] = id_mapping[str(data["project_id"])]
        data["volume_id"] = id_mapping.get(str(data.get("volume_id", "")))
        for field in ("created_at", "updated_at"):
            if field in data:
                del data[field]

        ch = Chapter(**data)
        db.add(ch)
        await db.flush()
        return old_id, ch

    async def _import_scene(
        self,
        db: AsyncSession,
        *,
        scene_data: dict[str, Any],
        id_mapping: dict[str, uuid.UUID],
        embedding_dimension: int,
        manifest_dimension: int,
    ) -> tuple[str, Scene]:
        """Import a scene record."""
        data = dict(scene_data)
        old_id = str(data["id"])
        data["id"] = uuid.uuid4()
        data["chapter_id"] = id_mapping[str(data["chapter_id"])]
        if data.get("pov_character_id"):
            data["pov_character_id"] = id_mapping.get(str(data["pov_character_id"]))
        for field in ("created_at", "updated_at"):
            if field in data:
                del data[field]

        scene = Scene(**data)
        db.add(scene)
        await db.flush()
        return old_id, scene

    async def _import_dependency(
        self,
        db: AsyncSession,
        *,
        dep_data: dict[str, Any],
        new_project_id: uuid.UUID,
        id_mapping: dict[str, uuid.UUID],
    ) -> tuple[str, Dependency]:
        """Import a dependency record."""
        data = dict(dep_data)
        old_id = str(data["id"])
        data["id"] = uuid.uuid4()
        data["project_id"] = new_project_id
        data["source_id"] = id_mapping.get(str(data.get("source_id", "")))
        data["target_id"] = id_mapping.get(str(data.get("target_id", "")))
        for field in ("created_at", "updated_at"):
            if field in data:
                del data[field]

        dep = Dependency(**data)
        db.add(dep)
        await db.flush()
        return old_id, dep

    async def _import_snapshot(
        self,
        db: AsyncSession,
        *,
        snap_data: dict[str, Any],
        id_mapping: dict[str, uuid.UUID],
    ) -> tuple[str, Snapshot]:
        """Import a snapshot record."""
        data = dict(snap_data)
        old_id = str(data["id"])
        data["id"] = uuid.uuid4()
        data["project_id"] = id_mapping[str(data["project_id"])]
        if data.get("target_id"):
            data["target_id"] = id_mapping.get(str(data["target_id"]))
        for field in ("created_at", "updated_at"):
            if field in data:
                del data[field]

        snap = Snapshot(**data)
        db.add(snap)
        await db.flush()
        return old_id, snap

    async def _import_memory(
        self,
        db: AsyncSession,
        *,
        mem_data: dict[str, Any],
        new_project_id: uuid.UUID,
        id_mapping: dict[str, uuid.UUID],
        embedding_dimension: int,
        manifest_dimension: int,
    ) -> tuple[str, Memory]:
        """Import a memory record."""
        data = dict(mem_data)
        old_id = str(data["id"])
        data["id"] = uuid.uuid4()
        data["project_id"] = new_project_id
        if data.get("chapter_id"):
            data["chapter_id"] = id_mapping.get(str(data["chapter_id"]))
        for field in ("created_at", "updated_at"):
            if field in data:
                del data[field]

        if embedding_dimension != manifest_dimension:
            data["embedding"] = None

        mem = Memory(**data)
        db.add(mem)
        await db.flush()
        return old_id, mem


project_package_service = ProjectPackageService()
