"""Dependency service layer for impact analysis and relationship tracking."""

from typing import Any

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.models.dependency import Dependency, DependencyType
from app.schemas.dependency import DependencyCreate, DependencyUpdate, ImpactDetail
from app.services.base import CRUDBase


class CRUDDependency(CRUDBase[Dependency, DependencyCreate, DependencyUpdate]):
    """CRUD operations for Dependency model with impact analysis."""

    async def get_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Dependency]:
        """Get all dependencies for a project."""
        stmt = (
            select(Dependency)
            .where(Dependency.project_id == project_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_source(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        source_type: str,
        source_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Dependency]:
        """Get all dependencies for a specific source object."""
        stmt = (
            select(Dependency)
            .where(
                Dependency.project_id == project_id,
                Dependency.source_type == source_type,
                Dependency.source_id == source_id,
            )
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_target(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        target_type: str,
        target_id: Any,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Dependency]:
        """Get all dependencies pointing to a specific target object."""
        stmt = (
            select(Dependency)
            .where(
                Dependency.project_id == project_id,
                Dependency.target_type == target_type,
                Dependency.target_id == target_id,
            )
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def query_dependencies(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        source_type: str | None = None,
        source_id: Any | None = None,
        target_type: str | None = None,
        target_id: Any | None = None,
        dependency_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Dependency]:
        """Query dependencies with optional filters."""
        conditions = [Dependency.project_id == project_id]

        if source_type is not None:
            conditions.append(Dependency.source_type == source_type)
        if source_id is not None:
            conditions.append(Dependency.source_id == source_id)
        if target_type is not None:
            conditions.append(Dependency.target_type == target_type)
        if target_id is not None:
            conditions.append(Dependency.target_id == target_id)
        if dependency_type is not None:
            conditions.append(Dependency.dependency_type == dependency_type)

        stmt = (
            select(Dependency)
            .where(and_(*conditions))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_with_project(
        self,
        db: AsyncSession,
        *,
        obj_in: DependencyCreate,
        project_id: Any,
    ) -> Dependency:
        """Create a new dependency for a specific project."""
        obj_dict = obj_in.model_dump(exclude={"project_id"})
        db_obj = Dependency(**obj_dict, project_id=project_id)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def get_or_create(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        source_type: str,
        source_id: Any,
        target_type: str,
        target_id: Any,
        dependency_type: str | None = None,
    ) -> tuple[Dependency, bool]:
        """Get an existing dependency or create a new one.

        Returns:
            tuple[Dependency, bool]: The dependency and whether it was created (True) or existed (False)
        """
        stmt = select(Dependency).where(
            and_(
                Dependency.project_id == project_id,
                Dependency.source_type == source_type,
                Dependency.source_id == source_id,
                Dependency.target_type == target_type,
                Dependency.target_id == target_id,
            )
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing, False

        db_obj = Dependency(
            project_id=project_id,
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            dependency_type=dependency_type,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj, True

    async def delete_by_target(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        target_type: str,
        target_id: Any,
    ) -> int:
        """Delete all dependencies pointing to a specific target object."""
        stmt = delete(Dependency).where(
            and_(
                Dependency.project_id == project_id,
                Dependency.target_type == target_type,
                Dependency.target_id == target_id,
            )
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount

    async def delete_by_source(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        source_type: str,
        source_id: Any,
    ) -> int:
        """Delete all dependencies from a specific source object."""
        stmt = delete(Dependency).where(
            and_(
                Dependency.project_id == project_id,
                Dependency.source_type == source_type,
                Dependency.source_id == source_id,
            )
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount

    async def analyze_impact(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        source_type: str,
        source_id: Any,
    ) -> list[ImpactDetail]:
        """Analyze the impact of modifying a source object.

        Returns a list of all objects that would be affected by modifying
        the specified source object, based on outgoing dependencies.
        """
        dependencies = await self.get_by_source(
            db, project_id=project_id, source_type=source_type, source_id=source_id
        )

        impacts = []
        for dep in dependencies:
            impacts.append(
                ImpactDetail(
                    target_type=dep.target_type,  # type: ignore
                    target_id=dep.target_id,
                    dependency_type=dep.dependency_type,  # type: ignore
                    description=self._describe_impact(dep),
                )
            )
        return impacts

    async def analyze_reverse_impact(
        self,
        db: AsyncSession,
        *,
        project_id: Any,
        target_type: str,
        target_id: Any,
    ) -> list[ImpactDetail]:
        """Analyze what would be affected if a target object is modified.

        Returns a list of all source objects that depend on this target,
        i.e., what would break if this object is changed/deleted.
        """
        dependencies = await self.get_by_target(
            db, project_id=project_id, target_type=target_type, target_id=target_id
        )

        impacts = []
        for dep in dependencies:
            impacts.append(
                ImpactDetail(
                    target_type=dep.source_type,  # type: ignore
                    target_id=dep.source_id,
                    dependency_type=dep.dependency_type,  # type: ignore
                    description=self._describe_reverse_impact(dep),
                )
            )
        return impacts

    def _describe_impact(self, dependency: Dependency) -> str:
        """Generate a human-readable description of the impact."""
        base = f"Modifying {dependency.source_type}:{dependency.source_id}"
        if dependency.dependency_type == DependencyType.REFERENCES:
            return f"{base} affects referenced {dependency.target_type}:{dependency.target_id}"
        elif dependency.dependency_type == DependencyType.INFLUENCES:
            return f"{base} influences {dependency.target_type}:{dependency.target_id}"
        elif dependency.dependency_type == DependencyType.CONTAINS:
            return f"{base} contains {dependency.target_type}:{dependency.target_id}"
        elif dependency.dependency_type == DependencyType.PRECEDES:
            return f"{base} precedes {dependency.target_type}:{dependency.target_id}"
        else:
            return f"{base} has dependency on {dependency.target_type}:{dependency.target_id}"

    def _describe_reverse_impact(self, dependency: Dependency) -> str:
        """Generate a human-readable description of the reverse impact."""
        base = f"{dependency.source_type}:{dependency.source_id}"
        if dependency.dependency_type == DependencyType.REFERENCES:
            return f"{base} references this {dependency.target_type}"
        elif dependency.dependency_type == DependencyType.INFLUENCES:
            return f"{base} is influenced by this {dependency.target_type}"
        elif dependency.dependency_type == DependencyType.CONTAINS:
            return f"{base} contains this {dependency.target_type}"
        elif dependency.dependency_type == DependencyType.PRECEDES:
            return f"{base} precedes this {dependency.target_type}"
        else:
            return f"{base} depends on this {dependency.target_type}"


# Singleton instance
dependency_service = CRUDDependency(Dependency)
