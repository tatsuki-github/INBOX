# ADR 045: なごみ SB 予想に玉名郡ナイター更新を反映

- Status: Accepted
- Date: 2026-09-19

## Context

なごみ駅伝の区間オーダー SB / 予想（`scripts/generate_nagomi_order_sb_preview.py`）は
`2026-sb-adopted.json` と Notion を主ソースにしていた。
2026-08-29 玉名郡ナイターで SB 更新した選手が、予想に未反映のまま残っていた。

正本:

- PDF: `…/0829_玉名郡ナイター中・長距離記録会/第25回ナイター中長距離記録会_結果.pdf`
- 構造化: 同フォルダの `全結果.md`（中学生のみ。小学・高校・一般は除外。記録一覧であり、SB判定は持たない）
- 岱明メモ: `岱明の結果.md`（SB明記を含む所属別メモ）

## Decision

1. `load_sb_index()` の最終段でナイター資料を読み、**SB と明記された行だけ**を候補にする。
2. `全結果.md` のタイム一覧は SB 判定を持たないため、未注記の行（例: 増岡里俐 5:55.5）は採用しない。
3. SB明記行でも、既存同距離 SB より速い場合のみ上書きする（例: 松野凛空は既存の4:22.33を維持）。
4. 男女セクションがある資料では、指定 gender と一致する行だけを採用する。
5. 氏名ゆれは `norm_name` で吸収（空白・﨑/崎・髙/高・凜/凛・瀨/瀬 等）。
6. DNS・小学・高校一般は取り込み対象外。
7. `2026-sb-adopted.json` 本体の書き換えは本スライス外。

## Consequences

- ナイターの生タイムを誤ってSB扱いせず、SB明記された更新だけをなごみ予想に反映する。
- PDF → 構造化: `python scripts/extract_tamana_nighter_results.py`
- 再生成: `python scripts/generate_nagomi_order_sb_preview.py`
