# Google Drive import INDEX — いだてん岱明

Snapshot under `input/external/drive/` (ADR 010). Drive remains source of truth.

**Counts:** imported=61, stub=35, skipped=3, meta_files=151

## Personal (`personal/`) — `1DkMD7BcofiAuUarIi8GoRFeK05KiCosK`

| Path | Status | Notes |
|---|---|---|
| `personal/2025年度玉名市の中学生.md` | imported | markdown |
| `personal/ATRC.md` | imported | markdown |
| `personal/Googleドライブマニュアル.md` | skipped | Large Google Doc (~269KB exported); skipped full body per import policy — viewUrl only |
| `personal/いだてん岱明出場予定.md` | imported | markdown |
| `personal/いだてん岱明部員.md` | imported | markdown |
| `personal/ウォーミングアップ.md` | imported | markdown |
| `personal/中体連駅伝.md` | imported | markdown |
| `personal/中学生の練習.md` | imported | markdown |
| `personal/中学選手権_のコピー.csv` | imported | csv |
| `personal/動きづくり.md` | imported | markdown |
| `personal/勤怠.md` | imported | markdown |
| `personal/参考サイト.md` | imported | markdown |
| `personal/夏休みの練習.md` | imported | markdown |
| `personal/早熟と後伸びについて.md` | imported | markdown |
| `personal/謝礼金.md` | imported | Source document appears empty (sensitive title retained) |
| `personal/通信陸上.md` | imported | markdown |
| `personal/通信陸上_のコピー.csv` | imported | csv |
| `personal/選手権と通信のタイム差_のコピー.csv` | imported | csv |

## Shared — drive `0APcRf6IAzVPGUk9PVA`

### 名簿
- `shared/名簿/2025年度.csv` — **imported**
- `shared/名簿/2025年度_岱明中学校陸上競技部_部員名簿.csv` — **imported**

### 練習
- `shared/練習/玉名市練習会/2025-12-30.md` — **imported**
- `shared/練習/練習の記録.csv` — **imported**
- `shared/練習/練習の記録.md` — **imported**
- `shared/練習/駅伝試走/2025.pdf.md` — **?**
- `shared/練習/駅伝試走/2025.pdf` — **stub** (PDF binary not imported into git; viewUrl only (ADR 010))

### 記録データベース
- `shared/記録データベース/2025年度/3000m予想タイムランキング.csv` — **imported**
- `shared/記録データベース/2025年度/中学選手権.csv` — **imported**
- `shared/記録データベース/2025年度/県中体連.csv` — **imported**
- `shared/記録データベース/2025年度/通信陸上.csv` — **imported**
- `shared/記録データベース/2025年度/選手権と通信のタイム差.csv` — **imported**
- `shared/記録データベース/2026年度/中学生記録.csv` — **imported**
- `shared/記録データベース/印刷用/中学選手権.md` — **imported**
- `shared/記録データベース/印刷用/通信陸上.md` — **imported**
- `shared/記録データベース/印刷用/選手権と通信のタイム差.md` — **imported**

### 大会
- Catalog: `shared/大会/INDEX.md`
- Google Docs → MD imported for 2025/2026 event results & notes where present
- PDFs / images → meta stub or `.pdf.md` stub with viewUrl (binaries not committed)
- 2025年度 metas: 35
- 2026年度 metas: 22

### 分析
- `shared/分析/2026年度荒玉男子.pdf.md` — **?**
- `shared/分析/2026年度荒玉男子.pdf` — **stub**: Multi-MB PDF binary not imported; meta+viewUrl only (ADR 010)
- `shared/分析/2026年荒玉女子.pdf.md` — **?**
- `shared/分析/2026年荒玉女子.pdf` — **stub**: Multi-MB PDF binary not imported; meta+viewUrl only (ADR 010)
- `shared/分析/関係図_2026.pdf.md` — **?**
- `shared/分析/関係図_2026.pdf` — **stub**: Multi-MB PDF binary not imported; meta+viewUrl only (ADR 010)

### 競技規則
- `shared/競技規則/厚さ20mm以下レース用シューズ.md` — **imported**: markdown
- `shared/競技規則/陸上競技ルールブック2025.pdf.md` — **?**
- `shared/競技規則/陸上競技ルールブック2025.pdf` — **skipped**: Commercial rulebook PDF; skipped full text per import policy (ADR 010 / phase1 OOS)

### 指導者研修会
- `48` PDF/meta stubs under `20250516/` and `20251008/` (no binaries)

### フォト
- `shared/フォト/INDEX.md` / `README.md` — photos out of text import; folder link only

### Notionバックアップ
- Placeholder / empty

## Skip policy
- Multi-MB PDFs & commercial books: stub/skipped + viewUrl
- Photos/images: INDEX link only
- Huge Google Docs (Drive manual): skipped body
