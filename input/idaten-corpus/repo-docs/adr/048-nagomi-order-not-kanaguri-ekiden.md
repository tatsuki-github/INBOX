# ADR 048: なごみ区間オーダーは金栗駅伝と分けて正本へ

- Status: Accepted
- Date: 2026-09-19

## Context

「なごみ駅伝の岱明男子1区は誰？」は 2026-09-20 の区間オーダー正本
（`drive-text/大会/2026年度/0920_*なごみ*/男子区間オーダーリスト.md`）で答えるべきだが、
`NAGOMI_RE` が裸の「金栗」をなごみに含め、`meetDriveTokens` が `金栗` を返すため
`0315_金栗駅伝` と `0411_金栗記念選抜` と Drive `.meta.json` が勝っていた。
金栗駅伝は 3/15 の別大会、金栗PROJECT は所属トラック正本である。

## Decision

1. **なごみ**は `なごみ|金栗四三` のみ。`金栗駅伝` / `金栗記念` は MeetKind `other`。
2. nagomi の drive トークンは `なごみ`（フォルダ名のなごみ大会）。裸の `金栗` は使わない。
3. 区間・オーダー質問は `区間オーダーリスト` を preferred にし、結果ファイル・開催要項・SB予想より先。
4. 年未指定のなごみオーダーは `defaultYear`（2026）フォルダを使う。
5. `.meta.json` は preferred / retrieve から除外する。
6. KG スコアと QueryHint を TS / Python で同期する。

## Consequences

- なごみの「1区は誰」が当年オーダーに寄る。
- 「金栗駅伝の日付は？」は 3/15 フォルダのまま（other）。
- 金栗PROJECT 全記録は arato-tamana のまま。
- ベクトル DB は導入しない。

## Alternatives Considered

- 金栗をすべてなごみ別名のままにする: 却下。3/15 金栗駅伝と衝突する
- 氏名→オーダーの別インデックス: 却下。フォルダ正本で足りる

## テスト戦略

| 層 | 対象 | 配置 |
|:---|:---|:---|
| 単体 | 大会種別・drive トークン・オーダー boost | `backend/tests/meets.test.ts` `legs.test.ts` |
| 統合 | オフライン 1区 | `backend/tests/answer.test.ts` |
| KG | refs がなごみ | `backend/tests/kgQuery.test.ts` `tests/test_knowledge_graph.py` |
