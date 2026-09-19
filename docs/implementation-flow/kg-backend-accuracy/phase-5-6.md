# Phase 5–6: KG 強化の実装・検証

## 実装内容

- `scripts/knowledge_graph/builder.py` — `out/analysis/**/*.md` の Source 自動登録、チーム stem ラベル、QueryHint 追加
- `scripts/knowledge_graph/query.py` / `backend/src/kg/query.ts` — 金栗PROJECT ≠ なごみ、学校別平均・優勝差・所属全記録の加点
- `backend/src/kg/mapRefs.ts` — `practice.{year}.json` と kpace ダイジェストの実在パス
- KG 再生成（502 nodes / 1402 edges）+ `backend/data/knowledge-graph.json` 同期
- ADR 046、README、implementation-flow 記録

## 受け入れ条件（Phase 1）

1. [x] 女子800m 上位3人平均 → `2026_women_800m_1500m_pb_school_ranking.md`
2. [x] 優勝との差 → `aragyoku_2024_2025_focus_teams.md`
3. [x] 菊水 1 区 → `aragyoku-teams/菊水.md`
4. [x] 金栗PROJECT 全記録 → `arato-tamana-teams/金栗PROJECT.md`（なごみハブへ誤誘導しない）
5. [x] practice 年次 / kpace mapRefs
6. [x] ジュニア／なごみ／GZ／玉名付属 回帰 Green

## QE5

| ステップ | 結果 |
|:---|:---|
| QE5-0 verify | backend `npm test` 175 passed / `lint` / `build` 成功。Python KG 10 passed。`--check` OK |
| QE5-1 improve-flow | なごみ判定を `isNagomiMeetQuery` に抽出。QueryHint 文言から「なごみ」を除去し誤判定を防止 |
| QE5-2 bug-finder | Critical=0 High=0。検出: QueryHint hint 内の「なごみ」がテスト偽陽性 → 修正済み |
| QE5-3 | 上記 Medium 相当を修正 |
| QE5-4 refactor | スコア分岐の関数化。退行: kgQuery 11 + mapRefs 7 + lint 再実行 Green |
| QE5-5 test 4本柱 | 出力値ベース（corpus_sources / mapped path）。モックなし。HOW 非検証 |
| QE5-7 Docs Sync | `docs/adr/046-kg-analysis-digest-routing.md` 新規。README / backend README リンク |

## R5

- 型: 新規 `enum`/`any` なし。mapRefs は `string \| null`
- Semantic Drift なし（Phase 3 の 3 層どおり）
- 受け入れ条件はテストで照合済み
- **Approved**

## Phase 6 統合レビュー

| 基準 | 結果 |
|:---|:---|
| A-1 要件カバレッジ | AC 6 件実装・テスト済み |
| A-2 章間整合 | Phase 0 extend / Phase 2-4 skip / ADR 046 一致 |
| A-5 Docs ↔ Code | ADR 046 が builder / mapRefs / query と一致 |
| B-1 Semantic Drift | retrieve/answer の契約は非破壊 |
| B-3 Edge | 金栗PROJECT vs なごみ、path traversal 既存テスト維持 |
| B-4 Privacy | 新規ログなし |
| B-6 Test | ドメイン単体 + 既存 answer 回帰 175 |
| B-7 Build & Lint | シェル実行成功 |
| bug-finder | Critical=0 High=0 |

**Approved**（差し戻し 0 回）

## 検証コマンド

```
cd backend && npm test && npm run lint && npm run build
.venv/bin/python -m pytest tests/test_knowledge_graph.py -q
.venv/bin/python scripts/build_knowledge_graph.py --check
.venv/bin/python scripts/sync_backend_kg.py --check
```
