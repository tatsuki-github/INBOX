# アーキテクチャ設計: 無名区間質問の荒玉デフォルト

## 特性（優先順）

1. 正本到達性（通信陸上スタートリストに流さない）
2. 大会明示時の非破壊（ジュニア／なごみ／通信）
3. 既存 LINE 運用質問との分離（ADR 035）
4. KG と retrieve の判定一致
5. ランタイムは `backend/data/*` のみ

## コンポーネント

```
domain/legs.ts          — isLegAthleteQuestion
domain/meets.ts         — detectMeetKind が無名区間→aragyoku
kg/query.ts + query.py  — aragyoku-teams 加点、スタートリスト減点
rag/retrieve.ts         — path bonus/penalty
domain/answer.ts        — preferred に focus / teams hub
```

## ADR（会話ドラフト）

- 採番: 047
- 判断: 大会名なしの区間選手質問はクラブデフォルトの荒玉正本へ。通信陸上 Entity の氏名ヒットは減点。
- 不採用: ベクトル検索、氏名→学校の別インデックス。

## テスト戦略

- ドメイン: legs / meets
- 統合: answer オフライン preview
- KG: query.ts + Python query.py
- 配置: `backend/tests/*.test.ts`, `tests/test_knowledge_graph.py`

## QE3 / R3

- 3 層は既存パイプラインへの差分のみ。循環依存なし（legs は無依存）。
- **Approved**
