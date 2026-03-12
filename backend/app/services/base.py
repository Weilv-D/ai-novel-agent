"""Base service class for CRUD operations."""

from importlib import import_module
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, UnaryExpression, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base CRUD service with generic create, read, update, delete operations."""

    def __init__(self, model: type[ModelType]) -> None:
        """Initialize with a SQLAlchemy model."""
        self._model = model

    @property
    def model(self) -> type[ModelType]:
        """Get the model class."""
        return self._model

    async def get(self, db: AsyncSession, id: Any) -> ModelType:
        """Get a single record by ID."""
        result = await db.execute(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        obj = result.scalar_one_or_none()
        if obj is None:
            raise NotFoundException(f"{self.model.__name__} not found")
        return obj

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        order_by: UnaryExpression[Any] | None = None,
    ) -> list[ModelType]:
        """Get multiple records with pagination."""
        stmt = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_dict = obj_in.model_dump()
        db_obj = self.model(**obj_dict)  # type: ignore[arg-type]
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Update an existing record."""
        if isinstance(obj_in, BaseModel):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            update_data = obj_in

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, *, id: Any) -> ModelType:
        """Delete a record by ID."""
        obj = await self.get(db, id)
        await db.delete(obj)
        await db.flush()
        return obj

    async def count(self, db: AsyncSession) -> int:
        """Count all records."""
        from sqlalchemy import func

        result = await db.execute(select(func.count()).select_from(self.model))
        return result.scalar() or 0
