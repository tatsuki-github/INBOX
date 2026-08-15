#!/usr/bin/env python3
"""Strava API から自分のアクティビティを取得し、input/events.YYYY.yaml に取り込む。

認証:
  1. https://www.strava.com/settings/api でアプリを作成
  2. 環境変数 STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET を設定
  3. python3 scripts/import_strava.py auth で認可URLを表示し、code を交換
  4. 以降は .strava_tokens.json（gitignore）の refresh_token で自動更新

取り込み:
  python3 scripts/import_strava.py import --after 2026-01-01
  python3 scripts/generate_calendar.py --year 2026
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TOKEN_PATH = ROOT / ".strava_tokens.json"
API_BASE = "https://www.strava.com/api/v3"
AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
DEFAULT_REDIRECT_URI = "http://localhost/exchange_token"
DEFAULT_SCOPE = "activity:read_all,read"
STRAVA_URL_PREFIX = "https://www.strava.com/activities/"

SPORT_TAG_JA = {
    "Run": "ラン",
    "TrailRun": "トレイルラン",
    "Walk": "ウォーク",
    "Hike": "ハイキング",
    "Ride": "バイク",
    "MountainBikeRide": "MTB",
    "GravelRide": "グラベル",
    "VirtualRide": "バーチャルバイク",
    "VirtualRun": "バーチャルラン",
    "Swim": "スイム",
    "Workout": "ワークアウト",
    "WeightTraining": "筋トレ",
    "Yoga": "ヨガ",
    "Rowing": "ローイング",
}


class LiteralStr(str):
    """複数行文字列を YAML の | で出すためのマーカー。"""


def literal_representer(dumper: yaml.Dumper, data: LiteralStr):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(LiteralStr, literal_representer)


def maybe_literal(text: str) -> str | LiteralStr:
    if "\n" in text:
        return LiteralStr(text if text.endswith("\n") else text + "\n")
    return text


def env_or_none(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def require_client_credentials() -> tuple[str, str]:
    client_id = env_or_none("STRAVA_CLIENT_ID")
    client_secret = env_or_none("STRAVA_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit(
            "STRAVA_CLIENT_ID と STRAVA_CLIENT_SECRET を環境変数に設定してください。"
            "\nhttps://www.strava.com/settings/api でアプリを作成できます。"
        )
    return client_id, client_secret


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> Any:
    data = None
    req_headers = dict(headers or {})
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail}") from exc


def load_token_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"トークンファイルの形式が不正です: {path}")
    return data


def save_token_store(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def build_authorize_url(
    client_id: str,
    *,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    scope: str = DEFAULT_SCOPE,
) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "approval_prompt": "force",
            "scope": scope,
        }
    )
    return f"{AUTH_URL}?{query}"


def exchange_authorization_code(
    client_id: str,
    client_secret: str,
    code: str,
) -> dict[str, Any]:
    return http_json(
        "POST",
        TOKEN_URL,
        form={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
    )


def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> dict[str, Any]:
    return http_json(
        "POST",
        TOKEN_URL,
        form={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )


def merge_token_response(store: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    updated = dict(store)
    for key in ("access_token", "refresh_token", "expires_at", "expires_in", "token_type"):
        if key in payload and payload[key] is not None:
            updated[key] = payload[key]
    athlete = payload.get("athlete")
    if isinstance(athlete, dict) and athlete.get("id") is not None:
        updated["athlete_id"] = athlete["id"]
    updated["updated_at"] = datetime.now(timezone.utc).isoformat()
    return updated


class StravaClient:
    """アクセストークンの自動更新付き Strava API クライアント。"""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        token_path: Path,
        http: Callable[..., Any] = http_json,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = token_path
        self.http = http
        self.store = load_token_store(token_path)

    def ensure_access_token(self, *, skew_seconds: int = 120) -> str:
        access = env_or_none("STRAVA_ACCESS_TOKEN")
        if access:
            return access

        refresh = env_or_none("STRAVA_REFRESH_TOKEN") or str(self.store.get("refresh_token") or "")
        access = str(self.store.get("access_token") or "")
        expires_at = int(self.store.get("expires_at") or 0)
        now = int(datetime.now(timezone.utc).timestamp())

        if access and expires_at and expires_at > now + skew_seconds:
            return access

        if not refresh:
            raise SystemExit(
                "有効な Strava トークンがありません。"
                "\n先に `python3 scripts/import_strava.py auth` を実行するか、"
                "STRAVA_REFRESH_TOKEN / STRAVA_ACCESS_TOKEN を設定してください。"
            )

        # 環境変数の refresh_token をストアに載せてから更新する
        if not self.store.get("refresh_token"):
            self.store["refresh_token"] = refresh

        payload = self.http(
            "POST",
            TOKEN_URL,
            form={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
        )
        if not isinstance(payload, dict):
            raise RuntimeError("トークン更新レスポンスが不正です。")
        old_refresh = refresh
        self.store = merge_token_response(self.store, payload)
        save_token_store(self.token_path, self.store)
        new_refresh = str(self.store.get("refresh_token") or "")
        if new_refresh and new_refresh != old_refresh:
            print(
                "注意: Strava が refresh_token を更新しました。"
                f"\n  新しい値を Secrets / 環境変数 STRAVA_REFRESH_TOKEN に反映してください。"
                f"\n  保存先: {self.token_path}",
                file=sys.stderr,
            )
        access = str(self.store.get("access_token") or "")
        if not access:
            raise RuntimeError("トークン更新レスポンスに access_token がありません。")
        return access

    def list_activities(
        self,
        *,
        after: datetime | None = None,
        before: datetime | None = None,
        per_page: int = 100,
        max_pages: int = 50,
    ) -> list[dict[str, Any]]:
        token = self.ensure_access_token()
        activities: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            params: dict[str, str] = {
                "page": str(page),
                "per_page": str(per_page),
            }
            if after is not None:
                params["after"] = str(int(after.timestamp()))
            if before is not None:
                params["before"] = str(int(before.timestamp()))
            url = f"{API_BASE}/athlete/activities?{urllib.parse.urlencode(params)}"
            batch = self.http(
                "GET",
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            if not isinstance(batch, list):
                raise RuntimeError(f"予期しないレスポンス: {type(batch).__name__}")
            if not batch:
                break
            activities.extend(batch)
            if len(batch) < per_page:
                break
        return activities


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_strava_local_datetime(value: str) -> datetime:
    """start_date_local は末尾 Z 付きでもローカル時刻として扱う。"""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1]
    return datetime.fromisoformat(text)


def meters_to_km(meters: float | int | None) -> float | None:
    if meters is None:
        return None
    return round(float(meters) / 1000.0, 2)


def format_duration(seconds: int | float | None) -> str | None:
    if seconds is None:
        return None
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_pace_min_per_km(average_speed_mps: float | None) -> str | None:
    """平均ペース（分/km）。Run 系向け。"""
    if not average_speed_mps or average_speed_mps <= 0:
        return None
    sec_per_km = 1000.0 / float(average_speed_mps)
    minutes = int(sec_per_km // 60)
    seconds = int(round(sec_per_km % 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}'{seconds:02d}\"/km"


def activity_url(activity_id: int | str) -> str:
    return f"{STRAVA_URL_PREFIX}{activity_id}"


def extract_strava_id_from_urls(urls: object) -> str | None:
    if not urls:
        return None
    items = urls if isinstance(urls, list) else [urls]
    for item in items:
        text = str(item).strip()
        if text.startswith(STRAVA_URL_PREFIX):
            return text.removeprefix(STRAVA_URL_PREFIX).split("?")[0].strip("/")
    return None


def sport_tags(activity: dict[str, Any]) -> list[str]:
    sport = str(activity.get("sport_type") or activity.get("type") or "").strip()
    tags = ["自分の練習", "strava"]
    if sport:
        tags.append(SPORT_TAG_JA.get(sport, sport))
    return tags


def build_description(activity: dict[str, Any]) -> str:
    lines: list[str] = []
    name = str(activity.get("name") or "").strip()
    sport = str(activity.get("sport_type") or activity.get("type") or "").strip()
    if name:
        lines.append(f"種目名: {name}")
    if sport:
        lines.append(f"種別: {sport}")

    distance_km = meters_to_km(activity.get("distance"))
    if distance_km is not None:
        lines.append(f"距離: {distance_km:.2f}km")

    moving = format_duration(activity.get("moving_time"))
    if moving:
        lines.append(f"移動時間: {moving}")
    elapsed = format_duration(activity.get("elapsed_time"))
    if elapsed and elapsed != moving:
        lines.append(f"経過時間: {elapsed}")

    pace = format_pace_min_per_km(activity.get("average_speed"))
    sport_lower = sport.lower()
    if pace and ("run" in sport_lower or sport_lower in {"walk", "hike"}):
        lines.append(f"平均ペース: {pace}")

    elev = activity.get("total_elevation_gain")
    if elev is not None and float(elev) > 0:
        lines.append(f"獲得標高: {round(float(elev))}m")

    avg_hr = activity.get("average_heartrate")
    if avg_hr is not None:
        lines.append(f"平均心拍: {round(float(avg_hr))}bpm")

    description = str(activity.get("description") or "").strip()
    if description:
        lines.append("")
        lines.append(description)

    return "\n".join(lines).strip()


def activity_to_event(
    activity: dict[str, Any],
    *,
    title_mode: str = "personal",
) -> dict[str, Any]:
    activity_id = activity.get("id")
    if activity_id is None:
        raise ValueError("activity.id がありません")

    local_raw = activity.get("start_date_local") or activity.get("start_date")
    if not local_raw:
        raise ValueError(f"activity {activity_id}: start_date_local がありません")
    start_dt = parse_strava_local_datetime(str(local_raw))
    elapsed = int(activity.get("elapsed_time") or activity.get("moving_time") or 0)
    end_dt = start_dt + timedelta(seconds=max(elapsed, 0))

    sport = str(activity.get("sport_type") or activity.get("type") or "").strip()
    name = str(activity.get("name") or "").strip() or sport or "Strava"

    if title_mode == "strava":
        title = name
    elif title_mode == "sport":
        title = SPORT_TAG_JA.get(sport, sport or name)
    else:
        title = "自分の練習"

    event: dict[str, Any] = {
        "title": title,
        "date": start_dt.date().isoformat(),
        "all_day": False,
        "category": "予定",
        "status": "done",
        "start_time": start_dt.strftime("%H:%M"),
        "end_time": end_dt.strftime("%H:%M"),
        "tags": sport_tags(activity),
        "urls": [activity_url(activity_id)],
        "description": maybe_literal(build_description(activity)),
    }
    if end_dt.date() != start_dt.date():
        event["end_date"] = end_dt.date().isoformat()
    return event


def item_strava_id(item: dict[str, Any]) -> str | None:
    return extract_strava_id_from_urls(item.get("urls") or item.get("url"))


def load_existing_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return list(data.get("events") or [])


def write_year_yaml(path: Path, year: int, events: list[dict]) -> None:
    events_sorted = sorted(
        events,
        key=lambda e: (
            e.get("date") is None or e.get("date") == "",
            e.get("date") or "9999-99-99",
            e.get("start_time") or "",
            e.get("title") or "",
        ),
    )
    for event in events_sorted:
        desc = event.get("description")
        if isinstance(desc, str) and "\n" in desc and not isinstance(desc, LiteralStr):
            event["description"] = maybe_literal(desc)

    payload = {
        "year": year,
        "events": events_sorted,
    }
    header = (
        f"# カスタム予定・メモ（{year}年）\n"
        "# 祝日は scripts/generate_calendar.py が自動追加します。\n"
        f"# 件数: {len(events_sorted)}\n"
    )
    with path.open("w", encoding="utf-8") as f:
        f.write(header)
        yaml.dump(
            payload,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=1000,
        )


def filter_activities(
    activities: list[dict[str, Any]],
    *,
    sports: set[str] | None,
) -> list[dict[str, Any]]:
    if not sports:
        return activities
    normalized = {s.lower() for s in sports}
    out: list[dict[str, Any]] = []
    for activity in activities:
        sport = str(activity.get("sport_type") or activity.get("type") or "").lower()
        if sport in normalized:
            out.append(activity)
    return out


def merge_strava_events(
    existing: list[dict],
    incoming: list[dict],
    *,
    update_existing: bool,
) -> tuple[list[dict], int, int]:
    """戻り値: (merged, added, updated)"""
    by_id: dict[str, int] = {}
    for idx, item in enumerate(existing):
        sid = item_strava_id(item)
        if sid:
            by_id[sid] = idx

    merged = list(existing)
    added = 0
    updated = 0
    for item in incoming:
        sid = item_strava_id(item)
        if sid and sid in by_id:
            if update_existing:
                merged[by_id[sid]] = item
                updated += 1
            continue
        if sid:
            by_id[sid] = len(merged)
        merged.append(item)
        added += 1
    return merged, added, updated


def import_activities(
    activities: list[dict[str, Any]],
    out_dir: Path,
    *,
    merge: bool,
    update_existing: bool,
    title_mode: str,
    dry_run: bool,
) -> dict[int, tuple[int, int, int]]:
    """戻り値: year -> (total, added, updated)"""
    incoming: dict[int, list[dict]] = defaultdict(list)
    for activity in activities:
        event = activity_to_event(activity, title_mode=title_mode)
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
        merged, added, updated = merge_strava_events(
            existing,
            year_incoming,
            update_existing=update_existing,
        )
        if not dry_run and (added or updated or (not merge and year_incoming)):
            write_year_yaml(path, year, merged)
        results[year] = (len(merged), added, updated)
    return results


def cmd_auth(args: argparse.Namespace) -> int:
    client_id, client_secret = require_client_credentials()
    if not args.code:
        url = build_authorize_url(
            client_id,
            redirect_uri=args.redirect_uri,
            scope=args.scope,
        )
        print("次のURLをブラウザで開き、認可後のリダイレクトURLから code= をコピーしてください。")
        print()
        print(url)
        print()
        print("例:")
        print(
            f"  STRAVA_CLIENT_ID=... STRAVA_CLIENT_SECRET=... "
            f"python3 scripts/import_strava.py auth --code YOUR_CODE"
        )
        print()
        print(
            "※ Authorization Callback Domain に localhost を設定し、"
            f"redirect_uri は {args.redirect_uri} にしてください。"
        )
        return 0

    payload = exchange_authorization_code(client_id, client_secret, args.code)
    store = merge_token_response({}, payload)
    save_token_store(args.token_file, store)
    print(f"トークンを保存しました: {args.token_file}")
    if store.get("athlete_id"):
        print(f"athlete_id: {store['athlete_id']}")
    print("expires_at:", store.get("expires_at"))
    print("次に実行:")
    print("  python3 scripts/import_strava.py import --after 2026-01-01")
    return 0


def to_epoch_datetime(d: date, *, end_of_day: bool = False) -> datetime:
    if end_of_day:
        return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def cmd_import(args: argparse.Namespace) -> int:
    activities: list[dict[str, Any]]
    if args.from_json:
        with args.from_json.open(encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, list):
            raise SystemExit("--from-json はアクティビティ配列の JSON を指定してください。")
        activities = loaded
    else:
        client_id, client_secret = require_client_credentials()
        client = StravaClient(
            client_id=client_id,
            client_secret=client_secret,
            token_path=args.token_file,
        )
        after = to_epoch_datetime(args.after) if args.after else None
        before = to_epoch_datetime(args.before, end_of_day=True) if args.before else None
        activities = client.list_activities(after=after, before=before)

    sports = {s.strip() for s in (args.sport or []) if s.strip()} or None
    activities = filter_activities(activities, sports=sports)

    results = import_activities(
        activities,
        args.out_dir,
        merge=args.merge,
        update_existing=args.update,
        title_mode=args.title_mode,
        dry_run=args.dry_run,
    )

    added_total = sum(a for _, a, _ in results.values())
    updated_total = sum(u for _, _, u in results.values())
    touched_years = {
        int(str(a.get("start_date_local") or a.get("start_date") or "0000")[:4])
        for a in activities
        if a.get("start_date_local") or a.get("start_date")
    }
    prefix = "[dry-run] " if args.dry_run else ""
    print(
        f"{prefix}取り込み完了: 取得 {len(activities)} 件 / "
        f"新規 {added_total} 件 / 更新 {updated_total} 件"
        f"（merge={'on' if args.merge else 'off'}, title_mode={args.title_mode}）"
    )
    for year, (total, added, updated) in results.items():
        if added == 0 and updated == 0 and year not in touched_years:
            continue
        print(
            f"  {year}: 合計 {total} 件（+{added} / ~{updated}）"
            f" -> {args.out_dir / f'events.{year}.yaml'}"
        )

    if not args.dry_run and added_total + updated_total > 0:
        years = sorted(
            year for year, (_, added, updated) in results.items() if added or updated
        )
        if years:
            print("カレンダー再生成の例:")
            for year in years:
                print(f"  python3 scripts/generate_calendar.py --year {year}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Strava の練習（アクティビティ）を events YAML に取り込みます。"
    )
    parser.add_argument(
        "--token-file",
        type=Path,
        default=DEFAULT_TOKEN_PATH,
        help=f"トークン保存先（デフォルト: {DEFAULT_TOKEN_PATH.name}）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser("auth", help="OAuth 認可URL表示 / code 交換")
    auth.add_argument("--code", help="認可後に得た authorization code")
    auth.add_argument(
        "--redirect-uri",
        default=DEFAULT_REDIRECT_URI,
        help=f"認可リダイレクトURI（デフォルト: {DEFAULT_REDIRECT_URI}）",
    )
    auth.add_argument(
        "--scope",
        default=DEFAULT_SCOPE,
        help=f"要求スコープ（デフォルト: {DEFAULT_SCOPE}）",
    )
    auth.set_defaults(func=cmd_auth)

    imp = sub.add_parser("import", help="アクティビティを YAML に取り込む")
    imp.add_argument(
        "--after",
        type=parse_iso_date,
        help="この日以降のアクティビティ（YYYY-MM-DD, UTC 00:00）",
    )
    imp.add_argument(
        "--before",
        type=parse_iso_date,
        help="この日以前のアクティビティ（YYYY-MM-DD, UTC 23:59:59）",
    )
    imp.add_argument(
        "--sport",
        action="append",
        default=[],
        help="取り込む sport_type（複数指定可。例: --sport Run --sport Ride）",
    )
    imp.add_argument(
        "--title-mode",
        choices=("personal", "strava", "sport"),
        default="personal",
        help="件名: personal=自分の練習 / strava=Strava名 / sport=種別名",
    )
    imp.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "input",
        help="YAML出力先（デフォルト: input/）",
    )
    imp.add_argument(
        "--merge",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="既存 YAML に追記マージする（デフォルト: する）",
    )
    imp.add_argument(
        "--update",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="同一 Strava ID があれば内容を更新する（デフォルト: する）",
    )
    imp.add_argument(
        "--from-json",
        type=Path,
        help="APIの代わりに保存済みアクティビティJSON配列を使う（テスト/オフライン用）",
    )
    imp.add_argument(
        "--dry-run",
        action="store_true",
        help="書き込まず件数だけ表示する",
    )
    imp.set_defaults(func=cmd_import)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
