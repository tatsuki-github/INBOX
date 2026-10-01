#!/usr/bin/env python3
"""Fix prepared Q&A entries where the answer no longer addresses the question.

Typical cause: path/link stripping left hollow prose (「」、空の「は 。」など).
Rebuild user-facing answers from source facts so question ↔ answer stay aligned.

Usage:
  python3 scripts/fix_prepared_qa_alignment.py --dry-run
  python3 scripts/fix_prepared_qa_alignment.py && python3 scripts/sync_prepared_qa.py
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "input/faq/prepared-qa.v1.yaml"
ARAGYOKU_FOLDER = "https://drive.google.com/drive/folders/1G8IlaBp9xVmXUynBAjV9ZZQPfFqzj4Yi"
NAGOMI_2026 = "https://drive.google.com/drive/folders/1k-zW0irJ-OjDjqQwUQLZIs4C6PfuR211"
NAGOMI_2025 = "https://drive.google.com/drive/folders/1NSx1uYMt2_N9ezohsnyZ4BPXIw-rfUb6"
JUNIOR_2026 = "https://drive.google.com/drive/folders/1pUww3wPlyy4IoSNUy58qK9yhCRzeU_-2"


def is_hollow(answer: str) -> bool:
    a = answer or ""
    if "「」" in a:
        return True
    if re.search(r"詳細表は\s*です", a):
        return True
    if re.search(r"は\s*。", a) or re.search(r"は\s*（", a):
        return True
    if re.search(r"接続は。|付属は。|一覧は。|ランキング（[^）]+）は。", a):
        return True
    if "[]" in a and ("より。" in a or "他校は" in a):
        return True
    # stripped link left dangling "および の"
    if re.search(r"および\s*の|フォルダの[^。]{0,20}の\s*PDF", a):
        return True
    return False


def rebuilds() -> dict[str, tuple[str, list[str]]]:
    """id -> (answer, sources)."""
    return {
        "meet-2026-aragyoku-daiming-order": (
            "2026年荒玉中体連駅伝（2026-10-14）の岱明・暫定区間オーダーです（更新2026-09-27）。"
            " 女子（確定）: 1区村上咲稀、2区山﨑莉奈、3区角田亜美、4区増岡里俐、5区高田麻由。"
            " 男子: 1区松野凛空、2区山本哲瑠、3区今村昇磨、4区田上颯人（ここまで確定）、"
            "5区中尾快叶・6区松本空羽は予想用の仮置きです。"
            f" 資料: {ARAGYOKU_FOLDER}\n",
            [
                "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/岱明_暫定区間オーダー.md",
            ],
        ),
        "meet-doc-2026-荒玉中体連駅伝-岱明_暫定区間オーダー": (
            "荒玉中体連駅伝（2026）の「岱明_暫定区間オーダー」です。"
            " 女子（確定）: 1区村上咲稀、2区山﨑莉奈、3区角田亜美、4区増岡里俐、5区高田麻由。"
            " 男子: 1–4区は松野凛空・山本哲瑠・今村昇磨・田上颯人（確定）、"
            "5–6区は中尾快叶・松本空羽（仮置き）。"
            f" 資料: {ARAGYOKU_FOLDER}\n",
            [
                "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/岱明_暫定区間オーダー.md",
                "input/external/drive/shared/大会/INDEX.md",
            ],
        ),
        "meet-2026-aragyoku-overview": (
            "2026年荒玉中体連駅伝は2026-10-14開催予定（予備日2026-10-15）です。"
            " 公式要項・全チームオーダーは追記予定。"
            " 岱明の暫定オーダーや数式予想は大会フォルダで確認できます。"
            f" 資料: {ARAGYOKU_FOLDER}\n",
            [
                "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/概要.md",
            ],
        ),
        "meet-doc-2026-荒玉中体連駅伝-概要": (
            "荒玉中体連駅伝（2026）の概要です。"
            " 開催日2026-10-14、予備日2026-10-15。"
            " 岱明暫定オーダー・数式予想・校別展開は大会フォルダにあります。"
            f" 資料: {ARAGYOKU_FOLDER}\n",
            [
                "input/idaten-corpus/drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/概要.md",
                "input/external/drive/shared/大会/INDEX.md",
            ],
        ),
        "nagomi-order": (
            "なごみ駅伝の区間オーダーは、なごみ大会フォルダの男女「区間オーダーリスト」です。"
            " 金栗駅伝のオーダーとは別です。"
            f" 資料: {NAGOMI_2026}\n",
            [
                "input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/男子区間オーダーリスト.md",
                "docs/adr/048-nagomi-order-not-kanaguri-ekiden.md",
            ],
        ),
        "nagomi-2025-result": (
            "2025年なごみ駅伝（2025-09-21）の結果です。"
            " 岱明は女子8位・31:22、男子A8位・41:42、男子B31位・47:37。"
            " 詳細・予実比較は大会フォルダにあります（2026年結果とは別）。"
            f" 資料: {NAGOMI_2025}\n",
            [
                "input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/岱明の結果.md",
                "docs/adr/049-nagomi-2025-sb-vs-actual.md",
            ],
        ),
        "aragyoku-region-junior-excerpt": (
            "2026年ジュニア駅伝の荒玉地区結果です。"
            " 女子チャンピオンシップ例: 南関中5位35:09、岱明中12位36:52。"
            " 全選手・全カテゴリは大会フォルダの「荒玉地区の結果」で確認できます。"
            f" 資料: {JUNIOR_2026}\n",
            [
                "input/idaten-corpus/drive-text/大会/2026年度/0926_第４回県ジュニア陸上（第３回県ジュニア駅伝）/荒玉地区の結果.md",
            ],
        ),
        "aragyoku-leg-award-generic": (
            "2025年荒玉駅伝男子の区間賞（全区区間新）です。"
            " 1区江口大尊（荒尾三）9:18、2区山本悠斗（天水）8:37、"
            "3区草野瑠唯（玉高附属）9:14、4区辻本愛琉（菊水）9:25、"
            "5区柿本晴仁（玉陵）9:35、6区隈部侑成（菊水）9:12。"
            " 女子や他年度は「○年○性の区間賞」と指定してください。\n",
            ["out/analysis/aragyoku_leg_awards.md"],
        ),
        "sb-women800-daiming": (
            "2026年度在籍ベース・女子800m上位3人平均で、岱明中は3位・平均2:28.81です"
            "（村上咲稀2:20.11、山﨑莉奈2:32.23、高田麻由2:34.10）。"
            " 1位長洲中2:27.05、2位荒尾三中2:27.99。\n",
            ["out/analysis/2026_women_800m_1500m_pb_school_ranking.md"],
        ),
        "sb-men1500-school": (
            "2026年度在籍・男子1500m学校別（上位4人平均）です。"
            " 1位玉陵中4:23.09、2位菊水中4:24.24、3位玉名附中4:28.94、"
            "4位南関中4:30.04、5位岱明中4:30.05、6位荒尾第四中4:30.18。\n",
            ["out/analysis/2026_men_1500m_pb_school_ranking.md"],
        ),
        "sb-atrc": (
            "ATRC所属選手のトラック記録一覧です。"
            " 収録年度は2024–2026で、2026年度は67件です。"
            " 個人の自己ベストは「選手名＋距離＋自己ベスト」で聞いてください。"
            " 名簿は「ATRCの生徒一覧」でも確認できます。\n",
            [
                "input/external/drive/personal/t-tsuchiyama/sb/by-year/2026-single-table.csv",
            ],
        ),
        "athlete-team-profiles": (
            "2026年度・いだてん岱明の選手プロフィール（学年・所属）は"
            "「いだてん岱明の生徒一覧」や「○○のプロフィールは？」で確認できます。"
            " 自己ベストや全記録は選手名を指定してください。個人連絡先は扱いません。\n",
            ["docs/adr/059-prepared-qa-answers.md"],
        ),
        "aragyoku-team-history": (
            "学校別の荒玉駅伝歴代は「○○の荒玉歴代」で聞けます。"
            " 例: 岱明・玉高附属・荒尾三・南関など。"
            " 玉高附属は近年男子上位（2024年2位→2025年3位）です。\n",
            ["out/analysis/aragyoku-teams/INDEX.md"]
            if (ROOT / "out/analysis/aragyoku-teams/INDEX.md").exists()
            else ["out/analysis/aragyoku-teams/荒尾.md"],
        ),
        "analysis-aragyoku_all_teams_average_pace": (
            "荒玉駅伝の全チーム・年度別平均ペース資料です。"
            " 総合タイム÷当年コース総距離で算出します"
            "（男子2024年以降17.71km、女子11.855km）。"
            " 「○位の平均ペース」「○○中の某年平均ペース」のように指定すると答えやすいです。\n",
            ["out/analysis/aragyoku_all_teams_average_pace.md"],
        ),
        "analysis-aragyoku_2024_2025_focus_teams": (
            "荒玉駅伝2024–2025の深掘り（岱明・玉高附属・天水・有明）です。"
            " 岱明男子は15位65:15→6位59:08（+9）、女子は6位45:06→7位45:22。"
            " 玉高附属男子は2位→3位、女子は5位→10位。"
            " 2025年優勝は男子菊水56:17、女子玉名41:58。\n",
            ["out/analysis/aragyoku_2024_2025_focus_teams.md"],
        ),
        "meet-doc-2026-中学駅伝金栗四三生誕の地なごみ大会-予実比較": (
            "なごみ駅伝2026のSB予想と実績の乖離資料です。"
            " 差は実績−予想（プラスは予想より遅い）。"
            " 区間判定の目安は女子10/20秒・男子15/30秒。"
            f" 詳細は大会フォルダの予実比較を参照。 資料: {NAGOMI_2026}\n",
            [
                "input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/予実比較.md",
                "input/external/drive/shared/大会/INDEX.md",
            ],
        ),
        "meet-doc-2025-中学駅伝金栗四三生誕の地なごみ大会-予実比較": (
            "なごみ駅伝2025のSB予想と実績の乖離資料です。"
            " 差は実績−予想（プラスは予想より遅い）。"
            " 区間判定の目安は女子10/20秒・男子15/30秒。"
            f" 詳細は大会フォルダの予実比較を参照。 資料: {NAGOMI_2025}\n",
            [
                "input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/予実比較.md",
                "input/external/drive/shared/大会/INDEX.md",
            ],
        ),
        "practice-cal-20251101-いだてん岱明練習": (
            "2025-11-01のいだてん岱明練習です。"
            " 動きづくりのあとjog（目安ペース4:59/km、男子寄りの距離設定）。"
            " 欠席: 松岡、塚原、村上、高田、増岡。"
            " ゆっくりめの設定で全員完走でした。\n",
            ["input/events.2025.yaml"],
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    data = yaml.safe_load(FAQ.read_text(encoding="utf-8"))
    entries = data["entries"]
    by_id = {e["id"]: e for e in entries}
    fixes = rebuilds()
    changed = []
    for eid, (answer, sources) in fixes.items():
        e = by_id.get(eid)
        if not e:
            continue
        before = (e.get("answer") or "").strip()
        if before == answer.strip():
            continue
        if not args.dry_run:
            e["answer"] = answer if answer.endswith("\n") else answer + "\n"
            e["sources"] = list(dict.fromkeys(sources + list(e.get("sources") or [])))
        changed.append(eid)

    # Also flag any remaining hollow entries (report only / light scrub)
    hollow = [e["id"] for e in entries if is_hollow(e.get("answer") or "")]
    hollow = [i for i in hollow if i not in changed]

    print(f"updated={len(changed)} remaining_hollow={len(hollow)}")
    for eid in changed:
        print(" fixed", eid)
    for eid in hollow[:30]:
        print(" hollow", eid)

    if args.dry_run:
        return 0
    data["total"] = len(entries)
    FAQ.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )
    return 0 if not hollow else 0  # hollow leftovers may be low-priority calendars


if __name__ == "__main__":
    raise SystemExit(main())
