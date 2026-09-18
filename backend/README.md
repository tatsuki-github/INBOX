# LINE いだてん岱明 Q&A Backend（Express）

いだてん岱明専用コーパスだけを参照する LINE Messaging API バックエンドです。
Vercel では **別プロジェクト**、Root Directory = `backend`。

## ローカル

```bash
# コーパス + RAG 索引（リポジトリルートで。初回またはソース更新時）
python3 scripts/build_idaten_corpus.py

cd backend
cp .env.example .env
# 必要なら .env を編集（LINE / OPENAI）。無くても health とオフライン回答は動く
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
| LINE 実機 | `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN` + ngrok 等 |

Webhook は `POST /webhook`。LINE 実機検証には [ngrok](https://ngrok.com/) 等で HTTPS 公開し、LINE Developers の Webhook URL に設定します。

## 環境変数

| 変数 | 必須 | 説明 |
|:---|:---|:---|
| `LINE_CHANNEL_SECRET` | 本番 | 署名検証 |
| `LINE_CHANNEL_ACCESS_TOKEN` | 本番 | reply |
| `AI_PROVIDER` | 任意 | `openai`（既定）または `anthropic` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | 任意 | 未設定時はコーパス抜粋のオフライン回答 |
| `PORT` | 任意 | ローカル listen（既定 3001） |

## Vercel

1. 新規プロジェクトをこのリポジトリに接続
2. **Root Directory** = `backend`
3. Framework: Other（`vercel.json` の `@vercel/node` を使用）
4. 上記環境変数を設定
5. Deploy 後、Webhook URL: `https://<deployment>/webhook`
6. LINE Developers で Webhook を有効化し Verify

既存の `web/` 用 Vercel プロジェクトとは **分けて**運用します。

## コーパス規約

- 正本フォルダ: [`input/idaten-corpus/`](../input/idaten-corpus/)（テキストのみ）
- デプロイ同梱索引: [`data/rag_index.json`](data/rag_index.json)
- ランタイムは上記以外のパスを読まない（スコープ漏洩防止）
- 再生成: `python3 scripts/build_idaten_corpus.py` 後にコミット

## 回答範囲

**答える**: いだてん岱明の練習・駅伝・記録・名簿などコーパス内の内容  
**答えない**: 天気・一般雑談など（定型拒否）

## セキュリティ / プライバシー

- 生徒名簿等の PII を含む。LINE は関係者向けチャネル前提。
- アプリログにユーザー ID・質問本文を出さない。
- 署名不正は 401。

## 設計

- [ADR 015](../docs/adr/015-line-idaten-qa-backend.md)
- [Phase 0](../docs/implementation-flow/line-idaten-bot/phase-0.md)
