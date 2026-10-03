"""Source projections for facts that loose time-token checks cannot establish."""
from __future__ import annotations

import copy
import json
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CAREER_ROW = re.compile(
    r"(20\d{2})年(男子|女子)・([^\d／。]+?)(\d+)区（([^）]+)）(?:／総合(\d+)位)?"
)


def normalized_answer(answer: str) -> str:
    return re.sub(r"\s+", "", answer).rstrip("。")


def check_career(answer: str, expected: str) -> list[str]:
    problems = []
    for pattern in (r"^(.+?)の荒玉駅伝出走歴", r"出走歴は(\d+)回"):
        actual, fresh = re.search(pattern, answer), re.search(pattern, expected)
        if not actual or not fresh or actual[1] != fresh[1]:
            problems.append("career_identity_or_count_mismatch")
    claims = {m.groups() for m in CAREER_ROW.finditer(answer)}
    supported = {m.groups() for m in CAREER_ROW.finditer(expected)}
    if claims - supported:
        problems.append("career_race_identity_mismatch")
    return problems


def render_practice(practice: dict) -> str:
    """Keep saved distances; laps must not replace an explicitly saved km value.

    Labels on legacy sets contain pace/group facts absent from their parsed
    segments. Keep the label, rather than appending conflicting segments.
    """
    from practice_models import LAP_M
    from practice_renderer import render_description

    practice = copy.deepcopy(practice)
    for item in practice.get("items") or []:
        if item.get("type") == "jog" and item.get("laps") and item.get("distance_km") is not None:
            if abs(float(item["distance_km"]) - int(item["laps"]) * LAP_M / 1000) > .005:
                distance, laps = item["distance_km"], item.pop("laps")
                item["label"] = (item.get("label") or (str(item.get("group") or "") + " ")).strip()
                item["label"] += f" {distance:g}km（保存距離・{laps}周） "
                # The label already carries the saved distance and lap count.
                item.pop("distance_km")
        if item.get("type") == "interval" and not item.get("distance_m") and item.get("distance_km"):
            item["distance_m"] = float(item["distance_km"]) * 1000
        if item.get("type") == "set" and item.get("label"):
            item.pop("segments", None)
    body = render_description(practice)
    body = re.sub(r"\n+", "、", body).strip("、")
    return re.sub(r"\s+", " ", body)


@lru_cache(maxsize=None)
def calendar_projections() -> dict[str, dict]:
    from generate_prepared_qa_bulk import slug
    out = {}
    for year in (2024, 2025, 2026):
        rel = f"input/events.{year}.yaml"
        data = yaml.load((ROOT / rel).read_text(), Loader=yaml.CSafeLoader)
        for ev in data.get("events") or []:
            title, date = ev.get("title") or "", str(ev.get("date") or "")[:10]
            if not date or not title:
                continue
            # Exact event identity only; no same-date or similar-title fallback.
            keys = [f"cal-{year}-{date.replace('-', '')}-{slug(title)[:28]}",
                    f"calx-{year}-{date.replace('-', '')}-{slug(title)[:28]}",
                    f"practice-cal-{date.replace('-', '')}-{slug(title)}",
                    f"practice-{year}-{date.replace('-', '')}-{slug(title)[:28]}"]
            # Only training/rest events belong to this projection.
            if not (ev.get("practice") or "いだてん岱明" in title or ("練習" in title and "中止" in title)):
                continue
            parts = [f"{date} の「{title}」です。"]
            if ev.get("start_time"):
                time = str(ev["start_time"])
                if ev.get("end_time"):
                    time += "–" + str(ev["end_time"])
                parts.append(f"時間は{time}です。")
            if "休み" in title:
                parts.append(("朝練" if "朝練" in title else "夕練" if "夕練" in title else "練習") + "は休みです。")
            elif ev.get("status") in {"cancelled", "canceled"} or "中止" in title:
                parts.append("中止です。")
            else:
                if ev.get("status") == "done":
                    parts.append("実施済みです。")
                practice = ev.get("practice") or {}
                body = render_practice(practice) if practice else ""
                if body:
                    parts.append(body.rstrip("。") + "。")
            for key in keys:
                if key in out:
                    raise ValueError("ambiguous calendar identity: " + key)
                out[key] = {"answer": " ".join(parts) + "\n", "sources": [rel],
                            "date": date, "title": title}
    return out


def dated_practice_questions(entry: dict, fresh: dict) -> list[str]:
    date = fresh["date"]
    y, m, d = map(int, date.split("-"))
    patterns = (date, date.replace("-", "/"), f"{y}年{m}月{d}日", f"{m}月{d}日")
    questions = [q for q in entry.get("questions") or [] if any(p in q for p in patterns)]
    return questions or [f"{date}の{fresh['title']}の内容は？"]


def school_sb_projections() -> dict[str, dict]:
    from generate_aragyoku_athlete_sb_qa import truthy_adopted, slug
    rel = "input/external/sb/middle-school/by-year/2026-sb-adopted.json"
    groups = defaultdict(list)
    for row in json.loads((ROOT / rel).read_text()):
        if truthy_adopted(row.get("SB採用")):
            school = re.sub(r"(中学校|中学|中)$", "", row.get("所属") or "")
            groups[(school, row.get("距離"))].append(row)
    out = {}
    for (school, distance), rows in groups.items():
        if not school or not distance:
            continue
        best = min(rows, key=lambda r: float(r.get("SB秒") or r.get("記録秒") or 1e12))
        answer = f"{school}の{distance}最速（2026年度・SB採用）は{best['名前']}の {best.get('SB') or best['記録']} です。"
        if best.get("大会名") or best.get("日付"):
            answer += f" 大会: {best.get('大会名', '')}（{best.get('日付', '')}）。"
        if best.get("参考", "").startswith(("https://", "http://")):
            answer += f" 大会結果: {best['参考']}。"
        out[f"sb-school-{slug(school)}-{slug(distance)}-best"] = {"answer": answer + "\n", "sources": [rel]}
    return out


def supplementary_projections() -> dict[str, dict]:
    verify_photo_reconciliations()
    import generate_prepared_qa_edge_5000 as edge
    import generate_prepared_qa_coach_analysis as coach
    out = {}
    for fn in (edge.gen_historical_races, edge.gen_who_at_rank, edge.gen_split_rank_top,
               edge.gen_team_pace, edge.gen_passing_rank, edge.gen_leg_grade, edge.gen_historical_rank_matrix):
        for entry in fn(set(), 100000):
            out[entry["id"]] = entry
    text = coach.FOCUS.read_text()
    blocks = coach.parse_focus_blocks(text)
    groups = [coach.gen_focus_entries(blocks), coach.gen_biggest_improver(blocks),
              coach.gen_highlights(text), coach.gen_top2_detail(), coach.gen_leg_award_coach(),
              coach.gen_sb_school_ranks(), coach.gen_formula_shortnames()]
    for entries in groups:
        for entry in entries:
            out[entry["id"]] = entry
    out.update(school_sb_projections())
    out.update(calendar_projections())
    out.update(complete_list_projections())
    out.update(nagomi_projections())
    out.update(photo_reviewed_projections())
    return out


def check_source_semantics(entry: dict, fresh: dict | None) -> list[str]:
    if not fresh:
        return []
    eid, answer = entry["id"], entry.get("answer") or ""
    if eid.startswith(("edgecmp-", "aragyoku-rank-benchmark-")):
        return [] if normalized_answer(answer) == normalized_answer(fresh["answer"]) else ["structured_comparison_or_benchmark_drift"]
    if eid in {"aragyoku-2024-女子-岱明-leg-detail", "aragyoku-2024-女子-team-岱明-rank"}:
        return [] if normalized_answer(answer) == normalized_answer(fresh["answer"]) else ["photo_reviewed_leg_identity_drift"]
    if eid in complete_list_projections() or eid in nagomi_projections():
        return [] if normalized_answer(answer) == normalized_answer(fresh["answer"]) else ["incomplete_or_broken_source_answer"]
    if eid.startswith("aragyoku-career-") and eid != "aragyoku-career-unknown":
        return check_career(answer, fresh["answer"])
    if eid in calendar_projections():
        problems = []
        if normalized_answer(answer) != normalized_answer(fresh["answer"]):
            problems.append("calendar_session_fact_drift")
        if entry.get("questions") != dated_practice_questions(entry, fresh):
            problems.append("undated_specific_practice_question")
        return problems
    if eid.startswith("edge5k-") and "unknown" not in fresh["answer"]:
        if normalized_answer(answer) != normalized_answer(fresh["answer"]):
            return ["structured_identity_grade_or_rank_drift"]
    if eid.startswith("sb-school-"):
        if normalized_answer(answer) != normalized_answer(fresh["answer"]):
            return ["school_season_best_drift"]
    if eid.startswith("teamhist-"):
        # Literal clock overlap cannot validate an obsolete runner list.
        names = re.search(r"区間選手:\s*(.*)", answer)
        expected = re.search(r"区間選手:\s*(.*)", fresh["answer"])
        if names and expected:
            actual_names = set(re.findall(r"[^、。\s]+", names[1])) - {"選手名未記入", "未記入"}
            known_names = set(re.findall(r"[^、。\s]+", expected[1])) - {"unknown"}
            if actual_names - known_names:
                return ["team_history_runner_identity_drift"]
    if re.match(r"aragyoku-20\d{2}-(男子|女子)-leg\d+-board$", eid):
        names = set(re.findall(r"\d+位\s*([^（\n]+)（", answer))
        expected = set(re.findall(r"\d+位\s*([^（\n]+)（", fresh["answer"]))
        if names - expected:
            return ["leg_board_runner_identity_drift"]
    return []


def repair_source_semantics(entry: dict, fresh: dict | None) -> None:
    """Refresh only source-derived fields whose stronger check finds drift."""
    if not fresh or not check_source_semantics(entry, fresh):
        return
    eid = entry["id"]
    answer = fresh["answer"]
    if eid.startswith("aragyoku-career-"):
        from polish_prepared_qa_quality import polish_career
        answer = polish_career(answer).rstrip("。") + "。\n"
    elif eid.startswith("teamhist-") and "unknown" in answer:
        answer = answer.split(" 区間選手:")[0].rstrip("。") + "。 選手名は未収録です。\n"
    entry["answer"] = answer
    if eid in calendar_projections():
        entry["questions"] = dated_practice_questions(entry, fresh)
        entry["sources"] = fresh["sources"]
    elif eid.startswith("sb-school-") or eid in complete_list_projections() or eid in nagomi_projections() or eid in photo_reviewed_projections():
        entry["sources"] = fresh["sources"]
        if fresh.get("questions"):
            entry["questions"] = fresh["questions"]


@lru_cache(maxsize=None)
def complete_list_projections() -> dict[str, dict]:
    """List questions must retain all rows, including explicit missing years."""
    out = {}
    rel = "out/analysis/2026_aragyoku_men_1500m_sb_individual_top20.md"
    rows = re.findall(r"^\| (\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$", (ROOT / rel).read_text(), re.M)
    if len(rows) != 20:
        raise ValueError("expected 20 ranked SB rows")
    out["sb-1500-top20"] = {"answer": "2026年度・荒玉地区男子1500m SB個人トップ20（同一選手は最速記録のみ）です。\n" +
        "\n".join(f"{rank}位 {name.strip()}（{school.strip()}）{mark.strip()}・{date.strip()}" for rank, name, school, mark, date in rows) + "\n", "sources": [rel]}
    rel = "input/aragyoku/winners-by-year.md"
    rows = re.findall(r"^\| (20\d{2}) \| (男子|女子) \| ([^|]+) \|", (ROOT / rel).read_text(), re.M)
    out["aragyoku-winners-all"] = {"answer": "収録されている荒玉駅伝の年度別優勝校一覧です。\n" +
        "\n".join(f"{year}年{gender}: {school.strip()}" for year, gender, school in rows) + "\n2014年女子の優勝校は未収録です。\n", "sources": [rel]}
    rel = "out/analysis/aragyoku_leg_awards.md"
    rows = re.findall(r"^2025年荒玉駅伝女子の([1-5])区区間賞は(.+)。$", (ROOT / rel).read_text(), re.M)
    if len(rows) != 5:
        raise ValueError("expected five women's leg awards")
    out["aragyoku-2025-women-leg-awards"] = {"answer": "2025年荒玉駅伝女子の全5区間の区間賞です。\n" +
        "\n".join(f"{leg}区 {details}" for leg, details in rows) + "\n", "sources": [rel]}
    rel = "out/analysis/aragyoku_all_teams_average_pace.md"
    rows = re.findall(r"^2025年荒玉駅伝(男子|女子)(\d+)位\s+(\S+)\s+のチーム全体平均ペースは\s+([^（]+)（総合\s*([^／]+)／([^）]+)）。$", (ROOT / rel).read_text(), re.M)
    if not rows:
        raise ValueError("missing 2025 team pace rows")
    out["aragyoku-average-pace"] = {"answer": "2025年荒玉駅伝・収録全チームの平均ペース（総合タイム÷コース総距離）です。\n" +
        "\n".join(f"{gender}{rank}位 {school}: {pace.strip()}（総合{total.strip()}／{distance}）" for gender, rank, school, pace, total, distance in rows) + "\n", "sources": [rel]}
    out["track-lap"] = {"answer": "岱明のトラックは、練習・ペース計算上1周560mとして扱います。練習記録に実測・保存距離がある場合は、その値を併記します。\n", "sources": ["docs/data-model.md", "scripts/practice_models.py"]}
    out["calendar-today"] = {"answer": "「今日の予定は？」または「〇月〇日の予定は？」と聞くと、いだてん岱明の練習・大会予定を検索できます。\n", "questions": ["今日の予定の聞き方は？", "予定の検索方法は？"], "sources": ["input/events.2026.yaml"]}
    out["aragyoku-unnamed-leg"] = {"answer": "大会名のない「何区を走った？」は荒玉駅伝を優先します。選手名と大会年を指定してください。例: 「2025年荒玉男子の岱明5区は？」→ 山本哲瑠。\n", "sources": ["docs/adr/047-unnamed-leg-athlete-routing.md", "out/analysis/aragyoku-teams/岱明.md"]}
    rel = "input/idaten-corpus/drive-text/練習/駅伝試走/2025.pdf.md"
    url = re.search(r"https://drive\.google\.com/file/d/[^\s`]+", (ROOT / rel).read_text())
    if not url:
        raise ValueError("missing trial PDF link")
    out["practice-doc-2025-pdf"] = {"answer": f"駅伝試走の資料「2025.pdf」です。本文はナレッジに未収録です。資料: {url[0]}\n", "sources": [rel]}
    rel = "out/analysis/2026-09-21_arato-tamana_middle_school_sb_updates.md"
    text = (ROOT / rel).read_text()
    counts = re.search(r"該当者: (\d+)名（SB更新(\d+)名、未更新(\d+)名）", text)
    if not counts:
        raise ValueError("missing SB update counts")
    total, updated, unchanged = counts.groups()
    schools = re.findall(r"^### (.+)（(\d+)名）$", text, re.M)
    out["analysis-2026-09-21_arato-tamana_middle_school_sb_updates"] = {"answer":
        f"2026-09-21の第３回熊本県長距離記録会に出場した荒玉地区中学生は{total}名で、SB更新{updated}名、未更新{unchanged}名です。"
        "学校分類はクラブ所属の学校配分と選手別指定に従い、荒玉地区外の竹熊紗良は除外しています。"
        "表の○はSB更新、—は未更新です。更新前SBは今回の取り込み前の同年度記録で、過去記録がない場合は—です。当日の新SB値は掲載していません。"
        " 学校別出場者: " + "、".join(f"{name}{count}名" for name, count in schools) + "。\n", "sources": [rel]}
    return out


@lru_cache(maxsize=None)
def nagomi_projections() -> dict[str, dict]:
    import generate_prepared_qa_nagomi_team_results as nagomi
    out = {}
    for year in (2025, 2026):
        for entry in nagomi.collect_year(year):
            out[entry["id"]] = entry
        # Legacy empty-team ids were table continuation/header rows, not teams.
        base = nagomi.MEET_DIRS[year]
        rows = {gender: nagomi.parse_results_md(base / f"{gender}成績表.md") for gender in ("男子", "女子")}
        answer = f"{year}年なごみ駅伝（{nagomi.DATES[year]}）の収録チーム結果一覧です。\n"
        for gender, results in rows.items():
            for row in results:
                rank = "オープン参加" if row["rank"] == "OP" else row["rank"] + "位"
                answer += f"{gender} {rank} {row['team']}: {row['total']}\n"
        answer += f"成績表: {nagomi.DRIVE[year]}\n"
        out[f"nagomi-team-{year}-x"] = {"answer": answer,
            "questions": [f"{year}年なごみ駅伝の全チームの総合順位は？", f"{year}年なごみ駅伝の全チーム結果一覧は？"],
            "sources": [str((base / f"{gender}成績表.md").relative_to(ROOT)) for gender in rows]}
    # A legacy athlete row was misread as a team. Read its detailed result row.
    rel = str((nagomi.MEET_DIRS[2026] / "男子成績表.md").relative_to(ROOT))
    details = re.search(r"^\| (\d+)区 \| 松浦眞大 \| [^|]* \| ([^|]+) \| (\d+) \| ([^|]+) \| (\d+) \|$", (ROOT / rel).read_text(), re.M)
    if not details:
        raise ValueError("missing Matsuura detailed result")
    teams = nagomi.parse_results_md(ROOT / rel)
    team = next(row for row in teams if any(leg.startswith("松浦眞大 ") for leg in row["legs"]))
    leg, split, rank, cumulative, passing = details.groups()
    out["nagomi-team-2026-松浦眞大"] = {"answer":
        f"2026年なごみ駅伝（2026-09-20）の松浦眞大は、{team['team']}の{leg}区で{split.strip()}（区間{rank}位）です。"
        f"{leg}区終了時点は通過{passing}位・累計{cumulative.strip()}。チームは総合{team['rank']}位・{team['total']}です。"
        f" 成績表: {nagomi.DRIVE[2026]}\n", "sources": [rel]}
    return out


def verify_photo_reconciliations() -> None:
    """An independently reviewed photo row must agree before projecting answers.

    This verifies the recorded transcription, not automatic image recognition.
    """
    import hashlib
    rel = 'input/aragyoku/reconciliations/2024-women-daimei-photo.json'
    expected = json.loads((ROOT / rel).read_text())
    if hashlib.sha256((ROOT / expected['image']).read_bytes()).hexdigest() != expected['image_sha256']:
        raise ValueError('photo evidence changed: ' + rel)
    for path in ('input/aragyoku/transcripts/2024-女子.json',
                 'input/aragyoku/women_full_2012_2025.json',
                 'input/aragyoku/women_top6_2012_2025.json'):
        data = json.loads((ROOT / path).read_text())
        block = data if 'teams' in data else data['years']['2024']
        team = next(t for t in block['teams'] if t['team'] == expected['team'])
        if (team['rank'], team['total']) != (expected['rank'], expected['total']):
            raise ValueError('photo team result drift: ' + path)
        for actual, verified in zip(team['legs'], expected['legs'], strict=True):
            if any(actual.get(key) != value for key, value in verified.items()):
                raise ValueError(f"photo leg identity/grade/result drift: {path} leg {verified['leg']}")



def photo_reviewed_projections() -> dict[str, dict]:
    from generate_prepared_qa_bulk import format_team_result_answer
    rel = 'input/aragyoku/reconciliations/2024-women-daimei-photo.json'
    row = json.loads((ROOT / rel).read_text())
    answer = format_team_result_answer(2024, '女子', row) + '\n'
    return {'aragyoku-2024-女子-岱明-leg-detail': {'answer': answer,
        'sources': ['input/aragyoku/transcripts/2024-女子.json', rel, row['image']]}}
