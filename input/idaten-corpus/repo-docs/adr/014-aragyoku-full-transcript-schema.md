# ADR 014: 荒玉駅伝 全順位・全フィールド文字起こしスキーマ

## 状況

荒玉（玉名荒尾）中体連駅伝の結果は、女子上位6校向けの限定的な JSON（`women_top6_2012_2025.json`）と
Notion 行プロパティ（岱明の順位・記録のみ）に分散していた。男子は未整備。
結果ボード画像には全参加校・全区間の選手名・学年・区間タイム・累計・通過順位・区間順位・
区間新などが印刷されているが、構造化データに取り込まれていなかった。

## 決定

1. **正本は年別 transcript JSON**（`input/aragyoku/transcripts/{year}-{gender}.json`）。
   ビルド成果物（`women_full_*` / `men_full_*`）は transcript を enrich・検証した派生とする。
2. **スキーマ `full-transcript-v1`** を採用する。
   - 大会メタ: `year`, `gender`, `date`, `source_drive_id`, `legs[]`, `weather`, `pace`, `daimyo`, `ocr_notes`
   - チーム: `rank`, `team`, `total`, `gap_to_leader`, `gap_to_prev`（ボードにあれば）
   - 区間: `leg`, `name`, `grade`, `split`, `cumulative`, `passing_rank`, `split_rank`,
     `split_record`, `status`, `raw_name_grade`, `computed.{split_rank,passing_rank}`
3. **女子13年（2014除く）+ 男子14年 = 27件**を対象とする。女子2014は `missing_years` に残す。
4. **検証ルール V-1〜V-9**（`validate_transcript.py`）をビルド前に必須通過とする。
   - V-7: ボード順位 vs タイムから再計算した順位の照合
   - V-8: `split_record` と当該区最速の整合
   - V-9: 岱明アンカーと Notion `rows.json` の照合（乖離は `ocr_notes` + board canonical で文書化）
5. **派生成果物**
   - `build_full.py` → full JSON、full athletes CSV、`women_top6`（rank≤6 抽出 + CSV reconciliations）
   - 既存 `aragyoku_women_track.py` は top6 の既存列のみ参照し互換維持
6. **KG/OCR 同期**: `scripts/sync_ocr_md.py` で `ekiden-history/ocr/*.md` にフル順位表を追記し、
   `media-manifest.json` に `transcript_path` / `schema` / `team_count` を登録する。

## 正本 vs 補助ソース

| ソース | 役割 |
|:---|:---|
| 結果ボード画像 | 全セルの正本（OCR → transcript） |
| Notion `rows.json` | 岱明・気温・2位ペースのクロスチェック（V-9） |
| `women_csv_reconciliations.json` | top6 派生時の氏名・学年補正（ADR 013 継続） |

ボード値と Notion が不一致の場合は **ボードを正本** とし、`ocr_notes` に記録する。

## ディレクトリ構成

```
input/aragyoku/
├── sources/           # Drive 画像 ID
├── ocr_raw/           # 生 OCR（27件）
├── transcripts/       # 年別 JSON 正本
├── reconciliations/   # CSV 照合マニフェスト
├── lib/               # schema, ranks, enrich, school_aliases
├── validate_transcript.py
├── build_full.py
├── women_full_2012_2025.json
├── men_full_2012_2025.json
└── women_top6_2012_2025.json  # 派生
```

## テスト戦略

- `tests/test_aragyoku_validate.py`: 順位計算・V-1〜V-9・fixture
- `tests/test_aragyoku_women_track.py`: top6 派生・CSV reconciliations・joined 回帰
- `build_full.py` 実行時: 全年 `assert_valid_year`

## 不採用

| 案 | 理由 |
|:---|:---|
| top6 JSON を手書き維持 | 全順位データと二重管理になる |
| Notion 順位を transcript 上書き | ボードが正本である方針と矛盾 |
| 区間順位の計算値のみ保存 | ボード印刷値の検証ができない |
