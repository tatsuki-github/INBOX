#!/usr/bin/env python3
"""Explainable pre-race Aragyoku 2026 model from dated race observations.

The current SB forecast is a comparison target, never an input observation.
Run with the repository's Python environment (numpy and PyYAML required).
"""
from __future__ import annotations

import csv
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_aragyoku_ekiden_sb_preview as base  # noqa: E402

AS_OF = date(2026, 9, 27)
FORECAST_DATE = date(2026, 10, 14)
OUT = ROOT / "out/analysis"
MEET = base.MEET_DIR
NAME_ALIASES = {"松野凜空": "松野凛空"}
RECENT_WINDOW_DAYS = 45
RECENT_HALF_LIFE_DAYS = 21
RECENT_ROAD_WEIGHT = 2.0
RECENT_TRACK_WEIGHT = 0.5
BEST_SHARE = 0.30
PEAK_EVIDENCE_DAYS = 30
# Scenario assumption: the junior park loop is rolling, but no measured
# elevation profile or independent course-time penalty is available here.
JUNIOR_HILL_FACTOR = 1.01
# The v1 baseline alignment is held fixed so the recency change can be
# evaluated without fitting the new forecast back to the old SB estimates.
BASELINE_SCALE = {"男子": 1.0051284240243719, "女子": 0.9860736188843046}


def norm_name(value: str) -> str:
    name = base.nagomi.norm_name(value or "")
    return NAME_ALIASES.get(name, name)


def seconds(value: str | float | int | None) -> float | None:
    if value is None or value == "" or str(value).upper() in {"DNS", "DNF", "—", "-"}:
        return None
    value = str(value).replace("分", ":").replace("秒", "").strip()
    try:
        parts = [float(x) for x in value.split(":")]
        return sum(x * 60 ** i for i, x in enumerate(reversed(parts)))
    except ValueError:
        return None


def day(value: str) -> date | None:
    try:
        return date.fromisoformat(value.replace("/", "-")[:10])
    except ValueError:
        return None


def distance(value: str) -> float | None:
    m = re.fullmatch(r"\s*([\d.]+)\s*(km|m)\s*", str(value), re.I)
    return float(m[1]) * (1 if m[2].lower() == "km" else .001) if m else None


def fmt(sec: float | None) -> str:
    if sec is None or not math.isfinite(sec):
        return "—"
    # Relay results and forecasts are recorded to whole seconds.
    whole = math.floor(sec + 0.5) if sec >= 0 else math.ceil(sec - 0.5)
    return f"{int(whole // 60)}:{int(whole % 60):02d}"


def load_targets() -> list[dict]:
    targets = []
    for gender in ("男子", "女子"):
        path = MEET / f"{gender}区間オーダー_SB予想_coverage.csv"
        for row in csv.DictReader(path.open(encoding="utf-8")):
            if not norm_name(row["name"]):
                continue
            targets.append({"gender": gender, "team": row["team"], "leg": int(row["leg"]),
                            "km": float(row["km"]), "name": row["name"],
                            "key": (gender, norm_name(row["name"])),
                            "baseline": seconds(row["pred_sec"]), "baseline_note": row["note"]})
    assert len({x["key"] for x in targets}) == len(targets), "Ambiguous target names"
    return targets


def extract(targets: list[dict]) -> tuple[list[dict], Counter]:
    by_key = {x["key"]: x for x in targets}
    obs: list[dict] = []
    rejected: Counter = Counter()
    seen: set[tuple] = set()

    def add(gender: str, name: str, when: str, km: float | None, time: str | float | None,
            kind: str, meet: str, source: str, *, leg: int | None = None,
            team: str = "", grade: int | None = None, status: str = "",
            include_non_target: bool = False) -> None:
        key = gender, norm_name(name)
        target = by_key.get(key)
        if target is None and not include_non_target:
            return
        d, sec = day(when), seconds(time)
        if status and status != "ok":
            rejected["nonfinish"] += 1
            return
        if d is None or d > AS_OF:
            rejected["future_or_undated"] += 1
            return
        if grade is not None and str(grade).isdigit() and int(grade) + 2026 - d.year > 3:
            rejected["graduated_athlete"] += 1
            return
        # A matching name from an explicitly different school is a namesake.
        if target is not None and team.endswith("中"):
            target_school = base.normalize_prior_team_to_school(target["team"]) or target["team"]
            source_school = base.normalize_prior_team_to_school(team) or team
            legacy_tamana_match = team == "玉名附中" and target_school == "玉名高附"
            if target_school != source_school and not legacy_tamana_match:
                rejected["different_school_namesake"] += 1
                return
        if km is None or not .7 <= km <= 10 or sec is None or sec <= 0:
            rejected["missing_or_invalid"] += 1
            return
        pace = sec / km
        if not 130 <= pace <= 420:
            rejected["implausible_pace"] += 1
            return
        identity = (gender, key[1], d.isoformat(), round(km, 3), round(sec, 2), kind)
        if identity in seen:
            rejected["duplicate"] += 1
            return
        seen.add(identity)
        obs.append({"gender": gender, "team": target["team"] if target else team,
                    "name": target["name"] if target else name,
                    "date": d.isoformat(), "distance_km": km, "time_sec": sec,
                    "type": kind, "meet": meet, "leg": leg, "source": source,
                    "source_team": team, "source_grade": grade})

    # Every dated middle-distance result, including non-SB races.
    for year in (2025, 2026):
        rel = f"input/external/drive/personal/t-tsuchiyama/sb/by-year/{year}-single-table.csv"
        with (ROOT / rel).open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                km = distance(row["距離"])
                if km is None:
                    continue
                meet = row["大会名"]
                kind = "road" if ("ロード" in meet or "マラソン" in meet) else "track"
                add(row["性別"], row["名前"], row["日付"], km, row["記録秒"],
                    kind, meet, rel, team=row["所属"],
                    grade=int(row["学年"]) if row["学年"].isdigit() else None)

    rel = "out/analysis/notion_records_2026.json"
    for row in json.loads((ROOT / rel).read_text(encoding="utf-8")):
        add(row.get("gender", ""), row.get("name", ""), row.get("date", ""),
            distance(row.get("distance", "")), row.get("record_seconds"),
            "track", row.get("meet", "Notion陸上記録"), rel,
            team=row.get("affiliation", ""), grade=row.get("grade"))

    # Official/published Nagomi leg split data; men 3km and women 2km.
    for year, prefix in ((2025, "0921"), (2026, "0920")):
        rel = (f"input/external/drive/shared/大会/{year}年度/"
               f"{prefix}_中学駅伝金栗四三生誕の地なごみ大会/成績表.json")
        payload = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        when = payload["event"]["date"]
        for field, gender, km in (("men", "男子", 3.0), ("women", "女子", 2.0)):
            for team in payload[field]:
                for leg, row in enumerate(team["legs"], 1):
                    add(gender, row.get("name", ""), when, km, row.get("split"),
                        "road_ekiden", "なごみ中学駅伝", rel, leg=leg,
                        team=team["team"], grade=row.get("grade"))

    # 2026 junior district transcription; known course lengths. Use the
    # complete official-result transcription, not the former partial excerpt.
    rel = ("input/external/drive/shared/大会/2026年度/"
           "0926_第４回県ジュニア陸上（第３回県ジュニア駅伝）/荒玉地区の結果.md")
    text = (ROOT / rel).read_text(encoding="utf-8")
    section = ""
    junior_team = ""
    for line in text.splitlines():
        if line.strip() in {"女子チャンピオンシップ", "女子チャレンジ", "女子オープン",
                            "男子チャンピオンシップ", "男子チャレンジ", "男子オープン"}:
            section = line.strip()
            junior_team = ""
            continue
        if section.endswith("チャンピオンシップ") and "位 " in line and " 総合" in line:
            junior_team = re.search(r"\d+位\s+(.+?)\s+総合", line).group(1)
            continue
        if section.endswith("チャンピオンシップ"):
            m = re.search(r"(\d)区\s+([\d.]+)km\s+(.+?)（(\d+)年）(\d+:\d{2})", line)
            if m:
                leg, km = int(m[1]), float(m[2])
                add("女子" if section.startswith("女子") else "男子", m[3],
                    "2026-09-26", km, m[5], "road_ekiden", "熊本県ジュニア駅伝",
                    rel, leg=leg, team=junior_team, grade=int(m[4]),
                    include_non_target=True)
        elif section.endswith("オープン"):
            m = re.search(r"\d+位\s+(.+?)\s+(.+?)（(\d+)年）(\d+:\d{2})", line)
            if m:
                gender = "女子" if section.startswith("女子") else "男子"
                add(gender, m[2], "2026-09-26", 2.3 if gender == "女子" else 2.6,
                    m[4], "road_ekiden", "熊本県ジュニア駅伝オープン", rel,
                    team=m[1], grade=int(m[3]), include_non_target=True)

    # 2025 junior: only the Daimei results have individual splits.
    rel = ("input/external/drive/shared/大会/2025年度/"
           "0927_第２回熊本県ジュニア駅伝競走大会/岱明の結果.md")
    gender = ""; open_race = False
    for line in (ROOT / rel).read_text(encoding="utf-8").splitlines():
        if line.strip() in {"男子", "女子"}:
            gender = line.strip(); open_race = False
        if line.startswith("参考"):
            gender = ""
        if line.startswith("オープン"):
            open_race = True
        if not gender:
            continue
        m = re.search(r"(?:\d区\s+[\d.]+km\s+)?([^\s]+)\s+(\d+分\d+秒|\d+:\d{2})", line)
        if m and not line.startswith("参考"):
            km = (2.3 if gender == "女子" else 2.6) if open_race else None
            leg_m = re.match(r"(?:([\d])区|[\d]位)\s+([\d.]+)km", line)
            if leg_m:
                km = float(leg_m[2])
            add(gender, m[1], "2025-09-27", km, m[2], "road_ekiden",
                "熊本県ジュニア駅伝", rel, leg=int(leg_m[1]) if leg_m and leg_m[1] else None, team="岱明中")

    # 2025 citizen road race has explicit 3km/5km individual times.
    rel = "input/external/drive/shared/大会/2025年度/1130_玉名市民マラソン/岱明の結果.md"
    gender = ""; km = None
    for line in (ROOT / rel).read_text(encoding="utf-8").splitlines():
        head = re.match(r"^(男子|女子)(\d+)km", line)
        if head:
            gender, km = head[1], float(head[2]); continue
        m = re.match(r"^(.+?)\s+\d\s+(\d+:\d{2})", line)
        if m and gender:
            add(gender, m[1], "2025-11-30", km, m[2], "road",
                "玉名市民マラソン", rel, team="岱明中")

    # Prior same-course Aragyoku splits. Current target/actual stays sealed.
    for year in (2024, 2025):
        for gender in ("男子", "女子"):
            rel = f"input/aragyoku/transcripts/{year}-{gender}.json"
            payload = json.loads((ROOT / rel).read_text(encoding="utf-8"))
            leg_km = {x["leg"]: x["distance_km"] for x in payload.get("legs", [])}
            if not leg_km:
                ds = base.MEN_DISTANCES_KM if gender == "男子" else base.WOMEN_DISTANCES_KM
                leg_km = dict(enumerate(ds, 1))
            for team in payload["teams"]:
                for row in team["legs"]:
                    grade = row.get("grade")
                    if not isinstance(grade, int) or grade + 2026 - year > 3:
                        continue
                    leg = row["leg"]
                    add(gender, row.get("name", ""), payload["date"], leg_km.get(leg),
                        row.get("split"), "aragyoku_prior", "荒玉駅伝", rel,
                        leg=leg, team=team["team"], grade=grade, status=row.get("status", "ok"))

    # A partial-name provisional runner can still have a measured prior-year
    # B-team split. Use it only when no other observation was found, and never
    # replace an actual 2026 result with the old SB forecast.
    observed_keys = {(r["gender"], norm_name(r["name"])) for r in obs}
    for prior in base.PRIOR_YEAR_B_TEAM_RETURNERS:
        key = (prior["gender"], norm_name(prior["name"]))
        target = by_key.get(key)
        if target is None or key in observed_keys or target["team"] != prior["school"]:
            continue
        before = len(obs)
        add(prior["gender"], prior["name"], prior["date"], prior["km"],
            prior["sec"], "aragyoku_prior", prior["meet"],
            "scripts/generate_aragyoku_ekiden_sb_preview.py:PRIOR_YEAR_B_TEAM_RETURNERS",
            leg=prior["leg"], team=prior["school"], grade=prior["grade_was"])
        if len(obs) > before:
            observed_keys.add(key)

    obs.sort(key=lambda x: (x["gender"], x["name"], x["date"], x["type"], x["distance_km"]))
    return obs, rejected


def estimate_exponents() -> dict[str, dict]:
    """800-to-1500m and 1500-to-3000m exponents from the track corpus.

    One median per athlete-season-school avoids prolific athletes dominating.
    A 45-day pairing controls for seasonal improvement. Female pairs are few,
    so that median is shrunk toward the pooled median of both sexes.
    """
    by_athlete: dict[tuple, list[tuple[float, float, date]]] = defaultdict(list)
    for year in (2025, 2026):
        rel = f"input/external/drive/personal/t-tsuchiyama/sb/by-year/{year}-single-table.csv"
        with (ROOT / rel).open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r["距離"] not in {"800m", "1500m", "3000m"}:
                    continue
                d, sec = day(r["日付"]), seconds(r["記録秒"])
                if d is None or d > AS_OF or sec is None:
                    continue
                km = {"800m": .8, "1500m": 1.5, "3000m": 3.0}[r["距離"]]
                by_athlete[(year, r["性別"], norm_name(r["名前"]), r["所属"])].append((km, sec, d))
    values: dict[tuple[str, str], list[float]] = {(g, segment): [] for g in ("男子", "女子")
                                                 for segment in ("short", "long")}
    for (_, gender, _, _), rows in by_athlete.items():
        if gender not in {"男子", "女子"}:
            continue
        for segment, low, high in (("short", .8, 1.5), ("long", 1.5, 3.0)):
            pairs = []
            for a in rows:
                if a[0] != low:
                    continue
                for b in rows:
                    if b[0] != high or abs((a[2] - b[2]).days) > 45:
                        continue
                    k = math.log(b[1] / a[1]) / math.log(high / low)
                    if .90 <= k <= 1.30:
                        pairs.append(k)
            if pairs:
                values[(gender, segment)].append(statistics.median(pairs))
    result: dict[str, dict] = {}
    for segment in ("short", "long"):
        pooled = statistics.median(values[("男子", segment)] + values[("女子", segment)])
        for gender in ("男子", "女子"):
            ks = values[(gender, segment)]
            raw = statistics.median(ks) if ks else pooled
            shrink = 20 if segment == "long" else 0
            result.setdefault(gender, {})[segment] = {
                "value": (len(ks) * raw + shrink * pooled) / (len(ks) + shrink),
                "n": len(ks), "raw_median": raw}
    return result


def estimate_women_middle_leg_effect(max_year: int = 2025) -> dict:
    """Estimate the recurring 3rd/4th-leg split difference from same-team pairs.

    Use each season's median of team-level (leg 4 - leg 3) differences, then
    take the median across seasons so larger fields and unusual years do not
    dominate. The two legs are the same distance in the historical sources.
    """
    season_medians = []
    team_pairs = 0
    for path in sorted((ROOT / "input/aragyoku/transcripts").glob("20??-女子.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            year = int(payload.get("year", path.name[:4]))
        except (ValueError, json.JSONDecodeError):
            continue
        if year > max_year:
            continue
        distances = {x["leg"]: float(x["distance_km"])
                     for x in payload.get("legs", [])}
        if not distances:
            distances = dict(enumerate(base.WOMEN_DISTANCES_KM, 1))
        if distances.get(3) != distances.get(4):
            continue
        differences = []
        for team in payload.get("teams", []):
            legs = {int(row["leg"]): row for row in team.get("legs", [])
                    if row.get("status", "ok") == "ok"}
            if 3 not in legs or 4 not in legs:
                continue
            t3, t4 = seconds(legs[3].get("split")), seconds(legs[4].get("split"))
            if t3 is None or t4 is None:
                continue
            differences.append(t4 - t3)
        if differences:
            season_medians.append((year, statistics.median(differences), len(differences)))
            team_pairs += len(differences)
    if not season_medians:
        differential = 0.0
    else:
        differential = statistics.median(row[1] for row in season_medians)
    return {
        "leg4_minus_leg3_median_sec": differential,
        "leg_offsets_sec": {"3": -differential / 2, "4": differential / 2},
        "season_count": len(season_medians),
        "team_pairs": team_pairs,
        "years": [row[0] for row in season_medians],
        "season_medians_sec": {str(year): value for year, value, _ in season_medians},
    }


def distance_convert(time_sec: float, source_km: float, target_km: float,
                     k_long: float, k_short: float) -> float:
    if source_km < 1.5 <= target_km:
        return time_sec * (1.5 / source_km) ** k_short * (target_km / 1.5) ** k_long
    return time_sec * (target_km / source_km) ** (k_short if target_km <= 1.5 else k_long)


def road_factor(observations: list[dict], gender: str, k: float, k_short: float) -> tuple[float, int, float]:
    # Road/ekiden versus track, same athlete and within 45 days. One median per athlete.
    by_athlete: dict[str, list[dict]] = defaultdict(list)
    for row in observations:
        if row["gender"] == gender and row["date"] >= "2026-01-01":
            by_athlete[norm_name(row["name"])].append(row)
    ratios = []
    for rows in by_athlete.values():
        pairs = []
        for road in rows:
            if road["type"] not in {"road", "road_ekiden"}:
                continue
            for track in rows:
                if track["type"] != "track" or abs((day(road["date"]) - day(track["date"])).days) > 45:
                    continue
                converted = distance_convert(track["time_sec"], track["distance_km"],
                                             road["distance_km"], k, k_short)
                ratio = road["time_sec"] / converted
                if .85 <= ratio <= 1.20:
                    pairs.append(ratio)
        if pairs:
            ratios.append(statistics.median(pairs))
    if not ratios:
        return 1.0, 0, float("nan")
    raw = statistics.median(ratios)
    return (len(ratios) * raw + 25) / (len(ratios) + 25), len(ratios), raw


def estimate_men_meet_transfer(k: float, k_short: float) -> tuple[dict, list[dict]]:
    """Estimate a conservative race-day projection and expose course evidence.

    The 2025 Nagomi-to-Aragyoku pairs anchor the transition, shrunk toward
    no improvement because course and weather effects are confounded. The
    junior course scenario is separately declared because the available
    paired results cannot isolate hills from fitness and course differences.
    """
    nagomi_rel = ("input/external/drive/shared/大会/2025年度/"
                  "0921_中学駅伝金栗四三生誕の地なごみ大会/成績表.json")
    junior_rel = ("input/external/drive/shared/大会/2025年度/"
                  "0927_第２回熊本県ジュニア駅伝競走大会/岱明の結果.md")
    aragyoku_rel = "input/aragyoku/transcripts/2025-男子.json"
    nagomi = json.loads((ROOT / nagomi_rel).read_text(encoding="utf-8"))
    aragyoku = json.loads((ROOT / aragyoku_rel).read_text(encoding="utf-8"))
    prior_by_name: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
    for team in nagomi["men"]:
        for leg in team["legs"]:
            sec = seconds(leg.get("split"))
            if sec is not None:
                prior_by_name[norm_name(leg["name"])].append((sec, 3.0, team["team"]))
    junior_by_name: dict[str, list[dict]] = defaultdict(list)
    in_men = False
    for line in (ROOT / junior_rel).read_text(encoding="utf-8").splitlines():
        if line.strip() == "男子":
            in_men = True
            continue
        if in_men and line.startswith("参考"):
            break
        if not in_men:
            continue
        match = re.search(r"([^\s]+)\s+(\d+)分(\d+)秒", line)
        if match:
            junior_by_name[norm_name(match[1])].append({
                "time_sec": int(match[2]) * 60 + int(match[3]),
                "distance_km": 3.0 if line.startswith("1区") else 2.6,
                "source_team": "岱明中"})
    leg_km = {x["leg"]: float(x["distance_km"]) for x in aragyoku["legs"]}
    aragyoku_name_counts = Counter(norm_name(leg["name"])
                                  for team in aragyoku["teams"] for leg in team["legs"])
    pairs = []
    for team in aragyoku["teams"]:
        for leg in team["legs"]:
            actual = seconds(leg.get("split")) if leg.get("status", "ok") == "ok" else None
            if actual is None:
                continue
            name = norm_name(leg["name"])
            if aragyoku_name_counts[name] != 1:
                continue
            target_km = leg_km[leg["leg"]]
            for source_type, candidates in (("nagomi", prior_by_name.get(name, [])),
                                            ("junior", junior_by_name.get(name, []))):
                if len(candidates) != 1:
                    continue
                source = candidates[0]
                source_sec = source[0] if source_type == "nagomi" else source["time_sec"]
                source_km = source[1] if source_type == "nagomi" else source["distance_km"]
                converted = distance_convert(source_sec, source_km, target_km, k, k_short)
                ratio = actual / converted
                if .80 <= ratio <= 1.20:
                    pairs.append({"source_meet": source_type, "name": leg["name"],
                                  "aragyoku_team": team["team"],
                                  "source_team": source[2] if source_type == "nagomi" else source["source_team"],
                                  "source_km": source_km,
                                  "source_sec": source_sec, "aragyoku_km": target_km,
                                  "aragyoku_sec": actual, "converted_sec": converted,
                                  "actual_over_converted": ratio,
                                  "source": nagomi_rel if source_type == "nagomi" else
                                  junior_rel})
    nagomi_ratios = [r["actual_over_converted"] for r in pairs if r["source_meet"] == "nagomi"]
    junior_ratios = [r["actual_over_converted"] for r in pairs if r["source_meet"] == "junior"]
    if not nagomi_ratios or not junior_ratios:
        return {"junior_course_factor": JUNIOR_HILL_FACTOR, "peak_factor": 1.0,
                "nagomi_pairs": len(nagomi_ratios), "junior_pairs": len(junior_ratios)}, pairs
    nagomi_median = statistics.median(nagomi_ratios)
    junior_median = statistics.median(junior_ratios)
    # 2025 Nagomi->Aragyoku spans 24 days, compared with 17 forecast days.
    # Forty neutral pseudo-pairs halve the potential fitness signal because
    # that historical ratio also contains weather and course differences.
    peak_weight = len(nagomi_ratios) / (len(nagomi_ratios) + 40)
    peak_factor = nagomi_median ** ((FORECAST_DATE - AS_OF).days / 24 * peak_weight)
    raw_course_factor = nagomi_median / junior_median
    return {"junior_course_factor": JUNIOR_HILL_FACTOR,
            "peak_factor": peak_factor,
            "nagomi_pairs": len(nagomi_ratios), "junior_pairs": len(junior_ratios),
            "nagomi_to_aragyoku_median": nagomi_median,
            "junior_to_aragyoku_median": junior_median,
            "raw_course_factor": raw_course_factor,
            "junior_course_factor_source": "rolling-course scenario assumption; elevation not measured",
            "peak_projection_days": (FORECAST_DATE - AS_OF).days,
            "peak_evidence_days": PEAK_EVIDENCE_DAYS}, pairs


def adjusted_equivalent(row: dict, km: float, k: float, k_short: float,
                        road_c: float, as_of: date, junior_course_factor: float,
                        peak_factor: float) -> float:
    road = row["type"] in {"road", "road_ekiden", "aragyoku_prior"}
    equivalent = distance_convert(row["time_sec"], row["distance_km"], km, k, k_short)
    equivalent /= road_c if road else 1.0
    if row["meet"].startswith("熊本県ジュニア駅伝"):
        equivalent /= junior_course_factor
    if as_of == AS_OF and day(row["date"]) >= AS_OF - timedelta(days=PEAK_EVIDENCE_DAYS):
        equivalent *= peak_factor
    return equivalent


def features(rows: list[dict], km: float, k: float, k_short: float, road_c: float,
             as_of: date = AS_OF, junior_course_factor: float = 1.0,
             peak_factor: float = 1.0, team: str = "",
             observation_weights: list[dict] | None = None) -> dict | None:
    if not rows:
        return None
    points = []
    best_points = []
    for r in rows:
        equiv = adjusted_equivalent(r, km, k, k_short, road_c, as_of,
                                    junior_course_factor, peak_factor)
        age = (as_of - day(r["date"])).days
        weight = 2 ** (-age / RECENT_HALF_LIFE_DAYS) * (
            RECENT_TRACK_WEIGHT if r["type"] == "track" else RECENT_ROAD_WEIGHT)
        observation_factor = 1.0
        for rule in observation_weights or []:
            if rule.get("team") and rule["team"] not in team:
                continue
            if rule.get("athlete") and norm_name(str(rule["athlete"])) != norm_name(r["name"]):
                continue
            if rule.get("meet") and rule["meet"] not in r["meet"]:
                continue
            if rule.get("date") and str(rule["date"]) != r["date"]:
                continue
            observation_factor *= max(0.0, float(rule.get("weight", 1.0)))
        weight *= observation_factor
        points.append((equiv, weight, r))
        if observation_factor >= 0.999:
            best_points.append((equiv, weight, r))
    # Multiple races on one date share that date's weight. The single best is
    # softened by the second-best when present.
    per_day = Counter(p[2]["date"] for p in points)
    points = [(t, w / per_day[r["date"]], r) for t, w, r in points]
    ranked = sorted(best_points or points, key=lambda x: x[0])
    best = sum(x[0] for x in ranked[:min(2, len(ranked))]) / min(2, len(ranked))
    recent_points = [x for x in points if (as_of - day(x[2]["date"])).days <= RECENT_WINDOW_DAYS]
    if not recent_points:
        # Keep a forecast for athletes who have no race inside the window.
        recent_points = points
    recent = sum(t * w for t, w, _ in recent_points) / sum(w for _, w, _ in recent_points)
    # The fast-side quartile is robust to one unusually slow recent race.
    ordered = sorted(recent_points, key=lambda x: x[0]); cumulative = 0; total = sum(x[1] for x in ordered)
    typical = ordered[-1][0]
    for value, weight, _ in ordered:
        cumulative += weight
        if cumulative >= .25 * total:
            typical = value; break
    return {"best": best, "recent": recent, "typical": typical,
            "n": len(rows), "latest": max(x["date"] for x in rows),
            "n_recent": len(recent_points),
            "types": sorted(set(x["type"] for x in rows))}


def fit(targets: list[dict], obs: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    by_key: dict[tuple, list[dict]] = defaultdict(list)
    for row in obs:
        by_key[(row["gender"], norm_name(row["name"]))].append(row)
    params = {}; comparisons = []
    exponents = estimate_exponents()
    women_leg_effect = estimate_women_middle_leg_effect()
    men_transfer, transfer_pairs = estimate_men_meet_transfer(
        exponents["男子"]["long"]["value"],
        exponents["男子"]["short"]["value"])
    human = {gender: base.load_human_notes(gender) for gender in ("男子", "女子")}
    for gender in ("男子", "女子"):
        k, n_k, raw_k = (exponents[gender]["long"][x] for x in ("value", "n", "raw_median"))
        k_short, n_short, raw_short = (exponents[gender]["short"][x] for x in ("value", "n", "raw_median"))
        rc, n_road, raw_road = road_factor(obs, gender, k, k_short)
        course = BASELINE_SCALE[gender]
        transfer = men_transfer if gender == "男子" else {
            "junior_course_factor": 1.0, "peak_factor": 1.0,
            "nagomi_pairs": 0, "junior_pairs": 0}
        params[gender] = {"distance_exponent": k, "distance_pairs": n_k, "distance_raw_median": raw_k,
                          "short_exponent": k_short, "short_pairs": n_short, "short_raw_median": raw_short,
                          "road_factor": rc, "road_pairs": n_road, "road_raw_median": raw_road,
                          "best_share": BEST_SHARE, "other_feature": "typical",
                          "recent_window_days": RECENT_WINDOW_DAYS,
                          "recent_half_life_days": RECENT_HALF_LIFE_DAYS,
                          "recent_road_weight": RECENT_ROAD_WEIGHT,
                          "recent_track_weight": RECENT_TRACK_WEIGHT,
                          "baseline_scale": course,
                          "baseline_scale_source": "v1 median alignment, held fixed",
                          "leg_effect": women_leg_effect if gender == "女子" else {
                              "leg4_minus_leg3_median_sec": 0.0,
                              "leg_offsets_sec": {}, "season_count": 0,
                              "team_pairs": 0, "years": [], "season_medians_sec": {}},
                          "observation_weight_rules": human[gender].get("formula_observation_weights", []),
                          **transfer}
        for t in [x for x in targets if x["gender"] == gender]:
            f = features(by_key[t["key"]], t["km"], k, k_short, rc,
                         junior_course_factor=transfer["junior_course_factor"],
                         peak_factor=transfer["peak_factor"], team=t["team"],
                         observation_weights=human[gender].get("formula_observation_weights", []))
            leg_effect_sec = float(params[gender]["leg_effect"]["leg_offsets_sec"].get(str(t["leg"]), 0.0))
            raw_pred = (None if f is None else
                        course * (BEST_SHARE * f["best"] + (1 - BEST_SHARE) * f["typical"]) + leg_effect_sec)
            pred = None if raw_pred is None else math.floor(raw_pred + 0.5)
            applied_adjustments = []
            for adj in human[gender].get("formula_adjustments", []):
                if adj.get("team") and str(adj["team"]) not in t["team"]:
                    continue
                if adj.get("athlete") and norm_name(str(adj["athlete"])) != norm_name(t["name"]):
                    continue
                if adj.get("leg") is not None and int(adj["leg"]) != t["leg"]:
                    continue
                if adj.get("set_sec") is not None:
                    pred = math.floor(float(adj["set_sec"]) + 0.5)
                elif adj.get("delta_sec") is not None and pred is not None:
                    pred = math.floor(pred + float(adj["delta_sec"]) + 0.5)
                applied_adjustments.append(str(adj.get("reason") or "人間考慮"))
            grade_override = next((int(adj["grade"])
                                   for adj in human[gender].get("grade_overrides", [])
                                   if adj.get("team") and str(adj["team"]) in t["team"]
                                   and adj.get("athlete")
                                   and norm_name(str(adj["athlete"])) == norm_name(t["name"])
                                   and str(adj.get("grade", "")).isdigit()
                                   and 1 <= int(adj["grade"]) <= 3), None)
            comparisons.append({"gender": gender, "team": t["team"], "leg": t["leg"],
                                "km": t["km"], "name": t["name"], "baseline_sec": t["baseline"],
                                "grade": grade_override if grade_override is not None else
                                next((int(r["source_grade"]) + AS_OF.year - int(r["date"][:4])
                                      for r in sorted(by_key[t["key"]],
                                                      key=lambda x: x["date"], reverse=True)
                                      if r.get("source_grade") is not None and r.get("date") and
                                      1 <= int(r["source_grade"]) + AS_OF.year - int(r["date"][:4]) <= 3),
                                     None),
                                "formula_sec": pred, "error_sec": None if pred is None or t["baseline"] is None else pred - t["baseline"],
                                "leg_effect_sec": leg_effect_sec,
                                "best_sec": f["best"] if f else None,
                                "recent_sec": f["recent"] if f else None,
                                "typical_sec": f["typical"] if f else None,
                                "n_races": f["n"] if f else 0,
                                "n_recent_races": f["n_recent"] if f else 0,
                                "latest_race": f["latest"] if f else "",
                                "race_types": ",".join(f["types"]) if f else "",
                                "baseline_note": t["baseline_note"],
                                "human_adjustment": " / ".join(applied_adjustments),
                                "prediction_basis": (
                                    "manual_provisional" if applied_adjustments and not f else
                                    "prior_year_B_provisional" if f and f["n"] == 1 and
                                    by_key[t["key"]][0]["meet"].endswith("B") else
                                    "race_records" if f else "unavailable")})
    return params, comparisons, transfer_pairs


def historical_track_backtest(params: dict) -> tuple[list[dict], dict]:
    """Evaluate old meet splits using only track evidence available before each meet.

    This is deliberately separate from fitting the current forecast. Historical
    road coverage is incomplete, so its error is a diagnostic, not a clean
    comparison against the all-race 2026 predictions.
    """
    school_map = base.load_arato_school_map()
    summary = {}; results = []

    def school(value: str) -> str:
        if value == "玉名附中":
            return "玉名高附"
        return base.normalize_prior_team_to_school(value) or ""

    for year in (2024, 2025):
        rel = f"input/external/drive/personal/t-tsuchiyama/sb/by-year/{year}-single-table.csv"
        track: dict[tuple, list[dict]] = defaultdict(list)
        with (ROOT / rel).open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                km = distance(r["距離"]); d = day(r["日付"]); sec = seconds(r["記録秒"])
                if km is None or d is None or sec is None or not 130 <= sec / km <= 420:
                    continue
                if "ロード" in r["大会名"] or "マラソン" in r["大会名"]:
                    continue
                resolved = base.resolve_analysis_school(
                    r["所属"], r["名前"],
                    affiliation_overrides=school_map["affiliation_overrides"],
                    athlete_overrides=school_map["athlete_overrides"])
                key = (r["性別"], school(resolved), norm_name(r["名前"]))
                track[key].append({"gender": r["性別"], "name": r["名前"],
                                   "date": d.isoformat(), "distance_km": km,
                                   "time_sec": sec, "type": "track",
                                   "meet": r["大会名"], "source": rel,
                                   "grade": int(r["学年"]) if r["学年"].isdigit() else None})
        for gender in ("男子", "女子"):
            tr_rel = f"input/aragyoku/transcripts/{year}-{gender}.json"
            payload = json.loads((ROOT / tr_rel).read_text(encoding="utf-8"))
            event_day = day(payload["date"])
            km_by_leg = {x["leg"]: float(x["distance_km"]) for x in payload.get("legs", [])}
            if not km_by_leg:
                km_by_leg = dict(enumerate(base.MEN_DISTANCES_KM if gender == "男子" else base.WOMEN_DISTANCES_KM, 1))
            p = params[gender]
            leg_effect = (estimate_women_middle_leg_effect(max_year=year - 1)
                          if gender == "女子" else {"leg_offsets_sec": {}})
            for team in payload["teams"]:
                s = school(team["team"])
                for leg in team["legs"]:
                    if leg.get("status", "ok") != "ok":
                        continue
                    actual = seconds(leg.get("split")); number = leg["leg"]
                    if actual is None:
                        continue
                    rs = [r for r in track.get((gender, s, norm_name(leg["name"])), [])
                          if day(r["date"]) < event_day and
                          (r["grade"] is None or leg.get("grade") is None or r["grade"] == leg["grade"])]
                    f = features(rs, km_by_leg[number], p["distance_exponent"],
                                 p["short_exponent"], p["road_factor"], event_day,
                                 p["junior_course_factor"], p["peak_factor"])
                    if f is None:
                        continue
                    raw = (p["best_share"] * f["best"] +
                           (1 - p["best_share"]) * f[p["other_feature"]])
                    leg_effect_sec = float(leg_effect["leg_offsets_sec"].get(str(number), 0.0))
                    pred = p["baseline_scale"] * raw + leg_effect_sec
                    results.append({"year": year, "gender": gender, "team": s,
                                    "name": leg["name"], "leg": number,
                                    "km": km_by_leg[number], "n_track_races": len(rs),
                                    "leg_effect_sec": leg_effect_sec,
                                    "actual_sec": actual, "formula_sec": pred,
                                    "actual_minus_formula_sec": actual - pred,
                                    "actual_over_raw": actual / raw})
    for gender in ("男子", "女子"):
        rows = [r for r in results if r["gender"] == gender]
        if rows:
            residuals = [r["actual_minus_formula_sec"] for r in rows]
            summary[gender] = {"n": len(rows),
                               "mae_sec": statistics.mean(abs(x) for x in residuals),
                               "rmse_sec": math.sqrt(statistics.mean(x*x for x in residuals)),
                               "median_actual_over_raw": statistics.median(r["actual_over_raw"] for r in rows),
                               "by_year": {str(y): sum(r["year"] == y for r in rows) for y in (2024, 2025)}}
    return results, summary


def write_report(obs: list[dict], comparisons: list[dict], params: dict,
                 backtest_summary: dict, rejected: Counter) -> None:
    output_rows = []
    team_totals = []
    for gender in ("男子", "女子"):
        rows = [r for r in comparisons if r["gender"] == gender]
        fields = ["team", "leg", "km", "name", "grade", "leg_effect_sec", "formula_sec", "formula_time",
                  "baseline_sec", "baseline_time", "error_sec", "n_races", "latest_race",
                  "prediction_basis", "human_adjustment"]
        path = OUT / f"aragyoku_2026_formula_{gender}.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
            for r in rows:
                writer.writerow({**{k: r[k] for k in fields if k in r},
                                 "formula_time": fmt(r["formula_sec"]),
                                 "baseline_time": fmt(r["baseline_sec"])})
        errors = [r["error_sec"] for r in rows if r["error_sec"] is not None]
        output_rows.append((gender, rows, errors))
        by_team: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            by_team[r["team"]].append(r)
        complete = []
        expected = 6 if gender == "男子" else 5
        for team, legs in by_team.items():
            if len(legs) != expected or any(r["formula_sec"] is None for r in legs):
                continue
            total = sum(r["formula_sec"] for r in legs)
            baseline = (sum(r["baseline_sec"] for r in legs)
                        if all(r["baseline_sec"] is not None for r in legs) else None)
            complete.append({"gender": gender, "team": team, "total_sec": total,
                             "total_time": fmt(total), "baseline_total_sec": baseline,
                             "baseline_total_time": fmt(baseline),
                             "delta_sec": total - baseline if baseline is not None else None,
                             "provisional_legs": sum(r["prediction_basis"] == "prior_year_B_provisional"
                                                     for r in legs),
                             "complete_legs": expected})
        for rank, row in enumerate(sorted(complete, key=lambda r: r["total_sec"]), 1):
            team_totals.append({"rank": rank, **row})
    with (OUT / "aragyoku_2026_formula_team_totals.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(team_totals[0])); writer.writeheader(); writer.writerows(team_totals)

    lines = [
        "# 荒玉駅伝2026：レース記録から作る説明可能な区間予測式",
        "",
        "基準日: 2026-09-27 ／ 大会予定日: 2026-10-14。現在の区間オーダーは仮置きを含む。",
        "このモデルは直近の駅伝・ロード実績を優先して区間タイムを予測する。旧 `区間オーダー_SB予想_coverage.csv` は比較値で、レース観測には混ぜていない。",
        "",
        "## データと除外",
        "",
        f"選手 {len(comparisons)} 名、採用レース {len(obs)} 件。重複除去 {rejected['duplicate']} 件、卒業済みと判定 {rejected['graduated_athlete']} 件、同名の別校 {rejected['different_school_namesake']} 件、欠損・非数値・不合理なペース等 {rejected['missing_or_invalid']} 件。",
        "採用対象は800m、1000m、1500m、3000m、ロード3km/5km、なごみ・県ジュニア・過去の荒玉駅伝区間記録。2025–2026年の全レース表とNotion補完を使用し、SBだけには限定していない。対象選手のクロスカントリーと独立したタイムトライアル結果は、確認した取り込み済み資料では特定できなかった。",
        "出典と全採用行: `out/analysis/aragyoku_2026_race_observations.csv`。2026年県ジュニアの荒玉関連行は公式結果PDFで照合し、チャンピオンシップ・チャレンジ・オープンの対象外選手も観測行とロード係数算定に含めた。PDF正本は `input/external/user-provided/2026-junior-ekiden/results-pdf/`。女子CS写真として登録された `IMG_1951_女子CS.jpg` は紙面見出しが男子チャレンジだったため、女子CSは公式PDFを採用した。",
        "",
        "## 最終式",
        "",
        "各レース j の距離 d_j (km)、タイム t_j (秒)、予測区間 L (km) から、距離換算記録を作る。対象区間はすべて1.5kmより長い。",
        "",
        "`q_j = t_j × (L / d_j)^k_long / C_type`（d_j ≥ 1.5km）",
        "`q_j = t_j × (1.5 / d_j)^k_short × (L / 1.5)^k_long / C_type`（d_j < 1.5km）",
        "",
        "`C_type = 1` はトラック、ロード・駅伝・前年荒玉には下表の男女別係数を使う。これは同一選手の45日以内のトラック対ロードを比較し、選手ごとの中央値を求めてから少数標本を1へ縮めた値。クロカン係数はデータがないため推定していない。",
        "男子のジュニア駅伝記録はさらに `H_junior=1.01` で割る。男子の基準日直前30日以内の記録は、本番までの仕上がり係数 `F_peak` を掛ける。どちらも岱明だけでなく条件に合う全校の記録へ適用する。女子は両係数を1とする。",
        "",
        "直近45日内の記録について `w_j = 2^(-age_days / 21) × type_weight / n_same_day`、`type_weight_track = 0.5`、`type_weight_road/ekiden = 2.0`。同日の複数記録はその日の重みを分け合う。45日内の記録がない選手だけ全記録に同じ式を使う。",
        "",
        "`B = 全記録の補正後 q_j 最速2件の平均`（1件ならその1件）、`Q_recent = 直近集合の補正後 q_j の重み付き25パーセンタイル`（速い側から重み累積25%の記録）。",
        "",
        "**基本式**: `T_pred = S_gender × (0.30 B + 0.70 Q_recent) + L_gender,leg`。人間考慮YAMLで、療養明け・練習参加など特定実績の重みや、個人記録のない暫定オーダーを個別指定できる。",
        "",
        "| 性別 | 短距離指数 k_short | 800/1500m組数 | 中長距離指数 k_long | 1500/3000m組数 | ロード係数 C_type | 種別比較数 | 現行予測合わせ S_gender |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for gender in ("男子", "女子"):
        p = params[gender]
        lines.append(f"| {gender} | {p['short_exponent']:.4f} | {p['short_pairs']} | {p['distance_exponent']:.4f} | {p['distance_pairs']} | {p['road_factor']:.4f} | {p['road_pairs']} | {p['baseline_scale']:.4f} |")
    lines += [
        "",
        "係数を代入した実用式（各jのqとwからB・Q_recentを求める）:",
        "",
    ]
    for gender in ("男子", "女子"):
        p = params[gender]
        lines.append(f"- **{gender}**: `k_short={p['short_exponent']:.4f}, k_long={p['distance_exponent']:.4f}`、ロード等は `C_j={p['road_factor']:.4f}`、`T={p['baseline_scale']:.4f}(0.30B+0.70Q_recent)+L_{gender},leg`。")
    human_adjustments = [r for r in comparisons if r["human_adjustment"]]
    if human_adjustments:
        lines += ["", "### 個別の数式調整", "",
                  "利用者からの選手別情報・予想順位の指定を、数式の自動値の後に個別反映した。"]
        lines += ["", "| 性別 | 学校 | 区間 | 選手 | 採用値 | 調整理由 |",
                  "| --- | --- | ---: | --- | ---: | --- |"]
        for row in human_adjustments:
            lines.append(f"| {row['gender']} | {row['team']} | {row['leg']} | {row['name']} | {fmt(row['formula_sec'])} | {row['human_adjustment']} |")
    leg_effect = params["女子"]["leg_effect"]
    lines += [
        "",
        "### 女子3区・4区の区間差補正",
        "",
        f"2012–2025年の女子荒玉駅伝から、同じチームの4区タイム−3区タイムを各年内の中央値にし、年ごとの中央値をさらに中央値化した。対象は距離が同じ年だけで、{leg_effect['season_count']}年・{leg_effect['team_pairs']}チーム組。区間差の中央値は4区が3区より{leg_effect['leg4_minus_leg3_median_sec']:.1f}秒遅い。",
        f"予測ではチーム合計を保つよう3区に{leg_effect['leg_offsets_sec']['3']:+.1f}秒、4区に{leg_effect['leg_offsets_sec']['4']:+.1f}秒を加える。個人の記録から計算した基礎値に対する、女子の区間位置補正である。山川綾は「伸びが限定的」との情報を優先し、人間考慮YAMLで個別に7:29へ調整する。",
    ]
    project_rows = [r for r in obs if r["gender"] == "女子" and
                    r["date"] == "2026-09-20" and r["meet"] == "なごみ中学駅伝" and
                    r.get("source_team", "").startswith("金栗PROJECT")]
    women_first = [r for r in comparisons if r["gender"] == "女子" and
                   r["leg"] == 1 and r["formula_sec"] is not None]
    if project_rows and women_first:
        lines += [
            "",
            "## 金栗PROJECT女子のなごみ実績チェック",
            "",
            "2026年なごみ駅伝の金栗PROJECT所属選手の2km実績は、ほかの競技会と同じ距離換算・ロード係数・直近重みで式へ投入している。独立した所属ボーナスは加えていないため、同じ実績を二重に評価しない。",
        ]
        woman_params = params["女子"]
        first_by_name = {norm_name(r["name"]): r for r in women_first}
        for race in sorted(project_rows, key=lambda r: r["time_sec"]):
            forecast = first_by_name.get(norm_name(race["name"]))
            if forecast is None:
                continue
            equivalent = (woman_params["baseline_scale"] *
                          distance_convert(race["time_sec"], race["distance_km"],
                                           forecast["km"], woman_params["distance_exponent"],
                                           woman_params["short_exponent"]) /
                          woman_params["road_factor"])
            rank = 1 + sum(r["formula_sec"] < forecast["formula_sec"] for r in women_first)
            lines.append(
                f"- {forecast['name']}（{forecast['team']}）: なごみ {fmt(race['time_sec'])}"
                f"/{race['distance_km']:g}km → 距離換算 {fmt(equivalent)}、"
                f"全区間式 {fmt(forecast['formula_sec'])}、1区{rank}位/{len(women_first)}校。"
            )
    lines += [
        "",
        "距離指数は地域の全選手について同一年・45日以内の800/1500m、1500/3000mを照合し、選手年度ごとの中央値を求めた。女子の中長距離15組は少ないため男女合算の中央値へ20組相当で縮めた。",
        "直近45日・21日半減期・ロード等4倍の種別重み比を全校共通で採用した。`S_gender` は旧モデルで求めたSB予想との中央値合わせ係数を固定し、今回の式に再適合していない。実際のコース係数を意味しない。",
        "",
        "## 男子ジュニア駅伝の起伏と本番までの仕上がり",
        "",
    ]
    transfer = params["男子"]
    lines += [
        f"2025年なごみ→荒玉の同一選手 {transfer['nagomi_pairs']} 件では、距離換算後の `荒玉実績 / なごみ実績` の中央値が {transfer['nagomi_to_aragyoku_median']:.4f}。2025年ジュニア→荒玉の同一選手 {transfer['junior_pairs']} 件の中央値は {transfer['junior_to_aragyoku_median']:.4f}。同名選手が荒玉で複数校に現れる組は除外した。照合明細は `out/analysis/aragyoku_2026_meet_transfer_pairs.csv`。2025年大会記録と正本の区間距離を使用した。",
        f"`F_peak = {transfer['nagomi_to_aragyoku_median']:.4f}^(({transfer['peak_projection_days']}/24) × ({transfer['nagomi_pairs']}/({transfer['nagomi_pairs']}+40))) = {transfer['peak_factor']:.4f}`。昨年の大会間24日を今年の基準日から本番まで{transfer['peak_projection_days']}日に換算し、コース・天候の差も混ざるため40件分の中立情報で縮めた。これは男子全校の直前30日以内の記録に適用する。",
        f"起伏の独立したタイム損失は資料から測定できない。ジュニア→荒玉と、なごみ→荒玉の比から出る相対コース係数は {transfer['raw_course_factor']:.4f} で、起伏による遅延を立証しない。このため `H_junior=1.01` はユーザーのコース所感に基づく**仮定**であり実測係数ではない。ジュニア記録にだけ適用し、感度範囲は1.00–1.02とする。",
        "男子の補正後記録は `q_adjusted = q_raw / H_junior × F_peak`（直前30日内のジュニア）、`q_raw × F_peak`（同期間の他の記録）。古い記録には仕上がり係数を掛けない。女子には適用しない。",
        "2026年ジュニアの今村8:27・田上8:26は `input/external/user-provided/2026-junior-ekiden/results-pdf/a40bc8e8fbf8daa401833dc1b8f6e5eb.pdf` で照合済み。地区抜粋にも記録を載せた。",
    ]
    for athlete in ("今村昇磨", "田上颯人"):
        row = next(r for r in comparisons if r["gender"] == "男子" and norm_name(r["name"]) == athlete)
        junior = next((r for r in obs if r["gender"] == "男子" and
                       norm_name(r["name"]) == athlete and r["date"] == "2026-09-26" and
                       r["meet"] == "熊本県ジュニア駅伝"), None)
        if junior:
            lines.append(f"- {row['team']}・{row['leg']}区 {row['name']}: ジュニア2.6km {fmt(junior['time_sec'])} → 荒玉{row['km']:g}km予測 {fmt(row['formula_sec'])}。")
    daimei_rows = [r for r in comparisons if r["gender"] == "男子" and r["team"] == "岱明中"]
    daimei_observations = defaultdict(list)
    for row in obs:
        if row["gender"] == "男子" and row["team"] == "岱明中":
            daimei_observations[norm_name(row["name"])].append(row)
    sensitivity = []
    for hill in (1.0, JUNIOR_HILL_FACTOR, 1.02):
        total = 0.0
        for row in daimei_rows:
            f = features(daimei_observations[norm_name(row["name"])], row["km"],
                         transfer["distance_exponent"], transfer["short_exponent"],
                         transfer["road_factor"], junior_course_factor=hill,
                         peak_factor=transfer["peak_factor"])
            total += transfer["baseline_scale"] * (BEST_SHARE * f["best"] +
                                                    (1 - BEST_SHARE) * f["typical"])
        sensitivity.append(f"H={hill:.2f}: {fmt(total)}")
    lines.append("岱明男子の起伏仮定への感度（仕上がり係数は固定）: " + " / ".join(sensitivity) + "。")
    nankan_rows = [r for r in comparisons if r["gender"] == "男子" and r["team"] == "南関中"]
    first_five_gap = (sum(r["formula_sec"] for r in daimei_rows if r["leg"] <= 5) -
                      sum(r["formula_sec"] for r in nankan_rows if r["leg"] <= 5))
    sixth_gap = (next(r["formula_sec"] for r in daimei_rows if r["leg"] == 6) -
                 next(r["formula_sec"] for r in nankan_rows if r["leg"] == 6))
    lines.append(f"岱明と南関の予測差は1–5区合計 {first_five_gap:+.1f}秒、6区 {sixth_gap:+.1f}秒。2026年ジュニア（5区制）の実績差は岱明が+8秒だった。現在の6区選手は仮置きで、この区間が総合差の主因。")
    lines += [
        "",
        "## 現行予測との比較",
        "",
        "| 性別 | 式で計算できた人数 | 旧SB値とも比較できた人数 | MAE | RMSE |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for gender, rows, errors in output_rows:
        mae = statistics.mean(abs(e) for e in errors)
        rmse = math.sqrt(statistics.mean(e*e for e in errors))
        lines.append(f"| {gender} | {sum(r['formula_sec'] is not None for r in rows)}/{len(rows)} | {len(errors)} | {mae:.1f}秒 | {rmse:.1f}秒 |")
    lines += [
        "",
        "これは旧SB予想との差であり、2026年本番結果への予測誤差ではない。直近実績を優先したため、旧SB予想との差が大きくなる場合がある。",
        "各選手の差は `out/analysis/aragyoku_2026_formula_comparison.csv`、男女別の利用用一覧は `out/analysis/aragyoku_2026_formula_男子.csv` / `out/analysis/aragyoku_2026_formula_女子.csv`。当年記録のない仮選手には、同一校・同じ部分表記の前年Bチーム区間記録がある場合だけ実測値を採用する。前年の学年から今年の在学資格を確認し、該当記録がなければ欠測を維持する。",
        "玉名中女子2区「亀木」は2025年Bチームの2km 7:12、4区「結菜」は同2km 7:28から計算した。1記録のみなら `B=Q_recent=q_prior` なので、`T=S_女子 × t_prior × (L/d_prior)^k_long / C_road`。前年からの成長率は仮定していない。氏名は部分表記で2026年の出走確認は未了。昨年Aチームの2区・4区選手は当時3年生のため代用していない。B記録の出典は `scripts/generate_aragyoku_ekiden_sb_preview.py` の `PRIOR_YEAR_B_TEAM_RETURNERS`（人間ヒアリング）で、一次資料との照合は未了。",
        "大会フォルダと検索コーパスには、現行の `区間オーダー_数式予想.md` / `区間オーダー_数式予想_coverage.csv` / `区間オーダー_数式予想.json` を同じ計算値で保存した。従来の `SB予想` は比較用の旧予測として残した。",
        "",
        "### 仮オーダーでのチーム合計",
        "",
        "全区間に計算値がある学校のみ。† は前年B記録だけに基づく仮選手を含む学校。未確定の選手交代で順位は変わる。全件は `out/analysis/aragyoku_2026_formula_team_totals.csv`。",
        "",
        "| 性別 | 式順位 | 学校 | 式の合計 | 現行予測合計 | 差 |",
        "| --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for r in team_totals:
        delta = f"{r['delta_sec']:+.1f}秒" if r["delta_sec"] is not None else "—"
        marker = "†" if r["provisional_legs"] else ""
        lines.append(f"| {r['gender']} | {r['rank']} | {r['team']}{marker} | {r['total_time']} | {r['baseline_total_time']} | {delta} |")
    lines += [
        "",
        "### 差が大きい選手",
        "",
        "| 性別 | 学校・区間 | 選手 | 現行 | 式 | 式−現行 | 主因 |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for gender, rows, _ in output_rows:
        ranked = sorted((r for r in rows if r["error_sec"] is not None),
                        key=lambda r: abs(r["error_sec"]), reverse=True)[:5]
        for r in ranked:
            note = r["baseline_note"]
            if "人間" in note:
                cause = "現行値の人間調整"
            elif r["n_races"] <= 2:
                cause = "記録が少なく前年推定に依存"
            elif "前年伸び" in note:
                cause = "現行値の前年からの成長仮定"
            else:
                cause = "現行値の距離換算・種別加重との差"
            lines.append(f"| {gender} | {r['team']} {r['leg']}区 | {r['name']} | {fmt(r['baseline_sec'])} | {fmt(r['formula_sec'])} | {r['error_sec']:+.1f}秒 | {cause} |")

    example = next(r for r in comparisons if r["gender"] == "男子" and norm_name(r["name"]) == "山本哲瑠")
    p = params["男子"]; km = example["km"]
    race_rows = [r for r in obs if r["gender"] == "男子" and norm_name(r["name"]) == "山本哲瑠"]
    def example_q(row: dict) -> float:
        return adjusted_equivalent(row, km, p["distance_exponent"],
                                   p["short_exponent"], p["road_factor"], AS_OF,
                                   p["junior_course_factor"], p["peak_factor"])
    ranked = sorted(race_rows, key=example_q)
    lines += [
        "",
        "## 計算例：岱明中・山本哲瑠（男子2区、2.855km）",
        "",
        "全レースは観測CSVに記録。以下は距離・コース・仕上がり補正後の最速2件。",
        "",
        "| レース | 元記録 | 2.855km補正後 q |",
        "| --- | ---: | ---: |",
    ]
    for r in ranked[:2]:
        converted = example_q(r)
        lines.append(f"| {r['date']} {r['meet']} {r['distance_km']:g}km | {fmt(r['time_sec'])} | {fmt(converted)} |")
    junior = next(r for r in race_rows if r["date"] == "2026-09-26" and r["distance_km"] == 2.6)
    q_junior = example_q(junior)
    other_value = example[p["other_feature"] + "_sec"]
    lines += [
        f"| {junior['date']} 県ジュニア駅伝 {junior['distance_km']:g}km | {fmt(junior['time_sec'])} | {fmt(q_junior)} |",
        "",
        f"`B = {example['best_sec']:.2f}秒`。全{example['n_races']}件のうち直近集合{example['n_recent_races']}件から `Q_recent = {example['typical_sec']:.2f}秒`。",
        f"`T = {p['baseline_scale']:.6f} × (0.30 × {example['best_sec']:.2f} + 0.70 × {other_value:.2f}) = {example['formula_sec']:.0f}秒`（1秒単位に四捨五入）。旧SB値は{fmt(example['baseline_sec'])}で、差は{example['error_sec']:+.1f}秒。",
        "",
        "## 過去本番への診断と次の校正",
        "",
        "2024・2025年の荒玉区間実績に対し、当時の大会前トラック記録だけを入力して再計算した。女子の区間補正は各照合年より前の大会だけから推定した。距離指数など他の係数は2026-09-27までのデータで決めたため、これは後方診断であり真の事前予測ではない。過去のロード記録も網羅できず、2026年の全種別モデルと同条件の比較ではない。",
        "",
        "| 性別 | 照合区間 | 実績との差MAE | RMSE | 実績 / B・M合成値の中央値 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for gender in ("男子", "女子"):
        s = backtest_summary[gender]
        lines.append(f"| {gender} | {s['n']} | {s['mae_sec']:.1f}秒 | {s['rmse_sec']:.1f}秒 | {s['median_actual_over_raw']:.4f} |")
    lines += [
        "",
        "歴史データでコース・区間を校正するときは、(1) その大会前日までの観測だけで同じB・Q_recentを算出し、(2) `実績 / (0.30B + 0.70Q_recent)` を男女別に求め、(3) 年と学校を分けて検証し、安定した場合だけSを置き換える。現時点の実績比はロード欠損や天候も含むため2026予想には適用していない。",
        "照合明細は `out/analysis/aragyoku_2026_historical_track_backtest.csv`。既存のSB式での区間差分析は `out/analysis/aragyoku_sb_calibration.md`。",
        "",
        "## 制約",
        "",
        "男女別のロード補正は男子18人、女子10人の比較に基づくため粗い。女子の距離指数も直接の1500/3000m組が15組だけ。1レースのみの選手は安定性を測れない。現行予測には監督の判断、故障・体調、前年からの伸び、仮オーダーが入っており、記録だけでは再現できない部分が残る。天候、コース勾配、選手の当日状態は入力がないため式に入れていない。",
        "",
        "再生成: `/opt/miniconda3/bin/python scripts/model_aragyoku_2026_formula.py`。係数は `out/analysis/aragyoku_2026_formula_coefficients.json` に保存。",
        "",
    ]
    (OUT / "aragyoku_2026_formula_report.md").write_text("\n".join(lines), encoding="utf-8")


def publish_predictions(comparisons: list[dict], params: dict) -> None:
    """Dual-write the formula forecast as the current meet prediction data."""
    by_gender = {gender: [r for r in comparisons if r["gender"] == gender]
                 for gender in ("男子", "女子")}
    ranked: dict[str, list[dict]] = {}
    team_payloads: dict[str, list[dict]] = {}
    for gender, rows in by_gender.items():
        teams: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            teams[r["team"]].append(r)
        expected = 6 if gender == "男子" else 5
        payloads = []
        for name, legs in teams.items():
            legs = sorted(legs, key=lambda r: r["leg"])
            complete = len(legs) == expected and all(r["formula_sec"] is not None for r in legs)
            cumulative = 0.0
            for r in legs:
                if r["formula_sec"] is not None:
                    cumulative += r["formula_sec"]
                    r["cumulative_sec"] = cumulative
                else:
                    r["cumulative_sec"] = None
            provisional_legs = [r["leg"] for r in legs
                                if r["prediction_basis"] in {"prior_year_B_provisional", "manual_provisional"}]
            for r in legs:
                r["provisional"] = r["prediction_basis"] in {
                    "prior_year_B_provisional", "manual_provisional"}
            payloads.append({"team": name, "complete": complete,
                             "provisional": bool(provisional_legs),
                             "provisional_legs": provisional_legs,
                             "total_sec": cumulative if complete else None,
                             "rank": None, "legs": legs})
        complete_teams = sorted((t for t in payloads if t["complete"]),
                                key=lambda t: t["total_sec"])
        for rank, team in enumerate(complete_teams, 1):
            team["rank"] = rank
        for leg_no in range(1, expected + 1):
            for rank, team in enumerate(sorted(complete_teams,
                                               key=lambda t: t["legs"][leg_no - 1]["formula_sec"]), 1):
                team["legs"][leg_no - 1]["leg_rank"] = rank
            for rank, team in enumerate(sorted(complete_teams,
                                               key=lambda t: t["legs"][leg_no - 1]["cumulative_sec"]), 1):
                team["legs"][leg_no - 1]["passing_rank"] = rank
        ranked[gender] = complete_teams
        team_payloads[gender] = payloads

    def leg_cell(r: dict) -> str:
        suffix = "†" if r["prediction_basis"] in {"prior_year_B_provisional", "manual_provisional"} else ""
        grade = f"{r['grade']}年" if r.get("grade") else "学年不明"
        if r["formula_sec"] is None:
            return f"{r['name']}（{grade}・記録不足）"
        if r.get("leg_rank") is None:
            return f"{r['name']}{suffix}（{grade}） {fmt(r['formula_sec'])}"
        compact = r["name"].replace(" ", "")
        return (f"{compact}{suffix}（{grade}） ({r['passing_rank']}){fmt(r['cumulative_sec'])} / "
                f"({r['leg_rank']}){fmt(r['formula_sec'])}")

    def render_gender(gender: str) -> str:
        p = params[gender]
        m = "直近45日（記録がなければ全期間）の重み付き25%値 Q_recent"
        correction_note = (
            f"男子はジュニア駅伝記録を起伏仮定1.01で補正し、直前30日以内の記録に本番仕上がり係数{p['peak_factor']:.4f}を掛ける。起伏係数は実測ではない。"
            if gender == "男子" else
            f"女子は歴代記録による区間補正を加える（3区 {p['leg_effect']['leg_offsets_sec']['3']:+.1f}秒、4区 {p['leg_effect']['leg_offsets_sec']['4']:+.1f}秒）。")
        n_legs = 6 if gender == "男子" else 5
        order_note = ("岱明女子は監督確定、他校は仮置き。" if gender == "女子" else
                      "岱明男子1–4区は監督確定、5–6区と他校は仮置き。")
        lines = [f"# 荒玉中体連駅伝 2026 {gender} 区間オーダー・数式予想",
                 "", f"基準日: {AS_OF.isoformat()} / 大会: 2026-10-14",
                 "", f"公式オーダー未着。{order_note}"
                 "トラック・ロード・駅伝の全採用レースから算出する。人間考慮YAMLに明示された実績重みと、記録未確認選手の暫定タイムだけを個別適用する。",
                 f"数式: `T = {p['baseline_scale']:.4f} × (0.30 B + 0.70 Q_recent) + L_leg`。"
                 f"Bは全記録の最速2件平均、{m}。直近の半減期21日、ロード・駅伝の重みはトラックの4倍。距離指数は短距離 {p['short_exponent']:.4f} / 中長距離 {p['distance_exponent']:.4f}。",
                 correction_note,
                 "詳細: `out/analysis/aragyoku_2026_formula_report.md`。"
                 "旧SB予測は `区間オーダー_SB予想.md` に保存。",
                 "", "## 総合予想（全区間に数式値がある学校）", "",
                 "| 順位 | 学校 | 合計 | " + " | ".join(f"{i}区" for i in range(1, n_legs + 1)) + " |",
                 "| ---: | --- | ---: | " + " | ".join("---" for _ in range(n_legs)) + " |"]
        for t in ranked[gender]:
            marker = "†" if t["provisional"] else ""
            lines.append(f"| {t['rank']} | {t['team']}{marker} | {fmt(t['total_sec'])} | " +
                         " | ".join(leg_cell(r) for r in t["legs"]) + " |")
        incomplete = [t for t in team_payloads[gender] if not t["complete"]]
        if incomplete:
            lines += ["", "## 合計順位対象外", "",
                      "全区間の選手名またはレース記録がそろっていないため、合計順位は付けない。", ""]
            for t in incomplete:
                missing = ", ".join(f"{r['leg']}区{r['name']}" for r in t["legs"]
                                    if r["formula_sec"] is None)
                if len(t["legs"]) < n_legs:
                    missing += f"、未登録{n_legs - len(t['legs'])}区間"
                lines.append(f"- {t['team']}: {missing}")
        lines += ["", "## 区間別データ", "",
                  "| 学校 | 区間 | 距離 | 選手 | 学年 | 数式予想 | 通過予想 | 区間順 | 通過順 | 採用レース数 | 直近レース | 旧SB予測 |",
                  "| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
        for t in team_payloads[gender]:
            for r in t["legs"]:
                provisional = "†" if r["prediction_basis"] in {"prior_year_B_provisional", "manual_provisional"} else ""
                lines.append(f"| {t['team']} | {r['leg']} | {r['km']:g}km | {r['name']}{provisional} | "
                             f"{r['grade'] if r.get('grade') else '—'} | {fmt(r['formula_sec'])} | "
                             f"{fmt(r['cumulative_sec']) if t['complete'] else '—'} | "
                             f"{r.get('leg_rank', '—')} | {r.get('passing_rank', '—')} | "
                             f"{r['n_races']} | {r['latest_race'] or '—'} | {fmt(r['baseline_sec'])} |")
        lines += ["", "† は前年Bチームの実測区間記録だけを持つ仮選手、または個人記録がなく人間考慮で暫定設定した選手。欠測区間に旧SB予測を代入していない。全レースの出典と個人別誤差は分析レポートを参照。", ""]
        return "\n".join(lines)

    gender_md = {gender: render_gender(gender) for gender in ("男子", "女子")}
    combined_md = ("# 荒玉中体連駅伝 2026 数式予想\n\n"
                   f"基準日: {AS_OF.isoformat()} / 大会: 2026-10-14\n\n"
                   "現行の区間予測。旧SB方式は `区間オーダー_SB予想.md`。"
                   "各区間の採用レースと計算式は `out/analysis/aragyoku_2026_formula_report.md`。\n\n"
                   + gender_md["女子"] + "\n---\n\n" + gender_md["男子"])
    scenario_lines = ["# 荒玉中体連駅伝 2026 校別展開・数式予想", "",
                      f"基準日: {AS_OF.isoformat()} / 大会: 2026-10-14。公式オーダー未着。",
                      "数値の正本: [区間オーダー_数式予想.md](区間オーダー_数式予想.md)。",
                      "昨年実績との比較・旧SB方式の展開は `校別展開予想.md`。", ""]
    for gender in ("男子", "女子"):
        scenario_lines += [f"## {gender}", "", "| 順位 | 学校 | 合計 | 区間予想 |",
                           "| ---: | --- | ---: | --- |"]
        for t in ranked[gender]:
            splits = " / ".join(
                f"{r['leg']}区 {r['name']}（{r['grade']}年） {fmt(r['formula_sec'])}"
                if r.get("grade") else f"{r['leg']}区 {r['name']}（学年不明） {fmt(r['formula_sec'])}"
                for r in t["legs"])
            marker = "†" if t["provisional"] else ""
            scenario_lines.append(f"| {t['rank']} | {t['team']}{marker} | {fmt(t['total_sec'])} | {splits} |")
        scenario_lines += ["", "† は前年B記録のみの仮選手を含む学校。全区間がそろわない学校は合計順位対象外。", ""]

    # Keep the SB source rows and add reproducible formula fields. This also
    # retains blank provisional legs, which are absent from comparisons.
    source_rows = []
    by_slot = {(r["gender"], r["team"], r["leg"]): r for r in comparisons}
    for gender in ("女子", "男子"):
        path = MEET / f"{gender}区間オーダー_SB予想_coverage.csv"
        for row in csv.DictReader(path.open(encoding="utf-8")):
            r = by_slot.get((gender, row["team"], int(row["leg"])))
            source_rows.append({"gender": gender, "team": row["team"], "leg": row["leg"],
                                "km": row["km"], "name": row["name"],
                                "grade": r["grade"] if r and r.get("grade") else "",
                                "pred_sec": str(r["formula_sec"]) if r and r["formula_sec"] is not None else "",
                                "pred": fmt(r["formula_sec"]) if r else "—",
                                "baseline_sb_sec": row["pred_sec"],
                                "baseline_sb": row["pred"],
                                "delta_sec": f"{r['error_sec']:+.1f}" if r and r["error_sec"] is not None else "",
                                "n_races": r["n_races"] if r else 0,
                                "latest_race": r["latest_race"] if r else "",
                                "race_types": r["race_types"] if r else "",
                                "prediction_basis": r["prediction_basis"] if r else "unavailable",
                                "human_adjustment": r["human_adjustment"] if r else "",
                                "sb_800": row["sb_800"], "sb_1500": row["sb_1500"],
                                "sb_3000": row["sb_3000"],
                                "model": "aragyoku_2026_formula_v6_context", "as_of": AS_OF.isoformat()})
    payload = {"event": "荒玉中体連駅伝", "event_date": "2026-10-14",
               "as_of": AS_OF.isoformat(), "model": "aragyoku_2026_formula_v6_context",
               "coefficients": params, "teams": team_payloads}
    for out_dir in (MEET, base.CORPUS_MEET):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "区間オーダー_数式予想.md").write_text(combined_md, encoding="utf-8")
        (out_dir / "男子区間オーダー_数式予想.md").write_text(gender_md["男子"], encoding="utf-8")
        (out_dir / "女子区間オーダー_数式予想.md").write_text(gender_md["女子"], encoding="utf-8")
        (out_dir / "校別展開_数式予想.md").write_text("\n".join(scenario_lines), encoding="utf-8")
        (out_dir / "区間オーダー_数式予想.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for name, rows in (("区間オーダー_数式予想_coverage.csv", source_rows),
                           ("男子区間オーダー_数式予想_coverage.csv", [r for r in source_rows if r["gender"] == "男子"]),
                           ("女子区間オーダー_数式予想_coverage.csv", [r for r in source_rows if r["gender"] == "女子"])):
            with (out_dir / name).open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        overview = out_dir / "概要.md"
        if overview.exists():
            content = overview.read_text(encoding="utf-8")
            current = ("- 現行・数式予想: [区間オーダー_数式予想.md](区間オーダー_数式予想.md) "
                       "/ [区間CSV](区間オーダー_数式予想_coverage.csv) "
                       "/ [JSON](区間オーダー_数式予想.json)\n"
                       "- 校別展開・数式予想: [校別展開_数式予想.md](校別展開_数式予想.md)\n"
                       "- 旧SB方式の比較値: [区間オーダー_SB予想.md](区間オーダー_SB予想.md) "
                       "/ [校別展開予想.md](校別展開予想.md)\n")
            content = content.replace("- 校別展開予想: [校別展開予想.md](校別展開予想.md)\n", current)
            if "- 現行・数式予想:" not in content:
                raise ValueError(f"Could not update current forecast link in {overview}")
            content = content.replace("- SB予想生成: `python3 scripts/generate_aragyoku_ekiden_sb_preview.py`",
                                      "- 生成順: `python3 scripts/generate_aragyoku_ekiden_sb_preview.py` "
                                      "→ `/opt/miniconda3/bin/python scripts/model_aragyoku_2026_formula.py`")
            overview.write_text(content, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    targets = load_targets()
    obs, rejected = extract(targets)
    params, comparisons, transfer_pairs = fit(targets, obs)
    backtest, backtest_summary = historical_track_backtest(params)
    publish_predictions(comparisons, params)
    for name, data in (("aragyoku_2026_race_observations.csv", obs),
                       ("aragyoku_2026_formula_comparison.csv", comparisons),
                       ("aragyoku_2026_historical_track_backtest.csv", backtest),
                       ("aragyoku_2026_meet_transfer_pairs.csv", transfer_pairs)):
        with (OUT / name).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)
    write_report(obs, comparisons, params, backtest_summary, rejected)
    (OUT / "aragyoku_2026_formula_coefficients.json").write_text(
        json.dumps({"as_of": AS_OF.isoformat(), "params": params,
                    "historical_track_backtest": backtest_summary,
                    "rejected": dict(rejected), "observations": len(obs)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for gender in ("男子", "女子"):
        rows = [x for x in comparisons if x["gender"] == gender]
        errors = [x["error_sec"] for x in rows if x["error_sec"] is not None]
        print(gender, "observations", sum(x["gender"] == gender for x in obs),
              "covered", sum(x["formula_sec"] is not None for x in rows), "/", len(rows),
              "MAE", round(statistics.mean(abs(e) for e in errors), 1),
              "RMSE", round(math.sqrt(statistics.mean(e * e for e in errors)), 1),
              "params", params[gender])
    print("rejected", dict(rejected))
    print("historical track-only backtest", backtest_summary)


if __name__ == "__main__":
    main()
