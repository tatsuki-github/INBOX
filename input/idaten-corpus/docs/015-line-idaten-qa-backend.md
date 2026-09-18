# ADR 015: LINE いだてん岱明 Q&A バックエンド（Express / Vercel）

## 状況

いだてん岱明の運用知識は `input/external/`・`input/aragyoku/`・カレンダー YAML などに分散している。
指導者・関係者が LINE 公式アカウントから質問したいが、既存は Python CLI と Next.js（`web/`）のみで、
Messaging API バックエンドが無い。回答範囲を岱明以外に広げると誤答・漏洩リスクがある。

## 決定

1. **新規 `backend/`** を Express + TypeScript で実装し、**別 Vercel プロジェクト**（Root Directory = `backend`）としてデプロイする。既存 `web/` は変更しない。
2. **単一コーパス** `input/idaten-corpus/` を `scripts/build_idaten_corpus.py` でテキストのみ集約する。ランタイムは `backend/data/rag_index.json`（BM25）だけを読み、他リポジトリパスは読まない。
3. **スコープガード**でいだてん岱明以外の質問を拒否し、LLM に投げない。
4. LINE Messaging API: `POST /webhook` で署名検証（HMAC-SHA256）後、同期 reply。非テキストは定型案内。
5. LLM は既定で **Gemini Developer API（無料枠）** — `AI_PROVIDER=gemini`、モデル `gemini-3.5-flash-lite`、`GEMINI_API_KEY`（Google AI Studio）。未設定時はオフライン抜粋。`openai` / `anthropic` も切替可能。

## 不採用

| 案 | 理由 |
|:---|:---|
| `web/` に Route Handler で同居 | ユーザー要求は Express。Root Directory=`web` と衝突 |
| リポジトリ全体を RAG | スコープ外回答・サイズ・PII リスク |
| バイナリ（画像/PDF）をバンドル | Vercel サイズ制限。OCR テキストで足りる |
| Python を Vercel で実行 | Express/Node 要求と運用複雑性 |

## テスト戦略

| 層 | 対象 | 配置 |
|:---|:---|:---|
| ドメイン単体 | scope / signature / BM25 retrieve / answer / reply split | `backend/tests/*.test.ts` |
| コントローラ統合 | `POST /webhook`（署名・拒否・非テキスト） | `backend/tests/webhook.test.ts` |
| E2E | 実 LINE チャネル | 手動（README） |

ピラミッド目安: 単体 多 : 統合 少 : E2E 手動。

## 結果

- `backend/` + Vitest 緑
- コーパス再生成手順を `backend/README.md` に記載
- 関連: ADR 010 / 011、`docs/implementation-flow/line-idaten-bot/`
