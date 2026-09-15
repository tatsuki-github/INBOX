#!/usr/bin/env python3
"""女子GPXを連結・再利用して、男子6区の走行線を構成する。

男子2区の実GPSを優先し、残りを女子の道路上GPSから連続するよう構成する。
共通アンカー（女子5区終点＝男子6区終点）と実測男子2区を基準に、指定された
男子区間距離の境界を女子の既存トラック上へ配置する。

これは男子の新規GPS測定ではなく、女子コースとの共通性を前提にした
動画用の派生トラックである。各動画の距離進行は別途公式距離へ補正する。
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_aragyoku_women_course_videos import Point, cumulative_m, interpolate, parse_gpx  # noqa: E402


NAMESPACE = "http://www.topografix.com/GPX/1/1"
ET.register_namespace("", NAMESPACE)


def cut(points: list[Point], start_fraction: float, end_fraction: float) -> list[Point]:
    """元の走行向きで、距離割合[start, end]だけを取り出す（逆向きも可）。"""
    cumulative = cumulative_m(points)
    total = cumulative[-1]
    start_m, end_m = total * start_fraction, total * end_fraction
    ascending = end_m >= start_m
    lower, upper = (start_m, end_m) if ascending else (end_m, start_m)
    selected = [interpolate(points, cumulative, lower)]
    selected.extend(point for point, distance in zip(points[1:-1], cumulative[1:-1]) if lower < distance < upper)
    selected.append(interpolate(points, cumulative, upper))
    return selected if ascending else list(reversed(selected))


def cut_metres(points: list[Point], start_m: float, end_m: float) -> list[Point]:
    cumulative = cumulative_m(points)
    if not (0 <= start_m <= end_m <= cumulative[-1]):
        raise ValueError((start_m, end_m, cumulative[-1]))
    selected = [interpolate(points, cumulative, start_m)]
    selected.extend(point for point, distance in zip(points[1:-1], cumulative[1:-1]) if start_m < distance < end_m)
    selected.append(interpolate(points, cumulative, end_m))
    return selected


def merge(*segments: list[Point]) -> list[Point]:
    output: list[Point] = []
    for segment in segments:
        for point in segment:
            if not output or (point.lat, point.lon) != (output[-1].lat, output[-1].lon):
                output.append(point)
    return output


def write_gpx(path: Path, name: str, points: list[Point]) -> None:
    root = ET.Element(f"{{{NAMESPACE}}}gpx", version="1.1", creator="Aragyoku course video generator")
    trk = ET.SubElement(root, f"{{{NAMESPACE}}}trk")
    ET.SubElement(trk, f"{{{NAMESPACE}}}name").text = name
    segment = ET.SubElement(trk, f"{{{NAMESPACE}}}trkseg")
    for point in points:
        ET.SubElement(segment, f"{{{NAMESPACE}}}trkpt", lat=f"{point.lat:.7f}", lon=f"{point.lon:.7f}")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--women-gpx-dir", type=Path, required=True)
    parser.add_argument("--men-leg2-gpx", type=Path, required=True, help="実測の男子2区GPX")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source = {leg: parse_gpx(next(args.women_gpx_dir.glob(f"*女子{leg}区.gpx"))) for leg in range(1, 6)}
    actual_leg2 = parse_gpx(args.men_leg2_gpx)
    official = {1: 3000, 2: 2855, 3: 3000, 4: 3000, 5: 2855, 6: 3000}
    # 男子2区の実GPSは女子3区終点→女子3区始点の向き。これを固定し、
    # 受け渡しが連続するように1区・3〜6区を女子の既存走行線から切り出す。
    men = {
        1: merge(cut(source[2], 0.855 / 1.855, 1.0), source[3]),
        2: actual_leg2,
        3: source[1],
        4: merge(source[2], cut(source[3], 0.0, 1.145 / 2.0)),
        5: merge(cut(source[3], 1.145 / 2.0, 1.0), source[4]),
        6: source[5],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for leg, points in men.items():
        filename = f"荒玉駅伝男子{leg}区.gpx"
        write_gpx(args.output_dir / filename, f"荒玉駅伝 男子{leg}区（女子GPS派生）", points)
        records.append({
            "leg": leg,
            "official_m": official[leg],
            "derived_gps_m": round(cumulative_m(points)[-1], 1),
            "file": filename,
        })
    manifest = {
        "title": "荒玉駅伝男子コース: 女子GPSからの派生トラック",
        "method": "実測男子2区（女子3区終点→女子3区始点）を固定し、受け渡しが連続する1区・3〜6区を女子GPSの既存走行線から切出し",
        "caveat": "男子2区以外は男子の実測GPSではない。動画の距離表示は公式距離へ補正される。",
        "actual_gps_legs": [2],
        "legs": records,
    }
    (args.output_dir / "荒玉駅伝男子_派生GPX情報.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
