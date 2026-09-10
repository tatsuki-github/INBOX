# Notion — いだてん岱明ワークスペース

ワークスペース ID: `a24d9f9b-65a9-46d9-ab85-5bb4ee324987`

カタログ: [`_catalog.json`](_catalog.json)

## 優先データベース

| DB | schema | rows | 備考 |
|:---|:---|:---|:---|
| いだてん岱明生徒 | ✅ | ✅ 15 | `databases/いだてん岱明生徒/`（`idaten-students` と同期） |
| いだてん岱明の未来 | ✅ | ✅ | |
| 練習のバリエーション | ✅ | ✅ 3 | インターバル・時間走 |
| 動きづくり | ✅ | ✅ 1+ | 洛南高校 動きづくり |
| 怪我について | ✅ | ✅ 1+ | 因子ランキング |
| 荒玉中体連駅伝戦略 | ✅ | ✅ 5+ | 区間配分・運用チェック |
| 荒玉中体連駅伝歴代 | ✅ | 部分 | search+fetch で年次行を追加中 |
| 2026年度中学生記録 | ✅ + fetch_raw | ✅ 755 | `out/analysis/notion_records_2026.json` 由来 |
| 2025年度中学生記録(v2) | ✅ + fetch_raw | schema/raw | query 上限のため rows は raw 参照 |
| カレンダー | ✅ | — | **正本は `input/events.*.yaml`**（個別 MD は作らない） |
| INBOX (1) | ✅ | pending | |

## 制約

- `notion-ai-search` / meeting notes / 一部 SQL query はプラン上限
- 代替: `notion-search` + `notion-fetch`
