# ADR 047: 大会名なしの区間選手質問は荒玉正本へ

- Status: Accepted
- Date: 2026-09-19

## Context

「案浦竜士は何区を走った？」は区間選手質問だが、`isLegAthleteQuestion` が `\d区` を要求していたため
未検出だった。`detectMeetKind` は `none` になり、KG の通信陸上 Entity（hint に氏名がある）と
スタートリストが勝った。オフライン回答に `6区` が出ず、probe-legs が 1/30 で落ちていた。

ADR 035 は「○年○校○区は誰」と LINE 運用メモの衝突を扱ったが、大会名も区番号もない問いを残していた。

## Decision

1. **`isLegAthleteQuestion` を `domain/legs.ts` に共有**し、`何区を走った` / `は何区` を含む。距離・地点分担は除外。
2. **無名の区間選手質問は `detectMeetKind` = aragyoku**。ジュニア／なごみ／通信大会・通信陸上を明示したときはそちら。
3. **retrieve**: 氏名を含む `aragyoku-teams/{校}.md` を preferred にし、チームハブやスタートリストを入れない。チャンク本文に氏名があれば加点。
4. **オフライン preview**: `| N | 氏名 |` を `N区 氏名` として明示する（正本は表形式のため）。
5. **KG**: QueryHint「選手は何区を走った？」と、スタートリスト／通信陸上の減点を TS / Python で同期。

## Consequences

- 大会名なしの「何区」は荒玉チーム正本・focus 分析へ寄る。
- 通信陸上のスタートリストを明示した質問は従来どおり other。
- ベクトル DB は導入しない。

## Alternatives Considered

- 氏名→所属の別インデックス: 却下。コーパス本文検索で足りる。
- ベクトル検索: 却下（運用コスト、ADR 016）。

## テスト戦略

| 層 | 対象 | 配置 |
|:---|:---|:---|
| 単体 | 何区検出・大会種別 | `backend/tests/legs.test.ts`, `meets.test.ts` |
| 単体 | 氏名抽出 | `backend/tests/retrieve.test.ts` |
| 統合 | オフライン 6区 | `backend/tests/answer.test.ts` |
| KG | refs が aragyoku-teams | `backend/tests/kgQuery.test.ts`, `tests/test_knowledge_graph.py` |
