#!/usr/bin/env python3
"""Build backend/data/meet-result-urls.json from record CSVs and out/*/source.csv."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "backend" / "data" / "meet-result-urls.json"
RECORD_ROOT = ROOT / "input" / "idaten-corpus" / "drive-text" / "記録データベース"
OUT_ROOT = ROOT / "out"

JUNK_URL_SUBSTR = (
    "b652729b4a1eecb47ebc1e6e01321a6e.pdf",  # shared calendar placeholder PDF
)

# Prefer federation / timing-system hosts; drop news blogs from source.csv
OFFICIAL_HOST_HINTS = (
    "kumariku.org",
    "kumariku.com",
    "kcrk.jp",
    "meet7.org",
    "jaaf.or.jp",
    "rikuren.jp",
)

MEET_TITLE_HINTS = (
    "駅伝",
    "マラソン",
    "選手権",
    "記録会",
    "陸上",
    "通信",
    "ナイター",
    "金栗",
    "ジュニア",
    "なごみ",
    "チャレンジ",
    "混成",
    "オリンピック",
    "選抜",
    "中体連",
)

URL_RE = re.compile(r"https?://[^\s\"']+")


def _is_junk(url: str) -> bool:
    return any(j in url for j in JUNK_URL_SUBSTR)


def _is_official_result_url(url: str) -> bool:
    host = urlsplit(url).netloc.lower()
    return any(h in host for h in OFFICIAL_HOST_HINTS)


def _looks_like_meet_title(title: str) -> bool:
    t = (title or "").strip()
    if not t or len(t) > 80:
        return False
    if "「" in t or "」" in t or "？！" in t or "！！" in t:
        return False
    if t.startswith("【") and "】" in t:
        return False
    return any(h in t for h in MEET_TITLE_HINTS)


def _normalize_date(raw: str) -> str | None:
    s = (raw or "").strip().replace(".", "/").replace("-", "/")
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})$", s)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{y:04d}-{mo:02d}-{d:02d}"


def _year_from_date(date: str | None) -> int | None:
    if not date:
        return None
    try:
        return int(date[:4])
    except ValueError:
        return None


def _add_url(
    bucket: dict[str, dict[str, object]],
    *,
    title: str,
    url: str,
    date: str | None = None,
    year: int | None = None,
) -> None:
    title = (title or "").strip()
    url = (url or "").strip().strip('"')
    if not title or not url.startswith("http") or _is_junk(url):
        return
    key = title
    entry = bucket.get(key)
    if entry is None:
        entry = {
            "title": title,
            "date": date,
            "year": year or _year_from_date(date),
            "url_counts": Counter(),
        }
        bucket[key] = entry
    counts: Counter[str] = entry["url_counts"]  # type: ignore[assignment]
    counts[url] += 1
    if date and not entry.get("date"):
        entry["date"] = date
        entry["year"] = year or _year_from_date(date)
    elif year and not entry.get("year"):
        entry["year"] = year


def _ingest_long_csv(path: Path, bucket: dict[str, dict[str, object]]) -> None:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "参考" not in reader.fieldnames:
            return
        for row in reader:
            title = (row.get("大会名") or "").strip()
            url = (row.get("参考") or "").strip()
            date = _normalize_date(row.get("日付") or "")
            _add_url(bucket, title=title, url=url, date=date)


def _ingest_wide_csv(path: Path, bucket: dict[str, dict[str, object]]) -> None:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return
        # pairs like 1500m大会 + 1500mURL (require explicit 大会 column)
        fields = list(reader.fieldnames)
        meet_url_pairs: list[tuple[str, str]] = []
        for col in fields:
            if not col.endswith("URL"):
                continue
            prefix = col[: -len("URL")]
            meet_col = f"{prefix}大会"
            if meet_col not in fields:
                continue
            meet_url_pairs.append((meet_col, col))
        if not meet_url_pairs:
            return
        for row in reader:
            for meet_col, url_col in meet_url_pairs:
                url = (row.get(url_col) or "").strip()
                title = (row.get(meet_col) or "").strip()
                if not title or not url:
                    continue
                date = None
                for dcol in (f"{meet_col.replace('大会', '日付')}", "日付"):
                    if dcol and dcol in row:
                        date = _normalize_date(row.get(dcol) or "")
                        if date:
                            break
                _add_url(bucket, title=title, url=url, date=date)


def _ingest_source_csv(path: Path, year: int, bucket: dict[str, dict[str, object]]) -> None:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("title") or "").strip()
            if not _looks_like_meet_title(title):
                continue
            raw = (row.get("urls") or "").strip()
            if not raw:
                continue
            date = (row.get("date") or "").strip() or None
            for part in re.split(r"\s*\|\s*", raw):
                url = (part or "").strip()
                if not _is_official_result_url(url):
                    continue
                _add_url(bucket, title=title, url=url, date=date, year=year)


def build_entries() -> list[dict[str, object]]:
    bucket: dict[str, dict[str, object]] = {}

    if RECORD_ROOT.is_dir():
        for csv_path in sorted(RECORD_ROOT.rglob("*.csv")):
            # skip meta-only copies
            try:
                with csv_path.open(encoding="utf-8-sig", newline="") as f:
                    header = next(csv.reader(f), [])
            except OSError:
                continue
            if "参考" in header and "大会名" in header:
                _ingest_long_csv(csv_path, bucket)
            elif any(c.endswith("URL") for c in header):
                _ingest_wide_csv(csv_path, bucket)

    for year_dir in sorted(OUT_ROOT.glob("20*")):
        if not year_dir.is_dir():
            continue
        try:
            year = int(year_dir.name)
        except ValueError:
            continue
        source = year_dir / "source.csv"
        if source.exists():
            _ingest_source_csv(source, year, bucket)

    meets: list[dict[str, object]] = []
    for entry in bucket.values():
        counts: Counter[str] = entry["url_counts"]  # type: ignore[assignment]
        # most frequent first, then stable by URL
        urls = [u for u, _ in counts.most_common()]
        # Prefer distinct path prefixes (drop near-duplicate heat pages after 5)
        selected: list[str] = []
        seen_prefix: set[str] = set()
        for u in urls:
            path = urlsplit(u).path.rsplit("/", 1)[0]
            key = f"{urlsplit(u).netloc}{path}"
            if key in seen_prefix and len(selected) >= 3:
                continue
            seen_prefix.add(key)
            selected.append(u)
            if len(selected) >= 5:
                break
        meets.append(
            {
                "title": entry["title"],
                "date": entry.get("date"),
                "year": entry.get("year"),
                "urls": selected,
            }
        )

    meets.sort(key=lambda m: (m.get("year") or 0, m.get("date") or "", str(m["title"])))
    return meets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEST)
    args = parser.parse_args()

    meets = build_entries()
    payload = {
        "version": 1,
        "generated_from": [
            "input/idaten-corpus/drive-text/記録データベース/**/*.csv",
            "out/*/source.csv",
        ],
        "meets": meets,
    }
    args.dest.parent.mkdir(parents=True, exist_ok=True)
    args.dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.dest.relative_to(ROOT)} ({len(meets)} meets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
