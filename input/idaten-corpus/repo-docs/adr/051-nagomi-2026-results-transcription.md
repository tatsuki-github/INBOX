# ADR 051: 2026 なごみ駅伝成績表の文字起こし

- Status: Accepted
- Date: 2026-09-21
- Updated: 2026-09-21（カレンダー同期）

## Context

2026-09-20 開催の第12回なごみ大会の成績表写真（女子1枚・男子2枚）が提供された。
2026-09-21、同じ成績表のPDF（女子2ページ・男子2ページ）が追加提供され、既存転記の検証原本とした。
ナレッジには区間オーダーと SB 予想はあるが、実績成績表が未登録だった。
また 2025 なごみは `events.2025.yaml` に岱明結果が入っている一方、
2026 は開催要項のまま `status: scheduled` だった。

## Decision

1. 構造化正本を `scripts/nagomi_2026_results_data.py` に置く。
2. `scripts/generate_nagomi_2026_results.py` で `女子成績表.md` / `男子成績表.md` / `成績表.json`
   を Drive と `idaten-corpus/drive-text` へ dual-write する。
3. 原本PDFは同フォルダに `女子成績表.pdf` / `男子成績表.pdf`、既存の原本写真も併存させる。
4. 氏名は成績表を優先し、2026-09-18 区間オーダーと突合して正規化する。
5. 通過記録の加算整合（区間合計＝通過）を生成時に検証する。今回のPDF全4ページは目視照合し、順位・区間タイム・氏名を校正した。
6. **同じ生成でカレンダーも更新する**: `scripts/nagomi_calendar_sync.py` が
   `input/events.2026.yaml` のなごみイベントを `status: done` にし、
   description 先頭に【結果（岱明）】＋成績表パスを載せる（開催要項は残す）。
7. 続けて `python3 scripts/generate_calendar.py --year 2026` で out/KG を更新する。

## Consequences

- KG QueryHint「2026年のなごみ駅伝の結果は？」を追加。
- 「ナレッジに追加」＝成績表＋カレンダー＋カレンダー再生成、がなごみ2026の手順になる（AGENTS.md）。
- 予実比較（SB予想 vs 実績）は本 ADR のスコープ外（必要なら別スライス）。
- 再生成: `python3 scripts/generate_nagomi_2026_results.py` → `python3 scripts/generate_calendar.py --year 2026`
