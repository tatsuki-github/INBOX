"""Configuration for AI practice generation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = ROOT / "input"
PROMPTS_DIR = ROOT / "prompts"
OUT_DIR = ROOT / "out" / "ai"
RULES_PATH = INPUT_DIR / "ai_generation_rules.yaml"
TEMPLATES_PATH = INPUT_DIR / "practice_templates.yaml"
RAG_INDEX_PATH = OUT_DIR / "rag_index.json"

MAX_LINT_RETRIES = 3
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
DEFAULT_OPENAI_MODEL = "gpt-4o"


@dataclass(frozen=True)
class AIConfig:
    provider: str
    anthropic_api_key: str | None
    openai_api_key: str | None
    anthropic_model: str
    openai_model: str
    max_retries: int

    @property
    def llm_available(self) -> bool:
        if self.provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.provider == "openai":
            return bool(self.openai_api_key)
        return bool(self.anthropic_api_key or self.openai_api_key)


def load_config() -> AIConfig:
    provider = os.environ.get("AI_PROVIDER", "anthropic").lower()
    return AIConfig(
        provider=provider,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL),
        openai_model=os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        max_retries=int(os.environ.get("AI_MAX_RETRIES", str(MAX_LINT_RETRIES))),
    )
