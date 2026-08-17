#!/usr/bin/env python3
"""Explain practice menus using RAG + Norwegian Method context."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ai.intensity_distribution import distribution_guidance_for_prompt
from ai.config import load_config  # noqa: E402
from ai.llm_client import create_llm_client  # noqa: E402
from ai.prompt_builder import build_explain_system_prompt, build_explain_user_prompt  # noqa: E402
from ai.rag.retriever import retrieve_context  # noqa: E402


def explain_offline(question: str, context_chunks: list[str]) -> str:
    lines = ["（オフライン説明 — LLM 未使用）", "", f"Q: {question}", "", "関連コンテキスト:"]
    for idx, chunk in enumerate(context_chunks, 1):
        preview = chunk[:400].replace("\n", " ")
        lines.append(f"{idx}. {preview}...")
    lines.append("")
    lines.append(distribution_guidance_for_prompt())
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    chunks = retrieve_context(args.question, top_k=args.top_k)
    config = load_config()
    llm = None if args.dry_run else create_llm_client(config)

    if llm is None:
        print(explain_offline(args.question, chunks))
        return 0

    system = build_explain_system_prompt()
    user = build_explain_user_prompt(args.question, chunks)
    print(llm.complete(system, user))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
