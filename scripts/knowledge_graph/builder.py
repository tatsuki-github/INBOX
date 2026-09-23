"""Build a routing-oriented knowledge graph from repository sources."""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
KG_PATH = ROOT / "out" / "knowledge-graph.json"
KG_MIN_PATH = ROOT / "out" / "knowledge-graph.min.json"
KG_HTML_PATH = ROOT / "out" / "knowledge-graph.html"
KG_PDF_PATH = ROOT / "out" / "knowledge-graph.pdf"

SOURCE_GLOBS: list[tuple[str, list[str], str]] = [
    # (glob_or_path relative, topics, hint)
    ("README.md", ["meta", "calendar", "practice"], "リポジトリ概要・生成コマンド・INBOX 運用"),
    ("calendar.md", ["calendar"], "当年の Markdown カレンダー（生成物）"),
    ("docs/data-model.md", ["schema", "practice", "calendar"], "イベント/練習のデータ辞書"),
    ("docs/ai-practice-generation.md", ["ai", "practice", "norwegian"], "AI 練習生成・RAG・ADR 入口"),
    ("input/practice_templates.yaml", ["practice", "template"], "名前付き練習テンプレート正本"),
    ("input/practice_schedules.yaml", ["practice", "schedule"], "朝夕練スケジュール定義"),
    ("input/ai_generation_rules.yaml", ["ai", "practice", "rules"], "AI 固定/可変/創作ルール"),
    ("input/daniels_vdot_paces.yaml", ["pace", "danish", "norwegian"], "Daniels VDOT ペース表"),
    ("input/arato_tamana_report.yaml", ["athlete_records", "arato"], "荒尾・玉名記録 PDF 設定"),
    ("out/daiming-practice-menus-kpace.md", ["practice", "pace"], "岱明練習 k/pace 横断一覧。トラック1周=560m"),
    (
        "out/analysis/line-chats/INDEX.md",
        ["practice", "calendar", "ekiden"],
        "岱明 LINE 衛生化抜粋の目録（保護者・指導者・有田）",
    ),
    (
        "out/analysis/line-chats/daiming-parents.md",
        ["practice", "calendar"],
        "保護者 LINE: 銀マット・集合・合同練習・朝練など運用連絡",
    ),
    (
        "out/analysis/line-chats/daiming-staff.md",
        ["practice", "calendar", "ekiden"],
        "指導者 LINE: 練習・引率・大会運用",
    ),
    (
        "out/analysis/line-chats/arita-taisho.md",
        ["practice", "ekiden", "pace"],
        "有田大将×土山: 分割走・補強・荒玉準備・合同練習の指導相談",
    ),
    ("input/external/INDEX.md", ["meta", "practice", "athlete_records"], "外部ソース（Drive/Notion/GitHub）取り込み目録"),
    ("input/external/drive/INDEX.md", ["practice", "athlete_records", "meta"], "Google ドライブいだてん関連スナップショット"),
    (
        "input/external/drive/shared/練習/玉名市練習会/2026-09-22.md",
        ["practice", "calendar", "athlete_records"],
        "2026-09-22 玉名市練習会の岱明実施結果（女子/男子1000m、選手別タイム・所感）",
    ),
    ("input/external/notion/INDEX.md", ["practice", "athlete_records", "injury"], "Notion いだてん岱明スナップショット"),
    ("input/external/github/INDEX.md", ["meta"], "関連リポジトリ調査（対象外含む）"),
    (
        "input/external/drive/shared/練習/練習の記録.md",
        ["practice"],
        "共有ドライブ練習ログ（2025）",
    ),
    (
        "input/external/drive/shared/名簿/2025年度_岱明中学校陸上競技部_部員名簿.csv",
        ["practice", "athlete_records"],
        "2025 岱明部員名簿",
    ),
    (
        "input/external/notion/databases/いだてん岱明生徒/rows.json",
        ["practice", "athlete_records"],
        "Notion 生徒 DB スナップショット",
    ),
    (
        "input/external/notion/databases/2026年度中学生記録/rows.json",
        ["athlete_records"],
        "Notion 2026 中学生記録スナップショット",
    ),
    (
        "input/external/media-manifest.json",
        ["ekiden", "athlete_records", "practice"],
        "外部メディア索引（画像・OCR・PDF パス）",
    ),
    (
        "input/external/notion/media/ekiden-history/INDEX.md",
        ["ekiden", "athlete_records"],
        "荒玉中体連駅伝歴代の画像・OCR 入口",
    ),
    (
        "docs/aragyoku-ekiden-distance-definitions.md",
        ["ekiden", "schema", "athlete_records"],
        "荒玉駅伝の年度別・男女別区間距離の正本定義",
    ),
    (
        "input/external/notion/databases/荒玉中体連駅伝歴代/rows.json",
        ["ekiden", "athlete_records"],
        "荒玉中体連駅伝歴代（岱明順位・記録）",
    ),
    (
        "input/external/sb/middle-school/INDEX.md",
        ["athlete_records", "meta"],
        "t-tsuchiyama 中学生 SB（ワイド＋年度別）目録",
    ),
    (
        "input/external/sb/middle-school/wide/中学生SB.csv",
        ["athlete_records"],
        "中学生ワイド SB（Drive SBデータベース）",
    ),
    (
        "docs/adr/012-middle-school-sb-all-years.md",
        ["athlete_records", "meta"],
        "中学生 SB 全年度取り込み ADR",
    ),
    (
        "docs/adr/002-norwegian-method-integration.md",
        ["norwegian", "pace", "ai", "practice"],
        "Norwegian Method 統合（GZ/T はコードで決定論）",
    ),
    (
        "docs/adr/008-daniels-vdot-gz-guidance.md",
        ["norwegian", "pace", "ai"],
        "Daniels VDOT → T → GZ の算出と CLI 規約",
    ),
    (
        "docs/tamana-weather.md",
        ["meta", "calendar"],
        "玉名天気データの更新手順（Open-Meteo / weather/tamana-forecast）",
    ),
    (
        "out/analysis/aragyoku-overview.md",
        ["ekiden", "pace"],
        "荒玉駅伝概要（区間距離・使い方・現行/旧コース）",
    ),
    (
        "out/analysis/aragyoku_2024_2025_focus_teams.md",
        ["ekiden", "pace", "analysis"],
        "荒玉2024–2025深掘り（岱明・玉高附属＝玉名付属・天水・有明の区間・前年比）",
    ),
    (
        "out/analysis/aragyoku_meet_records.md",
        ["ekiden", "analysis"],
        "荒玉ボード上部の大会記録・区間記録（meet_records）年別一覧",
    ),
    (
        "out/analysis/aragyoku_all_teams_average_pace.md",
        ["ekiden", "pace"],
        "荒玉全チーム・全年度の平均ペース（順位別歴代＋年度別全校）",
    ),
    (
        "out/analysis/aragyoku_leg_awards.md",
        ["ekiden", "analysis"],
        "荒玉区間賞・区間上位（当日結果・名前・学年・所属）",
    ),
    (
        "out/analysis/aragyoku_top6_historical_average_pace.md",
        ["ekiden", "pace"],
        "荒玉総合1〜6位の年度別平均ペース（全チーム版の要約）",
    ),
    (
        "out/analysis/aragyoku_top2_finish_counts.md",
        ["ekiden"],
        "荒玉駅伝 総合2位以内の学校と回数（男女合算・男女別）",
    ),
    (
        "out/analysis/2026_aragyoku_men_3000m_sb_ranking.md",
        ["athlete_records", "ekiden"],
        "荒玉地区 男子3000m SBランキング（2026）",
    ),
    (
        "out/analysis/2026_aragyoku_men_1500m_sb_individual_top20.md",
        ["athlete_records", "ekiden"],
        "荒玉地区 男子1500m SB 個人トップ20（2026）",
    ),
    (
        "out/analysis/2026_men_1500m_pb_school_ranking.md",
        ["athlete_records"],
        "男子1500m PB 学校別ランキング（上位4人平均）。SB CSV 行より先に読む",
    ),
    (
        "out/analysis/2026_women_800m_1500m_pb_school_ranking.md",
        ["athlete_records"],
        "女子800m/1500m PB 学校別ランキング（上位3人平均）。岱明800m上位3人平均 2:28.81",
    ),
    (
        "out/analysis/athletes/takada-mana.md",
        ["athlete_records"],
        "高田麻那（文徳高）SB。高田麻由（岱明）とは別人",
    ),
    (
        "out/analysis/arato-tamana-teams/ATRC.md",
        ["athlete_records"],
        "ATRC 所属選手のトラック記録一覧",
    ),
    (
        "input/aragyoku/course-videos.md",
        ["ekiden"],
        "荒玉駅伝コース動画の Google ドライブ URL",
    ),
    (
        "input/idaten-corpus/aragyoku/winners-by-year.md",
        ["ekiden"],
        "荒玉駅伝 年度別優勝・準優勝校（コーパス）",
    ),
    (
        "input/idaten-corpus/aragyoku/course-videos.md",
        ["ekiden"],
        "荒玉コース動画案内（コーパスコピー）",
    ),
]

LIGHTWEIGHT_SUFFIXES = {".csv", ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp"}

TOPIC_DEFS: list[tuple[str, str, str]] = [
    (
        "calendar",
        "カレンダー / 予定",
        "年次予定・メモ・祝日。正本 input/events.*.yaml とコーパス calendar/events.daiming.yaml（岱明フィルタ）",
    ),
    (
        "practice",
        "岱明練習",
        "practice ブロック・メニュー・欠席・テンプレ。コーパス practice/ と drive-text/personal・練習ログ",
    ),
    (
        "athlete_records",
        "選手記録",
        "荒尾・玉名・中学生 SB・学校別PB平均・所属全記録・Notion 生徒/記録 DB。コーパス sb/ out-analysis/ notion-db/",
    ),
    ("norwegian", "Norwegian Method", "GZ/閾値・VDOT・原則メモ"),
    ("ai", "AI 練習生成", "プロンプト・ルール・週次/単日生成"),
    ("schema", "スキーマ", "JSON Schema とデータモデル"),
    ("pace", "ペース", "k/pace・VDOT・GZ 表"),
    ("injury", "ケガ / RRI", "ランニング障害・回復エビデンス・怪我について Notion"),
    ("meta", "リポジトリ運用", "README・生成パイプライン・idaten-corpus INDEX"),
    (
        "ekiden",
        "駅伝・大会",
        "荒玉歴代 OCR/構造化、なごみ・ジュニア・玉名・金栗など drive-text/大会/ の開催要項・結果",
    ),
]

QUERY_HINTS: list[tuple[str, str, list[str]]] = [
    (
        "練習メニューの中身は？",
        "practice 付きイベントと practice.json / practice_templates / コーパス practice/ を見る",
        [
            "topic:practice",
            "source:input/practice_templates.yaml",
            "corpus:practice",
            "source:out/2026/practice.json",
            "source:out/daiming-practice-menus-kpace.md",
        ],
    ),
    (
        "欠席者は誰？",
        "practice_absentees.csv と events YAML の absentees",
        [
            "topic:practice",
            "source:out/2026/practice_absentees.csv",
            "source:input/events.2026.yaml",
            "corpus:practice",
        ],
    ),
    (
        "GZ / 閾値ペースは？",
        "Norwegian メモ + daniels_pace / VDOT 表",
        [
            "topic:norwegian",
            "topic:pace",
            "source:input/daniels_vdot_paces.yaml",
            "source:docs/adr/008-daniels-vdot-gz-guidance.md",
            "source:docs/adr/002-norwegian-method-integration.md",
            "source:input/memos/norwegian_method_applied_full.txt",
        ],
    ),
    (
        "選手の記録は？",
        "notion_records・荒尾玉名・sb/・analysis-ocr を見る",
        [
            "topic:athlete_records",
            "corpus:sb",
            "corpus:notion-db",
            "corpus:analysis-ocr",
            "source:input/external/sb/middle-school/wide/中学生SB.csv",
        ],
    ),
    (
        "今日の予定は？",
        "events YAML / events.json / calendar.md / calendar/events.daiming.yaml",
        [
            "topic:calendar",
            "source:input/events.2026.yaml",
            "source:calendar.md",
            "corpus:calendar",
        ],
    ),
    (
        "〇月〇日の予定は？",
        "日付を YYYY-MM-DD / MMDD に正規化し events YAML と drive-text/大会/ の開催要項を見る",
        [
            "topic:calendar",
            "topic:ekiden",
            "source:input/events.2026.yaml",
            "corpus:calendar",
            "corpus:drive-text",
        ],
    ),
    (
        "AI で練習を作るには？",
        "ai-practice-generation.md と prompts / rules",
        [
            "topic:ai",
            "source:docs/ai-practice-generation.md",
            "source:input/ai_generation_rules.yaml",
            "corpus:repo-docs",
        ],
    ),
    (
        "荒玉駅伝の歴代は？",
        "駅伝歴代 rows + media-manifest + ekiden-ocr/*.md + aragyoku/",
        [
            "topic:ekiden",
            "source:input/external/notion/databases/荒玉中体連駅伝歴代/rows.json",
            "source:input/external/media-manifest.json",
            "source:input/external/notion/media/ekiden-history/INDEX.md",
            "corpus:aragyoku",
            "corpus:ekiden-ocr",
            "source:out/analysis/aragyoku-overview.md",
        ],
    ),
    (
        "2024年と2025年の荒玉駅伝で岱明・玉名付属・天水・有明はどうだった？",
        "out/analysis/aragyoku_2024_2025_focus_teams.md を正本（前年比・区間・区間新）。玉名付属=玉高附属",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_2024_2025_focus_teams.md",
            "source:out/analysis/aragyoku-teams/岱明.md",
            "source:out/analysis/aragyoku-teams/玉高附属.md",
            "source:out/analysis/aragyoku-teams/天水.md",
            "source:out/analysis/aragyoku-teams/有明.md",
            "corpus:out-analysis",
            "corpus:aragyoku",
        ],
    ),
    (
        "2025年荒玉駅伝の岱明男子は何位？",
        "aragyoku_2024_2025_focus_teams.md と aragyoku-teams/岱明.md（2025男子6位・59:08）",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_2024_2025_focus_teams.md",
            "source:out/analysis/aragyoku-teams/岱明.md",
            "corpus:out-analysis",
            "corpus:aragyoku",
        ],
    ),
    (
        "玉名付属中の荒玉駅伝2024と2025は？",
        "玉名付属=玉高附属。aragyoku_2024_2025_focus_teams.md と aragyoku-teams/玉高附属.md",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_2024_2025_focus_teams.md",
            "source:out/analysis/aragyoku-teams/玉高附属.md",
            "corpus:out-analysis",
            "corpus:aragyoku",
        ],
    ),
    (
        "天水中の荒玉駅伝で区間新は誰？",
        "2025男子2区・山本悠斗 8:37（区間新）。正本は aragyoku_2024_2025_focus_teams.md",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_2024_2025_focus_teams.md",
            "source:out/analysis/aragyoku-teams/天水.md",
            "corpus:out-analysis",
            "corpus:aragyoku",
        ],
    ),
    (
        "有明中の荒玉駅伝2024-2025の分析は？",
        "aragyoku_2024_2025_focus_teams.md の有明節（男子11→12位、女子13→12位、2024男子1区区間新）",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_2024_2025_focus_teams.md",
            "source:out/analysis/aragyoku-teams/有明.md",
            "corpus:out-analysis",
            "corpus:aragyoku",
        ],
    ),
    (
        "荒玉駅伝の男子2区の大会区間記録は誰？",
        "out/analysis/aragyoku_meet_records.md を正本（ボード上部・meet_records）。当日区間新とは別",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_meet_records.md",
            "corpus:out-analysis",
            "corpus:aragyoku",
        ],
    ),
    (
        "2025年荒玉駅伝男子の総合大会記録は？",
        "aragyoku_meet_records.md の2025男子（ボード印刷値）。優勝タイムとは別概念の場合あり",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_meet_records.md",
            "corpus:out-analysis",
            "corpus:aragyoku",
        ],
    ),
    (
        "荒玉駅伝で2位までに入った学校と回数は？",
        "out/analysis/aragyoku_top2_finish_counts.md を正本として読む（男女合算・男女別）",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_top2_finish_counts.md",
            "source:input/idaten-corpus/aragyoku/winners-by-year.md",
            "corpus:aragyoku",
            "corpus:out-analysis",
        ],
    ),
    (
        "荒玉地区で3000mが一番速いのは？",
        "out/analysis/2026_aragyoku_men_3000m_sb_ranking.md の1位（隈部侑成）を返す",
        [
            "topic:athlete_records",
            "topic:ekiden",
            "source:out/analysis/2026_aragyoku_men_3000m_sb_ranking.md",
            "corpus:out-analysis",
            "corpus:sb",
        ],
    ),
    (
        "今年の荒玉地区の男子1500mSBランキングトップ20は？",
        "out/analysis/2026_aragyoku_men_1500m_sb_individual_top20.md を正本として返す",
        [
            "topic:athlete_records",
            "topic:ekiden",
            "source:out/analysis/2026_aragyoku_men_1500m_sb_individual_top20.md",
            "corpus:out-analysis",
            "corpus:sb",
        ],
    ),
    (
        "ATRCの選手の全記録は？",
        "out/analysis/arato-tamana-teams/ATRC.md を優先（所属別全記録ダイジェスト）",
        [
            "topic:athlete_records",
            "source:out/analysis/arato-tamana-teams/ATRC.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "高田麻那の記録は？",
        "out/analysis/athletes/takada-mana.md と sb/SBデータベース.csv。高田麻由（岱明）と混同しない",
        [
            "topic:athlete_records",
            "source:out/analysis/athletes/takada-mana.md",
            "corpus:sb",
            "corpus:out-analysis",
        ],
    ),
    (
        "女子800mで岱明の上位3人平均は？",
        "2026_women_800m_1500m_pb_school_ranking.md の学校別上位3人平均（SB CSV より先）",
        [
            "topic:athlete_records",
            "source:out/analysis/2026_women_800m_1500m_pb_school_ranking.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "男子1500m学校別ランキングは？",
        "2026_men_1500m_pb_school_ranking.md の上位4人平均。個人SB行より学校別正本を優先",
        [
            "topic:athlete_records",
            "source:out/analysis/2026_men_1500m_pb_school_ranking.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "2025年岱明男子の優勝との差は？",
        "aragyoku_2024_2025_focus_teams.md の優勝との差列。meet_records ボードではない",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_2024_2025_focus_teams.md",
            "source:out/analysis/aragyoku-teams/岱明.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "菊水の荒玉駅伝の1区は誰？",
        "out/analysis/aragyoku-teams/菊水.md を正本（区間選手）。OCR 散発ヒットにしない",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku-teams/菊水.md",
            "source:out/analysis/aragyoku-teams/INDEX.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "選手は何区を走った？",
        "大会名なしの区間は荒玉チーム正本。スタートリストや通信陸上の出走表ではない",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_2024_2025_focus_teams.md",
            "source:out/analysis/aragyoku-teams/INDEX.md",
            "corpus:out-analysis",
            "corpus:aragyoku",
        ],
    ),
    (
        "〇〇中の荒玉駅伝の過去の順位は？",
        "out/analysis/aragyoku-teams/{チーム}.md。玉名付属=玉高附属。区間選手も含む",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku-teams/INDEX.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "金栗PROJECT所属選手の全記録",
        "out/analysis/arato-tamana-teams/金栗PROJECT.md。駅伝開催要項フォルダは使わない",
        [
            "topic:athlete_records",
            "source:out/analysis/arato-tamana-teams/金栗PROJECT.md",
            "source:out/analysis/arato-tamana-teams/INDEX.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "南関中の所属選手の記録一覧",
        "out/analysis/arato-tamana-teams/南関中.md の所属別全記録",
        [
            "topic:athlete_records",
            "source:out/analysis/arato-tamana-teams/南関中.md",
            "source:out/analysis/arato-tamana-teams/INDEX.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "岱明のトラック1周は？",
        "practice/daiming-practice-menus-kpace.md と docs/data-model.md。1周=560m。LINE 会話は使わない",
        [
            "topic:practice",
            "source:out/daiming-practice-menus-kpace.md",
            "source:docs/data-model.md",
            "corpus:practice",
        ],
    ),
    (
        "去年の荒玉駅伝の優勝校は？",
        "相対年を西暦に展開し aragyoku/winners-by-year.md（優勝+準優勝）と transcripts/{year}-*.json の rank=1/2 を読む",
        [
            "topic:ekiden",
            "corpus:aragyoku",
            "source:input/idaten-corpus/aragyoku/winners-by-year.md",
            "source:out/analysis/aragyoku-overview.md",
        ],
    ),
    (
        "荒玉駅伝のコース動画は？",
        "aragyoku/course-videos.md の Google ドライブフォルダ URL を返す（確定回答）",
        [
            "topic:ekiden",
            "corpus:aragyoku",
            "source:input/aragyoku/course-videos.md",
            "source:input/idaten-corpus/aragyoku/course-videos.md",
        ],
    ),
    (
        "2025年の荒玉駅伝の区間賞の名前と学年は？",
        "aragyoku_leg_awards.md の2025年男女セクション（区間賞＝split_rank1）。大会記録ボードとは別",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_leg_awards.md",
            "corpus:out-analysis",
            "corpus:aragyoku",
        ],
    ),
    (
        "荒玉駅伝の区間賞は誰？",
        "aragyoku_leg_awards.md を正本（当日区間賞・学年・所属）。meet_records の歴代区間記録とは別",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_leg_awards.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "男子1位の平均ペースは？",
        "aragyoku_all_teams_average_pace.md の順位別歴代平均ペース（男子）。距離定義で総合÷総距離",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_all_teams_average_pace.md",
            "source:out/analysis/aragyoku_top6_historical_average_pace.md",
            "source:docs/aragyoku-ekiden-distance-definitions.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "荒玉駅伝の平均ペースは？",
        "全チーム版 aragyoku_all_teams_average_pace.md を正本。上位6位要約は top6_historical_average_pace.md",
        [
            "topic:ekiden",
            "source:out/analysis/aragyoku_all_teams_average_pace.md",
            "source:out/analysis/aragyoku_top6_historical_average_pace.md",
            "source:out/analysis/aragyoku-overview.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "女子の荒玉駅伝の過去5年間の優勝校、準優勝校は？",
        "winners-by-year.md の「女子・直近5年」表（優勝+準優勝）。回数集計の top2_finish_counts だけでは年度別準優勝が欠ける",
        [
            "topic:ekiden",
            "corpus:aragyoku",
            "source:input/idaten-corpus/aragyoku/winners-by-year.md",
            "source:out/analysis/aragyoku_top2_finish_counts.md",
        ],
    ),
    (
        "荒玉駅伝の優勝校は？",
        "aragyoku/winners-by-year.md（年度別優勝・準優勝）と transcripts の teams[rank=1/2]、ekiden-ocr 該当年",
        [
            "topic:ekiden",
            "corpus:aragyoku",
            "source:input/idaten-corpus/aragyoku/winners-by-year.md",
            "source:out/analysis/aragyoku-overview.md",
        ],
    ),
    (
        "荒玉駅伝の準優勝校は？",
        "winners-by-year.md の準優勝校列（rank=2）。top2_finish_counts は回数集計のみで年度一覧には使わない",
        [
            "topic:ekiden",
            "corpus:aragyoku",
            "source:input/idaten-corpus/aragyoku/winners-by-year.md",
        ],
    ),
    (
        "荒玉駅伝の過去の優勝校を全て提示して",
        "「全て提示」系は winners-by-year.md 正本を全文寄りで渡す（OCR/focus 分析に散らさない）",
        [
            "topic:ekiden",
            "corpus:aragyoku",
            "source:input/idaten-corpus/aragyoku/winners-by-year.md",
        ],
    ),
    (
        "全チームの平均ペースを全て提示して",
        "aragyoku_all_teams_average_pace.md を文書順で網羅取得（BM25 散発ヒットにしない）",
        [
            "topic:ekiden",
            "corpus:out-analysis",
            "source:out/analysis/aragyoku_all_teams_average_pace.md",
            "source:docs/aragyoku-ekiden-distance-definitions.md",
        ],
    ),
    (
        "荒玉駅伝の区間距離は？",
        "docs/aragyoku-ekiden-distance-definitions.md の年度別・男女別区間距離定義を優先する",
        [
            "topic:ekiden",
            "source:docs/aragyoku-ekiden-distance-definitions.md",
            "source:out/analysis/aragyoku-overview.md",
            "corpus:aragyoku",
        ],
    ),
    (
        "なごみ駅伝は？",
        "drive-text/大会/*/0920_*なごみ* または 0921_*なごみ* の開催要項・結果・区間オーダーを見る。"
        "2026年度は女子成績表.md / 男子成績表.md / 予実比較.md。"
        "2025年度は同名＋予実比較.md。"
        "ギャップ分析 HTML は out/analysis/nagomi_sb_gap_analysis.html。"
        "金栗駅伝・金栗記念は別大会。荒玉・aragyoku は使わない",
        [
            "topic:ekiden",
            "topic:calendar",
            "corpus:drive-text",
            "corpus:calendar",
            "corpus:out-analysis",
            "source:input/events.2026.yaml",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/女子成績表.md",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/男子成績表.md",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/予実比較.md",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/男子区間オーダーリスト.md",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/女子区間オーダーリスト.md",
            "source:input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/女子成績表.md",
            "source:input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/男子成績表.md",
            "source:input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/予実比較.md",
            "source:out/analysis/nagomi_sb_gap_analysis.html",
        ],
    ),
    (
        "2026年のなごみ駅伝の結果は？",
        "drive-text/大会/2026年度/0920_*なごみ*/女子成績表.md と 男子成績表.md を見る。"
        "予実比較.md / out/analysis/nagomi_sb_gap_analysis.html で SB 予想との差を見る。"
        "優勝は女子金栗PROJECT A（26:55）・男子NJAC（38:33）。岱明は女子A6位・男子A18位。",
        [
            "topic:ekiden",
            "corpus:drive-text",
            "corpus:out-analysis",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/女子成績表.md",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/男子成績表.md",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/成績表.json",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/予実比較.md",
            "source:out/analysis/nagomi_sb_gap_analysis.html",
        ],
    ),
    (
        "なごみ駅伝の予想と実績の差は？",
        "out/analysis/nagomi_sb_gap_analysis.html と各年度 予実比較.md を見る。"
        "差=実績−予想。5段階（大きく／少し上回った・妥当・少し／大きく下回った、ADR 052）。"
        "荒尾玉名関連は女子個人上位5・男子上位6と関連チーム表あり。",
        [
            "topic:ekiden",
            "corpus:out-analysis",
            "corpus:drive-text",
            "source:out/analysis/nagomi_sb_gap_analysis.html",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/予実比較.md",
            "source:input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/予実比較.md",
            "source:docs/adr/052-nagomi-sb-gap-analysis.md",
        ],
    ),
    (
        "2025年のなごみ駅伝の結果は？",
        "drive-text/大会/2025年度/0921_*なごみ*/女子成績表.md と 男子成績表.md を見る。予実比較.md はレース前SB予想との差。",
        [
            "topic:ekiden",
            "corpus:drive-text",
            "source:input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/女子成績表.md",
            "source:input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/男子成績表.md",
            "source:input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/予実比較.md",
            "source:input/idaten-corpus/drive-text/大会/2025年度/0921_中学駅伝金栗四三生誕の地なごみ大会/岱明の結果.md",
        ],
    ),
    (
        "なごみ駅伝の区間オーダーは？",
        "drive-text/大会/2026年度/0920_*なごみ*/男子区間オーダーリスト.md と 女子区間オーダーリスト.md を優先。"
        "金栗駅伝・金栗記念は別大会。荒玉は使わない",
        [
            "topic:ekiden",
            "corpus:drive-text",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/男子区間オーダーリスト.md",
            "source:input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/女子区間オーダーリスト.md",
        ],
    ),
    (
        "ジュニア駅伝の結果は？",
        "drive-text/大会/*/*ジュニア駅伝*/岱明の結果.md および 結果_*.pdf.md を見る。"
        "荒玉・aragyoku・ekiden-ocr は別大会なので選ばない",
        [
            "topic:ekiden",
            "topic:calendar",
            "corpus:drive-text",
        ],
    ),
    (
        "去年のジュニア駅伝の岱明の結果は？",
        "相対年を西暦に展開し drive-text/大会/{year}年度/*ジュニア*/岱明の結果.md を優先。"
        "荒玉優勝校・transcripts は使わない",
        [
            "topic:ekiden",
            "topic:calendar",
            "corpus:drive-text",
        ],
    ),
    (
        "部員名簿は？",
        "Notion いだてん岱明生徒 DB と Drive 名簿 CSV（コーパス notion-db/いだてん岱明生徒）",
        [
            "topic:athlete_records",
            "topic:practice",
            "corpus:notion-db",
            "source:input/idaten-corpus/notion-db/いだてん岱明生徒",
            "source:input/external/notion/databases/いだてん岱明生徒/rows.json",
            "source:input/external/drive/shared/名簿/2025年度_岱明中学校陸上競技部_部員名簿.csv",
        ],
    ),
    (
        "中学生SBは？",
        "コーパス sb/ と input/external/sb/middle-school/ を見る",
        [
            "topic:athlete_records",
            "corpus:sb",
            "source:input/external/sb/middle-school/wide/中学生SB.csv",
            "source:input/external/sb/middle-school/INDEX.md",
            "source:docs/adr/012-middle-school-sb-all-years.md",
        ],
    ),
    (
        "開催要項は？",
        "drive-text/大会/ 各大会フォルダの開催要項.md を見る（大会名でフォルダを特定）",
        [
            "topic:ekiden",
            "corpus:drive-text",
        ],
    ),
    (
        "ケガ・障害は？",
        "injury トピックと Notion 怪我について・RRI メモ",
        [
            "topic:injury",
            "corpus:notion-db",
            "source:input/memos/rri_healing_evidence_review.md",
            "source:input/external/notion/INDEX.md",
        ],
    ),
    (
        "オーダー・区間は？",
        "荒玉の区間・オーダーなら荒玉戦略 Notion・分析 OCR・歴代 OCR。"
        "なごみなら該大会フォルダの区間オーダーリスト（金栗駅伝は別）。ジュニアは該大会フォルダ",
        [
            "topic:ekiden",
            "topic:athlete_records",
            "source:out/analysis/aragyoku-overview.md",
            "source:docs/aragyoku-ekiden-distance-definitions.md",
            "corpus:aragyoku",
            "corpus:drive-text",
            "corpus:analysis-ocr",
        ],
    ),
    (
        "銀マット・合同練習・保護者連絡は？",
        "out/analysis/line-chats（parents/staff）を優先。カレンダーに無い一次連絡が多い",
        [
            "topic:practice",
            "topic:calendar",
            "source:out/analysis/line-chats/daiming-parents.md",
            "source:out/analysis/line-chats/daiming-staff.md",
            "source:out/analysis/line-chats/INDEX.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "有田先輩の練習・補強の考え方は？",
        "out/analysis/line-chats/arita-taisho.md（分割走・補強・厚底・荒玉目安・合同練習）",
        [
            "topic:practice",
            "topic:ekiden",
            "source:out/analysis/line-chats/arita-taisho.md",
            "source:out/analysis/line-chats/INDEX.md",
            "corpus:out-analysis",
        ],
    ),
    (
        "玉名の天気データはどう更新する？",
        "docs/tamana-weather.md（Open-Meteo・tamana-forecast・更新間隔）",
        [
            "topic:meta",
            "topic:calendar",
            "source:docs/tamana-weather.md",
            "corpus:repo-docs",
        ],
    ),
]

# Explicit Topic → corpus hub links that auto topic-tagging can miss.
TOPIC_CORPUS_HUBS: list[tuple[str, str]] = [
    ("topic:norwegian", "corpus:repo-docs"),
    ("topic:norwegian", "corpus:practice"),
    ("topic:norwegian", "corpus:notion-pages"),
    ("topic:pace", "corpus:practice"),
    ("topic:pace", "corpus:repo-docs"),
    ("topic:pace", "corpus:out-analysis"),
    ("topic:practice", "corpus:out-analysis"),
    ("topic:meta", "corpus:docs"),
    ("topic:meta", "corpus:repo-docs"),
    ("topic:injury", "corpus:notion-pages"),
    ("topic:ekiden", "corpus:out-analysis"),
    ("topic:calendar", "corpus:out-analysis"),
    ("topic:athlete_records", "corpus:out-analysis"),
    ("topic:athlete_records", "corpus:sb"),
    ("topic:practice", "corpus:practice"),
]

# Team digest filenames → spoken aliases (hints + scoring).
ANALYSIS_TEAM_ALIASES: dict[str, list[str]] = {
    "玉高附属": ["玉名付属", "玉名附属", "付属中", "玉名高校附属", "玉名附中", "玉名附"],
    "岱明": ["岱明中", "いだてん岱明"],
    "岱明中": ["岱明"],
    "天水": ["天水中"],
    "天水中": ["天水"],
    "有明": ["有明中"],
    "南関": ["南関中"],
    "南関中": ["南関"],
    "菊水": ["菊水中"],
    "長洲": ["長洲中"],
    "長洲中": ["長洲"],
    "金栗PROJECT": ["金栗プロジェクト"],
}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _dedupe_preserve(items: Iterable[str]) -> list[str]:
    """Unique while keeping first-seen order (preferred refs must stay early)."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _node(
    node_id: str,
    node_type: str,
    label: str,
    *,
    topics: Iterable[str] = (),
    refs: Iterable[str] = (),
    hint: str = "",
) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "label": label,
        "topics": sorted(set(topics)),
        "refs": _dedupe_preserve(refs),
        "hint": hint,
    }


def _edge(frm: str, to: str, rel: str) -> dict[str, str]:
    return {"from": frm, "to": to, "rel": rel}


def _add_node(nodes: dict[str, dict[str, Any]], node: dict[str, Any]) -> None:
    existing = nodes.get(node["id"])
    if existing is None:
        nodes[node["id"]] = node
        return
    existing["topics"] = sorted(set(existing["topics"]) | set(node["topics"]))
    existing["refs"] = _dedupe_preserve([*existing["refs"], *node["refs"]])
    if node["hint"] and (not existing["hint"] or len(node["hint"]) > len(existing["hint"])):
        existing["hint"] = node["hint"]


def _add_edge(edges: set[tuple[str, str, str]], frm: str, to: str, rel: str) -> None:
    if frm == to:
        return
    edges.add((frm, to, rel))


def _discover_years() -> list[int]:
    years: list[int] = []
    for path in sorted((ROOT / "input").glob("events.*.yaml")):
        m = re.fullmatch(r"events\.(\d{4})\.yaml", path.name)
        if m:
            years.append(int(m.group(1)))
    return years


def _source_id(rel_path: str) -> str:
    return f"source:{rel_path}"


def _register_source(
    nodes: dict[str, dict[str, Any]],
    edges: set[tuple[str, str, str]],
    rel_path: str,
    *,
    topics: list[str],
    hint: str,
    derived_from: str | None = None,
    label: str | None = None,
) -> str:
    sid = _source_id(rel_path)
    _add_node(
        nodes,
        _node(
            sid,
            "Source",
            label if label else Path(rel_path).name,
            topics=topics,
            refs=[rel_path],
            hint=hint,
        ),
    )
    if label:
        nodes[sid]["label"] = label
    for topic in topics:
        _add_edge(edges, f"topic:{topic}", sid, "search_here")
    if derived_from:
        _add_edge(edges, sid, derived_from, "derived_from")
    return sid


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _athlete_key(name: str) -> str:
    name = name.strip()
    # Prefer family-name-ish short forms already used in absentees
    return name


def _collect_athletes_from_absentees(year: int) -> set[str]:
    path = ROOT / "out" / str(year) / "practice_absentees.csv"
    names: set[str] = set()
    if not path.exists():
        return names
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = (row.get("name") or "").strip()
            if name:
                names.add(_athlete_key(name))
    return names


def _collect_athletes_from_events(year: int) -> set[str]:
    path = ROOT / "input" / f"events.{year}.yaml"
    data = _load_yaml(path)
    names: set[str] = set()
    if not isinstance(data, dict):
        return names
    for ev in data.get("events") or []:
        practice = ev.get("practice") or {}
        for name in practice.get("absentees") or []:
            if isinstance(name, str) and name.strip():
                names.add(_athlete_key(name.strip()))
    return names


def _collect_athletes_from_records(path: Path) -> dict[str, dict[str, Any]]:
    """Return mapping short/full name -> sample affiliation info."""
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    by_name: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return by_name
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = (row.get("name") or "").strip()
        if not name:
            continue
        aff = (row.get("affiliation") or "").strip()
        # Keep 岱明関連を優先してヒント化
        if name not in by_name or ("岱明" in aff and "岱明" not in (by_name[name].get("affiliation") or "")):
            by_name[name] = {
                "affiliation": aff,
                "grade": row.get("grade"),
                "gender": row.get("gender"),
            }
    return by_name


def _templates() -> list[dict[str, Any]]:
    data = _load_yaml(ROOT / "input" / "practice_templates.yaml")
    if not isinstance(data, dict):
        return []
    return list(data.get("templates") or [])


def _tags_from_events(year: int) -> set[str]:
    path = ROOT / "input" / f"events.{year}.yaml"
    data = _load_yaml(path)
    tags: set[str] = set()
    if not isinstance(data, dict):
        return tags
    for ev in data.get("events") or []:
        raw = ev.get("tags") or []
        if isinstance(raw, str):
            raw = [t.strip() for t in raw.split(",") if t.strip()]
        for tag in raw:
            if isinstance(tag, str) and tag.strip():
                tags.add(tag.strip())
    return tags


def _peek_text_summary(path: Path, *, max_chars: int = 220) -> str:
    """First meaningful lines of a text file for KG hints (what is written there)."""
    if not path.is_file():
        return ""
    if path.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"}:
        return path.name
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("---"):
            continue
        lines.append(s.lstrip("#").strip())
        if sum(len(x) for x in lines) >= max_chars:
            break
    joined = " / ".join(lines)
    return joined[:max_chars]


def _register_idaten_corpus(
    nodes: dict[str, dict[str, Any]],
    edges: set[tuple[str, str, str]],
) -> None:
    """
    Register LINE corpus hubs + meet folders with content hints so KG routing
    knows *what is written where* (input/idaten-corpus/).
    """
    corpus = ROOT / "input" / "idaten-corpus"
    if not corpus.is_dir():
        return

    index = corpus / "INDEX.md"
    if index.exists():
        _register_source(
            nodes,
            edges,
            _rel(index),
            topics=["meta", "calendar", "practice", "ekiden", "athlete_records"],
            hint="いだてん岱明コーパス目録（LINE Q&A 参照範囲）: " + _peek_text_summary(index, max_chars=180),
        )

    dir_specs: list[tuple[str, list[str], str]] = [
        ("ekiden-ocr", ["ekiden", "athlete_records"], "荒玉駅伝歴代の OCR 本文（年×男女）"),
        ("aragyoku", ["ekiden", "athlete_records"], "荒玉駅伝の構造化 JSON/MD・transcripts・winners-by-year・course-videos"),
        ("analysis-ocr", ["ekiden", "athlete_records"], "分析 PDF の OCR（所属ランキング等）"),
        ("out-analysis", ["ekiden", "athlete_records", "analysis", "practice", "pace", "calendar"], "out/analysis の md/json（ペース分析・LINE 衛生化・関係図など）"),
        ("repo-docs", ["schema", "meta", "ai"], "docs/ 配下の Markdown（ADR・データモデル等）"),
        ("calendar", ["calendar", "practice"], "岱明フィルタ済み events.daiming.yaml"),
        ("practice", ["practice"], "練習 JSON / menus / absentees 抜粋"),
        ("sb", ["athlete_records"], "中学生 SB（全所属・wide CSV 行単位）"),
        ("notion-db", ["practice", "athlete_records", "ekiden", "injury"], "Notion DB スナップショット"),
        ("notion-pages", ["practice", "meta"], "Notion ページ Markdown"),
        ("drive-text", ["ekiden", "practice", "calendar", "athlete_records"], "Drive テキスト（大会・記録データベース・個人メモ）"),
        ("docs", ["ekiden", "schema", "meta"], "関連 ADR・区間距離定義のコピー"),
    ]
    for dirname, topics, base_hint in dir_specs:
        dpath = corpus / dirname
        if not dpath.is_dir():
            continue
        rel = _rel(dpath)
        # Count text-ish children for hint richness
        children = [p.name for p in sorted(dpath.iterdir()) if not p.name.startswith(".")][:12]
        hint = f"{base_hint}. 例: {', '.join(children)}"
        eid = f"corpus:{dirname}"
        _add_node(
            nodes,
            _node(
                eid,
                "Entity",
                f"コーパス/{dirname}",
                topics=topics,
                refs=[rel, f"input/idaten-corpus/{dirname}"],
                hint=hint,
            ),
        )
        for t in topics:
            _add_edge(edges, f"topic:{t}", eid, "search_here")
        # Also register as Source for path scoring
        _register_source(
            nodes,
            edges,
            f"input/idaten-corpus/{dirname}",
            topics=topics,
            hint=hint,
        )

    # Notion DB folders with content peek
    notion_db = corpus / "notion-db"
    if notion_db.is_dir():
        for sub in sorted(notion_db.iterdir()):
            if not sub.is_dir():
                continue
            rows = sub / "rows.json"
            hint = f"Notion DB「{sub.name}」"
            if rows.exists():
                hint += ": " + _peek_text_summary(rows, max_chars=160)
            topics = ["athlete_records", "practice"]
            if "駅伝" in sub.name or "荒玉" in sub.name:
                topics = ["ekiden", "athlete_records"]
            if "怪我" in sub.name or "ケガ" in sub.name:
                topics = ["injury"]
            if "生徒" in sub.name or "名簿" in sub.name:
                topics = ["practice", "athlete_records"]
            _register_source(
                nodes,
                edges,
                _rel(sub),
                topics=topics,
                hint=hint,
            )
            # Prefer rows.json as concrete ref
            if rows.exists():
                _register_source(
                    nodes,
                    edges,
                    _rel(rows),
                    topics=topics,
                    hint=hint,
                )

    # Meet / race folders under drive-text/大会
    taikai_root = corpus / "drive-text" / "大会"
    if taikai_root.is_dir():
        _register_source(
            nodes,
            edges,
            _rel(taikai_root / "INDEX.md") if (taikai_root / "INDEX.md").exists() else _rel(taikai_root),
            topics=["ekiden", "calendar"],
            hint="大会フォルダ目録（年度別・開催要項・結果の入口）: "
            + _peek_text_summary(taikai_root / "INDEX.md", max_chars=160),
        )
        for year_dir in sorted(taikai_root.glob("*年度")):
            if not year_dir.is_dir():
                continue
            year_label = year_dir.name
            for meet_dir in sorted(year_dir.iterdir()):
                if not meet_dir.is_dir():
                    continue
                name = meet_dir.name
                files = sorted(
                    p.name
                    for p in meet_dir.iterdir()
                    if p.is_file() and not p.name.endswith(".meta.json")
                )
                summary_bits: list[str] = []
                for prefer in (
                    "岱明の結果.md",
                    "女子成績表.md",
                    "男子成績表.md",
                    "成績表.json",
                    "開催要項.md",
                    "開催要項.pdf.md",
                ):
                    cand = meet_dir / prefer
                    if cand.exists():
                        summary_bits.append(_peek_text_summary(cand, max_chars=140))
                        break
                if not summary_bits and files:
                    first_md = next((meet_dir / f for f in files if f.endswith(".md")), None)
                    if first_md and first_md.exists():
                        summary_bits.append(_peek_text_summary(first_md, max_chars=120))
                mmdd = ""
                m = re.match(r"^(\d{4})", name)
                if m:
                    mmdd = m.group(1)
                meet_topics = ["ekiden", "calendar"]
                if "ジュニア" in name:
                    meet_topics.append("junior_ekiden")
                elif "なごみ" in name or "金栗" in name:
                    meet_topics.append("nagomi")
                elif "荒玉" in name or "中体連" in name:
                    meet_topics.append("aragyoku")
                hint = (
                    f"{year_label} 大会「{name}」。"
                    + (f"日付キー MMDD={mmdd}。" if mmdd else "")
                    + f"ファイル: {', '.join(files[:8])}。"
                    + (" 内容: " + " ".join(summary_bits) if summary_bits else "")
                )
                refs = [_rel(meet_dir)]
                # Prefer result files early in refs for result-oriented Q&A
                preferred_files = [
                    f
                    for f in files
                    if f == "岱明の結果.md"
                    or f in {
                        "女子成績表.md",
                        "男子成績表.md",
                        "成績表.json",
                        "女子成績表.pdf",
                        "男子成績表.pdf",
                    }
                    or f.startswith("結果_")
                    or ("岱明" in f and "結果" in f and f.endswith(".md"))
                ]
                other_files = [f for f in files if f not in preferred_files]
                for f in (preferred_files + other_files)[:12]:
                    refs.append(_rel(meet_dir / f))
                mid = f"meet:{year_label}:{name[:48]}"
                _add_node(
                    nodes,
                    _node(
                        mid,
                        "Entity",
                        name,
                        topics=meet_topics,
                        refs=refs,
                        hint=hint[:500],
                    ),
                )
                _add_edge(edges, "topic:ekiden", mid, "search_here")
                _add_edge(edges, "topic:calendar", mid, "see_also")
                # Link year entity if present
                ym = re.search(r"(20\d{2})", year_label)
                if ym:
                    _add_edge(edges, f"entity:year:{ym.group(1)}", mid, "see_also")


def _analysis_topics(path: Path) -> list[str]:
    rel = path.as_posix()
    parent = path.parent.name
    name = path.name
    if parent == "line-chats":
        return ["practice", "calendar"]
    if parent == "arato-tamana-teams" or parent == "athletes":
        return ["athlete_records"]
    if "pb_school" in name or "_sb_" in name:
        return ["athlete_records"]
    if parent == "aragyoku-teams" or "aragyoku" in name:
        return ["ekiden", "athlete_records"]
    if "line-chats" in rel:
        return ["practice", "calendar"]
    return ["ekiden", "athlete_records"]


def _register_analysis_digests(
    nodes: dict[str, dict[str, Any]],
    edges: set[tuple[str, str, str]],
) -> None:
    """Register out/analysis markdown digests so KG can 0-hop to exact team/ranking files."""
    analysis = ROOT / "out" / "analysis"
    if not analysis.is_dir():
        return
    team_parents = {"aragyoku-teams", "arato-tamana-teams"}
    for path in sorted(analysis.rglob("*.md")):
        rel = _rel(path)
        parent = path.parent.name
        is_team = parent in team_parents and path.stem != "INDEX"
        aliases = ANALYSIS_TEAM_ALIASES.get(path.stem, [])
        peek = _peek_text_summary(path, max_chars=200)
        hint_bits: list[str] = []
        if aliases:
            hint_bits.append("別名: " + "、".join(aliases))
        if is_team and parent == "aragyoku-teams":
            hint_bits.append("荒玉駅伝チーム別歴代（区間選手・順位）")
        elif is_team:
            hint_bits.append("荒尾玉名の所属別トラック全記録")
        if peek:
            hint_bits.append(peek)
        hint = "。".join(hint_bits) if hint_bits else path.name
        label = path.stem if is_team else None
        sid = _source_id(rel)
        if sid not in nodes:
            _register_source(
                nodes,
                edges,
                rel,
                topics=_analysis_topics(path),
                hint=hint,
                label=label,
            )
        else:
            if label:
                nodes[sid]["label"] = label
            existing_hint = nodes[sid].get("hint") or ""
            for extra in hint_bits:
                if extra and extra not in existing_hint:
                    existing_hint = extra + "。" + existing_hint
            nodes[sid]["hint"] = existing_hint
        if aliases:
            alias_blob = "、".join(aliases)
            if alias_blob not in (nodes[sid].get("hint") or ""):
                nodes[sid]["hint"] = f"別名: {alias_blob}。" + (nodes[sid].get("hint") or "")


def _register_external_media(
    nodes: dict[str, dict[str, Any]],
    edges: set[tuple[str, str, str]],
) -> None:
    """Register MediaAsset nodes from media-manifest so LLMs can follow local paths."""
    manifest_path = ROOT / "input" / "external" / "media-manifest.json"
    if not manifest_path.exists():
        return
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return

    for item in items:
        if not isinstance(item, dict):
            continue
        topic = str(item.get("topic") or "meta")
        topics = [topic]
        if topic == "ekiden":
            topics.append("athlete_records")
        elif topic == "analysis":
            topics.extend(["ekiden", "athlete_records"])
        elif topic == "photo":
            topics.append("practice")

        stem = str(item.get("stem") or "media")
        local = item.get("local_path")
        ocr = item.get("ocr_path")
        binary = bool(item.get("binary_saved"))
        refs: list[str] = []
        for candidate in (local, ocr, item.get("meta_path")):
            if not candidate:
                continue
            p = Path(str(candidate))
            if p.is_absolute():
                try:
                    refs.append(p.resolve().relative_to(ROOT.resolve()).as_posix())
                except ValueError:
                    refs.append(p.as_posix())
            else:
                refs.append(p.as_posix())
        if not refs:
            continue
        # Prefer OCR / readable path in hint
        ocr_rel = None
        if ocr:
            op = Path(str(ocr))
            try:
                ocr_rel = (
                    op.resolve().relative_to(ROOT.resolve()).as_posix()
                    if op.is_absolute()
                    else op.as_posix()
                )
            except ValueError:
                ocr_rel = op.as_posix()
        hint_bits = [
            f"topic={topic}",
            "binary=yes" if binary else "binary=pending",
        ]
        if ocr_rel:
            hint_bits.append(f"ocr={ocr_rel}")
        if item.get("notion_page_url"):
            hint_bits.append("notion添付あり")
        label = stem
        if item.get("year") and item.get("gender"):
            label = f"荒玉駅伝 {item['year']} {item['gender']}"
        elif topic == "analysis":
            label = f"分析 {stem}"
        elif topic == "photo":
            label = f"フォト {item.get('event_folder') or ''}/{stem}".strip("/")

        mid = f"media:{topic}:{stem}"
        _add_node(
            nodes,
            _node(
                mid,
                "MediaAsset",
                label,
                topics=topics,
                refs=refs,
                hint="; ".join(hint_bits),
            ),
        )
        for t in topics:
            _add_edge(edges, f"topic:{t}", mid, "search_here")
        # Point MediaAsset at the manifest / INDEX hubs (avoid exploding Source nodes per photo)
        if "source:input/external/media-manifest.json" in nodes:
            _add_edge(edges, mid, "source:input/external/media-manifest.json", "documented_in")
        if topic == "ekiden" and "source:input/external/notion/media/ekiden-history/INDEX.md" in nodes:
            _add_edge(edges, mid, "source:input/external/notion/media/ekiden-history/INDEX.md", "see_also")
        if topic == "ekiden" and "source:input/external/notion/databases/荒玉中体連駅伝歴代/rows.json" in nodes:
            _add_edge(edges, mid, "source:input/external/notion/databases/荒玉中体連駅伝歴代/rows.json", "derived_from")


def build_knowledge_graph(*, generated_at: str | None = None) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: set[tuple[str, str, str]] = set()
    years = _discover_years()

    for topic_id, label, hint in TOPIC_DEFS:
        _add_node(
            nodes,
            _node(f"topic:{topic_id}", "Topic", label, topics=[topic_id], hint=hint),
        )

    # Static high-value sources
    for rel, topics, hint in SOURCE_GLOBS:
        path = ROOT / rel
        if path.exists():
            _register_source(nodes, edges, rel, topics=topics, hint=hint)

    # Docs ADR
    adr_dir = ROOT / "docs" / "adr"
    if adr_dir.exists():
        for path in sorted(adr_dir.glob("*.md")):
            rel = _rel(path)
            sid = _register_source(
                nodes,
                edges,
                rel,
                topics=["ai", "practice", "meta"],
                hint=f"ADR: {path.stem}",
            )
            _add_edge(edges, "source:docs/ai-practice-generation.md", sid, "see_also")

    # Prompts
    prompts_dir = ROOT / "prompts"
    if prompts_dir.exists():
        for path in sorted(prompts_dir.iterdir()):
            if path.is_file() and path.suffix in {".md", ".yaml", ".yml"}:
                rel = _rel(path)
                _register_source(
                    nodes,
                    edges,
                    rel,
                    topics=["ai", "practice"],
                    hint=f"LLM プロンプト / few-shot: {path.name}",
                )

    # Schemas
    schemas_dir = ROOT / "schemas"
    if schemas_dir.exists():
        for path in sorted(schemas_dir.glob("*.json")):
            rel = _rel(path)
            _register_source(
                nodes,
                edges,
                rel,
                topics=["schema"],
                hint=f"JSON Schema: {path.name}",
            )

    # Memos
    memos_dir = ROOT / "input" / "memos"
    if memos_dir.exists():
        for path in sorted(memos_dir.rglob("*")):
            if not path.is_file():
                continue
            rel = _rel(path)
            topics = ["meta"]
            hint = f"メモ素材: {path.name}"
            lower = path.name.lower()
            if "norwegian" in lower:
                topics = ["norwegian", "practice", "pace"]
                hint = "Norwegian Method 原典メモ"
            elif "rri" in lower or "heal" in lower or "injur" in lower:
                topics = ["injury"]
                hint = "ランニング障害・回復エビデンス"
            elif path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                topics = ["calendar", "practice"]
                hint = f"画像メモ（構造参照のみ）: {path.name}"
            _register_source(nodes, edges, rel, topics=topics, hint=hint)

    # Research projects
    research = ROOT / "projects" / "running-injury-research"
    if research.exists():
        for path in sorted(research.rglob("*.md")):
            rel = _rel(path)
            _register_source(
                nodes,
                edges,
                rel,
                topics=["injury"],
                hint=f"障害研究メモ: {path.name}",
            )

    # Year nodes + event / practice outputs
    athlete_refs: dict[str, set[str]] = defaultdict(set)
    template_ids: dict[str, str] = {}

    for tpl in _templates():
        tid = str(tpl.get("id") or "").strip()
        if not tid:
            continue
        label = str(tpl.get("label") or tid)
        template_ids[tid] = label
        nid = f"entity:template:{tid}"
        _add_node(
            nodes,
            _node(
                nid,
                "Template",
                label,
                topics=["practice", "template"],
                refs=["input/practice_templates.yaml"],
                hint=f"テンプレート ID `{tid}`",
            ),
        )
        _add_edge(edges, nid, "source:input/practice_templates.yaml", "documented_in")
        _add_edge(edges, "topic:practice", nid, "related_to")

    for year in years:
        yid = f"entity:year:{year}"
        _add_node(
            nodes,
            _node(
                yid,
                "Year",
                f"{year}年",
                topics=["calendar", "practice"],
                refs=[f"input/events.{year}.yaml"],
                hint=f"{year} 年次カレンダーと練習のハブ",
            ),
        )

        events_yaml = f"input/events.{year}.yaml"
        if (ROOT / events_yaml).exists():
            sid = _register_source(
                nodes,
                edges,
                events_yaml,
                topics=["calendar", "practice"],
                hint=f"{year}年イベント正本（practice 含む）",
            )
            _add_edge(edges, yid, sid, "search_here")

        out_dir = ROOT / "out" / str(year)
        year_outputs = [
            ("events.json", ["calendar"], f"{year}年イベント JSON（生成物）"),
            ("practice.json", ["practice"], f"{year}年練習セッション（生成物）"),
            ("practice_items.csv", ["practice"], f"{year}年メニュー項目行"),
            ("practice_absentees.csv", ["practice", "athlete"], f"{year}年欠席者（session×選手）"),
            ("practice-summary.md", ["practice"], f"{year}年練習サマリ"),
            ("calendar.md", ["calendar"], f"{year}年 Markdown カレンダー"),
            ("source.csv", ["calendar"], f"{year}年 source CSV（軽量）"),
            ("google.csv", ["calendar"], f"{year}年 Google CSV（軽量）"),
            ("notion.csv", ["calendar"], f"{year}年 Notion CSV（軽量）"),
        ]
        for name, topics, hint in year_outputs:
            path = out_dir / name
            if not path.exists():
                continue
            rel = _rel(path)
            light = path.suffix.lower() in LIGHTWEIGHT_SUFFIXES and name.endswith(".csv")
            if light:
                hint = hint + "（派生・参照のみ）"
            sid = _register_source(
                nodes,
                edges,
                rel,
                topics=topics,
                hint=hint,
                derived_from=_source_id(events_yaml) if (ROOT / events_yaml).exists() else None,
            )
            _add_edge(edges, yid, sid, "search_here")

        for name in _collect_athletes_from_absentees(year) | _collect_athletes_from_events(year):
            athlete_refs[name].add(f"out/{year}/practice_absentees.csv")
            athlete_refs[name].add(f"input/events.{year}.yaml")

        for tag in _tags_from_events(year):
            # Keep only somewhat specific tags to avoid exploding the graph
            if tag in {"予定", "メモ", "祝日"}:
                continue
            tid = f"entity:tag:{tag}"
            _add_node(
                nodes,
                _node(
                    tid,
                    "Entity",
                    tag,
                    topics=["calendar", "practice"] if "練習" in tag or "practice" in tag else ["calendar"],
                    refs=[events_yaml],
                    hint=f"イベントタグ `{tag}`",
                ),
            )
            _add_edge(edges, tid, _source_id(events_yaml), "mentioned_in")

    # Athlete records
    records_path = ROOT / "out" / "analysis" / "notion_records_2026.json"
    record_athletes = _collect_athletes_from_records(records_path)
    if records_path.exists():
        rel = _rel(records_path)
        sid = _register_source(
            nodes,
            edges,
            rel,
            topics=["athlete_records"],
            hint="荒尾・玉名中学生記録行（Notion 由来 JSON）",
        )
        _add_edge(edges, "topic:athlete_records", sid, "search_here")

    for pdf in sorted((ROOT / "out" / "analysis").glob("*.pdf")) if (ROOT / "out" / "analysis").exists() else []:
        rel = _rel(pdf)
        _register_source(
            nodes,
            edges,
            rel,
            topics=["athlete_records"],
            hint=f"記録 PDF（参照のみ）: {pdf.name}",
        )

    # Prefer short names already used in practice; also index full record names for 岱明
    daiming_full_names = {
        name: info
        for name, info in record_athletes.items()
        if "岱明" in (info.get("affiliation") or "")
    }

    all_athlete_labels = set(athlete_refs) | set(daiming_full_names)
    # Map short absentee names to full names when unique prefix match
    for short in list(athlete_refs):
        matches = [full for full in daiming_full_names if full.startswith(short)]
        if len(matches) == 1:
            athlete_refs[short].add(_rel(records_path))
            full = matches[0]
            athlete_refs[full] |= set(athlete_refs[short]) | {_rel(records_path)}

    for name in sorted(all_athlete_labels):
        refs = set(athlete_refs.get(name, set()))
        info = record_athletes.get(name) or {}
        if records_path.exists() and (name in record_athletes or any(f.startswith(name) for f in daiming_full_names)):
            refs.add(_rel(records_path))
        aff = info.get("affiliation") or ""
        hint = f"所属:{aff}" if aff else "部員エンティティ"
        nid = f"entity:athlete:{name}"
        _add_node(
            nodes,
            _node(
                nid,
                "Athlete",
                name,
                topics=["athlete", "practice", "athlete_records"],
                refs=refs or (["out/analysis/notion_records_2026.json"] if records_path.exists() else []),
                hint=hint,
            ),
        )
        for ref in refs:
            _add_edge(edges, nid, _source_id(ref), "mentioned_in")
        _add_edge(edges, "topic:practice", nid, "related_to")
        if aff:
            _add_edge(edges, "topic:athlete_records", nid, "related_to")

    # External media (images / OCR / analysis PDFs) — paths for LLM follow-up reads
    _register_external_media(nodes, edges)

    # LINE いだてんコーパス（内容ヒント付きハブ + 大会フォルダ）
    _register_idaten_corpus(nodes, edges)

    # Generated analysis digests (team / ranking / LINE chats)
    _register_analysis_digests(nodes, edges)

    # Query hints — prefer concrete Source/corpus; attach refs for 0-hop routing
    for idx, (label, hint, targets) in enumerate(QUERY_HINTS):
        qid = f"query:{idx}:{label[:24]}"
        q_refs: list[str] = []
        q_topics: list[str] = []
        for target in targets:
            if target.startswith("topic:"):
                q_topics.append(target[len("topic:") :])
            elif target in nodes:
                for ref in nodes[target].get("refs") or []:
                    q_refs.append(ref)
        _add_node(
            nodes,
            _node(
                qid,
                "QueryHint",
                label,
                topics=q_topics,
                refs=q_refs,
                hint=hint,
            ),
        )
        for target in targets:
            if target.startswith("topic:"):
                _add_edge(edges, qid, target, "search_here")
                continue
            if target not in nodes:
                continue
            # Source docs: documented_in; corpus hubs: search_here
            rel = "documented_in" if target.startswith("source:") else "search_here"
            _add_edge(edges, qid, target, rel)

    # Topic ↔ corpus hub insurance links
    for topic_id, hub_id in TOPIC_CORPUS_HUBS:
        if topic_id in nodes and hub_id in nodes:
            _add_edge(edges, topic_id, hub_id, "search_here")

    # Cross-links
    if "source:input/daniels_vdot_paces.yaml" in nodes:
        _add_edge(
            edges,
            "topic:norwegian",
            "source:input/daniels_vdot_paces.yaml",
            "see_also",
        )
    if "source:docs/adr/008-daniels-vdot-gz-guidance.md" in nodes:
        _add_edge(
            edges,
            "topic:norwegian",
            "source:docs/adr/008-daniels-vdot-gz-guidance.md",
            "documented_in",
        )
        _add_edge(
            edges,
            "topic:pace",
            "source:docs/adr/008-daniels-vdot-gz-guidance.md",
            "documented_in",
        )
    if "source:docs/tamana-weather.md" in nodes:
        _add_edge(
            edges,
            "topic:meta",
            "source:docs/tamana-weather.md",
            "documented_in",
        )
        _add_edge(
            edges,
            "topic:calendar",
            "source:docs/tamana-weather.md",
            "see_also",
        )
    if "source:input/memos/norwegian_method_applied_full.txt" in nodes:
        _add_edge(
            edges,
            "topic:pace",
            "source:input/memos/norwegian_method_applied_full.txt",
            "documented_in",
        )

    generated = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    graph = {
        "version": 1,
        "generated_at": generated,
        "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
        "edges": [
            _edge(frm, to, rel)
            for frm, to, rel in sorted(edges)
            if frm in nodes and to in nodes
        ],
    }
    return graph


def normalize_graph_for_compare(graph: dict[str, Any]) -> dict[str, Any]:
    """Drop volatile fields for CI equality checks."""
    nodes = []
    for n in graph.get("nodes") or []:
        node = dict(n)
        if isinstance(node.get("refs"), list):
            node["refs"] = sorted(str(x) for x in node["refs"])
        if isinstance(node.get("topics"), list):
            node["topics"] = sorted(str(x) for x in node["topics"])
        nodes.append(node)
    nodes.sort(key=lambda n: str(n.get("id") or ""))
    edges = sorted(
        (dict(e) for e in (graph.get("edges") or [])),
        key=lambda e: (
            str(e.get("from") or ""),
            str(e.get("to") or ""),
            str(e.get("type") or ""),
        ),
    )
    return {
        "version": graph.get("version"),
        "nodes": nodes,
        "edges": edges,
    }


def write_knowledge_graph(
    path: Path | None = None,
    *,
    min_path: Path | None = None,
    html_path: Path | None = None,
    pdf_path: Path | None = None,
    generated_at: str | None = None,
) -> tuple[Path, Path, Path, Path, dict[str, Any]]:
    from .html_renderer import write_knowledge_graph_html
    from .pdf_renderer import write_knowledge_graph_pdf

    path = path or KG_PATH
    min_path = min_path or KG_MIN_PATH
    html_path = html_path or KG_HTML_PATH
    pdf_path = pdf_path or KG_PDF_PATH
    graph = build_knowledge_graph(generated_at=generated_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    min_path.write_text(json.dumps(graph, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    html_out = write_knowledge_graph_html(graph, html_path)
    pdf_out = write_knowledge_graph_pdf(graph, pdf_path)
    return path, min_path, html_out, pdf_out, graph
