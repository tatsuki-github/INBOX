"""Practice validation wrapper with lint retry support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lint_events import validate_practice_block  # noqa: E402

from .creative_rules import (
    GenerationRules,
    load_rules,
    validate_experiment_notes,
    validate_fixed_constraints,
    validate_template_diff,
)


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)

    @property
    def error_text(self) -> str:
        return "\n".join(self.errors)


def validate_practice(
    title: str,
    practice: dict[str, Any],
    *,
    base_items: list[dict[str, Any]] | None = None,
    rules: GenerationRules | None = None,
    is_experiment: bool = False,
) -> ValidationResult:
    rules = rules or load_rules()
    errors: list[str] = []
    errors.extend(validate_practice_block(title, practice))
    errors.extend(validate_fixed_constraints(practice, rules))
    errors.extend(validate_experiment_notes(practice, rules, is_experiment=is_experiment))
    if base_items is not None:
        errors.extend(
            validate_template_diff(
                base_items,
                practice.get("items") or [],
                rules,
                is_experiment=is_experiment,
            )
        )
    return ValidationResult(ok=not errors, errors=errors)


@dataclass
class RetryState:
    attempt: int = 0
    max_attempts: int = 3
    last_errors: list[str] = field(default_factory=list)

    def can_retry(self) -> bool:
        return self.attempt < self.max_attempts

    def record_failure(self, errors: list[str]) -> None:
        self.attempt += 1
        self.last_errors = list(errors)
