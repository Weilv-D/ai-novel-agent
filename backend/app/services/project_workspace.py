"""Aggregated project workspace and tree helpers."""

from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.project import (
    ProjectAgentSettings,
    ProjectResponse,
    ProjectTreeChapterResponse,
    ProjectTreeResponse,
    ProjectTreeSceneResponse,
    ProjectTreeVolumeResponse,
    ProjectWorkspaceResponse,
    ProjectWorkspaceSummaryResponse,
)
from app.services.agent_workflow import agent_workflow_service
from app.services.chapter import chapter_service, scene_service, volume_service
from app.services.character import character_service
from app.services.project import project_service
from app.services.world_setting import world_setting_service


class ProjectWorkspaceService:
    """Build project tree and workspace aggregates for the frontend."""

    async def get_tree_response(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
    ) -> ProjectTreeResponse:
        project = await project_service.get(db, id=project_id)
        volumes = await volume_service.get_by_project(db, project_id=project.id, limit=500)
        chapters = await chapter_service.get_by_project(db, project_id=project.id, limit=1000)

        chapter_ids = [chapter.id for chapter in chapters]
        scenes_by_chapter: dict[UUID, list[ProjectTreeSceneResponse]] = {}
        for chapter_id in chapter_ids:
            scene_records = await scene_service.get_by_chapter(db, chapter_id=chapter_id, limit=500)
            scenes_by_chapter[chapter_id] = [ProjectTreeSceneResponse.model_validate(scene) for scene in scene_records]

        chapters_by_volume: dict[UUID, list[ProjectTreeChapterResponse]] = {}
        ungrouped_chapters: list[ProjectTreeChapterResponse] = []
        for chapter in chapters:
            chapter_node = ProjectTreeChapterResponse(
                id=chapter.id,
                project_id=chapter.project_id,
                volume_id=chapter.volume_id,
                chapter_number=chapter.chapter_number,
                title=chapter.title,
                outline=chapter.outline,
                status=chapter.status,
                scenes=scenes_by_chapter.get(chapter.id, []),
            )
            if chapter.volume_id is None:
                ungrouped_chapters.append(chapter_node)
                continue
            chapters_by_volume.setdefault(chapter.volume_id, []).append(chapter_node)

        volume_nodes = [
            ProjectTreeVolumeResponse(
                id=volume.id,
                project_id=volume.project_id,
                volume_number=volume.volume_number,
                title=volume.title,
                outline=volume.outline,
                chapters=chapters_by_volume.get(volume.id, []),
            )
            for volume in volumes
        ]
        return ProjectTreeResponse(
            project_id=project.id,
            volumes=volume_nodes,
            ungrouped_chapters=ungrouped_chapters,
        )

    async def get_workspace_response(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
    ) -> ProjectWorkspaceResponse:
        project = await project_service.get(db, id=project_id)
        tree = await self.get_tree_response(db, project_id=project_id)
        thread = await agent_workflow_service.get_or_create_thread_response(db, project_id=project_id)
        thread_state = await agent_workflow_service.get_thread_state_response(db, thread_id=thread.id)
        characters = await character_service.get_by_project(db, project_id=project_id, limit=500)
        world_settings = await world_setting_service.get_by_project(db, project_id=project_id, limit=500)
        chapter_count = sum(len(volume.chapters) for volume in tree.volumes) + len(tree.ungrouped_chapters)
        scene_count = sum(len(chapter.scenes) for volume in tree.volumes for chapter in volume.chapters) + sum(
            len(chapter.scenes) for chapter in tree.ungrouped_chapters
        )
        latest_run = thread_state.current_run or (thread_state.recent_runs[0] if thread_state.recent_runs else None)
        context_source = "live_context"
        if latest_run is not None and latest_run.active_bundle_contract is not None:
            context_source = latest_run.active_bundle_contract.source
        return ProjectWorkspaceResponse(
            project=ProjectResponse.model_validate(project),
            agent_settings=ProjectAgentSettings.model_validate(project.agent_settings),
            tree=tree,
            default_thread=thread_state.thread,
            latest_checkpoint=thread_state.latest_checkpoint,
            current_run=thread_state.current_run,
            recent_runs=thread_state.recent_runs,
            workspace_summary=ProjectWorkspaceSummaryResponse(
                volume_count=len(tree.volumes),
                chapter_count=chapter_count,
                scene_count=scene_count,
                character_count=len(characters),
                world_setting_count=len(world_settings),
                latest_run_status=cast(str | None, latest_run.status if latest_run is not None else None),
                context_source=context_source,
            ),
        )


project_workspace_service = ProjectWorkspaceService()
