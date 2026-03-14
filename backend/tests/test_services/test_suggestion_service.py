"""Integration tests for Suggestion service layer with real DB."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.project import Project
from app.models.suggestion import SuggestionStatus, SuggestionType
from app.schemas.suggestion import SuggestionCreate, SuggestionUpdate
from app.services.project import project_service
from app.services.suggestion import suggestion_service


@pytest.fixture
async def test_project(db_session: AsyncSession) -> Project:
    """Create a test project for suggestion tests."""
    from app.schemas.project import ProjectCreate

    user_id = uuid4()
    return await project_service.create_with_user(
        db_session,
        obj_in=ProjectCreate(name="Test Novel", genre="Fantasy"),
        user_id=user_id,
    )


class TestSuggestionServiceCreate:
    """Tests for suggestion_service.create_with_project."""

    @pytest.mark.asyncio
    async def test_create_suggestion_valid(self, db_session: AsyncSession, test_project: Project):
        """Test creating a suggestion with valid data."""
        suggestion_in = SuggestionCreate(
            project_id=test_project.id,
            target_type="character",
            target_id=uuid4(),
            type=SuggestionType.CHARACTER_EDIT,
            content={"name": "New Name", "reason": "Character development"},
        )

        result = await suggestion_service.create_with_project(
            db_session, obj_in=suggestion_in, project_id=test_project.id
        )

        assert result.id is not None
        assert isinstance(result.id, UUID)
        assert result.project_id == test_project.id
        assert result.target_type == "character"
        assert result.type == SuggestionType.CHARACTER_EDIT
        assert result.content["name"] == "New Name"
        assert result.status == SuggestionStatus.DRAFT

    @pytest.mark.asyncio
    async def test_create_suggestion_minimal(self, db_session: AsyncSession, test_project: Project):
        """Test creating a suggestion with minimal required fields."""
        suggestion_in = SuggestionCreate(
            project_id=test_project.id,
            target_type="chapter",
            target_id=uuid4(),
            type=SuggestionType.CHAPTER_EDIT,
            content={"summary": "New summary"},
        )

        result = await suggestion_service.create_with_project(
            db_session, obj_in=suggestion_in, project_id=test_project.id
        )

        assert result.id is not None
        assert result.status == SuggestionStatus.DRAFT


class TestSuggestionServiceGetByProject:
    """Tests for suggestion_service.get_by_project."""

    @pytest.mark.asyncio
    async def test_get_by_project_empty(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_project returns empty list when no suggestions exist."""
        result = await suggestion_service.get_by_project(db_session, project_id=test_project.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_project_with_suggestions(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_project returns suggestions for specific project."""
        target_id = uuid4()

        # Create suggestions
        await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit 1"},
            ),
            project_id=test_project.id,
        )
        await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit 2"},
            ),
            project_id=test_project.id,
        )

        result = await suggestion_service.get_by_project(db_session, project_id=test_project.id)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_by_project_with_status_filter(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_project with status filtering."""
        target_id = uuid4()

        # Create draft suggestion
        draft_suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Draft"},
            ),
            project_id=test_project.id,
        )

        # Create and confirm a suggestion
        patched_suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Patched"},
            ),
            project_id=test_project.id,
        )
        await suggestion_service.confirm(db_session, suggestion_id=patched_suggestion.id)

        # Filter by draft status
        draft_results = await suggestion_service.get_by_project(
            db_session, project_id=test_project.id, status=SuggestionStatus.DRAFT.value
        )
        assert len(draft_results) == 1
        assert draft_results[0].id == draft_suggestion.id

        # Filter by patched status
        patched_results = await suggestion_service.get_by_project(
            db_session, project_id=test_project.id, status=SuggestionStatus.PATCHED.value
        )
        assert len(patched_results) == 1
        assert patched_results[0].id == patched_suggestion.id


class TestSuggestionServiceGetByTarget:
    """Tests for suggestion_service.get_by_target."""

    @pytest.mark.asyncio
    async def test_get_by_target(self, db_session: AsyncSession, test_project: Project):
        """Test get_by_target returns suggestions for specific target."""
        target_id = uuid4()
        other_target_id = uuid4()

        # Create suggestions for different targets
        await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit 1"},
            ),
            project_id=test_project.id,
        )
        await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit 2"},
            ),
            project_id=test_project.id,
        )
        await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=other_target_id,
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Other Edit"},
            ),
            project_id=test_project.id,
        )

        result = await suggestion_service.get_by_target(
            db_session, project_id=test_project.id, target_type="character", target_id=target_id
        )
        assert len(result) == 2


class TestSuggestionServiceStateTransitions:
    """Tests for suggestion state transitions."""

    @pytest.mark.asyncio
    async def test_confirm_draft_suggestion(self, db_session: AsyncSession, test_project: Project):
        """Test confirming a draft suggestion moves it to patched."""
        suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit"},
            ),
            project_id=test_project.id,
        )
        assert suggestion.status == SuggestionStatus.DRAFT

        impact_analysis = {"affected_objects": ["chapter_1", "chapter_2"]}
        result = await suggestion_service.confirm(
            db_session, suggestion_id=suggestion.id, impact_analysis=impact_analysis
        )

        assert result.status == SuggestionStatus.PATCHED
        assert result.impact_analysis == impact_analysis

    @pytest.mark.asyncio
    async def test_confirm_non_draft_fails(self, db_session: AsyncSession, test_project: Project):
        """Test confirming a non-draft suggestion raises BadRequestException."""
        suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit"},
            ),
            project_id=test_project.id,
        )
        # Move to patched
        await suggestion_service.confirm(db_session, suggestion_id=suggestion.id)

        # Try to confirm again - should fail
        with pytest.raises(BadRequestException, match="Cannot confirm suggestion"):
            await suggestion_service.confirm(db_session, suggestion_id=suggestion.id)

    @pytest.mark.asyncio
    async def test_discard_draft_suggestion(self, db_session: AsyncSession, test_project: Project):
        """Test discarding a draft suggestion."""
        suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit"},
            ),
            project_id=test_project.id,
        )

        result = await suggestion_service.discard(db_session, suggestion_id=suggestion.id)

        assert result.status == SuggestionStatus.DISCARDED

    @pytest.mark.asyncio
    async def test_discard_patched_suggestion(self, db_session: AsyncSession, test_project: Project):
        """Test discarding a patched suggestion."""
        suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit"},
            ),
            project_id=test_project.id,
        )
        await suggestion_service.confirm(db_session, suggestion_id=suggestion.id)

        result = await suggestion_service.discard(db_session, suggestion_id=suggestion.id)

        assert result.status == SuggestionStatus.DISCARDED

    @pytest.mark.asyncio
    async def test_discard_committed_fails(self, db_session: AsyncSession, test_project: Project):
        """Test discarding a committed suggestion raises BadRequestException."""
        suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit"},
            ),
            project_id=test_project.id,
        )
        await suggestion_service.confirm(db_session, suggestion_id=suggestion.id)
        await suggestion_service.commit(db_session, suggestion_id=suggestion.id)

        with pytest.raises(BadRequestException, match="Cannot discard a committed suggestion"):
            await suggestion_service.discard(db_session, suggestion_id=suggestion.id)

    @pytest.mark.asyncio
    async def test_commit_patched_suggestion(self, db_session: AsyncSession, test_project: Project):
        """Test committing a patched suggestion marks it as committed."""
        suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit"},
            ),
            project_id=test_project.id,
        )
        await suggestion_service.confirm(db_session, suggestion_id=suggestion.id)

        result = await suggestion_service.commit(db_session, suggestion_id=suggestion.id)

        assert result.status == SuggestionStatus.COMMITTED
        assert result.committed_at is not None
        # Note: The suggestion is marked committed but the actual content application
        # to the target object is not yet implemented - this records the commit decision.

    @pytest.mark.asyncio
    async def test_commit_non_patched_fails(self, db_session: AsyncSession, test_project: Project):
        """Test committing a non-patched suggestion raises BadRequestException."""
        suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Edit"},
            ),
            project_id=test_project.id,
        )

        with pytest.raises(BadRequestException, match="Cannot commit suggestion"):
            await suggestion_service.commit(db_session, suggestion_id=suggestion.id)


class TestSuggestionServiceGetPendingCount:
    """Tests for suggestion_service.get_pending_count."""

    @pytest.mark.asyncio
    async def test_get_pending_count_empty(self, db_session: AsyncSession, test_project: Project):
        """Test get_pending_count returns 0 when no suggestions exist."""
        count = await suggestion_service.get_pending_count(db_session, project_id=test_project.id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_get_pending_count_with_draft_and_patched(self, db_session: AsyncSession, test_project: Project):
        """Test get_pending_count counts draft and patched suggestions."""
        target_id = uuid4()

        # Create draft suggestions
        for _ in range(2):
            await suggestion_service.create_with_project(
                db_session,
                obj_in=SuggestionCreate(
                    project_id=test_project.id,
                    target_type="character",
                    target_id=target_id,
                    type=SuggestionType.CHARACTER_EDIT,
                    content={"name": "Draft"},
                ),
                project_id=test_project.id,
            )

        # Create patched suggestion
        patched = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Patched"},
            ),
            project_id=test_project.id,
        )
        await suggestion_service.confirm(db_session, suggestion_id=patched.id)

        # Create committed suggestion (should not count)
        committed = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Committed"},
            ),
            project_id=test_project.id,
        )
        await suggestion_service.confirm(db_session, suggestion_id=committed.id)
        await suggestion_service.commit(db_session, suggestion_id=committed.id)

        # Create discarded suggestion (should not count)
        discarded = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=target_id,
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Discarded"},
            ),
            project_id=test_project.id,
        )
        await suggestion_service.discard(db_session, suggestion_id=discarded.id)

        count = await suggestion_service.get_pending_count(db_session, project_id=test_project.id)
        assert count == 3  # 2 draft + 1 patched


class TestSuggestionServiceGet:
    """Tests for suggestion_service.get."""

    @pytest.mark.asyncio
    async def test_get_existing(self, db_session: AsyncSession, test_project: Project):
        """Test getting an existing suggestion by ID."""
        suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Test"},
            ),
            project_id=test_project.id,
        )

        result = await suggestion_service.get(db_session, id=suggestion.id)

        assert result.id == suggestion.id
        assert result.type == SuggestionType.CHARACTER_EDIT

    @pytest.mark.asyncio
    async def test_get_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent suggestion raises NotFoundException."""
        non_existent_id = uuid4()

        with pytest.raises(NotFoundException, match="Suggestion not found"):
            await suggestion_service.get(db_session, id=non_existent_id)


class TestSuggestionServiceUpdate:
    """Tests for suggestion_service.update."""

    @pytest.mark.asyncio
    async def test_update_suggestion_content(self, db_session: AsyncSession, test_project: Project):
        """Test updating suggestion content."""
        suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "Original"},
            ),
            project_id=test_project.id,
        )

        updated = await suggestion_service.update(
            db_session,
            db_obj=suggestion,
            obj_in=SuggestionUpdate(content={"name": "Updated", "reason": "Better"}),
        )

        assert updated.id == suggestion.id
        assert updated.content["name"] == "Updated"
        assert updated.content["reason"] == "Better"


class TestSuggestionServiceDelete:
    """Tests for suggestion_service.delete."""

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session: AsyncSession, test_project: Project):
        """Test deleting a suggestion successfully."""
        suggestion = await suggestion_service.create_with_project(
            db_session,
            obj_in=SuggestionCreate(
                project_id=test_project.id,
                target_type="character",
                target_id=uuid4(),
                type=SuggestionType.CHARACTER_EDIT,
                content={"name": "To Delete"},
            ),
            project_id=test_project.id,
        )
        suggestion_id = suggestion.id

        deleted = await suggestion_service.delete(db_session, id=suggestion_id)

        assert deleted.id == suggestion_id

        # Verify suggestion is actually deleted
        with pytest.raises(NotFoundException, match="Suggestion not found"):
            await suggestion_service.get(db_session, id=suggestion_id)
