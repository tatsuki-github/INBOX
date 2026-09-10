# Notion export — いだてん岱明

- Workspace: `いだてん岱明` (`a24d9f9b-65a9-46d9-ab85-5bb4ee324987`)
- Exported (UTC): 2026-09-10 09:25Z
- Branch: `cursor/idaten-data-import-8246`
- Mode: read-only Notion MCP; large DBs via `query_data_sources` **view** mode
- `rows.json` はクリーンな配列。完全性は各 DB の `export.status.json` と下表を参照。
- ページ断片 `rows_page*.json` はマージ後削除済み。

## Counts

- Database directories: **15**
  - complete: **9**
  - partial: **4**
  - schema-only: **2**
- Pages: **11** (`pages/<slug>.md` + `.meta.json`)

## Databases

| slug | status | rows | schema | notes |
|---|---|---:|:---:|---|
| `2025年度sb` | partial | 700 | ✅ | has_more → rows.json next_cursor |
| `2025年度中学生記録` | partial | 1100 | ✅ | has_more → rows.json next_cursor | fetch_raw.md |
| `2025年度中学生記録v2` | schema_only | 0 | ✅ | fetch_raw.md |
| `2026年度中学生記録` | partial | 755 | ✅ | list of 755 rows from prior export + analysis; full DB incomplete. See also rows_daimyo_view.json (76 complete 岱明中 view). | has_more → rows.json next_cursor | fetch_raw.md |
| `2026年度全て` | schema_only | 0 | ✅ | fetch_raw.md |
| `2026年度高校生記録` | partial | 800 | ✅ | has_more → rows.json next_cursor |
| `inbox-(1)` | complete | 387 | ✅ | Complete via view mode. pages 1-3 full props; page4 compact fields. |
| `いだてん岱明の未来` | complete | 1 | ✅ |  |
| `いだてん岱明生徒` | complete | 15 | ✅ |  |
| `カレンダー` | complete | 382 | ✅ | Complete for view 全件同期用 (2026-01-01 to 2027-01-01). |
| `動きづくり` | complete | 1 | ✅ |  |
| `怪我について` | complete | 1 | ✅ |  |
| `練習のバリエーション` | complete | 3 | ✅ |  |
| `荒玉中体連駅伝戦略` | complete | 5 | ✅ |  |
| `荒玉中体連駅伝歴代` | complete | 27 | ✅ |  |

## Pages

| slug | title |
|---|---|
| `2025-男子` | 2025 男子 |
| `ノルウェー` | ノルウェー |
| `ノルウェーメソッド-inbox` | ノルウェーメソッド-inbox |
| `ノルウェーメソッド` | ノルウェーメソッド |
| `ランニング` | ランニング |
| `岱明ノルウェーメソッド` | 岱明ノルウェーメソッド |
| `岱明朝練と夕練` | 岱明朝練と夕練 |
| `怪我の因子ランキング` | 怪我の因子ランキング |
| `残り練習-スタミナ→RP` | 残り練習【部活カレンダー準拠】スタミナ→RP |
| `洛南高校動きづくり` | 洛南高校動きづくり |
| `記録データベース` | 記録データベース |

## Failures / limits

- query_data_sources SQL/rows mode hit workspace usage limit → continued with unlimited view mode
- notion-ai-search unavailable (used notion-search / list_* / fetch / query view)
- 2025年度中学生記録: partial (1100+ rows; has_more; next_cursor in rows.json)
- 2026年度高校生記録: partial (800+ rows; has_more)
- 2025年度sb: partial (700+ rows; has_more)
- 2026年度中学生記録: 755 rows + 76-row 岱明中 view complete; full DB not exhausted
- 2025年度中学生記録v2 / 2026年度全て: schema (+fetch_raw) only
- カレンダー view「全件同期用」covers 2026-01-01..2027-01-01 only (382 rows complete for that view)
- inbox-(1) page4 uses compact fields (pages 1–3 have full property payloads)
- 荒玉中体連駅伝歴代: ファイル&メディア attachment blobs omitted; other properties complete (27/27)
- Hub-linked DBs not separately exported: 小学生/大学・一般記録, 大会, 選手権2025, 通信2025, ランニングシューズ, 荒玉駅伝○×クイズ

## Resume cursors (partial)

- `2025年度sb`: `s:mcp_non_archived_48aaa9e2-efed-43b6-87d6-0c5c903f8aa3:340a38e8-3034-8158-9f85-ffff6cf3249f`
- `2025年度中学生記録`: `s:mcp_non_archived_ae0c3bc9-bda7-40e0-a6e2-1b95c1dcb502:355a38e8-3034-8141-9552-f94f6369109e`
- `2026年度中学生記録`: `None`
- `2026年度高校生記録`: `s:mcp_non_archived_1735c5e7-b163-4483-bcfe-fad849840694:39ba38e8-3034-81f2-880a-ca22bbdb2694`

