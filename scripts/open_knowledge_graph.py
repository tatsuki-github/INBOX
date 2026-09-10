#!/usr/bin/env python3
"""Serve out/knowledge-graph.html over HTTP and print the URL.

GitHub のファイル画面や、一部環境の file:// + CDN 制限では開けないことがあるため、
ローカル HTTP で確実に開くためのヘルパー。
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "out"
HTML_NAME = "knowledge-graph.html"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--build",
        action="store_true",
        help="Regenerate the knowledge graph before serving",
    )
    args = parser.parse_args(argv)

    if args.build:
        sys.path.insert(0, str(ROOT / "scripts"))
        from knowledge_graph.builder import write_knowledge_graph

        write_knowledge_graph()

    html_path = OUT_DIR / HTML_NAME
    if not html_path.exists():
        print(f"Missing {html_path}. Run: python3 scripts/build_knowledge_graph.py", file=sys.stderr)
        return 1

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT_DIR))
    url = f"http://127.0.0.1:{args.port}/{HTML_NAME}"
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"Serving {OUT_DIR}")
        print(f"Open: {url}")
        if not args.no_browser:
            try:
                webbrowser.open(url)
            except Exception as exc:
                print(f"(browser open skipped: {exc})", file=sys.stderr)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
