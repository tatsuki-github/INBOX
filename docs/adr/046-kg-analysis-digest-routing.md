# ADR 046: 分析ダイジェストの KG Source 自動登録と practice パス対応

- Status: Accepted
- Date: 2026-09-19

## Context

LINE Q&A は KG で「どこを読むか」を決める（ADR 016 / 031）。
`out/analysis/` には学校別 PB 平均・優勝差・チーム区間・所属全記録の正本があるが、
KG Source は ATRC と focus 数校に偏り、QueryHint が 0-hop で refs を持てなかった。
加えて `out/2026/practice.json` が `practice/practice.json` に map され、コーパス実体
`practice/practice.2026.json` とずれていた。
「金栗」はなごみ駅伝の別名と `金栗PROJECT` 所属が衝突していた。

## Decision

1. **`_register_analysis_digests`**: `out/analysis/**/*.md` を Source 化。チームファイルは stem を label、別名を hint に載せる。
2. **QueryHint**: 学校別平均・優勝差・菊水1区・金栗PROJECT 全記録・トラック周長を正本 Source に直結。
3. **mapRefs**: `out/{year}/practice.json` → `practice/practice.{year}.json`、`out/daiming-practice-menus-kpace.md` → `practice/`。
4. **スコア**: 金栗PROJECT をなごみ加点から除外。学校別平均 / 優勝差 / 所属全記録を digest 加点。
5. TS（`backend/src/kg/query.ts`）と Python（`scripts/knowledge_graph/query.py`）を同期。

## Consequences

- KG がチーム名・学校別質問で exact ファイルへ誘導できる。
- 練習メニュー質問が実在するコーパスパスを preferred に載せられる。
- 金栗駅伝（なごみ）と金栗PROJECT（所属記録）が分離される。
- ベクトル DB は引き続き導入しない。

## Alternatives Considered

- retrieve/answer の preferred ハードコードをさらに増やす: 却下 — Router が KG 地図を外すと再発する
- 全 Source を全 Topic に全結合: 却下 — ADR 031 どおり誤誘導

## テスト戦略

| 層 | 対象 | 配置 |
|:---|:---|:---|
| 単体 | mapRefs 年次 practice / kpace | `backend/tests/mapRefs.test.ts` |
| 単体 | 学校別平均・優勝差・菊水・金栗PROJECT・トラック | `backend/tests/kgQuery.test.ts` |
| 単体 | builder 経路 | `tests/test_knowledge_graph.py` |
| 回帰 | ジュニア / なごみ / GZ / 玉名付属 | 既存 `kgQuery.test.ts` |
