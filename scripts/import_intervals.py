#!/usr/bin/env python3
"""Intervals.icu のアクティビティをカレンダー YAML に取り込む。

Strava 経由で同期されたアクティビティは Intervals.icu API から詳細を取得できない
（Strava TOS 制限）ため、可能なら Strava API で詳細を補完する。
Strava API が使えない場合は開始時刻など最小限の情報で登録する。

例:
  python3 scripts/import_intervals.py import --date 2026-08-14 --period morning
  python3 scripts/generate_calendar.py --year 2026
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.import_strava import (  # noqa: E402
    LiteralStr,
    activity_to_event,
    env_or_none,
    import_activities,
    item_strava_id,
    maybe_literal,
    merge_strava_events,
    require_client_credentials,
    StravaClient,
)

API_BASE = "https://intervals.icu/api/v1"
INTERVALS_ACTIVITY_URL = "https://intervals.icu/activity/{activity_id}"
DEFAULT_DURATION_MINUTES = 45
MORNING_END_HOUR = 12


def intervals_credentials() -> tuple[str, str]:
    api_key = env_or_none("INTERVALS_ICU_API_KEY")
    athlete_id = env_or_none("INTERVALS_ICU_ATHLETE_ID")
    if not api_key or not athlete_id:
        raise SystemExit(
            "INTERVALS_ICU_API_KEY と INTERVALS_ICU_ATHLETE_ID を環境変数に設定してください。"
        )
    return api_key, athlete_id


def intervals_http(
    method: str,
    path: str,
    *,
    api_key: str,
    query: dict[str, str] | None = None,
) -> Any:
    url = f"{API_BASE}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    token = base64.b64encode(f"API_KEY:{api_key}".encode()).decode()
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {token}",
            "User-Agent": "INBOX-import/1.0",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail}") from exc


def list_intervals_activities(
    athlete_id: str,
    *,
    api_key: str,
    oldest: date,
    newest: date,
) -> list[dict[str, Any]]:
    payload = intervals_http(
        "GET",
        f"athlete/{athlete_id}/activities",
        api_key=api_key,
        query={
            "oldest": oldest.isoformat(),
            "newest": newest.isoformat(),
        },
    )
    if not isinstance(payload, list):
        raise RuntimeError("Intervals.icu activities レスポンスが不正です。")
    return payload


def parse_local_start(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1]
    return datetime.fromisoformat(text)


def in_period(start: datetime, period: str) -> bool:
    if period == "all":
        return True
    if period == "morning":
        return start.hour < MORNING_END_HOUR
    if period == "afternoon":
        return MORNING_END_HOUR <= start.hour < 18
    if period == "evening":
        return start.hour >= 18
    raise ValueError(f"未知の period: {period}")


def try_fetch_strava_activity(
    client: StravaClient | None,
    activity_id: str,
) -> dict[str, Any] | None:
    if client is None:
        return None
    try:
        token = client.ensure_access_token()
    except RuntimeError:
        return None
    url = f"https://www.strava.com/api/v3/activities/{activity_id}"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else None
    except urllib.error.HTTPError:
        return None


def build_fallback_description(
    activities: list[dict[str, Any]],
    *,
    strava_unavailable: bool,
) -> str:
    lines = ["Intervals.icu から自動取り込み（Strava 同期アクティビティ）"]
    for item in activities:
        start = parse_local_start(str(item["start_date_local"]))
        lines.append(f"- 記録開始: {start.strftime('%H:%M')}")
        lines.append(f"- Activity ID: {item.get('id')}")
    if strava_unavailable:
        lines.append("")
        lines.append(
            "詳細（距離・ペース等）は Strava API 制限のため未取得。"
            " https://www.strava.com/settings/api でアプリを再有効化し、"
            " STRAVA_REFRESH_TOKEN を更新すると自動補完されます。"
        )
    return "\n".join(lines)


def intervals_group_to_event(
    activities: list[dict[str, Any]],
    *,
    strava_activity: dict[str, Any] | None,
    strava_unavailable: bool,
    title_mode: str,
) -> dict[str, Any]:
    if strava_activity:
        event = activity_to_event(strava_activity, title_mode=title_mode)
        tags = list(event.get("tags") or [])
        if "intervals" not in tags:
            tags.append("intervals")
        event["tags"] = tags
        return event

    sorted_items = sorted(
        activities,
        key=lambda item: parse_local_start(str(item["start_date_local"])),
    )
    first = sorted_items[0]
    last = sorted_items[-1]
    start_dt = parse_local_start(str(first["start_date_local"]))
    last_start = parse_local_start(str(last["start_date_local"]))
    end_dt = last_start + timedelta(minutes=DEFAULT_DURATION_MINUTES)

    activity_ids = [str(item["id"]) for item in sorted_items]
    urls = [INTERVALS_ACTIVITY_URL.format(activity_id=aid) for aid in activity_ids]
    urls.extend(f"https://www.strava.com/activities/{aid}" for aid in activity_ids)

    return {
        "title": "自分の練習",
        "date": start_dt.date().isoformat(),
        "all_day": False,
        "category": "予定",
        "status": "done",
        "start_time": start_dt.strftime("%H:%M"),
        "end_time": end_dt.strftime("%H:%M"),
        "tags": ["ランニング", "自分の練習", "intervals"],
        "urls": urls,
        "description": maybe_literal(
            build_fallback_description(sorted_items, strava_unavailable=strava_unavailable)
        ),
    }


def item_intervals_id(item: dict[str, Any]) -> str | None:
    urls = item.get("urls") or item.get("url") or []
    items = urls if isinstance(urls, list) else [urls]
    for raw in items:
        text = str(raw).strip()
        prefix = "https://intervals.icu/activity/"
        if text.startswith(prefix):
            return text.removeprefix(prefix).split("?")[0].strip("/")
    return None


def merge_intervals_events(
    existing: list[dict],
    incoming: list[dict],
    *,
    update_existing: bool,
) -> tuple[list[dict], int, int]:
    by_intervals: dict[str, int] = {}
    by_strava: dict[str, int] = {}
    for idx, item in enumerate(existing):
        iid = item_intervals_id(item)
        if iid:
            by_intervals[iid] = idx
        sid = item_strava_id(item)
        if sid:
            by_strava[sid] = idx

    merged = list(existing)
    added = 0
    updated = 0
    for item in incoming:
        iid = item_intervals_id(item)
        sid = item_strava_id(item)
        target_idx = None
        if iid and iid in by_intervals:
            target_idx = by_intervals[iid]
        elif sid and sid in by_strava:
            target_idx = by_strava[sid]

        if target_idx is not None:
            if update_existing:
                merged[target_idx] = item
                updated += 1
            continue

        if iid:
            by_intervals[iid] = len(merged)
        if sid:
            by_strava[sid] = len(merged)
        merged.append(item)
        added += 1
    return merged, added, updated


def import_intervals_events(
    events: list[dict[str, Any]],
    out_dir: Path,
    *,
    merge: bool,
    update_existing: bool,
    dry_run: bool,
) -> dict[int, tuple[int, int, int]]:
    from collections import defaultdict

    from scripts.import_strava import load_existing_events, write_year_yaml

    incoming: dict[int, list[dict]] = defaultdict(list)
    for event in events:
        year = int(str(event["date"])[:4])
        incoming[year].append(event)

    results: dict[int, tuple[int, int, int]] = {}
    years = set(incoming)
    if merge:
        for path in out_dir.glob("events.*.yaml"):
            suffix = path.name.removeprefix("events.").removesuffix(".yaml")
            if suffix.isdigit():
                years.add(int(suffix))

    for year in sorted(years):
        path = out_dir / f"events.{year}.yaml"
        existing = load_existing_events(path) if merge and path.exists() else []
        year_incoming = incoming.get(year, [])
        if not year_incoming and not existing:
            continue
        merged, added, updated = merge_intervals_events(
            existing,
            year_incoming,
            update_existing=update_existing,
        )
        if not dry_run and (added or updated or (not merge and year_incoming)):
            write_year_yaml(path, year, merged)
        results[year] = (len(merged), added, updated)
    return results


def group_morning_activities(
    activities: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """同日・近接時刻のアクティビティを1セッションとして束ねる。"""
    if not activities:
        return []
    sorted_items = sorted(
        activities,
        key=lambda item: parse_local_start(str(item["start_date_local"])),
    )
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [sorted_items[0]]
    for item in sorted_items[1:]:
        prev_start = parse_local_start(str(current[-1]["start_date_local"]))
        this_start = parse_local_start(str(item["start_date_local"]))
        if this_start - prev_start <= timedelta(minutes=90):
            current.append(item)
        else:
            groups.append(current)
            current = [item]
    groups.append(current)
    return groups


def cmd_import(args: argparse.Namespace) -> int:
    api_key, athlete_id = intervals_credentials()

    target = args.date
    oldest = args.oldest or target
    newest = args.newest or target

    raw = list_intervals_activities(
        athlete_id,
        api_key=api_key,
        oldest=oldest,
        newest=newest,
    )
    filtered = [
        item
        for item in raw
        if item.get("start_date_local")
        and in_period(parse_local_start(str(item["start_date_local"])), args.period)
    ]

    strava_client: StravaClient | None = None
    strava_unavailable = False
    try:
        client_id, client_secret = require_client_credentials()
        strava_client = StravaClient(
            client_id=client_id,
            client_secret=client_secret,
            token_path=args.token_file,
        )
        strava_client.ensure_access_token()
    except (SystemExit, RuntimeError):
        strava_client = None
        strava_unavailable = True

    groups = group_morning_activities(filtered) if args.period == "morning" else [[item] for item in filtered]
    events: list[dict[str, Any]] = []
    for group in groups:
        strava_activity = None
        for item in group:
            strava_activity = try_fetch_strava_activity(strava_client, str(item["id"]))
            if strava_activity:
                break
        events.append(
            intervals_group_to_event(
                group,
                strava_activity=strava_activity,
                strava_unavailable=strava_unavailable,
                title_mode=args.title_mode,
            )
        )

    results = import_intervals_events(
        events,
        args.out_dir,
        merge=args.merge,
        update_existing=args.update,
        dry_run=args.dry_run,
    )

    added_total = sum(a for _, a, _ in results.values())
    updated_total = sum(u for _, _, u in results.values())
    prefix = "[dry-run] " if args.dry_run else ""
    print(
        f"{prefix}Intervals.icu 取り込み: 対象 {len(filtered)} 件 / "
        f"イベント {len(events)} 件 / 新規 {added_total} / 更新 {updated_total}"
    )
    if strava_unavailable:
        print("注意: Strava API が利用できないため、最小限の情報で登録しました。")
    for year, (total, added, updated) in results.items():
        if added or updated:
            print(
                f"  {year}: 合計 {total} 件（+{added} / ~{updated}）"
                f" -> {args.out_dir / f'events.{year}.yaml'}"
            )
    if not args.dry_run and added_total + updated_total > 0:
        years = sorted(year for year, (_, added, updated) in results.items() if added or updated)
        if years:
            print("カレンダー再生成:")
            for year in years:
                print(f"  python3 scripts/generate_calendar.py --year {year}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Intervals.icu の練習を events YAML に取り込みます。"
    )
    parser.add_argument(
        "--token-file",
        type=Path,
        default=ROOT / ".strava_tokens.json",
        help="Strava トークン保存先",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", help="アクティビティを YAML に取り込む")
    imp.add_argument("--date", type=date.fromisoformat, help="対象日 (YYYY-MM-DD)")
    imp.add_argument("--oldest", type=date.fromisoformat, help="開始日")
    imp.add_argument("--newest", type=date.fromisoformat, help="終了日")
    imp.add_argument(
        "--period",
        choices=("all", "morning", "afternoon", "evening"),
        default="all",
        help="時間帯フィルタ（morning=12時前）",
    )
    imp.add_argument(
        "--title-mode",
        choices=("personal", "strava", "sport"),
        default="personal",
    )
    imp.add_argument("--out-dir", type=Path, default=ROOT / "input")
    imp.add_argument("--merge", action=argparse.BooleanOptionalAction, default=True)
    imp.add_argument("--update", action=argparse.BooleanOptionalAction, default=True)
    imp.add_argument("--dry-run", action="store_true")
    imp.set_defaults(func=cmd_import)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "import" and not (args.date or (args.oldest and args.newest)):
        parser.error("--date または --oldest/--newest を指定してください。")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
