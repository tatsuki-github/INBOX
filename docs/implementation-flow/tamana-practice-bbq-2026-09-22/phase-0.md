# Phase 0: 作業種別記録 — 玉名市練習会&BBQ（2026-09-22）公式情報取り込み

| 項目 | 値 |
|:---|:---|
| 作業種別 | `extend`（Lite Path） |
| ゴール | 公式サイト（tamariku 練習会ページ）の内容を正本に反映し、リポジトリに無い時刻・会場・会費・申込締切等を追加。コーパス/カレンダー/KG を再生成 |
| 技術スタック | YAML/Markdown 正本 + corpus/calendar/KG パイプライン |
| 検証対象パッケージ | `backend`（RAG 再生成の退行確認） |
| Docs Sync | 有効 — `docs/implementation-flow/tamana-practice-bbq-2026-09-22/` |
| 優先特性 | 事実正確性 > LINE 回答 > 開発速度 |

## ルーター判定

1. bug-fix? No（欠損の追加が主）
2. perf-only? No
3. 既存変更? Yes → Lite
4a–4b No → **`extend`**

## スキップ

Phase 2 / 4 スキップ（UI なし）。Phase 1 / 3 簡略。

## スコープ

**In**: 公式ページ事実の正本化、`events.2026.yaml` 更新、Drive テキスト追加、生成物再構築  
**Out**: 申込フォーム実装、Notion リモート同期、選手出欠管理
