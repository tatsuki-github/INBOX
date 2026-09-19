# ADR 033: 荒玉駅伝ボード上部の大会／区間記録を transcript に構造化

## Status

Accepted

## Context

結果ボード写真の上部には、その時点の **大会記録（総合）** と **各区間の大会区間記録**（タイム・年号・保持者・所属）が印刷されている。
既存の `full-transcript-v1`（ADR 014）は参加校の当日結果と `split_record`（区間新フラグ）までで、このヘッダ表は未構造化だった。
OCR raw に断片は残るがノイズが多く、LINE Q&A や年跨ぎ検証に使えない。

大会区間記録は年をまたいでほぼ据え置きのため、年次比較で文字起こしの正誤を検出しやすい。

## Decision

1. 各 `input/aragyoku/transcripts/{year}-{gender}.json` に `meet_records` を追加する。
   - `total`: 総合大会記録（time / year_labels / school / name）
   - `legs[]`: 区間ごとの time / distance_km / holders[]（name, school, year_labels, western_years）
   - `course_era`: `women_standard` | `men_pre2024` | `men_2024plus`（距離再編で記録リセットを表現）
   - `source_image` / `notes`
2. 正本の抽出結果は `input/aragyoku/meet_records/canonical.json`（生抽出は `_extracted_raw.json`）。
3. 適用スクリプト: `input/aragyoku/apply_meet_records.py`（transcript + idaten-corpus 同期）。
4. 検証:
   - V-10: `meet_records` 必須・区間数一致・holders 非空
   - V-11: 同一 `course_era` 内で総合／区間タイムが年をまたいで悪化しない（再編境界は除外）
5. ヘッダは **その年のボード印刷値** を正とする（当日に破られても翌年ヘッダ更新まで据え置き）。

## Consequences

- 「女子1区の大会記録は？」「男子2区の歴代は？」にコーパス根拠で答えられる
- 年跨ぎ monotone 検証で誤読を早期検出できる
- 男子 2024 距離再編は `course_era` 切替で旧記録との断絶を明示

## Alternatives Considered

- OCR raw のみ頼る: 却下 — ノイズが多く保持者名が崩れる
- 最新年のヘッダだけ持つ: 却下 — 年次の記録更新履歴が消える
- `split_record` から逆算: 却下 — ボード上部の歴代表と当日区間新は別概念
