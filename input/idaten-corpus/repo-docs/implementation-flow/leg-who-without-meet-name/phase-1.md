# 調査レポート: 大会名なし「何区を走った」の正本誘導

## ユーザーストーリー

保護者・部員として、選手名だけで「何区を走った？」と聞きたい。なぜなら、荒玉の区間表があるのに通信陸上のスタートリストが返ると信じられないからだ。

## 受け入れ条件

1. [ ] `isLegAthleteQuestion("案浦竜士は何区を走った？")` が true（距離質問は false）
2. [ ] `detectMeetKind("案浦竜士は何区を走った？")` が `aragyoku`。ジュニア／なごみ／通信大会を明示したときはそちら
3. [ ] オフライン回答が `6区` と `案浦竜士` を含み、sources 先頭が `aragyoku-teams` または `focus_teams`
4. [ ] KG `corpus_sources` が `aragyoku-teams` を含み、先頭がスタートリスト／通信陸上ではない
5. [ ] 既存の「5区は誰」・ジュニア／なごみ回帰が Green

## 受け入れ条件 → テストマッピング

| # | 受け入れ条件 | テスト種別 | 対象層 | テスト意図 |
|:--|:-------------|:-----------|:-------|:-----------|
| 1 | 何区検出 | 単体(TDD) | domain/legs | 数字なし区間質問 |
| 2 | 大会種別 | 単体(TDD) | domain/meets | 無名→荒玉。指名大会は維持 |
| 3 | オフライン回答 | 統合 | answer.ts | 正本 6区。スタートリストではない |
| 4 | KG 誘導 | 単体(TDD) | kg/query | digest refs |
| 5 | 回帰 | 回帰 | meets/answer/kgQuery | ADR 035 維持 |

## スコープ

| In Scope | Out of Scope |
|:---------|:-------------|
| 共有 `isLegAthleteQuestion` | ベクトル DB |
| detectMeetKind の無名区間デフォルト | frontend |
| retrieve のスタートリスト減点 | rag_index 再チャンク |
| KG QueryHint + スコア同期 | 新規コーパス本文 |

## 依存関係

- ADR 035（区間選手 vs LINE）、017（大会ディスambiguation）、027（チーム MD）、046（digest Source）

## 影響ドキュメント一覧

| 変更予定コード | 更新対象 doc | 操作 |
|:---------------|:-------------|:-----|
| `backend/src/domain/legs.ts` | `docs/adr/047-*.md` | 新規 |
| retrieve / meets / query | ADR 035 追記リンク | 更新 |

## QE1 / R1

- AC は検証可能な検出・sources・6区に限定。
- **Approved**
