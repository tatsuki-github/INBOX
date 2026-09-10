# Google Drive import INDEX — いだてん岱明

Snapshot of Drive text content under `input/external/drive/`.
Source of truth remains Google Drive; this tree is a searchable copy (ADR 010).

## Personal (`personal/`) — parent `1DkMD7BcofiAuUarIi8GoRFeK05KiCosK`

| Path | Status | Notes |
|---|---|---|
| `personal/夏休みの練習.md` | imported | markdown |
| `personal/勤怠.md` | imported | markdown |
| `personal/ATRC.md` | imported | markdown |
| `personal/いだてん岱明部員.md` | imported | markdown |
| `personal/2025年度玉名市の中学生.md` | imported | markdown |
| `personal/早熟と後伸びについて.md` | imported | markdown |
| `personal/中体連駅伝.md` | imported | markdown |
| `personal/中学生の練習.md` | imported | markdown |
| `personal/参考サイト.md` | imported | markdown |
| `personal/通信陸上.md` | imported | markdown |
| `personal/ウォーミングアップ.md` | imported | markdown |
| `personal/動きづくり.md` | imported | markdown |
| `personal/いだてん岱明出場予定.md` | imported | markdown |
| `personal/謝礼金.md` | imported | Source document appears empty (sensitive title retained) |
| `personal/Googleドライブマニュアル.md` | skipped | Large Google Doc (~269KB exported); skipped full body per import policy — viewUrl only |
| `personal/通信陸上_のコピー.csv` | imported | csv |
| `personal/選手権と通信のタイム差_のコピー.csv` | imported | csv |
| `personal/中学選手権_のコピー.csv` | imported | csv |

## Shared (`shared/`) — drive `0APcRf6IAzVPGUk9PVA`

### 名簿
- `shared/名簿/2025年度.csv` — imported
- `shared/名簿/2025年度_岱明中学校陸上競技部_部員名簿.csv` — imported

### 練習
- `shared/練習/練習の記録.md` / `.csv` — imported
- `shared/練習/玉名市練習会/2025-12-30.md` — imported
- `shared/練習/駅伝試走/2025.pdf.meta.json` — stub (PDF binary skipped)

### 記録データベース
- `shared/記録データベース/2026年度/中学生記録.csv` — imported
- `shared/記録データベース/2025年度/` — 通信陸上 / 中学選手権 / 県中体連 / 選手権と通信のタイム差 / 3000m予想タイムランキング — imported CSV
- `shared/記録データベース/印刷用/` — markdown notes imported

### 大会
- See `shared/大会/INDEX.md` for full event folder catalog.
- Imported Docs: 2025 選手権・通信・荒玉結果; 2026 選手権結果・金栗概要/結果・荒玉概要
- PDF start lists / 要項: meta stubs only
- `shared/大会/荒玉駅伝歴代/` — empty at import

### 分析
- `関係図_2026.pdf` / `2026年度荒玉男子.pdf` / `2026年荒玉女子.pdf` — meta stubs only (multi-MB PDFs)

### 競技規則
- `厚さ20mm以下レース用シューズ.md` — imported
- `陸上競技ルールブック2025.pdf` — skipped (commercial rulebook)

### 指導者研修会
- `20250516/` and `20251008/` — PDF meta stubs only (no binaries)

### フォト
- `shared/フォト/INDEX.md` — link-only; photos out of text import

### Other
- `shared/Notionバックアップ/` — placeholder if present

## Skip policy
- PDFs > ~few MB / commercial books: meta stub + viewUrl
- Photos/images: folder INDEX only
- Huge Google Docs (e.g. Drive manual): skipped body

## Counts
- imported metas: 62
- stub metas: 35
- skipped metas: 3
