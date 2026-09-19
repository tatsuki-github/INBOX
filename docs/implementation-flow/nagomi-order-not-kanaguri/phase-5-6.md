# Phase 5–6: なごみ区間オーダー ≠ 金栗駅伝

## 実装

- `meets.ts` — なごみは `なごみ|金栗四三`。金栗駅伝・金栗記念は other。drive トークンは `なごみ`
- `answer.ts` — 年未指定のなごみオーダーは defaultYear。`.meta.json` を preferred から除外
- `retrieve.ts` — なごみ質問で 金栗駅伝フォルダと meta JSON をブロック。区間オーダーリストを pin
- `kg/query.ts` + `query.py` — なごみと金栗駅伝を分離してスコア
- QueryHint「なごみ駅伝の区間オーダーは？」
- `legs.ts` — `何区走った`（`を` なし）も区間選手質問

## QE5 / 検証

- [x] `backend` `npm test`（187） / `npm run lint` / `npm run build`
- [x] `pytest tests/test_knowledge_graph.py`（12）
- [x] probe-nagomi-order 0/4 FAIL、probe-v7 0/48、probe-legs 0/30、probe-dare 0/20
- [x] KG 再生成 506 nodes / 1417 edges + backend 同期

## R5 / Phase 6

- Critical=0, Major=0
- A-5: ADR 048 と実装一致
- **Approved**
