# Phase 5–6: 実装・検証 — 玉名市練習会&BBQ 公式取り込み

## 実装

| 成果物 | 内容 |
|:---|:---|
| `input/external/drive/shared/練習/玉名市練習会/2026-09-22.md` | 公式ページの構造化 |
| `input/events.2026.yaml` | 8:00・おおはま・会費・締切・URL。練習計画の 9/22 も午前 BBQ を明記 |
| 生成物 | corpus / rag / calendar / KG |

## 検証

- corpus 465 sources / 4666 chunks
- `backend npm test` 60/60
- RAG: おおはまふれあいセンター・会費等ヒット

## レビュー

**Approved**（Lite extend、UI/新コードなし）
