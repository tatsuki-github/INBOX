# 作業種別記録: 大会結果 URL を LINE 回答に付与

## 判定結果
- **作業種別**: extend
- **実行パス**: Lite
- **検証対象パッケージ**: backend

## Docs Sync 設定

| 項目 | 記録 |
|:-----|:-----|
| **Docs Sync** | 有効 |
| **Docs Root(s)** | docs |
| **ADR 永続化先** | docs/adr/ |

## 判定根拠（4 問）

| # | 質問 | 回答 | 根拠 |
|:--|:-----|:-----|:-----|
| 1 | バグか？ | No | 現状は意図的に URL 非表示 |
| 2 | 改善のみか？ | No | CSV URL を回答に載せる新振る舞い |
| 3 | 既存変更か？ | Yes | answer / format / data 索引 |
| 4 | 契約破壊か？ | 非破壊 | LINE API 契約は不変。テキスト末尾に URL 追加 |

## Lite Path スキップ

| Phase | 実行 | 理由 |
|:------|:-----|:-----|
| 1 | 簡略化 | CSV 位置は調査済み |
| 2/4 | スキップ | UI なし |
| 3 | 簡略化 | 索引 JSON + ドメイン関数 |
| 5–6 | 実行 | |

## ゴール

結果系の大会質問に対し、記録 CSV（`参考` / `*URL`）およびカレンダー `source.csv` の URL を回答末尾に返す。

## データソース

1. `input/idaten-corpus/drive-text/記録データベース/**/*.csv`（長表 `参考`、広表 `*URL`）
2. `out/*/source.csv` の `urls`（ジャンク共通 PDF は除外）
3. 生成物: `backend/data/meet-result-urls.json`（Vercel 同梱）
