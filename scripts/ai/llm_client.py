"""LLM client abstraction (Anthropic / OpenAI)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from .config import AIConfig, load_config


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


@dataclass
class MockLLMClient:
    """Deterministic client for tests and dry-run."""

    responses: list[str]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self.responses:
            return self.responses.pop(0)
        return "{}"


class AnthropicClient:
    def __init__(self, config: AIConfig) -> None:
        if not config.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        import anthropic

        self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self._model = config.anthropic_model

    def complete(self, system: str, user: str) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [block.text for block in message.content if hasattr(block, "text")]
        return "".join(parts)


class OpenAIClient:
    def __init__(self, config: AIConfig) -> None:
        if not config.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        import openai

        self._client = openai.OpenAI(api_key=config.openai_api_key)
        self._model = config.openai_model

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""


def create_llm_client(config: AIConfig | None = None) -> LLMClient | None:
    config = config or load_config()
    if not config.llm_available:
        return None
    provider = config.provider
    if provider == "openai" and config.openai_api_key:
        return OpenAIClient(config)
    if config.anthropic_api_key:
        return AnthropicClient(config)
    if config.openai_api_key:
        return OpenAIClient(config)
    return None


def extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        data = json.loads(match.group(0))
        if isinstance(data, dict):
            return data
    raise ValueError(f"Could not parse JSON from LLM response: {text[:200]!r}")
