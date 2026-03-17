"""Direct route tests for project package import/export wrappers."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.api.v1 import project_package as project_package_api


class TestProjectPackageApi:
    """Covers the thin package import/export route wrappers."""

    @pytest.mark.asyncio
    async def test_export_project_package_returns_zip_attachment(self) -> None:
        project_id = uuid4()

        with patch("app.api.v1.project_package.project_package_service.export_package", new_callable=AsyncMock) as mock_export:
            mock_export.return_value = (b"zip-bytes", "novel-package.zip")

            response = await project_package_api.export_project_package(
                db=MagicMock(),
                project_id=project_id,
            )

        assert response.body == b"zip-bytes"
        assert response.headers["content-disposition"] == 'attachment; filename="novel-package.zip"'

    @pytest.mark.asyncio
    async def test_import_project_package_reads_upload_and_delegates(self) -> None:
        upload = UploadFile(filename="novel-package.zip", file=BytesIO(b"zip-bytes"))
        sentinel = object()

        with patch("app.api.v1.project_package.project_package_service.import_package", new_callable=AsyncMock) as mock_import:
            mock_import.return_value = sentinel

            result = await project_package_api.import_project_package(
                db=MagicMock(),
                file=upload,
                new_name="导入副本",
            )

        assert result is sentinel
        mock_import.assert_awaited_once()
        assert mock_import.await_args.kwargs["zip_bytes"] == b"zip-bytes"
        assert mock_import.await_args.kwargs["new_name"] == "导入副本"
