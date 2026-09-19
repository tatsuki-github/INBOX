# Phase 5–6: 大会名なし「何区を走った」

## 実装

- `backend/src/domain/legs.ts` — 共有 `isLegAthleteQuestion`
- `meets.ts` — 無名区間 → aragyoku。通信陸上は other
- `retrieve.ts` — 氏名抽出、本文ヒット検索、スタートリスト除外、氏名加点
- `answer.ts` — チーム MD を preferred。preview で `N区 氏名`
- `kg/query.ts` + `query.py` — aragyoku-teams 加点、スタートリスト減点
- QueryHint「選手は何区を走った？」

## QE5 / 検証

- [x] 対象パッケージ `npm test` / `npm run lint`
- [x] probe-legs（案浦 6区）
- [x] KG 再生成 + sync（QueryHint 追加時）

## R5 / Phase 6

- Critical=0, Major=0
- A-5: ADR 047 と実装一致
- **Approved**
