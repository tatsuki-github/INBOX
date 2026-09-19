# アーキテクチャ設計: なごみ区間オーダーを金栗駅伝から分離する

## 特性（優先順）

1. 検索精度（正本フォルダへ誘導）
2. 大会 disambiguation（なごみ / 金栗駅伝 / 金栗記念 / 金栗PROJECT）
3. 既存パイプライン互換（KG → mapRefs → retrieve）
4. テスト容易性

## コンポーネント

- Business Logic: `detectMeetKind` / `meetDriveTokens` / `meetResultPathBoost`
- Data Access: retrieve の path ボーナスと corpus ブロック、KG スコア
- UI: なし

## ADR ドラフト

`docs/adr/048-nagomi-order-not-kanaguri-ekiden.md`

## テスト戦略

| 層 | 対象 | 配置 |
|:---|:---|:---|
| ドメイン | 大会種別・drive トークン・区間検出 | `meets.test.ts` `legs.test.ts` |
| 統合 | オフライン 1区 | `answer.test.ts` |
| KG | refs がなごみオーダー | `kgQuery.test.ts` / `test_knowledge_graph.py` |

ピラミッド: 単体 多 : 統合 少。ベクトル検索は使わない。

## QE3 / R3

- **Approved**
