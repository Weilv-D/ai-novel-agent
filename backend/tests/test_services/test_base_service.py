"""Tests for the generic CRUD base service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.base import CRUDBase


@pytest.fixture
def project_crud() -> CRUDBase[Project, ProjectCreate, ProjectUpdate]:
    """Create a CRUDBase bound to Project for exercising generic operations."""
    return CRUDBase(Project)


class TestCRUDBase:
    """Covers the generic CRUD operations exposed by CRUDBase."""

    @pytest.mark.asyncio
    async def test_get_raises_not_found(self, db_session: AsyncSession, project_crud: CRUDBase[Project, ProjectCreate, ProjectUpdate]) -> None:
        """Unknown ids should raise NotFoundException."""
        with pytest.raises(NotFoundException, match="Project not found"):
            await project_crud.get(db_session, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_create_get_multi_update_delete_and_count(
        self,
        db_session: AsyncSession,
        project_crud: CRUDBase[Project, ProjectCreate, ProjectUpdate],
    ) -> None:
        """CRUDBase should support the full create/list/update/delete lifecycle."""
        first = await project_crud.create(
            db_session,
            obj_in=ProjectCreate(name="Alpha", genre="Fantasy"),
        )
        await project_crud.create(
            db_session,
            obj_in=ProjectCreate(name="Beta", genre="Sci-Fi"),
        )

        listed = await project_crud.get_multi(
            db_session,
            order_by=Project.name.asc(),
        )
        assert [project.name for project in listed] == ["Alpha", "Beta"]

        updated = await project_crud.update(
            db_session,
            db_obj=first,
            obj_in=ProjectUpdate(summary="Updated summary"),
        )
        assert updated.summary == "Updated summary"

        updated_again = await project_crud.update(
            db_session,
            db_obj=updated,
            obj_in={"genre": "Epic Fantasy"},
        )
        assert updated_again.genre == "Epic Fantasy"

        assert await project_crud.count(db_session) == 2

    @pytest.mark.asyncio
    async def test_delete_uses_loaded_object(
        self,
        project_crud: CRUDBase[Project, ProjectCreate, ProjectUpdate],
    ) -> None:
        """delete() should remove the object returned by get()."""
        project = Project(id=uuid.uuid4(), name="Gamma", genre="Fantasy", meta={})
        db = MagicMock()
        db.delete = AsyncMock()
        db.flush = AsyncMock()

        with patch.object(project_crud, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = project

            deleted = await project_crud.delete(db, id=project.id)

        assert deleted is project
        db.delete.assert_awaited_once_with(project)
        db.flush.assert_awaited_once()
