#!/usr/bin/env python3
"""Query the repo knowledge graph for search paths and neighborhood context."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from knowledge_graph.query import query_knowledge_graph  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", "-q", required=True, help="Natural-language question")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--expand-hops", type=int, default=1)
    parser.add_argument("--context-files", type=int, default=6)
    parser.add_argument("--no-context", action="store_true", help="Return refs only")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)

    result = query_knowledge_graph(
        args.question,
        top_k=args.top_k,
        expand_hops=args.expand_hops,
        context_files=args.context_files,
        include_context=not args.no_context,
    )

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"Q: {result['question']}")
    print("\nMatched nodes:")
    for node in result["matched_nodes"][:12]:
        print(f"  - [{node['type']}] {node['label']} ({node['id']}) score={node['score']}")
        if node.get("hint"):
            print(f"      hint: {node['hint']}")
    print("\nRefs:")
    for ref in result["refs"]:
        print(f"  - {ref}")
    if result.get("contexts"):
        print("\nContext snippets:")
        for ctx in result["contexts"]:
            print(f"\n## {ctx['path']}")
            print(ctx["snippet"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
