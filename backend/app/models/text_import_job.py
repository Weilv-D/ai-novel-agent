"""Persistent background jobs for structured text import."""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class TextImportJobStatus(str, Enum):
    """Background text-import job statuses."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TextImportJob(Base, UUIDMixin, TimestampMixin):
    """Persistent background job for large text-import analysis."""

    __tablename__ = "text_import_jobs"

    status: Mapped[str] = mapped_column(
        String(20),
        default=TextImportJobStatus.QUEUED.value,
        nullable=False,
        index=True,
    )
    phase: Mapped[str | None] = mapped_column(String(50), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_encoding: Mapped[str | None] = mapped_column(String(60), nullable=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)

    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    failed_phases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
