"""Query the repository knowledge graph for routing paths + neighborhood context."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .builder import KG_PATH, ROOT, build_knowledge_graph

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u3040-\u30ff]+|[\u3400-\u9fff]+", re.UNICODE)
_PARTICLE_SPLIT = re.compile(r"[のとへをはがでにでもや]+")


def _tokenize(text: str) -> list[str]:
    """Tokenize for JP/EN routing queries (labels are often short JP names)."""
    text = text.lower().strip()
    tokens: list[str] = []
    for part in _PARTICLE_SPLIT.split(text):
        part = part.strip()
        if not part:
            continue
        for m in _TOKEN_RE.findall(part):
            if len(m) >= 1:
                tokens.append(m)
        # Character bigrams help when a compound stays glued
        chars = re.findall(r"[\u3400-\u9fff]", part)
        if len(chars) >= 2:
            for i in range(len(chars) - 1):
                tokens.append(chars[i] + chars[i + 1])
    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _resolve_relative_dates(question: str, *, as_of_date: date | None = None) -> str:
    """Expand relative day words to ISO dates in the calendar's Japan timezone."""
    offsets = {
        "今日": 0,
        "きょう": 0,
        "昨日": -1,
        "きのう": -1,
        "明日": 1,
        "あした": 1,
        "あす": 1,
        "today": 0,
        "yesterday": -1,
        "tomorrow": 1,
    }
    current_date = as_of_date or datetime.now(ZoneInfo("Asia/Tokyo")).date()
    week_monday = current_date - timedelta(days=current_date.weekday())
    weekday_jp = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}

    def replace_japanese_weekday(match: re.Match[str]) -> str:
        offset = {"先週": -1, "今週": 0, "来週": 1, None: 0}[match.group(1)]
        return (week_monday + timedelta(weeks=offset, days=weekday_jp[match.group(2)])).isoformat()

    resolved = re.sub(r"(先週|今週|来週)?([月火水木金土日])(?:曜日|曜)", replace_japanese_weekday, question)
    weekdays_en = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

    def replace_english_weekday(match: re.Match[str]) -> str:
        offset = {"last": -1, "this": 0, "next": 1, None: 0}[match.group(1).lower() if match.group(1) else None]
        weekday = weekdays_en.index(match.group(2).lower())
        return (week_monday + timedelta(weeks=offset, days=weekday)).isoformat()

    resolved = re.sub(
        r"\b(last|this|next)?\s*(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
        replace_english_weekday,
        resolved,
        flags=re.IGNORECASE,
    )
    pattern = "|".join(re.escape(term) for term in sorted(offsets, key=len, reverse=True))
    resolved = re.sub(
        pattern,
        lambda match: (current_date + timedelta(days=offsets[match.group(0).lower()])).isoformat(),
        resolved,
        flags=re.IGNORECASE,
    )

    def replace_month_day(match: re.Match[str]) -> str:
        try:
            return date(current_date.year, int(match.group(1)), int(match.group(2))).isoformat()
        except ValueError:
            return match.group(0)

    def replace_full_date(match: re.Match[str]) -> str:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
        except ValueError:
            return match.group(0)

    resolved = re.sub(r"(?<!\d)(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", replace_full_date, resolved)
    resolved = re.sub(r"(?<!\d)(\d{4})/(\d{1,2})/(\d{1,2})(?!\d)", replace_full_date, resolved)
    resolved = re.sub(r"(?<![\d年])(\d{1,2})\s*月\s*(\d{1,2})\s*日", replace_month_day, resolved)
    return re.sub(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?!\d)", replace_month_day, resolved)


def _resolve_week_range(question: str, *, as_of_date: date | None = None) -> tuple[date, date] | None:
    """Return Monday-Sunday bounds for a Japanese or English relative week phrase."""
    lowered = question.lower()
    offset_weeks = None
    for phrase in ("来週", "next week"):
        if phrase in lowered:
            offset_weeks = 1
            break
    if offset_weeks is None:
        for phrase in ("先週", "last week"):
            if phrase in lowered:
                offset_weeks = -1
                break
    if offset_weeks is None and any(phrase in lowered for phrase in ("今週", "this week")):
        offset_weeks = 0
    if offset_weeks is None:
        return None
    reference = as_of_date or datetime.now(ZoneInfo("Asia/Tokyo")).date()
    monday = reference - timedelta(days=reference.weekday()) + timedelta(weeks=offset_weeks)
    return monday, monday + timedelta(days=6)


def _resolve_month_range(question: str, *, as_of_date: date | None = None) -> tuple[date, date] | None:
    """Return date bounds for this/next/last month or an explicit Japanese month."""
    lowered = question.lower()
    reference = as_of_date or datetime.now(ZoneInfo("Asia/Tokyo")).date()
    offset = 0
    for phrase in ("来月", "next month"):
        if phrase in lowered:
            offset = 1
            break
    else:
        for phrase in ("先月", "last month"):
            if phrase in lowered:
                offset = -1
                break
        else:
            if not any(phrase in lowered for phrase in ("今月", "this month")):
                fiscal_year_month = re.search(r"(?<!\d)(\d{4})年度\s*(1[0-2]|0?[1-9])月", question)
                if fiscal_year_month:
                    year, month = int(fiscal_year_month.group(1)), int(fiscal_year_month.group(2))
                    if month <= 3:
                        year += 1
                    return date(year, month, 1), date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
                explicit_year_month = re.search(r"(?<!\d)(\d{4})年\s*(1[0-2]|0?[1-9])月(?!\d|日)", question)
                if explicit_year_month:
                    year, month = int(explicit_year_month.group(1)), int(explicit_year_month.group(2))
                    return date(year, month, 1), date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
                slash_year_month = re.search(r"(?<!\d)(\d{4})/(1[0-2]|0?[1-9])(?![/\d])", question)
                if slash_year_month:
                    year, month = int(slash_year_month.group(1)), int(slash_year_month.group(2))
                    return date(year, month, 1), date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
                iso_year_month = re.search(r"(?<!\d)(\d{4})-(1[0-2]|0[1-9])(?!-\d)", question)
                if iso_year_month:
                    year, month = int(iso_year_month.group(1)), int(iso_year_month.group(2))
                    return date(year, month, 1), date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
                explicit = re.search(r"(?<!\d)(1[0-2]|0?[1-9])月(?!\d|日)", question)
                if not explicit:
                    return None
                month = int(explicit.group(1))
                year = reference.year
                return date(year, month, 1), date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    target_month = reference.month + offset
    target_year = reference.year
    if target_month == 0:
        target_month, target_year = 12, target_year - 1
    elif target_month == 13:
        target_month, target_year = 1, target_year + 1
    return date(target_year, target_month, 1), date(
        target_year + (target_month == 12), target_month % 12 + 1, 1
    ) - timedelta(days=1)


def _resolve_fiscal_year_range(question: str) -> tuple[date, date] | None:
    """Return Japanese fiscal-year bounds (April through March)."""
    match = re.search(r"(?<!\d)(\d{4})年度", question)
    if not match:
        return None
    year = int(match.group(1))
    return date(year, 4, 1), date(year + 1, 3, 31)


def _resolve_calendar_year_range(
    question: str,
    *,
    as_of_date: date | None = None,
) -> tuple[date, date] | None:
    """Resolve calendar-year questions separately from Japanese fiscal years."""
    reference = as_of_date or datetime.now(ZoneInfo("Asia/Tokyo")).date()
    lowered = question.lower()
    offsets = {"去年": -1, "昨年": -1, "今年": 0, "来年": 1, "last year": -1, "this year": 0, "next year": 1}
    year = None
    for phrase, offset in offsets.items():
        if phrase in lowered:
            year = reference.year + offset
            break
    if year is None:
        explicit = re.search(r"(?<!\d)(\d{4})年(?!度|\d)", question)
        if explicit:
            year = int(explicit.group(1))
    if year is None:
        return None
    return date(year, 1, 1), date(year, 12, 31)


def load_graph(path: Path | None = None) -> dict[str, Any]:
    path = path or KG_PATH
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return build_knowledge_graph()


def _is_leg_athlete_question(query: str) -> bool:
    q = query
    if re.search(r"地点分担|2\.855|朝練|銀マット|タイム目安|43分|区間配分|補強メニュー", q):
        return False
    if re.search(r"距離は|何キロ", q) and not re.search(r"誰|選手|ランナー|走った", q):
        return False
    if re.search(r"(?:何|\d+)区を?走った|は何区(?:を|？|\?|!|！|$)|何区？", q):
        return True
    if re.search(r"\d区は誰|\d区の選手|\d区ランナー|何区は誰|区間選手", q):
        return True
    return bool(re.search(r"\d区", q) and re.search(r"誰|選手|ランナー|走った|区間タイム|区間順", q))


def _is_leg_time_question(query: str) -> bool:
    return bool(re.search(r"\d区", query) and re.search(r"何分|区間タイム|タイム", query))


def _score_node(node: dict[str, Any], q_tokens: list[str], query: str) -> float:
    label = (node.get("label") or "").lower()
    node_type = node.get("type", "")
    hint = (node.get("hint") or "").lower()
    topics = " ".join(node.get("topics") or []).lower()
    refs = " ".join(node.get("refs") or []).lower()
    blob = " ".join([node.get("id", ""), label, hint, topics, refs]).lower()
    q = query.lower().strip()
    score = 0.0
    # Exact / substring label hit (critical for athlete names)
    if label and label in q:
        score += 8.0
    for tok in q_tokens:
        if not tok:
            continue
        if tok == label:
            score += 6.0
            continue
        if tok and tok in label:
            score += 3.0
            continue
        # For Athlete nodes, avoid scoring generic hint/topic words
        if node_type == "Athlete":
            continue
        if tok in blob:
            score += 2.0 if len(tok) >= 2 else 0.5
    if node_type != "Athlete" and q and q in blob:
        score += 5.0
    track_record_intent = (
        any(term in q for term in ("pb", "ベスト", "自己ベスト", "最速", "記録", "タイム"))
        and any(distance in q for distance in ("800m", "1500m", "3000m", "800", "1500", "3000"))
    )
    if track_record_intent:
        if "arato-tamana-teams/" in blob and "所属別トラック全記録" in blob:
            score += 24.0
        if "aragyoku-teams/" in blob:
            score -= 12.0
        if "pb_school_ranking" in blob and not any(term in q for term in ("平均", "ランキング", "上位")):
            score -= 6.0
    injury_intent = any(term in q for term in ("怪我", "けが", "ケガ", "故障", "痛み", "障害"))
    if injury_intent:
        if "怪我について/rows.json" in blob:
            score += 32.0
        elif "怪我について" in label:
            score += 10.0
        if node_type == "QueryHint" and not any(term in blob for term in ("怪我について", "rri_healing", "injury")):
            score -= 8.0
    # Meet disambiguation (keep in sync with backend/src/kg/query.ts)
    if "ジュニア" in q:
        if "ジュニア" in blob:
            score += 22.0
        if any(x in blob for x in ("aragyoku", "荒玉", "ekiden-ocr", "winners-by-year")) and "ジュニア" not in blob:
            score -= 18.0
    if any(x in q for x in ("荒玉", "aragyoku", "中体連")) and any(
        x in blob for x in ("荒玉", "aragyoku", "中体連", "ekiden-ocr", "winners")
    ):
        score += 10.0
    kanaguri_project_q = "金栗project" in q or "金栗プロジェクト" in q
    nagomi_q = "なごみ" in q or "金栗四三" in q
    kanaguri_ekiden_q = "金栗駅伝" in q and "なごみ" not in q and "金栗四三" not in q
    if nagomi_q:
        if "なごみ" in blob:
            score += 22.0
        if any(x in blob for x in ("金栗駅伝", "金栗記念")) and "なごみ" not in blob:
            score -= 20.0
        if any(x in blob for x in ("aragyoku", "荒玉", "ekiden-ocr", "winners-by-year")) and "なごみ" not in blob:
            score -= 18.0
    if kanaguri_ekiden_q:
        if "金栗駅伝" in blob:
            score += 22.0
        if "なごみ" in blob and "金栗駅伝" not in blob:
            score -= 16.0
    if kanaguri_project_q and any(x in blob for x in ("金栗project", "金栗プロジェクト", "arato-tamana-teams")):
        score += 18.0
    if any(x in q for x in ("玉名付属", "玉名附属", "付属中")) and any(
        x in blob for x in ("玉高附属", "玉名付属", "玉名附属")
    ):
        score += 12.0
    if (("上位" in q and "平均" in q) or "学校別" in q or "所属別" in q) and any(
        x in q for x in ("800", "1500", "ランキング", "平均")
    ):
        if any(x in blob for x in ("pb_school_ranking", "学校別", "上位3人", "上位4人")):
            score += 18.0
        if any(x in blob for x in ("sb/", "中学生SB", "SBデータベース")) and "pb_school" not in blob:
            score -= 8.0
    if any(x in q for x in ("優勝との差", "優勝差", "優勝から")):
        if "focus_teams" in blob or "優勝との差" in blob:
            score += 16.0
        if ("meet_records" in blob or "大会記録" in blob) and "focus" not in blob:
            score -= 10.0
    if any(x in q for x in ("全記録", "記録一覧", "所属選手")) and (
        "arato-tamana-teams" in blob or "athletes/" in blob
    ):
        score += 14.0
    if "トラック" in q and any(x in q for x in ("1周", "一周", "周長", "何メートル", "何ｍ")):
        if any(x in blob for x in ("kpace", "data-model", "560")):
            score += 14.0
    if _is_leg_athlete_question(query):
        if nagomi_q:
            if "なごみ" in blob:
                score += 18.0
            if "オーダー" in blob or "区間" in blob:
                score += 8.0
            if "aragyoku-teams" in blob or "focus_teams" in blob:
                score -= 16.0
    if _is_leg_time_question(query) and re.search(r"20\d{2}", query):
        if "aragyoku-teams/" in blob and label and label in q:
            score += 30.0
        if "focus_teams" in blob:
            score -= 14.0
        if "aragyoku-teams/index.md" in blob:
            score -= 22.0
        if node_type == "QueryHint":
            score -= 30.0
        elif "ジュニア" not in q:
            if "aragyoku-teams" in blob or "focus_teams" in blob:
                score += 18.0
            if any(x in blob for x in ("スタートリスト", "タイムテーブル", "通信陸上")) and not (
                "aragyoku-teams" in blob or "focus_teams" in blob
            ):
                score -= 16.0
    if score <= 0:
        return 0.0
    boost = {
        "QueryHint": 1.5,
        "Topic": 1.2,
        "Source": 1.0,
        "Athlete": 1.4,
        "Template": 1.1,
        "Entity": 1.0,
        "Year": 1.0,
        "MediaAsset": 1.35,
    }
    score *= boost.get(node_type, 1.0)
    return score


def _adjacency(edges: list[dict[str, str]]) -> dict[str, list[tuple[str, str]]]:
    """Directed adjacency: from -> [(to, rel), ...]."""
    adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for e in edges:
        adj[e["from"]].append((e["to"], e["rel"]))
    return adj


def _read_neighborhood(
    path: Path,
    query: str,
    *,
    date_range: tuple[date, date] | None = None,
    max_chars: int = 2400,
) -> str:
    if not path.exists() or not path.is_file():
        return ""
    # Skip large binaries
    if path.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return f"[binary/image skipped: {_rel_safe(path)}]"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if not text.strip():
        return ""
    tokens = [t for t in _tokenize(query) if len(t) >= 2]
    if not tokens:
        return text[:max_chars]
    lines = text.splitlines()
    menu_intent = any(term in query.lower() for term in ("何をした", "メニュー", "練習内容", "実施内容"))
    if path.suffix.lower() == ".md" and menu_intent:
        for heading_idx, line in enumerate(lines):
            if not re.match(r"^#{1,6}\s*(?:メニュー|練習内容|実施内容)", line.strip()):
                continue
            heading_level = len(line) - len(line.lstrip("#"))
            end = heading_idx + 1
            while end < len(lines):
                next_heading = re.match(r"^(#{1,6})\s", lines[end].strip())
                if next_heading and len(next_heading.group(1)) <= heading_level:
                    break
                end += 1
            return "\n".join(lines[heading_idx:end])[:max_chars]
    requested_date = re.search(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)", query)
    hit_idxs = []
    date_anchored = False
    if date_range:
        start_date, end_date = date_range
        for index, line in enumerate(lines):
            match = re.search(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)", line)
            if match and start_date <= date.fromisoformat(match.group(1)) <= end_date:
                hit_idxs.append(index)
        date_anchored = bool(hit_idxs)
    elif requested_date:
        hit_idxs = [i for i, line in enumerate(lines) if requested_date.group(0) in line]
        if hit_idxs:
            calendar_list_intent = any(term in query.lower() for term in ("予定", "一覧", "カレンダー", "日程", "学校行事", "schedule"))
            if not calendar_list_intent:
                # A date may occur in several events on the same day. Prefer the
                # date row whose surrounding event text best matches the question.
                compact_query = re.sub(r"20\d{2}-\d{2}-\d{2}|今日|きょう|の|は|？|\s", "", query).lower()

                def date_window_score(index: int) -> int:
                    start = index
                    while start > 0 and not lines[start].startswith("- title:"):
                        start -= 1
                    end = index + 1
                    while end < len(lines) and not lines[end].startswith("- title:"):
                        end += 1
                    window = "\n".join(lines[start:end]).lower()
                    token_score = sum(token in window for token in tokens)
                    phrase_score = 100 if compact_query and compact_query in re.sub(r"\s", "", window) else 0
                    return token_score + phrase_score

                hit_idxs = [max(hit_idxs, key=date_window_score)]
            date_anchored = True
    if not hit_idxs:
        hit_idxs = [
            i
            for i, line in enumerate(lines)
            if any(tok in line.lower() for tok in tokens)
        ]
    if not hit_idxs:
        return text[:max_chars]
    windows: list[str] = []
    used: set[int] = set()
    if date_range and hit_idxs:
        max_chars = max(max_chars, 8000)
        blocks: list[tuple[int, int]] = []
        for idx in hit_idxs:
            start = idx
            while start > 0 and not lines[start].startswith("- title:"):
                start -= 1
            end = idx + 1
            while end < len(lines) and not lines[end].startswith("- title:"):
                end += 1
            blocks.append((start, end))
        for start, end in blocks:
            windows.append("\n".join(lines[start:end]))
        return "\n---\n".join(windows)[:max_chars]
    for idx in hit_idxs[:8]:
        start = max(0, idx - (8 if date_anchored else 4))
        end = min(len(lines), idx + (16 if date_anchored else 5))
        for j in range(start, end):
            if j not in used:
                used.add(j)
        chunk = "\n".join(lines[start:end])
        windows.append(chunk)
    joined = "\n---\n".join(windows)
    return joined[:max_chars]


def _rel_safe(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def query_knowledge_graph(
    question: str,
    *,
    graph: dict[str, Any] | None = None,
    top_k: int = 8,
    expand_hops: int = 1,
    context_files: int = 6,
    include_context: bool = True,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    graph = graph or load_graph()
    nodes = {n["id"]: n for n in graph.get("nodes") or []}
    edges = list(graph.get("edges") or [])
    adj = _adjacency(edges)
    normalized_question = unicodedata.normalize("NFKC", question)
    search_question = _resolve_relative_dates(normalized_question, as_of_date=as_of_date)
    q_tokens = _tokenize(search_question)

    scored = [
        (nid, _score_node(node, q_tokens, search_question))
        for nid, node in nodes.items()
    ]
    scored = [(nid, s) for nid, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    seeds = scored[:top_k]

    resolved_date = re.search(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)", search_question)
    week_range = _resolve_week_range(normalized_question, as_of_date=as_of_date)
    month_range = _resolve_month_range(normalized_question, as_of_date=as_of_date)
    fiscal_range = _resolve_fiscal_year_range(normalized_question)
    calendar_intent = any(term in normalized_question.lower() for term in ("予定", "一覧", "カレンダー", "日程", "学校行事", "schedule"))
    practice_intent = any(
        term in normalized_question.lower()
        for term in ("練習", "メニュー", "practice", "jog", "interval", "走る")
    )
    calendar_year_range = (
        _resolve_calendar_year_range(normalized_question, as_of_date=as_of_date)
        if calendar_intent or practice_intent
        else None
    )
    period_range = week_range or month_range or fiscal_range or calendar_year_range
    period_query_resolved = bool(period_range and not resolved_date and (calendar_intent or practice_intent))
    if period_query_resolved:
        start, end = period_range
        seeds = []
        if calendar_intent:
            for year in range(start.year, end.year + 1):
                source_id = f"source:input/events.{year}.yaml"
                if source_id in nodes:
                    seeds.append((source_id, 1.0))
        else:
            matching_week = []
            for nid, score in scored:
                match = re.match(r"entity:practice:(\d{4}-\d{2}-\d{2}):", nid)
                if not match:
                    continue
                event_date = date.fromisoformat(match.group(1))
                if start <= event_date <= end:
                    matching_week.append((event_date, nid, score))
            if matching_week:
                seeds = [(nid, score) for _, nid, score in sorted(matching_week)[:top_k]]
    elif resolved_date and any(term in question.lower() for term in ("予定", "一覧", "カレンダー", "日程", "学校行事", "schedule")):
        year = resolved_date.group(0)[:4]
        calendar_source_id = f"source:input/events.{year}.yaml"
        seeds = [(calendar_source_id, max((score for nid, score in scored if nid == calendar_source_id), default=1.0))]
    elif resolved_date:
        exact_practices = [
            (nid, score)
            for nid, score in scored
            if nid.startswith(f"entity:practice:{resolved_date.group(0)}:")
        ]
        if exact_practices:
            if practice_intent:
                # An exact dated practice is a better route than generic practice
                # hints or other sessions that share the same sport vocabulary.
                seeds = [max(exact_practices, key=lambda item: item[1])]
            else:
                # A calendar question about the same date must not be answered
                # with the practice session just because it has a date node.
                seeds = [
                    (nid, score)
                    for nid, score in seeds
                    if not nid.startswith("entity:practice:")
                ]
        elif practice_intent:
            date_refs = [
                (nid, score)
                for nid, score in scored
                if nodes[nid]["type"] == "Source"
                and resolved_date.group(0) in " ".join(nodes[nid].get("refs") or [])
                and any(term in " ".join([nodes[nid].get("label", ""), nodes[nid].get("hint", "")]).lower()
                        for term in ("練習", "practice", "training"))
            ]
            seeds = sorted(date_refs, key=lambda item: item[1], reverse=True)[:top_k]
            if not seeds:
                period_query_resolved = True

    # If a specific entity matched strongly, drop broad Topic/QueryHint seeds that flood refs
    if any(nodes[nid]["type"] in {"Athlete", "Template", "Year"} and s >= 8 for nid, s in seeds):
        seeds = [
            (nid, s)
            for nid, s in seeds
            if nodes[nid]["type"] not in {"Topic", "QueryHint"} or s >= 20
        ] or seeds[:3]

    # If nothing matched, fall back to Topic nodes by crude keyword map
    if not seeds and not period_query_resolved:
        fallback = []
        mapping = [
            (["練習", "メニュー", "jog", "interval", "欠席"], "topic:practice"),
            (["記録", "タイム", "選手", "PB"], "topic:athlete_records"),
            (["カレンダー", "予定", "祝日", "inbox"], "topic:calendar"),
            (["norwegian", "gz", "閾値", "vdot", "ペース"], "topic:norwegian"),
            (["ai", "生成", "プロンプト"], "topic:ai"),
            (["ケガ", "障害", "rri", "怪我"], "topic:injury"),
        ]
        q = question.lower()
        for keys, tid in mapping:
            if any(k.lower() in q for k in keys) and tid in nodes:
                fallback.append((tid, 1.0))
        seeds = fallback[:top_k] or [("topic:meta", 1.0)] if "topic:meta" in nodes else scored[:top_k]

    selected: dict[str, float] = {nid: score for nid, score in seeds}
    frontier = list(selected.keys())
    route_rels = {"search_here", "documented_in", "mentioned_in", "see_also"}
    exact_calendar_query = bool(calendar_intent and (resolved_date or period_query_resolved))
    for _ in range(0 if exact_calendar_query else max(0, expand_hops)):
        nxt: list[str] = []
        for nid in frontier:
            for neighbor, rel in adj.get(nid, []):
                if rel not in route_rels:
                    continue
                boost = 0.85 if rel in {"search_here", "mentioned_in", "documented_in"} else 0.55
                new_score = selected[nid] * boost
                if neighbor not in selected or new_score > selected[neighbor]:
                    selected[neighbor] = new_score
                    nxt.append(neighbor)
        frontier = nxt

    ordered_ids = sorted(selected.keys(), key=lambda i: selected[i], reverse=True)
    hit_nodes = [nodes[i] for i in ordered_ids if i in nodes]

    refs: list[str] = []
    seen_refs: set[str] = set()
    for node in hit_nodes:
        for ref in node.get("refs") or []:
            if ref not in seen_refs:
                seen_refs.add(ref)
                refs.append(ref)

    contexts: list[dict[str, str]] = []
    if include_context:
        for ref in refs[:context_files]:
            path = ROOT / ref
            snippet = _read_neighborhood(
                path,
                search_question,
                date_range=period_range if calendar_intent and period_query_resolved else None,
            )
            if snippet:
                contexts.append({"path": ref, "snippet": snippet})

    return {
        "question": question,
        "matched_nodes": [
            {
                "id": n["id"],
                "type": n["type"],
                "label": n["label"],
                "score": round(selected.get(n["id"], 0), 3),
                "hint": n.get("hint", ""),
                "refs": n.get("refs") or [],
            }
            for n in hit_nodes[: max(top_k * 3, 12)]
        ],
        "refs": refs,
        "contexts": contexts,
    }
