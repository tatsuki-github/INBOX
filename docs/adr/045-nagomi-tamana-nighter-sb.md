# ADR 045: なごみ SB 予想に玉名郡ナイター更新を反映

- Status: Accepted
- Date: 2026-09-19

## Context

なごみ駅伝の区間オーダー SB / 予想（`scripts/generate_nagomi_order_sb_preview.py`）は
`2026-sb-adopted.json` と Notion を主ソースにしていた。
2026-08-29 玉名郡ナイターで SB 更新した選手が、予想に未反映のまま残っていた。

正本:

- PDF: `…/0829_玉名郡ナイター中・長距離記録会/第25回ナイター中長距離記録会_結果.pdf`
- 構造化: 同フォルダの `全結果.md`（中学生のみ。小学・高校・一般は除外）
- 岱明メモ: `岱明の結果.md`（全結果が無いときのフォールバック）

## Decision

1. `load_sb_index()` の最終段で `全結果.md`（なければ岱明）を読み、
   **既存同距離 SB より速い場合のみ**上書きする。
2. 遅い・同等の記録は採用しない。
3. 氏名ゆれは `norm_name` で吸収（空白・﨑/崎・髙/高・凜/凛・瀨/瀬 等）。
4. DNS・小学・高校一般は取り込み対象外。
5. `2026-sb-adopted.json` 本体の書き換えは本スライス外。

## Consequences

- 岱明以外の学校・クラブ選手のナイター更新もなごみ予想に反映される。
- PDF → 構造化: `python scripts/extract_tamana_nighter_results.py`
- 再生成: `python scripts/generate_nagomi_order_sb_preview.py`
