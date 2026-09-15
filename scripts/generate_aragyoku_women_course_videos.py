#!/usr/bin/env python3
"""荒玉駅伝女子コースのGPXから、走行イメージ用の動画を作る。

GPSの地理座標は保持し、距離表示と進行率だけを大会の正式区間距離に
補正する。したがって、GPSの小さな記録誤差を理由に道路形状を歪めない。

出力:
  - 女子1区〜5区の走行コース動画（MP4）
  - 全5区を連結した全区間コース動画（MP4）
  - 補正率・始終点・GPX実測距離を記録した JSON

道路地図または衛星写真タイルを利用する。出力映像には帰属表示を常時描画する。
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


WOMEN_OFFICIAL_METRES = {1: 3000.0, 2: 1855.0, 3: 2000.0, 4: 2000.0, 5: 3000.0}
MEN_OFFICIAL_METRES = {1: 3000.0, 2: 2855.0, 3: 3000.0, 4: 3000.0, 5: 2855.0, 6: 3000.0}
# 描画関数では選択中カテゴリーの距離定義を一元的に参照する。
OFFICIAL_METRES = WOMEN_OFFICIAL_METRES

# 簡易コース図の地点記号を、GPS動画の各区間の始終点へ対応付ける。
# 座標を図面から推測せず、動画に使うGPXの連続した始終点をそのまま地点位置に使う。
CHECKPOINTS = {
    "women": {1: ("D", "B"), 2: ("B", "D"), 3: ("D", "A"), 4: ("A", "C"), 5: ("C", "GOAL")},
    "men": {1: ("C", "A"), 2: ("A", "D"), 3: ("D", "B"), 4: ("B", "E"), 5: ("E", "C"), 6: ("C", "GOAL")},
}
CHECKPOINT_INFO = {
    "women": {
        "D": "女子スタート・2区中継", "B": "女子1→2区中継", "A": "女子3→4区中継",
        "C": "女子4→5区中継", "GOAL": "女子ゴール",
    },
    "men": {
        "C": "男子1区スタート・5→6区中継", "A": "男子1→2区中継", "D": "男子2→3区中継",
        "B": "男子3→4区中継", "E": "男子4→5区中継", "GOAL": "男子ゴール",
    },
}
EARTH_RADIUS_M = 6_371_008.8
TILE_SIZE = 256
DEFAULT_FONT = Path("/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc")
MAP_STYLES = {
    "streets": {
        "template": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "地図 © OpenStreetMap contributors",
    },
    "satellite": {
        "template": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "衛星写真: Esri, Maxar, Earthstar Geographics, GIS User Community",
    },
}
USER_AGENT = "AragyokuWomenCourseVideo/1.0 (local course visualization)"


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float


def haversine_m(a: Point, b: Point) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def parse_gpx(path: Path) -> list[Point]:
    root = ET.parse(path).getroot()
    points: list[Point] = []
    for elem in root.iter():
        if elem.tag.endswith("trkpt") or elem.tag.endswith("rtept"):
            points.append(Point(float(elem.attrib["lat"]), float(elem.attrib["lon"])))
    if len(points) < 2:
        raise ValueError(f"{path.name}: 少なくとも2点のトラックポイントが必要です")
    return points


def cumulative_m(points: list[Point]) -> list[float]:
    out = [0.0]
    for a, b in zip(points, points[1:]):
        out.append(out[-1] + haversine_m(a, b))
    return out


def interpolate(points: list[Point], cumulative: list[float], distance_m: float) -> Point:
    if distance_m <= 0:
        return points[0]
    if distance_m >= cumulative[-1]:
        return points[-1]
    for index in range(1, len(cumulative)):
        if cumulative[index] >= distance_m:
            span = cumulative[index] - cumulative[index - 1]
            ratio = 0.0 if span == 0 else (distance_m - cumulative[index - 1]) / span
            a, b = points[index - 1], points[index]
            return Point(a.lat + (b.lat - a.lat) * ratio, a.lon + (b.lon - a.lon) * ratio)
    return points[-1]


def course_pause_events(points: list[Point], cumulative: list[float], official_m: float) -> list[tuple[float, str]]:
    """公式距離500mごとと、GPS軌跡の大きな曲がり角を確認停止地点にする。"""
    actual_m = cumulative[-1]
    scale = official_m / actual_m
    events: list[tuple[float, str]] = [(metres, f"{metres / 1000:.3f}km（500mポイント）") for metres in range(500, int(official_m), 500)]
    turns: list[tuple[float, float]] = []
    # 前後25mの進行ベクトルのなす角を用い、GPSの微小な揺れでは停止しない。
    for index in range(1, len(points) - 1):
        at = cumulative[index]
        if at < 35 or at > actual_m - 35:
            continue
        before = mercator_xy(interpolate(points, cumulative, at - 25), 18)
        here = mercator_xy(points[index], 18)
        after = mercator_xy(interpolate(points, cumulative, at + 25), 18)
        incoming = (here[0] - before[0], here[1] - before[1])
        outgoing = (after[0] - here[0], after[1] - here[1])
        length = math.hypot(*incoming) * math.hypot(*outgoing)
        if not length:
            continue
        cosine = max(-1.0, min(1.0, (incoming[0] * outgoing[0] + incoming[1] * outgoing[1]) / length))
        angle = math.degrees(math.acos(cosine))
        if angle >= 40:
            turns.append((at * scale, angle))
    # 1つの交差点に複数のGPS点がある場合は、最大角だけを採用する。
    selected: list[tuple[float, float]] = []
    for distance, angle in sorted(turns, key=lambda item: item[1], reverse=True):
        if all(abs(distance - previous) >= 180 for previous, _ in selected):
            selected.append((distance, angle))
    events.extend((round(distance, 1), f"曲がり角を確認（{round(angle)}°）") for distance, angle in selected)
    events.sort(key=lambda item: item[0])
    merged: list[tuple[float, str]] = []
    for distance, label in events:
        if merged and abs(distance - merged[-1][0]) < 75:
            prior_distance, prior_label = merged[-1]
            # 500m地点と角が近接した場合も、静止位置は必ず公式500m地点を優先する。
            chosen_distance = distance if "500mポイント" in label else prior_distance
            merged[-1] = (chosen_distance, f"{prior_label}・{label}")
        else:
            merged.append((distance, label))
    return merged


def progress_timeline(moving_frames: int, official_m: float, events: list[tuple[float, str]], pause_frames: int) -> list[tuple[float, str | None]]:
    """通常の進行フレームに、停止地点の完全静止フレームを挿入する。"""
    timeline: list[tuple[float, str | None]] = []
    pending = list(events)
    for frame_index in range(moving_frames):
        progress = frame_index / (moving_frames - 1)
        timeline.append((progress, None))
        while pending and progress * official_m >= pending[0][0]:
            event_m, label = pending.pop(0)
            timeline.extend([(event_m / official_m, label)] * pause_frames)
    return timeline


def mercator_xy(point: Point, zoom: int) -> tuple[float, float]:
    scale = TILE_SIZE * (2**zoom)
    x = (point.lon + 180.0) / 360.0 * scale
    lat_rad = math.radians(max(min(point.lat, 85.05112878), -85.05112878))
    y = (1 - math.asinh(math.tan(lat_rad)) / math.pi) / 2 * scale
    return x, y


def font(size: int) -> ImageFont.FreeTypeFont:
    if not DEFAULT_FONT.exists():
        raise FileNotFoundError(f"日本語フォントが見つかりません: {DEFAULT_FONT}")
    return ImageFont.truetype(str(DEFAULT_FONT), size=size)


def tile_path(cache: Path, style: str, zoom: int, x: int, y: int) -> Path:
    return cache / style / str(zoom) / str(x) / f"{y}.png"


def get_tile(cache: Path, style: str, zoom: int, x: int, y: int, offline: bool) -> Image.Image:
    max_tile = 2**zoom
    x %= max_tile
    if not 0 <= y < max_tile:
        return Image.new("RGB", (TILE_SIZE, TILE_SIZE), "#e7edf0")
    destination = tile_path(cache, style, zoom, x, y)
    if not destination.exists():
        if offline:
            raise FileNotFoundError(f"オフライン時に地図タイルが未キャッシュです: z{zoom}/{x}/{y}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(
            MAP_STYLES[style]["template"].format(z=zoom, x=x, y=y), headers={"User-Agent": USER_AGENT}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                destination.write_bytes(response.read())
            # タイルサーバーへ連続アクセスしないための短い間隔。
            time.sleep(0.08)
        except Exception as exc:
            raise RuntimeError(f"地図タイルを取得できませんでした: z{zoom}/{x}/{y}: {exc}") from exc
    return Image.open(destination).convert("RGB")


def base_map(cache: Path, style: str, zoom: int, center: tuple[float, float], width: int, height: int, offline: bool) -> tuple[Image.Image, float, float]:
    cx, cy = center
    left = cx - width / 2
    top = cy - height / 2
    min_x, max_x = math.floor(left / TILE_SIZE), math.floor((left + width) / TILE_SIZE)
    min_y, max_y = math.floor(top / TILE_SIZE), math.floor((top + height) / TILE_SIZE)
    canvas = Image.new("RGB", ((max_x - min_x + 1) * TILE_SIZE, (max_y - min_y + 1) * TILE_SIZE))
    for tx in range(min_x, max_x + 1):
        for ty in range(min_y, max_y + 1):
            canvas.paste(get_tile(cache, style, zoom, tx, ty, offline), ((tx - min_x) * TILE_SIZE, (ty - min_y) * TILE_SIZE))
    crop_left = int(round(left - min_x * TILE_SIZE))
    crop_top = int(round(top - min_y * TILE_SIZE))
    return canvas.crop((crop_left, crop_top, crop_left + width, crop_top + height)), left, top


def draw_text_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, text_font: ImageFont.FreeTypeFont, fill: str = "#ffffff") -> None:
    left, top = xy
    box = draw.multiline_textbbox((left, top), text, font=text_font, spacing=4)
    draw.rounded_rectangle((box[0] - 14, box[1] - 9, box[2] + 14, box[3] + 9), radius=12, fill=(10, 25, 42, 218))
    draw.multiline_text((left, top), text, font=text_font, fill=fill, spacing=4)


def draw_overview_ticker(
    draw: ImageDraw.ImageDraw,
    *,
    width: int,
    height: int,
    overview_routes: list[tuple[int, list[Point]]],
    current_leg: int,
    current_progress: float,
    current_point: Point,
    category_label: str,
    start_checkpoint: str,
    end_checkpoint: str,
) -> None:
    """右上に全体コースの進行状況を小図で重ねる。"""
    panel_w, panel_h = 355, 250
    # 縦長ではヘッダーと重ならないよう、全体位置をその直下の右側に置く。
    panel_x = width - panel_w - 24
    panel_y = 475 if height > width else 24
    draw.rounded_rectangle((panel_x, panel_y, panel_x + panel_w, panel_y + panel_h), radius=15, fill=(10, 25, 42, 222))
    title_font, body_font, tiny_font = font(24), font(20), font(16)
    before_m = sum(OFFICIAL_METRES[leg] for leg in OFFICIAL_METRES if leg < current_leg)
    current_m = before_m + OFFICIAL_METRES[current_leg] * current_progress
    total_m = sum(OFFICIAL_METRES.values())
    draw.text((panel_x + 18, panel_y + 13), "全体の現在地", font=title_font, fill="white")
    draw.text(
        (panel_x + 18, panel_y + 48),
        f"{category_label}{current_leg}区  |  {current_m / 1000:.3f} / {total_m / 1000:.3f}km",
        font=body_font,
        fill="#d8eaff",
    )

    # 全区間を同一のMercator座標に置き、余白を保ってミニマップへ正規化する。
    raw_routes = [(leg, [mercator_xy(point, 18) for point in points]) for leg, points in overview_routes]
    all_xy = [xy for _, route in raw_routes for xy in route]
    min_x, max_x = min(x for x, _ in all_xy), max(x for x, _ in all_xy)
    min_y, max_y = min(y for _, y in all_xy), max(y for _, y in all_xy)
    map_left, map_top = panel_x + 22, panel_y + 82
    map_w, map_h = panel_w - 44, panel_h - 108
    span_x, span_y = max(max_x - min_x, 1.0), max(max_y - min_y, 1.0)
    scale = min(map_w / span_x, map_h / span_y)
    offset_x = map_left + (map_w - span_x * scale) / 2
    offset_y = map_top + (map_h - span_y * scale) / 2

    def screen(xy: tuple[float, float]) -> tuple[float, float]:
        return (offset_x + (xy[0] - min_x) * scale, offset_y + (xy[1] - min_y) * scale)

    # 青い全体線の上に、通過済みを黄で重ねる。
    for _, route in raw_routes:
        draw.line([screen(xy) for xy in route], fill=(52, 150, 215, 230), width=6, joint="curve")
    for leg, route in raw_routes:
        if leg < current_leg:
            draw.line([screen(xy) for xy in route], fill=(244, 169, 35, 245), width=7, joint="curve")
        elif leg == current_leg:
            cutoff = max(1, round((len(route) - 1) * current_progress))
            if cutoff >= 1:
                draw.line([screen(xy) for xy in route[: cutoff + 1]], fill=(244, 169, 35, 245), width=7, joint="curve")
    marker = screen(mercator_xy(current_point, 18))
    draw.ellipse((marker[0] - 8, marker[1] - 8, marker[0] + 8, marker[1] + 8), fill="white", outline="#0a192a", width=2)
    draw.ellipse((marker[0] - 4, marker[1] - 4, marker[0] + 4, marker[1] + 4), fill="#da3d3a")
    checkpoint_font = font(18)
    for label, checkpoint in ((start_checkpoint, raw_routes[current_leg - 1][1][0]), (end_checkpoint, raw_routes[current_leg - 1][1][-1])):
        px, py = screen(checkpoint)
        draw.ellipse((px - 7, py - 7, px + 7, py + 7), fill="#ffffff", outline="#102a43", width=2)
        draw.text((px + 9, py - 12), label, font=checkpoint_font, fill="white", stroke_width=2, stroke_fill="#102a43")
    draw.text((panel_x + 18, panel_y + panel_h - 24), "黄: 通過済み　青: これから", font=tiny_font, fill="#d8eaff")


def draw_checkpoint_marker(draw: ImageDraw.ImageDraw, xy: tuple[float, float], label: str, width: int, height: int) -> None:
    """GPS上の中継地点を、画面内にあるときだけ道路上へ表示する。"""
    x, y = xy
    if not (-28 <= x <= width + 28 and -28 <= y <= height + 28):
        return
    marker_font = font(22)
    draw.ellipse((x - 11, y - 11, x + 11, y + 11), fill=(255, 255, 255, 245), outline=(21, 71, 105, 255), width=2)
    draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(23, 126, 184, 255))
    draw.text((x + 14, y - 15), label, font=marker_font, fill="white", stroke_width=3, stroke_fill="#102a43")


def render_leg(
    *,
    leg: int,
    points: list[Point],
    output: Path,
    cache: Path,
    frames_root: Path,
    zoom: int,
    width: int,
    height: int,
    fps: int,
    seconds_per_km: float,
    map_style: str,
    overview_routes: list[tuple[int, list[Point]]],
    category_label: str,
    category: str,
    offline: bool,
    pause_seconds: float,
) -> dict[str, object]:
    actual_cumulative = cumulative_m(points)
    actual_m = actual_cumulative[-1]
    official_m = OFFICIAL_METRES[leg]
    moving_frame_count = max(2, round(official_m / 1000 * seconds_per_km * fps))
    pause_events = course_pause_events(points, actual_cumulative, official_m) if pause_seconds else []
    pause_frame_count = round(pause_seconds * fps)
    timeline = progress_timeline(moving_frame_count, official_m, pause_events, pause_frame_count)
    frame_count = len(timeline)
    route_xy = [mercator_xy(point, zoom) for point in points]
    all_x, all_y = zip(*route_xy)
    frame_dir = frames_root / f"leg{leg}"
    frame_dir.mkdir(parents=True, exist_ok=True)
    label_font, hud_font, foot_font = font(35), font(24), font(17)
    checkpoint_font = font(20)
    start_checkpoint, end_checkpoint = CHECKPOINTS[category][leg]
    start_info = CHECKPOINT_INFO[category][start_checkpoint]
    end_info = CHECKPOINT_INFO[category][end_checkpoint]
    for frame_index, (progress, pause_notice) in enumerate(timeline):
        official_here = official_m * progress
        point = interpolate(points, actual_cumulative, actual_m * progress)
        cx, cy = mercator_xy(point, zoom)
        # 走者を画面下寄りに置き、進行方向の道路を長めに見せる。
        if frame_index < frame_count - 1:
            ahead = interpolate(points, actual_cumulative, min(actual_m, actual_m * progress + 20))
            ax, ay = mercator_xy(ahead, zoom)
            dx, dy = ax - cx, ay - cy
            magnitude = math.hypot(dx, dy)
            if magnitude:
                cx += dx / magnitude * 95
                cy += dy / magnitude * 95
        image, left, top = base_map(cache, map_style, zoom, (cx, cy), width, height, offline)
        image = image.convert("RGBA")
        draw = ImageDraw.Draw(image, "RGBA")
        route_screen = [(x - left, y - top) for x, y in route_xy]
        current_screen = mercator_xy(point, zoom)
        current_screen = (current_screen[0] - left, current_screen[1] - top)
        passed: list[tuple[float, float]] = []
        upcoming: list[tuple[float, float]] = []
        for raw, screen in zip(actual_cumulative, route_screen):
            (passed if raw <= actual_m * progress else upcoming).append(screen)
        if len(upcoming) < 2:
            upcoming = [current_screen, route_screen[-1]]
        if len(passed) < 2:
            passed = [route_screen[0], current_screen]
        draw.line(upcoming, fill=(36, 126, 198, 190), width=9, joint="curve")
        draw.line(passed, fill=(244, 169, 35, 235), width=10, joint="curve")
        draw_checkpoint_marker(draw, route_screen[0], start_checkpoint, width, height)
        draw_checkpoint_marker(draw, route_screen[-1], end_checkpoint, width, height)
        # 現在地: 外側の白縁と内側の赤で道路上の視認性を高める。
        x, y = current_screen
        draw.ellipse((x - 15, y - 15, x + 15, y + 15), fill=(255, 255, 255, 245), outline=(20, 50, 72, 255), width=2)
        draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(218, 61, 58, 255))
        style_label = "衛星写真" if map_style == "satellite" else "道路地図"
        portrait = height > width
        header_y = 260 if portrait else 25
        hud_y = 323 if portrait else 88
        draw_text_box(draw, (30, header_y), f"荒玉駅伝 {category_label}{leg}区  |  公式 {official_m / 1000:.3f}km  |  {style_label}", label_font)
        remain = max(0.0, official_m - official_here)
        draw_text_box(
            draw,
            (30, hud_y),
            f"進行 {official_here / 1000:.3f}km　残り {remain / 1000:.3f}km\nGPS {actual_m / 1000:.3f}km → 公式距離へ補正",
            hud_font,
        )
        checkpoint_y = 405 if portrait else 148
        draw_text_box(
            draw,
            (30, checkpoint_y),
            f"地点 {start_checkpoint} → {end_checkpoint}\n出発: {start_info}\n到着: {end_info}",
            checkpoint_font,
        )
        if pause_notice:
            draw_text_box(draw, (30, 505 if portrait else 230), f"⏸ 停止して確認: {pause_notice}", hud_font, fill="#ffd166")
        draw_overview_ticker(
            draw,
            width=width,
            height=height,
            overview_routes=overview_routes,
            current_leg=leg,
            current_progress=progress,
            current_point=point,
            category_label=category_label,
            start_checkpoint=start_checkpoint,
            end_checkpoint=end_checkpoint,
        )
        footer = f"青: これから走る区間　黄: 通過済み　|　{MAP_STYLES[map_style]['attribution']}"
        footer_y = height - 180 if portrait else height - 38
        draw.rectangle((0, footer_y, width, footer_y + 38), fill=(10, 25, 42, 218))
        draw.text((18, footer_y + 7), footer, font=foot_font, fill="white")
        image.convert("RGB").save(frame_dir / f"frame-{frame_index:05d}.jpg", quality=91, subsampling=0)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(fps),
        "-i", str(frame_dir / "frame-%05d.jpg"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-r", str(fps), str(output),
    ]
    subprocess.run(command, check=True)
    # 各区間のMP4が確定すれば、連結処理に必要なのはMP4だけ。
    # 高解像度フレームを残し続けないことで、長尺の縦動画でも容量を安定させる。
    shutil.rmtree(frame_dir)
    return {
        "leg": leg,
        "official_m": official_m,
        "gps_measured_m": round(actual_m, 1),
        "official_per_gps_scale": round(official_m / actual_m, 7),
        "moving_frames": moving_frame_count,
        "pause_seconds_each": pause_seconds,
        "pause_events": [{"official_m": distance, "label": label} for distance, label in pause_events],
        "frames": frame_count,
        "duration_seconds": round(frame_count / fps, 2),
        "start": {"lat": points[0].lat, "lon": points[0].lon},
        "end": {"lat": points[-1].lat, "lon": points[-1].lon},
        "video": output.name,
    }


def concatenate(videos: Iterable[Path], output: Path) -> None:
    list_file = output.with_suffix(".concat.txt")
    list_file.write_text("".join(f"file '{video.resolve()}'\n" for video in videos), encoding="utf-8")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", "-movflags", "+faststart", str(output),
        ], check=True)
    finally:
        list_file.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpx-dir", type=Path, required=True, help="女子1区.gpx〜女子5区.gpx のディレクトリ")
    parser.add_argument("--category", choices=("women", "men"), default="women", help="距離定義と表示する部門")
    parser.add_argument("--output-dir", type=Path, required=True, help="MP4と補正JSONの出力先")
    parser.add_argument("--cache-dir", type=Path, default=Path("work/osm-tile-cache"), help="地図タイルのキャッシュ先")
    parser.add_argument("--frames-dir", type=Path, default=Path("work/aragyoku-women-video-frames"), help="中間フレームの保存先")
    parser.add_argument("--map-style", choices=sorted(MAP_STYLES), default="satellite", help="背景地図の種類")
    parser.add_argument("--zoom", type=int, default=18)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--seconds-per-km", type=float, default=14.0)
    parser.add_argument("--pause-seconds", type=float, default=0.0, help="500m地点・大きな曲がり角ごとの静止時間（秒）")
    parser.add_argument("--skip-whole", action="store_true", help="全区間動画を再連結しない（個別動画のみ生成）")
    parser.add_argument("--offline", action="store_true", help="キャッシュ済みタイルのみ使用する")
    args = parser.parse_args()
    global OFFICIAL_METRES
    category_label = "女子" if args.category == "women" else "男子"
    OFFICIAL_METRES = WOMEN_OFFICIAL_METRES if args.category == "women" else MEN_OFFICIAL_METRES
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg が見つかりません")
    if args.width % 2 or args.height % 2:
        raise ValueError("MP4互換のため幅・高さは偶数にしてください")
    routes: list[tuple[int, list[Point]]] = []
    for leg in OFFICIAL_METRES:
        candidates = sorted(args.gpx_dir.glob(f"*{category_label}{leg}区.gpx"))
        if len(candidates) != 1:
            raise FileNotFoundError(f"{category_label}{leg}区GPXを一意に特定できません: {candidates}")
        routes.append((leg, parse_gpx(candidates[0])))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    details = []
    videos = []
    for leg, points in routes:
        output = args.output_dir / f"荒玉駅伝{category_label}{leg}区_コース動画.mp4"
        details.append(render_leg(
            leg=leg, points=points, output=output, cache=args.cache_dir, frames_root=args.frames_dir,
            zoom=args.zoom, width=args.width, height=args.height, fps=args.fps,
            seconds_per_km=args.seconds_per_km, map_style=args.map_style, overview_routes=routes,
            category_label=category_label, category=args.category, offline=args.offline, pause_seconds=args.pause_seconds,
        ))
        videos.append(output)
    whole = args.output_dir / f"荒玉駅伝{category_label}_全区間コース動画.mp4"
    if not args.skip_whole:
        concatenate(videos, whole)
    manifest = {
        "title": f"荒玉駅伝 {category_label}コース動画: GPS距離補正",
        "method": "座標列は保持し、累積距離・画面上の進行率のみを各区間の公式距離へ線形補正",
        "checkpoint_method": "簡易図の地点記号は、各GPX区間の始終点と中継の連続性に基づき動画上へ対応付け",
        "pause_method": "個別動画のみ、公式距離500mごとおよびGPS軌跡の40°以上の曲がり角で静止" if args.pause_seconds else "静止なし",
        "official_leg_metres": OFFICIAL_METRES,
        "video_format": {"width": args.width, "height": args.height, "fps": args.fps, "map_style": args.map_style, "zoom": args.zoom},
        "legs": details,
        "whole_course_video": None if args.skip_whole else whole.name,
    }
    (args.output_dir / f"荒玉駅伝{category_label}_距離補正情報.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
