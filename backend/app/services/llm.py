"""LLM service for OpenAI API integration.

Provides methods for:
- Text generation (chat completions)
- Text embeddings (vector generation)
- Streaming responses
"""

import logging
from typing import Any

from openai import AsyncOpenAI, APIError, RateLimitError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.core.config import get_settings
from app.core.exceptions import BadRequestException, ServiceUnavailableException

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMService:
    """Service for interacting with OpenAI-compatible LLM APIs."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        embedding_model: str | None = None,
        embedding_api_key: str | None = None,
        embedding_base_url: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> None:
        """Initialize the LLM service.

        Args:
            api_key: OpenAI API key for chat (defaults to settings)
            base_url: API base URL for chat (defaults to settings)
            model: Model name for chat completions (defaults to settings)
            embedding_model: Model name for embeddings (defaults to settings)
            embedding_api_key: API key for embeddings (defaults to chat api_key)
            embedding_base_url: API base URL for embeddings (defaults to chat base_url)
            max_tokens: Max tokens for generation (defaults to settings)
            temperature: Sampling temperature (defaults to settings)
        """
        # Chat config
        self.api_key = api_key if api_key is not None else settings.llm_api_key
        self.base_url = base_url if base_url is not None else settings.llm_base_url
        self.model = model if model is not None else settings.llm_model
        self.max_tokens = max_tokens if max_tokens is not None else settings.max_tokens
        self.temperature = temperature if temperature is not None else settings.temperature

        # Embedding config (falls back to chat config if not set)
        self.embedding_model = embedding_model if embedding_model is not None else settings.embedding_model
        self.embedding_api_key = embedding_api_key if embedding_api_key is not None else (settings.embedding_api_key or self.api_key)
        self.embedding_base_url = embedding_base_url if embedding_base_url is not None else (settings.embedding_base_url or self.base_url)

        if not self.api_key:
            logger.warning("LLM API key not configured")

        self._client: AsyncOpenAI | None = None
        self._embedding_client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Get or create the async OpenAI client for chat."""
        if self._client is None:
            if not self.api_key:
                raise BadRequestException("LLM API key not configured")
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    @property
    def embedding_client(self) -> AsyncOpenAI:
        """Get or create the async OpenAI client for embeddings."""
        if self._embedding_client is None:
            if not self.embedding_api_key:
                raise BadRequestException("Embedding API key not configured")
            # Reuse chat client if same provider
            if self.embedding_api_key == self.api_key and self.embedding_base_url == self.base_url:
                self._embedding_client = self.client
            else:
                self._embedding_client = AsyncOpenAI(
                    api_key=self.embedding_api_key,
                    base_url=self.embedding_base_url,
                )
        return self._embedding_client

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Generate text using the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Override default model
            max_tokens: Override default max tokens
            temperature: Override default temperature
            stream: Whether to stream the response

        Returns:
            Dict with 'content', 'model', 'usage' (tokens_in, tokens_out, total)

        Raises:
            BadRequestException: If API key not configured
            ServiceUnavailableException: If API call fails after retries
        """
        # Check API key before retry logic
        if not self.api_key:
            raise BadRequestException("LLM API key not configured")

        # Retry wrapper - this is what gets retried
        @retry(
            retry=retry_if_exception_type((RateLimitError, APIError)),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        async def _do_generate() -> Any:
            """Inner function that performs the actual API call."""
            return await self.client.chat.completions.create(
                model=model if model is not None else self.model,
                messages=messages,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                temperature=temperature if temperature is not None else self.temperature,
                stream=stream,
            )

        try:
            response = await _do_generate()

            if stream:
                # Return streaming response for async handling
                return {
                    "stream": response,
                    "model": model if model is not None else self.model,
                }

            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "tokens_in": response.usage.prompt_tokens,
                    "tokens_out": response.usage.completion_tokens,
                    "total": response.usage.total_tokens,
                },
            }

        except RateLimitError as e:
            # Re-raise after retries exhausted
            logger.error(f"Rate limit exceeded after retries: {e}")
            raise ServiceUnavailableException(f"LLM rate limit exceeded: {e}")
        except APIError as e:
            # Re-raise after retries exhausted
            logger.error(f"API error after retries: {e}")
            raise ServiceUnavailableException(f"LLM service error: {e}")
        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}")
            raise ServiceUnavailableException(f"LLM service unavailable: {e}")

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ):
        """Generate text using the LLM with streaming.

        Yields chunks of content as they arrive.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Override default model
            max_tokens: Override default max tokens
            temperature: Override default temperature

        Yields:
            Content chunks as strings
        """
        result = await self.generate(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )

        stream = result["stream"]
        async for chunk in stream:
            if delta := chunk.choices[0].delta.content:
                yield delta

    async def embed(
        self,
        texts: list[str],
        *,
        model: str | None = None,
    ) -> list[list[float]]:
        """Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            model: Override default embedding model

        Returns:
            List of embedding vectors (each is list of floats)

        Raises:
            BadRequestException: If API key not configured or texts empty
            ServiceUnavailableException: If API call fails after retries
        """
        if not texts:
            raise BadRequestException("Cannot embed empty text list")

        if not self.embedding_api_key:
            raise BadRequestException("Embedding API key not configured")

        # Retry wrapper - this is what gets retried
        @retry(
            retry=retry_if_exception_type((RateLimitError, APIError)),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        async def _do_embed() -> Any:
            """Inner function that performs the actual API call."""
            return await self.embedding_client.embeddings.create(
                model=model if model is not None else self.embedding_model,
                input=texts,
            )

        try:
            response = await _do_embed()
            return [item.embedding for item in response.data]

        except RateLimitError as e:
            # Re-raise after retries exhausted
            logger.error(f"Rate limit exceeded after retries: {e}")
            raise ServiceUnavailableException(f"Embedding rate limit exceeded: {e}")
        except APIError as e:
            # Re-raise after retries exhausted
            logger.error(f"API error after retries: {e}")
            raise ServiceUnavailableException(f"Embedding service error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in embedding generation: {e}")
            raise ServiceUnavailableException(f"Embedding service unavailable: {e}")

    async def embed_single(
        self,
        text: str,
        *,
        model: str | None = None,
    ) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed
            model: Override default embedding model

        Returns:
            Embedding vector (list of floats)

        Raises:
            BadRequestException: If API key not configured or text is empty
            ServiceUnavailableException: If API call fails after retries
        """
        if not text:
            raise BadRequestException("Cannot embed empty text")

        embeddings = await self.embed([text], model=model)
        return embeddings[0]

    async def health_check(self) -> bool:
        """Check if the LLM service is available.

        Returns:
            True if service is healthy, False otherwise
        """
        if not self.api_key:
            return False

        try:
            # Try a minimal API call
            await self.embed_single("test")
            return True
        except Exception:
            return False


# Singleton instance
llm_service = LLMService()
