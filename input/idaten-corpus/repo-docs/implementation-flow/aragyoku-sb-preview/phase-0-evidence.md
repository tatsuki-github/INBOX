# Phase 0: 予想タイムへの事実エビデンス記載（Lite extend）

## 作業種別

| 項目 | 値 |
|:---|:---|
| 種別 | `extend`（Lite Path） |
| 技術 | Python スクリプト + unittest（UI なし） |
| 検証対象 | `scripts` / `tests`（npm なし） |
| Docs Sync | 有効（`docs/adr/`、implementation-flow） |

## ゴール

区間オーダー SB 予想の**全選手**について、その予想タイムに至った**事実**（トラックSBの種目・記録・日付、駅伝の大会名・実測・距離・比例値・重み、前年荒玉からの伸び）をエビデンス列に記載する。推測・印象だけの文言は入れない。

## スキップ

- Phase 2 / 4: UI なし
- Phase 1 / 3: 簡略（既存パイプラインへの note 強化）
