#!/usr/bin/env python3
"""Build repository knowledge graph (routing map) into out/knowledge-graph.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from knowledge_graph.builder import (  # noqa: E402
    KG_HTML_PATH,
    KG_MIN_PATH,
    KG_PATH,
    ROOT,
    build_knowledge_graph,
    normalize_graph_for_compare,
    write_knowledge_graph,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=KG_PATH,
        help="Output path for pretty JSON (default: out/knowledge-graph.json)",
    )
    parser.add_argument(
        "--min-out",
        type=Path,
        default=KG_MIN_PATH,
        help="Output path for minified JSON",
    )
    parser.add_argument(
        "--html-out",
        type=Path,
        default=KG_HTML_PATH,
        help="Output path for visualization HTML",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed graph matches a fresh build (ignores generated_at)",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Override generated_at timestamp (testing / stable builds)",
    )
    args = parser.parse_args(argv)

    if args.check:
        if not args.out.exists():
            print(f"Missing committed graph: {args.out}", file=sys.stderr)
            return 1
        committed = json.loads(args.out.read_text(encoding="utf-8"))
        fresh = build_knowledge_graph(generated_at=committed.get("generated_at"))
        if normalize_graph_for_compare(committed) != normalize_graph_for_compare(fresh):
            print(
                "Knowledge graph is stale. Run: python3 scripts/build_knowledge_graph.py",
                file=sys.stderr,
            )
            print(
                f"committed nodes={len(committed.get('nodes') or [])} "
                f"edges={len(committed.get('edges') or [])}; "
                f"fresh nodes={len(fresh.get('nodes') or [])} "
                f"edges={len(fresh.get('edges') or [])}",
                file=sys.stderr,
            )
            return 1
        if not args.html_out.exists():
            print(f"Missing visualization HTML: {args.html_out}", file=sys.stderr)
            return 1
        html = args.html_out.read_text(encoding="utf-8")
        if 'id="kg-data"' not in html or "vis-network" not in html:
            print(f"HTML visualization looks incomplete: {args.html_out}", file=sys.stderr)
            return 1
        print(f"OK: {args.out} matches fresh build; HTML present")
        return 0

    path, min_path, html_path, graph = write_knowledge_graph(
        args.out,
        min_path=args.min_out,
        html_path=args.html_out,
        generated_at=args.generated_at,
    )
    print(f"Wrote {path.relative_to(ROOT)} ({len(graph['nodes'])} nodes, {len(graph['edges'])} edges)")
    print(f"Wrote {min_path.relative_to(ROOT)}")
    print(f"Wrote {html_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
