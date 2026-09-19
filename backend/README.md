# LINE いだてん岱明 Q&A Backend（Express）

いだてん岱明専用コーパスだけを参照する LINE Messaging API バックエンドです。
Vercel では **別プロジェクト**、Root Directory = `backend`。

## ローカル

```bash
# コーパス + RAG 索引（リポジトリルートで。初回またはソース更新時）
python3 scripts/build_idaten_corpus.py

cd backend
cp .env.example .env
# 必要なら .env を編集（LINE / GEMINI_API_KEY）。無くても health とオフライン回答は動く
npm install
npm test
npm run dev
# → http://localhost:3001/health
```

`.env` は `dotenv` で自動読み込みされます（コミットしない）。

| 段階 | 必要な設定 |
|:---|:---|
| health だけ | なし（`PORT` 既定 3001） |
| オフライン回答（LLM なし） | なし。スコープ内質問はコーパス抜粋 |
| 自然文回答（Gemini 無料枠） | [Google AI Studio](https://aistudio.google.com/apikey) で発行した `GEMINI_API_KEY` |
| LINE 実機 | `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN` + ngrok 等 |

Webhook は `POST /webhook`。LINE 実機検証には [ngrok](https://ngrok.com/) 等で HTTPS 公開し、LINE Developers の Webhook URL に設定します。

## 環境変数

| 変数 | 必須 | 説明 |
|:---|:---|:---|
| `LINE_CHANNEL_SECRET` | 本番 | 署名検証 |
| `LINE_CHANNEL_ACCESS_TOKEN` | 本番 | reply |
| `LINE_DENIED_USER_IDS` | 任意 | カンマ区切りの `userId`。載っているユーザーには **無応答**（LLM も呼ばない） |
| `AI_PROVIDER` | 任意 | **`gemini`（既定）** / `openai` / `anthropic` |
| `GEMINI_API_KEY` | 任意 | Gemini Developer API（無料枠）。モデルは `gemini-3.5-flash-lite` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | 任意 | 他プロバイダ切替時。未設定時はコーパス抜粋のオフライン回答 |
| `PORT` | 任意 | ローカル listen（既定 3001） |

## 拒否リスト（Vercel Logs → env）

公式アカウント側から友だちを削除・ブロックできないため、アプリ側で拒否する。

1. 対象ユーザーがボットに何かメッセージを送る
2. Vercel → Project **`idaten-line-backend`** → **Logs** で次を検索する  
   - `line message userId=` … 受信（本文はログに出さない）  
   - `line denied userId=` … 拒否して無応答にしたとき
3. Production の環境変数 `LINE_DENIED_USER_IDS` に `U...` をカンマ区切りで追加し、反映を待つ
4. 以降その ID は reply されない

補助: Messaging API `GET /v2/bot/followers/ids` で友だち ID 一覧も取得できる（表示名は別途 profile API）。

設計: [ADR 018](../docs/adr/018-line-denied-user-ids.md)

## Vercel

1. プロジェクト `idaten-line-backend`（Root Directory = `backend`）
2. 環境変数: `AI_PROVIDER=gemini`、`GEMINI_API_KEY=...`（＋ LINE キー）
3. Deploy 後、Webhook URL: `https://idaten-line-backend.vercel.app/webhook`
4. LINE Developers で Webhook を有効化し Verify

ローカルで CLI を使うときは、誤って別名プロジェクト（例: `backend`）にリンクしないこと。

```bash
cd backend
npx vercel link --yes --project idaten-line-backend --scope tatsukitsuchiyama-gmailcoms-projects
# → .vercel/project.json の projectName が idaten-line-backend であること
```

既存の `web/` 用 Vercel プロジェクトとは **分けて**運用します。

## コーパス規約

- 正本フォルダ: [`input/idaten-corpus/`](../input/idaten-corpus/)（テキストのみ）
- デプロイ同梱索引: [`data/rag_index.json`](data/rag_index.json)
- デプロイ同梱 KG: [`data/knowledge-graph.json`](data/knowledge-graph.json)（探索地図。本文ではない）
- 大会結果 URL 索引: [`data/meet-result-urls.json`](data/meet-result-urls.json)（記録 CSV / `source.csv` 由来。再生成は `python3 scripts/build_meet_result_urls.py`）
- 荒玉結果ボード画像（LINE Image）: [`data/aragyoku-board-images.json`](data/aragyoku-board-images.json)（`transcripts` の `source_drive_id`。再生成は `python3 scripts/generate_aragyoku_board_images_catalog.py`。ADR 043）
- 曖昧な自己ベスト質問は [`src/domain/clarify.ts`](src/domain/clarify.ts) が具体的な質問例を返す（ADR 021）
- 中学生 SB: コーパス `sb/中学生SB.csv` は **全所属・行単位チャンク**（ADR 022）。再生成は `uv run python scripts/build_idaten_corpus.py`
- 想定質問の根拠評価: `npx tsx scripts/eval-1000q/run.ts`（1000問）/ `eval-200q`（200問）（ADR 023）
- ランタイムは上記以外のパスを読まない（スコープ漏洩防止）
- コーパス再生成: `python3 scripts/build_idaten_corpus.py`（リポジトリルート）
- KG 再生成 + 同梱: `uv run python scripts/build_knowledge_graph.py && uv run python scripts/sync_backend_kg.py`
- 鮮度確認: `uv run python scripts/sync_backend_kg.py --check`

## 回答の流れ（KG 先行）

1. スコープ判定（日付・予定・大会も受理）
2. 日付正規化（`9/20` → `2026-09-20` / `0920`）
3. KG で候補ノード・corpus source を決定（必要なら Router LLM）
4. `rag_index` から該当 source の抜粋 + BM25 補助
5. Answer LLM（Gemini）が抜粋のみで回答

設計: [ADR 015](../docs/adr/015-line-idaten-qa-backend.md) / [ADR 016](../docs/adr/016-kg-first-idaten-qa.md)

## 回答範囲

**答える**: いだてん岱明の練習・駅伝・記録・名簿・大会予定などコーパス内の内容  
**答えない**: 天気・一般雑談など（定型拒否）  
**コーパスに無い事実**: 「コーチに直接聞いてください。」（内部用語「コーパス」は出さない）

## セキュリティ / プライバシー

- 生徒名簿等の PII を含む。LINE は関係者向けチャネル前提。
- 運用のため **userId のみ** Runtime Logs に出す（`line message userId=` / `line denied userId=`）。**質問本文は出さない**。
- 署名不正は 401。

## 設計

- [ADR 015](../docs/adr/015-line-idaten-qa-backend.md)
- [ADR 016](../docs/adr/016-kg-first-idaten-qa.md)
- [ADR 046](../docs/adr/046-kg-analysis-digest-routing.md)（分析ダイジェストの KG 誘導）
- [ADR 047](../docs/adr/047-unnamed-leg-athlete-routing.md)（大会名なしの区間選手質問）
- [ADR 048](../docs/adr/048-nagomi-order-not-kanaguri-ekiden.md)（なごみオーダー ≠ 金栗駅伝）
- [ADR 018](../docs/adr/018-line-denied-user-ids.md)（userId 拒否リスト）
- [Phase 0](../docs/implementation-flow/line-idaten-bot/phase-0.md)
