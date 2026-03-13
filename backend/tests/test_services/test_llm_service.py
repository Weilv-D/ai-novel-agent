"""Tests for LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx

import pytest
from openai import RateLimitError, APIError

from app.core.exceptions import BadRequestException, ServiceUnavailableException
from app.services.llm import LLMService


# Mock OpenAI classes for patching
class MockAsyncOpenAI:
    """Mock AsyncOpenAI class for testing."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.embeddings = MagicMock()


def _create_mock_response(status_code: int = 429) -> MagicMock:
    """Create a mock httpx Response for OpenAI exceptions."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.headers = MagicMock()
    mock_response.headers.get = MagicMock(return_value=None)
    return mock_response


def _create_mock_request() -> MagicMock:
    """Create a mock httpx Request for OpenAI exceptions."""
    mock_request = MagicMock(spec=httpx.Request)
    return mock_request


class TestLLMServiceInit:
    """Tests for LLM service initialization."""

    def test_init_default_settings(self) -> None:
        """Test initialization with default settings."""
        service = LLMService()
        assert service.api_key == ""  # Default from settings
        assert service.base_url == "https://api.openai.com/v1"
        assert service.model == "gpt-4o-mini"
        assert service.embedding_model == "text-embedding-3-small"

    def test_init_custom_settings(self) -> None:
        """Test initialization with custom settings."""
        service = LLMService(
            api_key="test-key",
            base_url="https://custom.api/v1",
            model="custom-model",
            embedding_model="custom-embed",
            max_tokens=2048,
            temperature=0.5,
        )
        assert service.api_key == "test-key"
        assert service.base_url == "https://custom.api/v1"
        assert service.model == "custom-model"
        assert service.embedding_model == "custom-embed"
        assert service.max_tokens == 2048
        assert service.temperature == 0.5


class TestLLMServiceGenerate:
    """Tests for LLM text generation."""

    @pytest.mark.asyncio
    async def test_generate_no_api_key(self) -> None:
        """Test generate raises error when no API key."""
        service = LLMService(api_key="")
        with pytest.raises(BadRequestException, match="API key not configured"):
            await service.generate([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_generate_success(self) -> None:
        """Test successful text generation."""
        service = LLMService(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated text"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30

        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            result = await service.generate([{"role": "user", "content": "test"}])

            assert result["content"] == "Generated text"
            assert result["model"] == "gpt-4o-mini"
            assert result["usage"]["tokens_in"] == 10
            assert result["usage"]["tokens_out"] == 20
            assert result["usage"]["total"] == 30

    @pytest.mark.asyncio
    async def test_generate_with_overrides(self) -> None:
        """Test generation with parameter overrides."""
        service = LLMService(api_key="test-key", max_tokens=1000, temperature=0.7)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Result"
        mock_response.model = "custom-model"
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 10
        mock_response.usage.total_tokens = 15

        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            result = await service.generate(
                [{"role": "user", "content": "test"}],
                model="custom-model",
                max_tokens=2000,
                temperature=0.5,
            )

            assert result["content"] == "Result"
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["max_tokens"] == 2000
            assert call_args.kwargs["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_generate_stream_mode(self) -> None:
        """Test generation in stream mode."""
        service = LLMService(api_key="test-key")

        mock_stream = MagicMock()

        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream)

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            result = await service.generate(
                [{"role": "user", "content": "test"}], stream=True
            )

            assert "stream" in result
            assert result["model"] == service.model


class TestLLMServiceEmbed:
    """Tests for LLM embedding generation."""

    @pytest.mark.asyncio
    async def test_embed_empty_list(self) -> None:
        """Test embed raises error for empty text list."""
        service = LLMService(api_key="test-key")
        with pytest.raises(BadRequestException, match="empty text list"):
            await service.embed([])

    @pytest.mark.asyncio
    async def test_embed_single_text(self) -> None:
        """Test embedding a single text."""
        service = LLMService(api_key="test-key")

        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]

        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            result = await service.embed(["test text"])

            assert len(result) == 1
            assert result[0] == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embed_multiple_texts(self) -> None:
        """Test embedding multiple texts."""
        service = LLMService(api_key="test-key")

        mock_response = MagicMock()
        mock_response.data = [MagicMock(), MagicMock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]
        mock_response.data[1].embedding = [0.4, 0.5, 0.6]

        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            result = await service.embed(["text1", "text2"])

            assert len(result) == 2
            assert result[0] == [0.1, 0.2, 0.3]
            assert result[1] == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    async def test_embed_single_convenience_method(self) -> None:
        """Test the embed_single convenience method."""
        service = LLMService(api_key="test-key")

        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]

        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            result = await service.embed_single("test text")

            assert result == [0.1, 0.2, 0.3]


class TestLLMServiceHealthCheck:
    """Tests for LLM service health check."""

    @pytest.mark.asyncio
    async def test_health_check_no_api_key(self) -> None:
        """Test health check fails with no API key."""
        service = LLMService(api_key="")
        assert await service.health_check() is False

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        """Test health check succeeds with valid API."""
        service = LLMService(api_key="test-key")

        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1, 0.2]

        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            result = await service.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self) -> None:
        """Test health check fails on error."""
        service = LLMService(api_key="test-key")

        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.embeddings.create = AsyncMock(side_effect=Exception("API error"))

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            result = await service.health_check()

            assert result is False


class TestLLMServiceRetryBehavior:
    """Tests for LLM service retry behavior on API errors."""

    @pytest.mark.asyncio
    async def test_generate_retries_on_rate_limit(self) -> None:
        """Test that generate retries on RateLimitError and eventually succeeds."""
        service = LLMService(api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after retries"
        mock_response.model = "gpt-4o-mini"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        # Fail twice, then succeed
        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                RateLimitError("Rate limit", response=_create_mock_response(429), body=None),
                RateLimitError("Rate limit", response=_create_mock_response(429), body=None),
                mock_response,
            ]
        )

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            result = await service.generate([{"role": "user", "content": "test"}])

            assert result["content"] == "Success after retries"
            assert mock_client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_fails_after_retries_exhausted(self) -> None:
        """Test that generate raises ServiceUnavailableException after all retries fail."""
        service = LLMService(api_key="test-key")

        # Always fail with RateLimitError
        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError("Rate limit", response=_create_mock_response(429), body=None)
        )

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            with pytest.raises(ServiceUnavailableException, match="rate limit exceeded"):
                await service.generate([{"role": "user", "content": "test"}])

            # Should retry 3 times (stop_after_attempt=3)
            assert mock_client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_embed_retries_on_api_error(self) -> None:
        """Test that embed retries on APIError and eventually succeeds."""
        service = LLMService(api_key="test-key")

        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]

        # Fail once, then succeed
        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.embeddings.create = AsyncMock(
            side_effect=[
                APIError("API error", request=_create_mock_request(), body=None),
                mock_response,
            ]
        )

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            result = await service.embed(["test"])

            assert result == [[0.1, 0.2, 0.3]]
            assert mock_client.embeddings.create.call_count == 2

    @pytest.mark.asyncio
    async def test_embed_fails_after_retries_exhausted(self) -> None:
        """Test that embed raises ServiceUnavailableException after all retries fail."""
        service = LLMService(api_key="test-key")

        # Always fail with APIError
        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.embeddings.create = AsyncMock(
            side_effect=APIError("API error", request=_create_mock_request(), body=None)
        )

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            with pytest.raises(ServiceUnavailableException, match="Embedding service error"):
                await service.embed(["test"])

            assert mock_client.embeddings.create.call_count == 3

    @pytest.mark.asyncio
    async def test_no_api_key_raises_bad_request_not_retry(self) -> None:
        """Test that missing API key raises BadRequestException without retries."""
        service = LLMService(api_key="")

        mock_client = MockAsyncOpenAI(api_key="test-key", base_url="https://api.openai.com/v1")
        mock_client.chat.completions.create = AsyncMock()

        with patch("app.services.llm.AsyncOpenAI", return_value=mock_client):
            with pytest.raises(BadRequestException, match="API key not configured"):
                await service.generate([{"role": "user", "content": "test"}])

            # Should not even attempt the API call
            assert mock_client.chat.completions.create.call_count == 0
