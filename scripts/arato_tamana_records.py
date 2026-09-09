"""Notion から荒尾・玉名地区の中学生記録を取得・フィルタ・グループ化する。"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "input" / "arato_tamana_report.yaml"

DISTANCE_ORDER = {"800m": 0, "1500m": 1, "3000m": 2, "3000mSC": 3}
GENDER_ORDER = {"男子": 0, "女子": 1}
SCHOOL_AFFILIATION_HINTS = ("中", "附")


@dataclass
class RecordRow:
    name: str
    affiliation: str
    grade: int | None
    gender: str
    distance: str
    time_text: str
    sb_text: str
    sb_adopted: bool
    date: str
    url: str
    record_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AffiliationSection:
    affiliation: str
    records: list[RecordRow] = field(default_factory=list)


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or DEFAULT_CONFIG
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _plain_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
    return str(value).strip()


def _extract_title(props: dict[str, Any]) -> str:
    title_prop = props.get("名前") or props.get("Name") or {}
    parts: list[str] = []
    for item in title_prop.get("title", []):
        text = item.get("plain_text") or item.get("text", {}).get("content", "")
        parts.append(text)
    return "".join(parts).strip()


def _extract_rich_text(props: dict[str, Any], key: str) -> str:
    prop = props.get(key) or {}
    if "rich_text" in prop:
        parts = [item.get("plain_text", "") for item in prop["rich_text"]]
        return "".join(parts).strip()
    if "url" in prop:
        return _plain_text(prop.get("url"))
    return _plain_text(prop.get("select", {}).get("name") if prop.get("select") else "")


def _extract_select(props: dict[str, Any], key: str) -> str:
    prop = props.get(key) or {}
    select = prop.get("select")
    if select:
        return _plain_text(select.get("name"))
    return ""


def _extract_number(props: dict[str, Any], key: str) -> float | None:
    prop = props.get(key) or {}
    value = prop.get("number")
    if value is None:
        return None
    return float(value)


def _extract_checkbox(props: dict[str, Any], key: str) -> bool:
    prop = props.get(key) or {}
    return bool(prop.get("checkbox"))


def notion_page_to_row(page: dict[str, Any]) -> RecordRow:
    props = page.get("properties", {})
    grade_num = _extract_number(props, "学年")
    return RecordRow(
        name=_extract_title(props),
        affiliation=_extract_rich_text(props, "所属"),
        grade=int(grade_num) if grade_num is not None else None,
        gender=_extract_select(props, "性別"),
        distance=_extract_select(props, "距離"),
        time_text=_extract_rich_text(props, "記録"),
        sb_text=_extract_rich_text(props, "SB"),
        sb_adopted=_extract_checkbox(props, "SB採用"),
        date=_extract_rich_text(props, "日付"),
        url=_extract_rich_text(props, "参考"),
        record_seconds=_extract_number(props, "記録秒"),
    )


def matches_arato_tamana(row: RecordRow, config: dict[str, Any]) -> bool:
    affiliation = row.affiliation or ""
    name = row.name or ""

    for keyword in config.get("exclude_name_keywords", []):
        if keyword in name and config.get("exclude_when_affiliation_contains", "") in affiliation:
            return False

    affiliation_hit = any(kw in affiliation for kw in config.get("affiliation_keywords", []))
    name_hit = any(n in name for n in config.get("extra_names", []))
    if not (affiliation_hit or name_hit):
        return False

    return True


def matches_prefecture(row: RecordRow, config: dict[str, Any], prefecture: str = "") -> bool:
    target = config.get("prefecture", "熊本県")
    include_empty = config.get("include_empty_prefecture", True)
    if not prefecture:
        return include_empty
    return prefecture == target


def row_from_cache_dict(data: dict[str, Any]) -> RecordRow:
    return RecordRow(
        name=data.get("name", ""),
        affiliation=data.get("affiliation", ""),
        grade=data.get("grade"),
        gender=data.get("gender", ""),
        distance=data.get("distance", ""),
        time_text=data.get("time_text", ""),
        sb_text=data.get("sb_text", ""),
        sb_adopted=bool(data.get("sb_adopted")),
        date=data.get("date", ""),
        url=data.get("url", ""),
        record_seconds=data.get("record_seconds"),
    )


def notion_page_to_row_with_prefecture(page: dict[str, Any]) -> tuple[RecordRow, str]:
    row = notion_page_to_row(page)
    props = page.get("properties", {})
    prefecture = _extract_rich_text(props, "都道府県")
    return row, prefecture


def filter_rows(
    rows: list[tuple[RecordRow, str]],
    config: dict[str, Any],
) -> list[RecordRow]:
    filtered: list[RecordRow] = []
    for row, prefecture in rows:
        if not matches_prefecture(row, config, prefecture):
            continue
        if not matches_arato_tamana(row, config):
            continue
        filtered.append(row)
    return filtered


def _parse_date_key(date_text: str) -> tuple[int, int, int]:
    text = date_text.strip()
    m = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return 9999, 12, 31


def sort_records(records: list[RecordRow]) -> list[RecordRow]:
    def key(row: RecordRow) -> tuple:
        y, mo, d = _parse_date_key(row.date)
        dist = DISTANCE_ORDER.get(row.distance, 99)
        seconds = row.record_seconds if row.record_seconds is not None else 99999.0
        gender = GENDER_ORDER.get(row.gender, 99)
        return (gender, row.name, y, mo, d, dist, seconds)

    return sorted(records, key=key)


def group_records_by_gender(records: list[RecordRow]) -> list[tuple[str, list[RecordRow]]]:
    """所属内で男子→女子の順にグループ化する。"""
    groups: dict[str, list[RecordRow]] = {}
    for row in records:
        gender = row.gender or "（性別不明）"
        groups.setdefault(gender, []).append(row)

    ordered_genders = sorted(groups.keys(), key=lambda g: GENDER_ORDER.get(g, 99))
    return [(gender, sort_records(groups[gender])) for gender in ordered_genders]


def _affiliation_sort_key(affiliation: str, count: int) -> tuple:
    is_school = any(h in affiliation for h in SCHOOL_AFFILIATION_HINTS)
    category = 0 if is_school else 1
    return (category, -count, affiliation)


def group_by_affiliation(records: list[RecordRow]) -> list[AffiliationSection]:
    buckets: dict[str, list[RecordRow]] = {}
    for row in records:
        key = row.affiliation or "（所属不明）"
        buckets.setdefault(key, []).append(row)

    sections: list[AffiliationSection] = []
    for affiliation, rows in buckets.items():
        sections.append(AffiliationSection(affiliation=affiliation, records=sort_records(rows)))

    sections.sort(key=lambda s: _affiliation_sort_key(s.affiliation, len(s.records)))
    return sections


def fetch_notion_pages(database_id: str, token: str) -> list[dict[str, Any]]:
    from notion_client import Client

    client = Client(auth=token)
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        kwargs: dict[str, Any] = {"database_id": database_id}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = client.databases.query(**kwargs)
        pages.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return pages


def fetch_filtered_records(config: dict[str, Any], token: str) -> list[RecordRow]:
    database_id = config["notion_database_id"]
    pages = fetch_notion_pages(database_id, token)
    raw_rows = [notion_page_to_row_with_prefecture(page) for page in pages]
    return filter_rows(raw_rows, config)


def save_cache(records: list[RecordRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [row.to_dict() for row in records]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cache(path: Path) -> list[RecordRow]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [row_from_cache_dict(item) for item in payload]


def shorten_url(url: str, max_len: int = 28) -> str:
    if not url:
        return ""
    text = url.replace("https://", "").replace("http://", "")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
