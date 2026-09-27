# Phase 0: 荒尾第四中をなごみ実績で揃える（Lite extend）

## 作業種別

| 項目 | 値 |
|:---|:---|
| 種別 | `extend` |
| 技術 | Python + unittest |
| Docs Sync | ADR 056 |

## ゴール

荒尾第四中男子は校内SBプールが5人で6区欠測になっていた。
なごみOP（藤井祐吏・松岡颯希・浦本崇彦）を見れば6人目が揃う。
仮オーダーを LOCKED で6人固定し、藤井のなごみ1区10:15を `RECENT_EKIDEN_MARKS` に注入する。

## スキップ

Phase 2/4。
