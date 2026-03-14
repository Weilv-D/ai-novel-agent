"""Base agent class and shared data structures."""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, cast

from app.services.llm import LLMService, llm_service

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context passed to an agent for processing."""

    project_id: str
    user_message: str
    history: list[dict[str, str]] = field(default_factory=list)
    context_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Result returned by an agent."""

    message: str
    suggestions: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for all specialized agents."""

    def __init__(self, llm: LLMService | None = None) -> None:
        self.llm = llm or llm_service

    @abstractmethod
    def build_system_prompt(self, context: AgentContext) -> str:
        """Build the system prompt for this agent."""
        ...

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        """Execute the agent logic and return a result."""
        ...

    async def _call_llm(
        self,
        context: AgentContext,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Call LLM with context and return the response content."""
        prompt = system_prompt or self.build_system_prompt(context)
        messages: list[dict[str, str]] = [{"role": "system", "content": prompt}]

        # Add conversation history
        for msg in context.history[-10:]:
            messages.append(msg)

        messages.append({"role": "user", "content": context.user_message})

        result = await self.llm.generate(messages, temperature=temperature)
        return result["content"]

    async def _call_llm_stream(
        self,
        context: AgentContext,
        *,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Call LLM with streaming and yield content chunks."""
        prompt = system_prompt or self.build_system_prompt(context)
        messages: list[dict[str, str]] = [{"role": "system", "content": prompt}]

        for msg in context.history[-10:]:
            messages.append(msg)

        messages.append({"role": "user", "content": context.user_message})

        async for chunk in self.llm.generate_stream(messages, temperature=temperature):
            yield chunk

    def _parse_json_from_response(self, text: str) -> dict[str, Any] | None:
        """Extract JSON object from LLM response text.

        Handles responses with markdown code fences or bare JSON.
        """
        def _as_json_object(value: Any) -> dict[str, Any] | None:
            if isinstance(value, dict):
                return cast(dict[str, Any], value)
            return None

        # Try to find JSON in code block
        import re
        json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
        if json_match:
            try:
                return _as_json_object(json.loads(json_match.group(1).strip()))
            except json.JSONDecodeError:
                pass

        # Try bare JSON
        for start in range(len(text)):
            if text[start] == "{":
                try:
                    return _as_json_object(json.loads(text[start:]))
                except json.JSONDecodeError:
                    continue

        logger.warning("Failed to parse JSON from response: %s", text[:200])
        return None
