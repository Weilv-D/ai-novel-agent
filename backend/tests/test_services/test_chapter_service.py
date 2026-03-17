"""Integration tests for Chapter/Scene/Volume service layer with real DB."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.schemas.chapter import ChapterCreate, SceneCreate, VolumeCreate
from app.schemas.project import ProjectCreate
from app.services.chapter import chapter_service, scene_service, volume_service
from app.services.project import project_service


class TestVolumeServiceGetByProject:
    """Tests for volume_service.get_by_project with real database."""

    @pytest.mark.asyncio
    async def test_get_by_project_empty(self, db_session: AsyncSession):
        """Test get_by_project returns empty list when no volumes exist."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        result = await volume_service.get_by_project(db_session, project_id=project.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_project_with_volumes(self, db_session: AsyncSession):
        """Test get_by_project returns volumes for specific project."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        # Create volumes
        await volume_service.create_with_project(
            db_session,
            obj_in=VolumeCreate(title="Volume 1", volume_number=1, project_id=project.id),
            project_id=project.id,
        )
        await volume_service.create_with_project(
            db_session,
            obj_in=VolumeCreate(title="Volume 2", volume_number=2, project_id=project.id),
            project_id=project.id,
        )

        # Get volumes for project
        result = await volume_service.get_by_project(db_session, project_id=project.id)
        assert len(result) == 2
        # Should be ordered by volume_number
        assert result[0].volume_number == 1
        assert result[1].volume_number == 2

    @pytest.mark.asyncio
    async def test_get_by_project_ordering(self, db_session: AsyncSession):
        """Test get_by_project orders by volume_number ascending."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        # Create volumes in non-sequential order
        await volume_service.create_with_project(
            db_session,
            obj_in=VolumeCreate(title="Volume 3", volume_number=3, project_id=project.id),
            project_id=project.id,
        )
        await volume_service.create_with_project(
            db_session,
            obj_in=VolumeCreate(title="Volume 1", volume_number=1, project_id=project.id),
            project_id=project.id,
        )
        await volume_service.create_with_project(
            db_session,
            obj_in=VolumeCreate(title="Volume 2", volume_number=2, project_id=project.id),
            project_id=project.id,
        )

        result = await volume_service.get_by_project(db_session, project_id=project.id)
        assert len(result) == 3
        assert result[0].volume_number == 1
        assert result[1].volume_number == 2
        assert result[2].volume_number == 3


class TestChapterServiceGetByProject:
    """Tests for chapter_service.get_by_project with real database."""

    @pytest.mark.asyncio
    async def test_get_by_project_empty(self, db_session: AsyncSession):
        """Test get_by_project returns empty list when no chapters exist."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        result = await chapter_service.get_by_project(db_session, project_id=project.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_project_with_chapters(self, db_session: AsyncSession):
        """Test get_by_project returns chapters for specific project."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        # Create chapters
        await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 1", chapter_number=1, project_id=project.id),
            project_id=project.id,
        )
        await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 2", chapter_number=2, project_id=project.id),
            project_id=project.id,
        )

        # Get chapters for project
        result = await chapter_service.get_by_project(db_session, project_id=project.id)
        assert len(result) == 2
        # Should be ordered by chapter_number
        assert result[0].chapter_number == 1
        assert result[1].chapter_number == 2


class TestChapterServiceGetByVolume:
    """Tests for chapter_service.get_by_volume with real database."""

    @pytest.mark.asyncio
    async def test_get_by_volume_empty(self, db_session: AsyncSession):
        """Test get_by_volume returns empty list when no chapters exist."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        volume = await volume_service.create_with_project(
            db_session,
            obj_in=VolumeCreate(title="Volume 1", volume_number=1, project_id=project.id),
            project_id=project.id,
        )

        result = await chapter_service.get_by_volume(db_session, volume_id=volume.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_volume_with_chapters(self, db_session: AsyncSession):
        """Test get_by_volume returns chapters for specific volume."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        volume = await volume_service.create_with_project(
            db_session,
            obj_in=VolumeCreate(title="Volume 1", volume_number=1, project_id=project.id),
            project_id=project.id,
        )

        # Create chapters for this volume
        chapter1 = await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 1", chapter_number=1, project_id=project.id),
            project_id=project.id,
        )
        chapter2 = await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 2", chapter_number=2, project_id=project.id),
            project_id=project.id,
        )

        # Update chapters to belong to volume
        chapter1.volume_id = volume.id
        chapter2.volume_id = volume.id
        await db_session.flush()

        # Get chapters for volume
        result = await chapter_service.get_by_volume(db_session, volume_id=volume.id)
        assert len(result) == 2
        # Should be ordered by chapter_number
        assert result[0].chapter_number == 1
        assert result[1].chapter_number == 2


class TestChapterServiceReorder:
    """Tests for chapter reordering with real database state."""

    @pytest.mark.asyncio
    async def test_reorder_within_volume_rewrites_chapter_numbers(self, db_session: AsyncSession):
        """Reordering chapters should persist sequential chapter numbers."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        volume = await volume_service.create_with_project(
            db_session,
            obj_in=VolumeCreate(title="Volume 1", volume_number=1, project_id=project.id),
            project_id=project.id,
        )

        chapter_one = await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 1", chapter_number=1, project_id=project.id, volume_id=volume.id),
            project_id=project.id,
        )
        chapter_two = await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 2", chapter_number=2, project_id=project.id, volume_id=volume.id),
            project_id=project.id,
        )
        chapter_three = await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 3", chapter_number=3, project_id=project.id, volume_id=volume.id),
            project_id=project.id,
        )

        reordered = await chapter_service.reorder_within_volume(
            db_session,
            project_id=project.id,
            volume_id=volume.id,
            chapter_ids=[chapter_three.id, chapter_one.id, chapter_two.id],
        )

        assert [chapter.id for chapter in reordered] == [chapter_three.id, chapter_one.id, chapter_two.id]
        assert [chapter.chapter_number for chapter in reordered] == [1, 2, 3]

        persisted = await chapter_service.get_by_volume(db_session, volume_id=volume.id)
        assert [chapter.id for chapter in persisted] == [chapter_three.id, chapter_one.id, chapter_two.id]


class TestSceneServiceReorder:
    """Tests for scene reordering with real database state."""

    @pytest.mark.asyncio
    async def test_reorder_within_chapter_rewrites_scene_order(self, db_session: AsyncSession):
        """Reordering scenes should persist sequential scene numbers."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        chapter = await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 1", chapter_number=1, project_id=project.id),
            project_id=project.id,
        )

        scene_one = await scene_service.create_with_chapter(
            db_session,
            obj_in=SceneCreate(scene_order=1, content="Scene 1", chapter_id=chapter.id),
            chapter_id=chapter.id,
        )
        scene_two = await scene_service.create_with_chapter(
            db_session,
            obj_in=SceneCreate(scene_order=2, content="Scene 2", chapter_id=chapter.id),
            chapter_id=chapter.id,
        )
        scene_three = await scene_service.create_with_chapter(
            db_session,
            obj_in=SceneCreate(scene_order=3, content="Scene 3", chapter_id=chapter.id),
            chapter_id=chapter.id,
        )

        reordered = await scene_service.reorder_within_chapter(
            db_session,
            chapter_id=chapter.id,
            scene_ids=[scene_three.id, scene_one.id, scene_two.id],
        )

        assert [scene.id for scene in reordered] == [scene_three.id, scene_one.id, scene_two.id]
        assert [scene.scene_order for scene in reordered] == [1, 2, 3]

        persisted = await scene_service.get_by_chapter(db_session, chapter_id=chapter.id)
        assert [scene.id for scene in persisted] == [scene_three.id, scene_one.id, scene_two.id]


class TestSceneServiceGetByChapter:
    """Tests for scene_service.get_by_chapter with real database."""

    @pytest.mark.asyncio
    async def test_get_by_chapter_empty(self, db_session: AsyncSession):
        """Test get_by_chapter returns empty list when no scenes exist."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        chapter = await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 1", chapter_number=1, project_id=project.id),
            project_id=project.id,
        )

        result = await scene_service.get_by_chapter(db_session, chapter_id=chapter.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_chapter_with_scenes(self, db_session: AsyncSession):
        """Test get_by_chapter returns scenes for specific chapter."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        chapter = await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 1", chapter_number=1, project_id=project.id),
            project_id=project.id,
        )

        # Create scenes
        await scene_service.create_with_chapter(
            db_session,
            obj_in=SceneCreate(scene_order=1, content="Content 1", chapter_id=chapter.id),
            chapter_id=chapter.id,
        )
        await scene_service.create_with_chapter(
            db_session,
            obj_in=SceneCreate(scene_order=2, content="Content 2", chapter_id=chapter.id),
            chapter_id=chapter.id,
        )

        # Get scenes for chapter
        result = await scene_service.get_by_chapter(db_session, chapter_id=chapter.id)
        assert len(result) == 2
        # Should be ordered by scene_order
        assert result[0].scene_order == 1
        assert result[1].scene_order == 2


class TestVolumeServiceCreateWithProject:
    """Tests for volume_service.create_with_project with real database."""

    @pytest.mark.asyncio
    async def test_create_with_project_valid(self, db_session: AsyncSession):
        """Test creating a volume with valid data."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        volume_in = VolumeCreate(
            title="Volume 1: The Beginning",
            volume_number=1,
            outline="The first volume of our epic tale",
            project_id=project.id,
        )

        result = await volume_service.create_with_project(
            db_session,
            obj_in=volume_in,
            project_id=project.id,
        )

        assert result.id is not None
        assert result.title == "Volume 1: The Beginning"
        assert result.volume_number == 1
        assert result.outline == "The first volume of our epic tale"
        assert result.project_id == project.id


class TestChapterServiceCreateWithProject:
    """Tests for chapter_service.create_with_project with real database."""

    @pytest.mark.asyncio
    async def test_create_with_project_valid(self, db_session: AsyncSession):
        """Test creating a chapter with valid data."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )

        chapter_in = ChapterCreate(
            title="Chapter 1: The Journey Begins",
            chapter_number=1,
            outline="Our hero begins their journey",
            project_id=project.id,
        )

        result = await chapter_service.create_with_project(
            db_session,
            obj_in=chapter_in,
            project_id=project.id,
        )

        assert result.id is not None
        assert result.title == "Chapter 1: The Journey Begins"
        assert result.chapter_number == 1
        assert result.outline == "Our hero begins their journey"
        assert result.project_id == project.id
        assert result.volume_id is not None

        volumes = await volume_service.get_by_project(db_session, project_id=project.id)
        assert len(volumes) == 1
        assert volumes[0].id == result.volume_id
        assert volumes[0].title == "第一卷"

    @pytest.mark.asyncio
    async def test_create_with_project_preserves_volume_id(self, db_session: AsyncSession):
        """Test creating a chapter with volume_id preserves the relationship (regression test for data loss bug)."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        volume = await volume_service.create_with_project(
            db_session,
            obj_in=VolumeCreate(title="Volume 1", volume_number=1, project_id=project.id),
            project_id=project.id,
        )

        # Create chapter WITH volume_id - this used to be lost (data loss bug)
        chapter_in = ChapterCreate(
            title="Chapter 1: The Journey Begins",
            chapter_number=1,
            project_id=project.id,
            volume_id=volume.id,  # This must be preserved!
        )

        result = await chapter_service.create_with_project(
            db_session,
            obj_in=chapter_in,
            project_id=project.id,
        )

        # Critical assertion: volume_id must NOT be None
        assert result.id is not None
        assert result.volume_id == volume.id, "volume_id must be preserved when creating chapter"
        assert result.project_id == project.id

        # Verify by querying through the volume
        volume_chapters = await chapter_service.get_by_volume(db_session, volume_id=volume.id)
        assert len(volume_chapters) == 1, "Chapter should be queryable through volume relationship"
        assert volume_chapters[0].id == result.id

    @pytest.mark.asyncio
    async def test_delete_volume_with_chapters_is_blocked(self, db_session: AsyncSession):
        """Non-empty volumes should not be deletable."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Volume Guard", genre="Fantasy"),
        )
        volume = await volume_service.create_with_project(
            db_session,
            obj_in=VolumeCreate(title="Volume 1", volume_number=1, project_id=project.id),
            project_id=project.id,
        )
        await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(
                title="Chapter 1",
                chapter_number=1,
                project_id=project.id,
                volume_id=volume.id,
            ),
            project_id=project.id,
        )

        with pytest.raises(BadRequestException, match="Cannot delete a volume that still contains chapters"):
            await volume_service.delete(db_session, id=volume.id)


class TestSceneServiceCreateWithChapter:
    """Tests for scene_service.create_with_chapter with real database."""

    @pytest.mark.asyncio
    async def test_create_with_chapter_valid(self, db_session: AsyncSession):
        """Test creating a scene with valid data."""
        project = await project_service.create_project(
            db_session,
            obj_in=ProjectCreate(name="Test Project", genre="Fantasy"),
        )
        chapter = await chapter_service.create_with_project(
            db_session,
            obj_in=ChapterCreate(title="Chapter 1", chapter_number=1, project_id=project.id),
            project_id=project.id,
        )

        scene_in = SceneCreate(
            scene_order=1,
            content="The hero wakes up and begins their adventure.",
            location="The Village",
            chapter_id=chapter.id,
        )

        result = await scene_service.create_with_chapter(
            db_session,
            obj_in=scene_in,
            chapter_id=chapter.id,
        )

        assert result.id is not None
        assert result.scene_order == 1
        assert result.content == "The hero wakes up and begins their adventure."
        assert result.location == "The Village"
        assert result.chapter_id == chapter.id
