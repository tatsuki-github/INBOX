"""Open-Meteo から玉名市の天気を取得・整形するユーティリティ。"""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta
from typing import Any

TAMANA_LOCATION = "玉名市"
TAMANA_LAT = 32.9336
TAMANA_LON = 130.5589
TAMANA_TIMEZONE = "Asia/Tokyo"

HOURLY_PARAMS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
]

# Open-Meteo WMO weather code → 日本語（主要コード）
WMO_CONDITION_JA: dict[int, str] = {
    0: "快晴",
    1: "晴れ",
    2: "一部曇り",
    3: "曇り",
    45: "霧",
    48: "霧氷",
    51: "霧雨（弱）",
    53: "霧雨（中）",
    55: "霧雨（強）",
    56: "着氷性霧雨（弱）",
    57: "着氷性霧雨（強）",
    61: "雨（弱）",
    63: "雨（中）",
    65: "雨（強）",
    66: "着氷性の雨（弱）",
    67: "着氷性の雨（強）",
    71: "雪（弱）",
    73: "雪（中）",
    75: "雪（強）",
    77: "霧雪",
    80: "にわか雨（弱）",
    81: "にわか雨（中）",
    82: "にわか雨（強）",
    85: "にわか雪（弱）",
    86: "にわか雪（強）",
    95: "雷雨",
    96: "雷雨（ひょう弱）",
    99: "雷雨（ひょう強）",
}

WIND_DIRECTIONS_16 = (
    "北",
    "北北東",
    "北東",
    "東北東",
    "東",
    "東南東",
    "南東",
    "南南東",
    "南",
    "南南西",
    "南西",
    "西南西",
    "西",
    "西北西",
    "北西",
    "北北西",
)


def wmo_to_condition(code: int | float | None) -> str:
    if code is None:
        return "不明"
    return WMO_CONDITION_JA.get(int(code), f"コード{int(code)}")


def degrees_to_direction(degrees: float | int | None) -> str:
    if degrees is None or (isinstance(degrees, float) and math.isnan(degrees)):
        return "不明"
    idx = int((float(degrees) + 11.25) / 22.5) % 16
    return WIND_DIRECTIONS_16[idx]


def infer_observation_time(ev: dict) -> time:
    """イベントの観測時刻を推定する。"""
    start_time = ev.get("start_time")
    if start_time:
        text = str(start_time).strip()
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(text, fmt).time()
            except ValueError:
                continue

    tags = ev.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    title = str(ev.get("title") or "")
    if "session:morning" in tags or "朝練" in title:
        return time(8, 0)
    if "session:evening" in tags or "夕練" in title:
        return time(18, 0)
    return time(12, 0)


def _fetch_open_meteo(base_url: str, start: date, end: date) -> dict[str, Any]:
    params = {
        "latitude": TAMANA_LAT,
        "longitude": TAMANA_LON,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(HOURLY_PARAMS),
        "timezone": TAMANA_TIMEZONE,
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "INBOX-calendar/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"Open-Meteo API error ({exc.code}): {body}") from exc


def fetch_hourly_weather(start: date, end: date, *, today: date | None = None) -> dict[str, dict[str, Any]]:
    """期間内の時間別天気を取得し、'YYYY-MM-DDTHH:00' → 値 の辞書を返す。"""
    if start > end:
        return {}

    today = today or date.today()
    archive_end = min(end, today - timedelta(days=1))
    forecast_start = max(start, today)

    merged: dict[str, dict[str, Any]] = {}

    if start <= archive_end:
        data = _fetch_open_meteo("https://archive-api.open-meteo.com/v1/archive", start, archive_end)
        merged.update(_hourly_to_index(data))

    if forecast_start <= end:
        data = _fetch_open_meteo("https://api.open-meteo.com/v1/forecast", forecast_start, end)
        merged.update(_hourly_to_index(data))

    return merged


def _hourly_to_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    result: dict[str, dict[str, Any]] = {}
    for i, ts in enumerate(times):
        row: dict[str, Any] = {}
        for key in HOURLY_PARAMS:
            values = hourly.get(key) or []
            row[key] = values[i] if i < len(values) else None
        result[ts] = row
    return result


def lookup_hourly(index: dict[str, dict[str, Any]], day: date, at: time) -> dict[str, Any] | None:
    key = f"{day.isoformat()}T{at.strftime('%H:00')}"
    return index.get(key)


def build_weather_record(
    day: date,
    at: time,
    hourly: dict[str, Any] | None,
    *,
    fetched_at: datetime | None = None,
) -> dict[str, Any]:
    """YAML に保存する weather オブジェクトを組み立てる。"""
    observed_at = f"{day.isoformat()}T{at.strftime('%H:%M')}"
    record: dict[str, Any] = {
        "location": TAMANA_LOCATION,
        "observed_at": observed_at,
        "source": "open-meteo",
    }
    if fetched_at:
        record["fetched_at"] = fetched_at.replace(microsecond=0).isoformat()

    if not hourly:
        record["condition"] = "データなし"
        return record

    record["condition"] = wmo_to_condition(hourly.get("weather_code"))
    temp = hourly.get("temperature_2m")
    humidity = hourly.get("relative_humidity_2m")
    precip = hourly.get("precipitation")
    wind_speed = hourly.get("wind_speed_10m")
    wind_dir = hourly.get("wind_direction_10m")

    if temp is not None:
        record["temperature_c"] = round(float(temp), 1)
    if humidity is not None:
        record["humidity_pct"] = int(round(float(humidity)))
    if precip is not None:
        record["precipitation_mm"] = round(float(precip), 1)
    if wind_dir is not None:
        record["wind_direction"] = degrees_to_direction(wind_dir)
    if wind_speed is not None:
        record["wind_speed_kmh"] = round(float(wind_speed), 1)

    return record


def format_weather_summary(weather: dict[str, Any] | None) -> str:
    """1行の天気サマリー（カレンダー表示用）。"""
    if not weather:
        return ""
    parts: list[str] = []
    if weather.get("condition"):
        parts.append(str(weather["condition"]))
    if weather.get("temperature_c") is not None:
        parts.append(f"{weather['temperature_c']}°C")
    if weather.get("humidity_pct") is not None:
        parts.append(f"湿度{weather['humidity_pct']}%")
    wind_bits: list[str] = []
    if weather.get("wind_direction"):
        wind_bits.append(str(weather["wind_direction"]))
    if weather.get("wind_speed_kmh") is not None:
        wind_bits.append(f"{weather['wind_speed_kmh']}km/h")
    if wind_bits:
        parts.append("風" + " ".join(wind_bits))
    if weather.get("precipitation_mm") is not None and float(weather["precipitation_mm"]) > 0:
        parts.append(f"降水{weather['precipitation_mm']}mm")
    location = weather.get("location") or TAMANA_LOCATION
    if parts:
        return f"【{location}】 " + " / ".join(parts)
    return f"【{location}】 {weather.get('condition', '不明')}"


def format_weather_detail_lines(weather: dict[str, Any] | None) -> list[str]:
    """Markdown 詳細表示用の行リスト。"""
    if not weather:
        return []
    lines = ["", "**天気（玉名市）**", ""]
    mapping = [
        ("観測時刻", weather.get("observed_at")),
        ("天気", weather.get("condition")),
        ("気温", f"{weather['temperature_c']}°C" if weather.get("temperature_c") is not None else None),
        ("湿度", f"{weather['humidity_pct']}%" if weather.get("humidity_pct") is not None else None),
        ("風向", weather.get("wind_direction")),
        ("風速", f"{weather['wind_speed_kmh']} km/h" if weather.get("wind_speed_kmh") is not None else None),
        ("降水量", f"{weather['precipitation_mm']} mm" if weather.get("precipitation_mm") is not None else None),
        ("データソース", weather.get("source")),
    ]
    for label, value in mapping:
        if value is not None and str(value).strip():
            lines.append(f"- **{label}**: {value}")
    return lines
