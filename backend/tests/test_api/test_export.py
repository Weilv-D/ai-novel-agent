"""Tests for export API routes."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1 import export as export_api
from app.core.exceptions import BadRequestException


class TestExportApi:
    """Tests for project export endpoints."""

    @pytest.mark.asyncio
    async def test_export_docx_returns_attachment_headers(self, client: AsyncClient) -> None:
        """DOCX export should return the correct content type and filename."""
        project_id = uuid.uuid4()

        with patch("app.api.v1.export.export_service.export_docx", new_callable=AsyncMock) as mock_export:
            mock_export.return_value = b"fake-docx"

            response = await client.get(f"/api/v1/projects/{project_id}/export?format=docx")

        assert response.status_code == 200
        assert response.content == b"fake-docx"
        assert response.headers["content-type"] == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert 'attachment; filename="novel.docx"' in response.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_export_txt_markdown_md_alias_and_invalid_format_direct_routes(self) -> None:
        """Direct route calls should wrap TXT/Markdown content and reject unsupported formats."""
        project_id = uuid.uuid4()

        with patch("app.api.v1.export.export_service.export_txt", new_callable=AsyncMock) as mock_txt:
            with patch("app.api.v1.export.export_service.export_markdown", new_callable=AsyncMock) as mock_markdown:
                mock_txt.return_value = "plain text"
                mock_markdown.return_value = "# markdown"

                txt_response = await export_api.export_project(
                    db=MagicMock(),
                    project_id=project_id,
                    format="txt",
                )
                markdown_response = await export_api.export_project(
                    db=MagicMock(),
                    project_id=project_id,
                    format="markdown",
                )
                md_alias_response = await export_api.export_project(
                    db=MagicMock(),
                    project_id=project_id,
                    format="md",
                )

        assert txt_response.body == b"plain text"
        assert txt_response.headers["content-disposition"] == 'attachment; filename="novel.txt"'
        assert markdown_response.body == b"# markdown"
        assert markdown_response.headers["content-disposition"] == 'attachment; filename="novel.md"'
        assert md_alias_response.body == b"# markdown"
        assert md_alias_response.headers["content-disposition"] == 'attachment; filename="novel.md"'

        with pytest.raises(BadRequestException, match="Unsupported format"):
            await export_api.export_project(
                db=MagicMock(),
                project_id=project_id,
                format="zip",
            )
