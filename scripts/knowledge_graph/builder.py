"""Build a routing-oriented knowledge graph from repository sources."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
KG_PATH = ROOT / "out" / "knowledge-graph.json"
KG_MIN_PATH = ROOT / "out" / "knowledge-graph.min.json"
KG_HTML_PATH = ROOT / "out" / "knowledge-graph.html"
KG_PDF_PATH = ROOT / "out" / "knowledge-graph.pdf"

SOURCE_GLOBS: list[tuple[str, list[str], str]] = [
    # (glob_or_path relative, topics, hint)
    ("README.md", ["meta", "calendar", "practice"], "リポジトリ概要・生成コマンド・INBOX 運用"),
    ("calendar.md", ["calendar"], "当年の Markdown カレンダー（生成物）"),
    ("docs/data-model.md", ["schema", "practice", "calendar"], "イベント/練習のデータ辞書"),
    ("docs/ai-practice-generation.md", ["ai", "practice", "norwegian"], "AI 練習生成・RAG・ADR 入口"),
    ("input/practice_templates.yaml", ["practice", "template"], "名前付き練習テンプレート正本"),
    ("input/practice_schedules.yaml", ["practice", "schedule"], "朝夕練スケジュール定義"),
    ("input/ai_generation_rules.yaml", ["ai", "practice", "rules"], "AI 固定/可変/創作ルール"),
    ("input/daniels_vdot_paces.yaml", ["pace", "danish", "norwegian"], "Daniels VDOT ペース表"),
    ("input/arato_tamana_report.yaml", ["athlete_records", "arato"], "荒尾・玉名記録 PDF 設定"),
    ("out/daiming-practice-menus-kpace.md", ["practice", "pace"], "岱明練習 k/pace 横断一覧"),
    ("input/external/INDEX.md", ["meta", "practice", "athlete_records"], "外部ソース（Drive/Notion/GitHub）取り込み目録"),
    ("input/external/drive/INDEX.md", ["practice", "athlete_records", "meta"], "Google ドライブいだてん関連スナップショット"),
    ("input/external/notion/INDEX.md", ["practice", "athlete_records", "injury"], "Notion いだてん岱明スナップショット"),
    ("input/external/github/INDEX.md", ["meta"], "関連リポジトリ調査（対象外含む）"),
    (
        "input/external/drive/shared/練習/練習の記録.md",
        ["practice"],
        "共有ドライブ練習ログ（2025）",
    ),
    (
        "input/external/drive/shared/名簿/2025年度_岱明中学校陸上競技部_部員名簿.csv",
        ["practice", "athlete_records"],
        "2025 岱明部員名簿",
    ),
    (
        "input/external/notion/databases/いだてん岱明生徒/rows.json",
        ["practice", "athlete_records"],
        "Notion 生徒 DB スナップショット",
    ),
    (
        "input/external/notion/databases/2026年度中学生記録/rows.json",
        ["athlete_records"],
        "Notion 2026 中学生記録スナップショット",
    ),
]

LIGHTWEIGHT_SUFFIXES = {".csv", ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp"}

TOPIC_DEFS: list[tuple[str, str, str]] = [
    ("calendar", "カレンダー / 予定", "年次予定・メモ・祝日の入口"),
    ("practice", "岱明練習", "practice ブロック・メニュー・欠席・テンプレ"),
    ("athlete_records", "選手記録", "荒尾・玉名中学生記録・所属ランキング"),
    ("norwegian", "Norwegian Method", "GZ/閾値・VDOT・原則メモ"),
    ("ai", "AI 練習生成", "プロンプト・ルール・週次/単日生成"),
    ("schema", "スキーマ", "JSON Schema とデータモデル"),
    ("pace", "ペース", "k/pace・VDOT・GZ 表"),
    ("injury", "ケガ / RRI", "ランニング障害・回復エビデンス"),
    ("meta", "リポジトリ運用", "README・生成パイプライン"),
]

QUERY_HINTS: list[tuple[str, str, list[str]]] = [
    (
        "練習メニューの中身は？",
        "practice 付きイベントと practice.json を見る",
        ["topic:practice", "source:input/practice_templates.yaml"],
    ),
    (
        "欠席者は誰？",
        "practice_absentees.csv と events YAML の absentees",
        ["topic:practice"],
    ),
    (
        "GZ / 閾値ペースは？",
        "Norwegian メモ + daniels_pace / VDOT 表",
        ["topic:norwegian", "topic:pace"],
    ),
    (
        "選手の記録は？",
        "notion_records と荒尾玉名 PDF/設定",
        ["topic:athlete_records"],
    ),
    (
        "今日の予定は？",
        "events YAML / events.json / calendar.md",
        ["topic:calendar"],
    ),
    (
        "AI で練習を作るには？",
        "ai-practice-generation.md と prompts / rules",
        ["topic:ai"],
    ),
]


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _node(
    node_id: str,
    node_type: str,
    label: str,
    *,
    topics: Iterable[str] = (),
    refs: Iterable[str] = (),
    hint: str = "",
) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "label": label,
        "topics": sorted(set(topics)),
        "refs": sorted(set(refs)),
        "hint": hint,
    }


def _edge(frm: str, to: str, rel: str) -> dict[str, str]:
    return {"from": frm, "to": to, "rel": rel}


def _add_node(nodes: dict[str, dict[str, Any]], node: dict[str, Any]) -> None:
    existing = nodes.get(node["id"])
    if existing is None:
        nodes[node["id"]] = node
        return
    existing["topics"] = sorted(set(existing["topics"]) | set(node["topics"]))
    existing["refs"] = sorted(set(existing["refs"]) | set(node["refs"]))
    if node["hint"] and (not existing["hint"] or len(node["hint"]) > len(existing["hint"])):
        existing["hint"] = node["hint"]


def _add_edge(edges: set[tuple[str, str, str]], frm: str, to: str, rel: str) -> None:
    if frm == to:
        return
    edges.add((frm, to, rel))


def _discover_years() -> list[int]:
    years: list[int] = []
    for path in sorted((ROOT / "input").glob("events.*.yaml")):
        m = re.fullmatch(r"events\.(\d{4})\.yaml", path.name)
        if m:
            years.append(int(m.group(1)))
    return years


def _source_id(rel_path: str) -> str:
    return f"source:{rel_path}"


def _register_source(
    nodes: dict[str, dict[str, Any]],
    edges: set[tuple[str, str, str]],
    rel_path: str,
    *,
    topics: list[str],
    hint: str,
    derived_from: str | None = None,
) -> str:
    sid = _source_id(rel_path)
    _add_node(
        nodes,
        _node(
            sid,
            "Source",
            Path(rel_path).name,
            topics=topics,
            refs=[rel_path],
            hint=hint,
        ),
    )
    for topic in topics:
        _add_edge(edges, f"topic:{topic}", sid, "search_here")
    if derived_from:
        _add_edge(edges, sid, derived_from, "derived_from")
    return sid


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _athlete_key(name: str) -> str:
    name = name.strip()
    # Prefer family-name-ish short forms already used in absentees
    return name


def _collect_athletes_from_absentees(year: int) -> set[str]:
    path = ROOT / "out" / str(year) / "practice_absentees.csv"
    names: set[str] = set()
    if not path.exists():
        return names
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = (row.get("name") or "").strip()
            if name:
                names.add(_athlete_key(name))
    return names


def _collect_athletes_from_events(year: int) -> set[str]:
    path = ROOT / "input" / f"events.{year}.yaml"
    data = _load_yaml(path)
    names: set[str] = set()
    if not isinstance(data, dict):
        return names
    for ev in data.get("events") or []:
        practice = ev.get("practice") or {}
        for name in practice.get("absentees") or []:
            if isinstance(name, str) and name.strip():
                names.add(_athlete_key(name.strip()))
    return names


def _collect_athletes_from_records(path: Path) -> dict[str, dict[str, Any]]:
    """Return mapping short/full name -> sample affiliation info."""
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    by_name: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return by_name
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = (row.get("name") or "").strip()
        if not name:
            continue
        aff = (row.get("affiliation") or "").strip()
        # Keep 岱明関連を優先してヒント化
        if name not in by_name or ("岱明" in aff and "岱明" not in (by_name[name].get("affiliation") or "")):
            by_name[name] = {
                "affiliation": aff,
                "grade": row.get("grade"),
                "gender": row.get("gender"),
            }
    return by_name


def _templates() -> list[dict[str, Any]]:
    data = _load_yaml(ROOT / "input" / "practice_templates.yaml")
    if not isinstance(data, dict):
        return []
    return list(data.get("templates") or [])


def _tags_from_events(year: int) -> set[str]:
    path = ROOT / "input" / f"events.{year}.yaml"
    data = _load_yaml(path)
    tags: set[str] = set()
    if not isinstance(data, dict):
        return tags
    for ev in data.get("events") or []:
        raw = ev.get("tags") or []
        if isinstance(raw, str):
            raw = [t.strip() for t in raw.split(",") if t.strip()]
        for tag in raw:
            if isinstance(tag, str) and tag.strip():
                tags.add(tag.strip())
    return tags


def build_knowledge_graph(*, generated_at: str | None = None) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()
    years = _discover_years()

    for topic_id, label, hint in TOPIC_DEFS:
        _add_node(
            nodes,
            _node(f"topic:{topic_id}", "Topic", label, topics=[topic_id], hint=hint),
        )

    # Static high-value sources
    for rel, topics, hint in SOURCE_GLOBS:
        path = ROOT / rel
        if path.exists():
            _register_source(nodes, edges, rel, topics=topics, hint=hint)

    # Docs ADR
    adr_dir = ROOT / "docs" / "adr"
    if adr_dir.exists():
        for path in sorted(adr_dir.glob("*.md")):
            rel = _rel(path)
            sid = _register_source(
                nodes,
                edges,
                rel,
                topics=["ai", "practice", "meta"],
                hint=f"ADR: {path.stem}",
            )
            _add_edge(edges, "source:docs/ai-practice-generation.md", sid, "see_also")

    # Prompts
    prompts_dir = ROOT / "prompts"
    if prompts_dir.exists():
        for path in sorted(prompts_dir.iterdir()):
            if path.is_file() and path.suffix in {".md", ".yaml", ".yml"}:
                rel = _rel(path)
                _register_source(
                    nodes,
                    edges,
                    rel,
                    topics=["ai", "practice"],
                    hint=f"LLM プロンプト / few-shot: {path.name}",
                )

    # Schemas
    schemas_dir = ROOT / "schemas"
    if schemas_dir.exists():
        for path in sorted(schemas_dir.glob("*.json")):
            rel = _rel(path)
            _register_source(
                nodes,
                edges,
                rel,
                topics=["schema"],
                hint=f"JSON Schema: {path.name}",
            )

    # Memos
    memos_dir = ROOT / "input" / "memos"
    if memos_dir.exists():
        for path in sorted(memos_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = _rel(path)
            topics = ["meta"]
            hint = f"メモ素材: {path.name}"
            lower = path.name.lower()
            if "norwegian" in lower:
                topics = ["norwegian", "practice", "pace"]
                hint = "Norwegian Method 原典メモ"
            elif "rri" in lower or "heal" in lower or "injur" in lower:
                topics = ["injury"]
                hint = "ランニング障害・回復エビデンス"
            elif path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                topics = ["calendar", "practice"]
                hint = f"画像メモ（構造参照のみ）: {path.name}"
            _register_source(nodes, edges, rel, topics=topics, hint=hint)

    # Research projects
    research = ROOT / "projects" / "running-injury-research"
    if research.exists():
        for path in sorted(research.rglob("*.md")):
            rel = _rel(path)
            _register_source(
                nodes,
                edges,
                rel,
                topics=["injury"],
                hint=f"障害研究メモ: {path.name}",
            )

    # Year nodes + event / practice outputs
    athlete_refs: dict[str, set[str]] = defaultdict(set)
    template_ids: dict[str, str] = {}

    for tpl in _templates():
        tid = str(tpl.get("id") or "").strip()
        if not tid:
            continue
        label = str(tpl.get("label") or tid)
        template_ids[tid] = label
        nid = f"entity:template:{tid}"
        _add_node(
            nodes,
            _node(
                nid,
                "Template",
                label,
                topics=["practice", "template"],
                refs=["input/practice_templates.yaml"],
                hint=f"テンプレート ID `{tid}`",
            ),
        )
        _add_edge(edges, nid, "source:input/practice_templates.yaml", "documented_in")
        _add_edge(edges, "topic:practice", nid, "related_to")

    for year in years:
        yid = f"entity:year:{year}"
        _add_node(
            nodes,
            _node(
                yid,
                "Year",
                f"{year}年",
                topics=["calendar", "practice"],
                refs=[f"input/events.{year}.yaml"],
                hint=f"{year} 年次カレンダーと練習のハブ",
            ),
        )

        events_yaml = f"input/events.{year}.yaml"
        if (ROOT / events_yaml).exists():
            sid = _register_source(
                nodes,
                edges,
                events_yaml,
                topics=["calendar", "practice"],
                hint=f"{year}年イベント正本（practice 含む）",
            )
            _add_edge(edges, yid, sid, "search_here")

        out_dir = ROOT / "out" / str(year)
        year_outputs = [
            ("events.json", ["calendar"], f"{year}年イベント JSON（生成物）"),
            ("practice.json", ["practice"], f"{year}年練習セッション（生成物）"),
            ("practice_items.csv", ["practice"], f"{year}年メニュー項目行"),
            ("practice_absentees.csv", ["practice", "athlete"], f"{year}年欠席者（session×選手）"),
            ("practice-summary.md", ["practice"], f"{year}年練習サマリ"),
            ("calendar.md", ["calendar"], f"{year}年 Markdown カレンダー"),
            ("source.csv", ["calendar"], f"{year}年 source CSV（軽量）"),
            ("google.csv", ["calendar"], f"{year}年 Google CSV（軽量）"),
            ("notion.csv", ["calendar"], f"{year}年 Notion CSV（軽量）"),
        ]
        for name, topics, hint in year_outputs:
            path = out_dir / name
            if not path.exists():
                continue
            rel = _rel(path)
            light = path.suffix.lower() in LIGHTWEIGHT_SUFFIXES and name.endswith(".csv")
            if light:
                hint = hint + "（派生・参照のみ）"
            sid = _register_source(
                nodes,
                edges,
                rel,
                topics=topics,
                hint=hint,
                derived_from=_source_id(events_yaml) if (ROOT / events_yaml).exists() else None,
            )
            _add_edge(edges, yid, sid, "search_here")

        for name in _collect_athletes_from_absentees(year) | _collect_athletes_from_events(year):
            athlete_refs[name].add(f"out/{year}/practice_absentees.csv")
            athlete_refs[name].add(f"input/events.{year}.yaml")

        for tag in _tags_from_events(year):
            # Keep only somewhat specific tags to avoid exploding the graph
            if tag in {"予定", "メモ", "祝日"}:
                continue
            tid = f"entity:tag:{tag}"
            _add_node(
                nodes,
                _node(
                    tid,
                    "Entity",
                    tag,
                    topics=["calendar", "practice"] if "練習" in tag or "practice" in tag else ["calendar"],
                    refs=[events_yaml],
                    hint=f"イベントタグ `{tag}`",
                ),
            )
            _add_edge(edges, tid, _source_id(events_yaml), "mentioned_in")

    # Athlete records
    records_path = ROOT / "out" / "analysis" / "notion_records_2026.json"
    record_athletes = _collect_athletes_from_records(records_path)
    if records_path.exists():
        rel = _rel(records_path)
        sid = _register_source(
            nodes,
            edges,
            rel,
            topics=["athlete_records"],
            hint="荒尾・玉名中学生記録行（Notion 由来 JSON）",
        )
        _add_edge(edges, "topic:athlete_records", sid, "search_here")

    for pdf in sorted((ROOT / "out" / "analysis").glob("*.pdf")) if (ROOT / "out" / "analysis").exists() else []:
        rel = _rel(pdf)
        _register_source(
            nodes,
            edges,
            rel,
            topics=["athlete_records"],
            hint=f"記録 PDF（参照のみ）: {pdf.name}",
        )

    # Prefer short names already used in practice; also index full record names for 岱明
    daiming_full_names = {
        name: info
        for name, info in record_athletes.items()
        if "岱明" in (info.get("affiliation") or "")
    }

    all_athlete_labels = set(athlete_refs) | set(daiming_full_names)
    # Map short absentee names to full names when unique prefix match
    for short in list(athlete_refs):
        matches = [full for full in daiming_full_names if full.startswith(short)]
        if len(matches) == 1:
            athlete_refs[short].add(_rel(records_path))
            full = matches[0]
            athlete_refs[full] |= set(athlete_refs[short]) | {_rel(records_path)}

    for name in sorted(all_athlete_labels):
        refs = set(athlete_refs.get(name, set()))
        info = record_athletes.get(name) or {}
        if records_path.exists() and (name in record_athletes or any(f.startswith(name) for f in daiming_full_names)):
            refs.add(_rel(records_path))
        aff = info.get("affiliation") or ""
        hint = f"所属:{aff}" if aff else "部員エンティティ"
        nid = f"entity:athlete:{name}"
        _add_node(
            nodes,
            _node(
                nid,
                "Athlete",
                name,
                topics=["athlete", "practice", "athlete_records"],
                refs=refs or (["out/analysis/notion_records_2026.json"] if records_path.exists() else []),
                hint=hint,
            ),
        )
        for ref in refs:
            _add_edge(edges, nid, _source_id(ref), "mentioned_in")
        _add_edge(edges, "topic:practice", nid, "related_to")
        if aff:
            _add_edge(edges, "topic:athlete_records", nid, "related_to")

    # Query hints
    for idx, (label, hint, targets) in enumerate(QUERY_HINTS):
        qid = f"query:{idx}:{label[:24]}"
        _add_node(
            nodes,
            _node(
                qid,
                "QueryHint",
                label,
                topics=[],
                refs=[],
                hint=hint,
            ),
        )
        for target in targets:
            if target in nodes:
                _add_edge(edges, qid, target, "search_here")
            elif target.startswith("topic:"):
                _add_edge(edges, qid, target, "search_here")

    # Cross-links
    if "source:input/daniels_vdot_paces.yaml" in nodes:
        _add_edge(
            edges,
            "topic:norwegian",
            "source:input/daniels_vdot_paces.yaml",
            "see_also",
        )
    if "source:input/memos/norwegian_method_applied_full.txt" in nodes:
        _add_edge(
            edges,
            "topic:pace",
            "source:input/memos/norwegian_method_applied_full.txt",
            "documented_in",
        )

    generated = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    graph = {
        "version": 1,
        "generated_at": generated,
        "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
        "edges": [
            _edge(frm, to, rel)
            for frm, to, rel in sorted(edges)
            if frm in nodes and to in nodes
        ],
    }
    return graph


def normalize_graph_for_compare(graph: dict[str, Any]) -> dict[str, Any]:
    """Drop volatile fields for CI equality checks."""
    return {
        "version": graph.get("version"),
        "nodes": graph.get("nodes") or [],
        "edges": graph.get("edges") or [],
    }


def write_knowledge_graph(
    path: Path | None = None,
    *,
    min_path: Path | None = None,
    html_path: Path | None = None,
    pdf_path: Path | None = None,
    generated_at: str | None = None,
) -> tuple[Path, Path, Path, Path, dict[str, Any]]:
    from .html_renderer import write_knowledge_graph_html
    from .pdf_renderer import write_knowledge_graph_pdf

    path = path or KG_PATH
    min_path = min_path or KG_MIN_PATH
    html_path = html_path or KG_HTML_PATH
    pdf_path = pdf_path or KG_PDF_PATH
    graph = build_knowledge_graph(generated_at=generated_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    min_path.write_text(json.dumps(graph, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    html_out = write_knowledge_graph_html(graph, html_path)
    pdf_out = write_knowledge_graph_pdf(graph, pdf_path)
    return path, min_path, html_out, pdf_out, graph
