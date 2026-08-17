"""Single-day practice generation orchestrator."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from .config import AIConfig, load_config
from .creative_rules import apply_template_base, load_rules
from .llm_client import LLMClient, create_llm_client, extract_json_object
from .prompt_builder import build_practice_system_prompt, build_practice_user_prompt
from .template_selector import TemplateMatch, select_best_template
from .validator import RetryState, validate_practice


@dataclass
class GenerationMetadata:
    template_id: str | None = None
    template_ids: list[str] = field(default_factory=list)
    is_experiment: bool = False
    attempts: int = 0
    llm_used: bool = False
    dry_run: bool = False


@dataclass
class GenerationResult:
    practice: dict[str, Any]
    metadata: GenerationMetadata
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _merge_llm_output(base: dict[str, Any], llm_data: dict[str, Any]) -> dict[str, Any]:
    practice = copy.deepcopy(base)
    if llm_data.get("warmup") is not None:
        practice["warmup"] = llm_data["warmup"]
    if llm_data.get("notes") is not None:
        practice["notes"] = llm_data["notes"]
    if isinstance(llm_data.get("items"), list) and llm_data["items"]:
        practice["items"] = llm_data["items"]
    if "absentees" in llm_data:
        practice["absentees"] = llm_data["absentees"]
    return practice


def _default_notes_for_template(template: TemplateMatch, query: str) -> str | None:
    base_notes = (template.practice or {}).get("notes")
    if base_notes:
        return str(base_notes)
    if "軽" in query or "gz" in query.lower():
        return "軽いポイント。勝ちにいかない。1本目は設定より遅めでOK。"
    return None


def generate_practice(
    query: str,
    *,
    title: str = "AI生成練習",
    template: TemplateMatch | None = None,
    llm: LLMClient | None = None,
    config: AIConfig | None = None,
    dry_run: bool = False,
    is_experiment: bool = False,
    t_pace: str | None = "4:01",
) -> GenerationResult:
    config = config or load_config()
    rules = load_rules()
    metadata = GenerationMetadata(is_experiment=is_experiment, dry_run=dry_run)

    template = template or select_best_template(query)
    if template is None:
        return GenerationResult(
            practice={"items": []},
            metadata=metadata,
            errors=["No matching template found for query"],
        )

    metadata.template_id = template.template_id
    metadata.template_ids = [template.template_id]
    base_practice = apply_template_base(template.practice)
    base_items = copy.deepcopy(base_practice.get("items") or [])

    if dry_run or llm is None:
        if not base_practice.get("notes"):
            note = _default_notes_for_template(template, query)
            if note:
                base_practice["notes"] = note
        if is_experiment and base_practice.get("notes"):
            prefix = (rules.creative.get("weekly_experiment") or {}).get(
                "require_notes_prefix", "【実験】"
            )
            if prefix and not str(base_practice["notes"]).startswith(prefix):
                base_practice["notes"] = prefix + str(base_practice["notes"])
        validation = validate_practice(
            title,
            base_practice,
            base_items=base_items,
            rules=rules,
            is_experiment=is_experiment,
        )
        metadata.attempts = 1
        return GenerationResult(
            practice=base_practice,
            metadata=metadata,
            errors=[] if validation.ok else validation.errors,
        )

    retry = RetryState(max_attempts=config.max_retries)
    practice = base_practice
    lint_errors: list[str] | None = None
    system = build_practice_system_prompt(t_pace=t_pace)

    while retry.can_retry():
        user = build_practice_user_prompt(query, template, lint_errors=lint_errors)
        raw = llm.complete(system, user)
        metadata.llm_used = True
        try:
            llm_data = extract_json_object(raw)
            practice = _merge_llm_output(base_practice, llm_data)
        except ValueError as exc:
            retry.record_failure([str(exc)])
            lint_errors = [str(exc)]
            continue

        validation = validate_practice(
            title,
            practice,
            base_items=base_items,
            rules=rules,
            is_experiment=is_experiment,
        )
        if validation.ok:
            metadata.attempts = retry.attempt + 1
            return GenerationResult(practice=practice, metadata=metadata)

        retry.record_failure(validation.errors)
        lint_errors = validation.errors

    metadata.attempts = retry.attempt
    return GenerationResult(
        practice=practice,
        metadata=metadata,
        errors=retry.last_errors,
    )


def generate_practice_auto(
    query: str,
    *,
    title: str = "AI生成練習",
    dry_run: bool = False,
    is_experiment: bool = False,
    t_pace: str | None = "4:01",
) -> GenerationResult:
    config = load_config()
    llm = None if dry_run else create_llm_client(config)
    return generate_practice(
        query,
        title=title,
        llm=llm,
        config=config,
        dry_run=dry_run or llm is None,
        is_experiment=is_experiment,
        t_pace=t_pace,
    )
