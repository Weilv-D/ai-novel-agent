"""LLM service for OpenAI API integration.

Provides methods for:
- Text generation (chat completions)
- Text embeddings (vector generation)
- Streaming responses
"""

import logging
from collections.abc import AsyncIterator
from typing import Any, Literal, TypedDict, cast, overload

from openai import APIError, AsyncOpenAI, AsyncStream, RateLimitError
from openai.types.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionMessageParam
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.cache import cache_service
from app.core.config import get_settings
from app.core.exceptions import BadRequestException, ServiceUnavailableException

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMUsage(TypedDict):
    """Token usage metadata returned by chat completions."""

    tokens_in: int
    tokens_out: int
    total: int


class LLMGenerateResponse(TypedDict):
    """Non-streaming LLM response payload."""

    content: str
    model: str
    usage: LLMUsage


class LLMStreamResponse(TypedDict):
    """Streaming LLM response payload."""

    stream: AsyncStream[ChatCompletionChunk]
    model: str


class LLMService:
    """Service for interacting with OpenAI-compatible LLM APIs."""

    CACHE_TTL_SECONDS = 3600

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

    @staticmethod
    def _build_generate_cache_key(
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Build a stable cache key for non-streaming generation requests."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        return f"llm:{cache_service.build_hash(payload)}"

    @overload
    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stream: Literal[False] = False,
    ) -> LLMGenerateResponse: ...

    @overload
    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stream: Literal[True],
    ) -> LLMStreamResponse: ...

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        stream: bool = False,
    ) -> LLMGenerateResponse | LLMStreamResponse:
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

        resolved_model = model if model is not None else self.model
        resolved_max_tokens = max_tokens if max_tokens is not None else self.max_tokens
        resolved_temperature = temperature if temperature is not None else self.temperature
        cache_key = ""

        if not stream:
            cache_key = self._build_generate_cache_key(
                model=resolved_model,
                messages=messages,
                temperature=resolved_temperature,
                max_tokens=resolved_max_tokens,
            )
            cached_response = await cache_service.get(cache_key)
            if isinstance(cached_response, dict):
                return cast(LLMGenerateResponse, cached_response)

        # Retry wrapper - this is what gets retried
        @retry(
            retry=retry_if_exception_type((RateLimitError, APIError)),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        async def _do_generate() -> ChatCompletion | AsyncStream[ChatCompletionChunk]:
            """Inner function that performs the actual API call."""
            typed_messages = cast(list[ChatCompletionMessageParam], messages)
            return await self.client.chat.completions.create(
                model=resolved_model,
                messages=typed_messages,
                max_tokens=resolved_max_tokens,
                temperature=resolved_temperature,
                stream=stream,
            )

        try:
            response = await _do_generate()

            if stream:
                # Return streaming response for async handling
                return {
                    "stream": cast(AsyncStream[ChatCompletionChunk], response),
                    "model": resolved_model,
                }

            completion = cast(ChatCompletion, response)
            usage = completion.usage
            payload: LLMGenerateResponse = {
                "content": completion.choices[0].message.content or "",
                "model": completion.model,
                "usage": {
                    "tokens_in": usage.prompt_tokens if usage is not None else 0,
                    "tokens_out": usage.completion_tokens if usage is not None else 0,
                    "total": usage.total_tokens if usage is not None else 0,
                },
            }
            if cache_key:
                await cache_service.set(cache_key, payload, ttl=self.CACHE_TTL_SECONDS)
            return payload

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
    ) -> AsyncIterator[str]:
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
