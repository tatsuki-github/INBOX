# ADR 016: KG 先行のいだてん岱明 Q&A（ベクトルなし）

## 状況

ADR 015 の LINE バックエンドは BM25（`rag_index.json`）のみで回答していた。
「9/20の予定は？」のような日付質問はスコープ拒否され、通っても `9/20` と `2026-09-20` / `0920` のトークン不一致でなごみ駅伝を取りこぼした。
リポジトリには探索地図として `out/knowledge-graph.json` がある。ベクトル DB を足さず、KG で「どこを読むか」を決めたい。

## 決定

1. **パイプライン**: Scope → 日付正規化 → KG スコアリング（TypeScript）→ Router LLM（任意）→ `rag_index` から source 指定取得 + BM25 補助 → Answer LLM。
2. **ランタイム読取は `backend/data/*` のみ**（ADR 015 維持）。KG は `scripts/sync_backend_kg.py` で `backend/data/knowledge-graph.json` に同梱。本文は引き続き `rag_index.json`。repo 直下 `input/` は読まない。
3. **refs → corpus source マッピング**（例: `input/events.YYYY.yaml` → `calendar/events.daiming.yaml`）。マッピング不能・パストラバーサルは破棄。
4. **日付質問**: `9/20` / `9月20日` を `YYYY-MM-DD` + `MMDD` に展開し、`drive-text/大会/` のフォルダ名マッチと calendar チャンクを優先。
5. **ベクトル DB は導入しない**。KG が探索地図、BM25 は保険。
6. **ユーザー向け回答**: コーパス抜粋のみを根拠にするが、パス・ソース名は本文に出さない。LINE は Markdown 非対応のためプレーンテキストで返し、送信前に `formatForLine` で記号を除去する。
7. **網羅性**: KG にコーパスハブ・大会フォルダ（`meet:*`）を「何が書いてあるか」ヒント付きで登録。検索は topK/近傍チャンク拡大し、抜け漏れを減らす。

## 不採用

| 案 | 理由 |
|:---|:---|
| 埋め込みベクトル DB | 運用・コスト。KG + パス読取で足りる |
| Vercel で Python KG クエリ | Express/Node ランタイムと不一致 |
| ランタイムで `input/` 直読み | Root=`backend` では未デプロイ。スコープ漏洩リスク |

## テスト戦略

| 層 | 対象 | 配置 |
|:---|:---|:---|
| 単体 | dates / scope / mapRefs / kg query / router / formatForLine | `backend/tests/*.test.ts` |
| 回帰 | 「9/20の予定」→ なごみがコンテキストに入る | `backend/tests/answer.test.ts` |
| 統合 | webhook 既存 | `backend/tests/webhook.test.ts` |

## 結果

- QueryHint「〇月〇日の予定は？」を KG builder に追加
- `backend` の Vitest で日付・なごみ回帰を固定
- 回答本文にファイルパス・ソースを出さない。コーパス根拠は維持
- LINE 向けに Markdown を平文へ整形（`formatForLine`）
- コーパス/大会ノードを内容ヒント付きで KG に追加し、近傍チャンク取得で抜け漏れを低減
- 関連: ADR 015、`scripts/knowledge_graph/query.py`（参考実装）
