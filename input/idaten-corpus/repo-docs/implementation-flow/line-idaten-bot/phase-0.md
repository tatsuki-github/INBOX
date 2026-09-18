# Phase 0: 作業種別記録 — LINE いだてん岱明 Q&A バックエンド

| 項目 | 値 |
|:---|:---|
| 作業種別 | `extend`（Lite Path） |
| ゴール | LINE 公式アカウントへのテキスト質問に対し、いだてん岱明コーパスのみから回答する Express API を別 Vercel プロジェクト（`backend/`）にデプロイする |
| 技術スタック | Express + TypeScript + `@line/bot-sdk` + Vitest + BM25 RAG + LLM（anthropic \| openai） |
| 検証対象パッケージ | `backend` のみ（`web/` 非変更） |
| Docs Sync | 有効 — Root: `docs/`、ADR 正本: `docs/adr/`（015） |
| 優先特性 | UX（明確な拒否）> 応答速度（Vercel 10s）> 開発速度 |

## ルーター判定

1. bug-fix? No  
2. perf-only? No  
3. 既存コードベースへの変更? Yes → Lite Path  
4a. 既存契約破壊? No  
4b. レガシー段階差し込み? No  
4c. → **`extend`**

## スキップ判定

| Phase | 扱い | 理由 |
|:---|:---|:---|
| 1 調査 | 簡略 | ADR 010/011・`input/external/` が正本。LINE/Vercel Express は標準 |
| 2 UX | 会話 UX のみ | UI は LINE クライアント |
| 3 アーキテクチャ | 実施 | コーパス境界・署名・デプロイが新規 |
| 4 UI/ビジュアル | **スキップ** | Web UI なし |
| 5–6 | 実施 | TDD + Docs/ADR |

## スコープ

**In**: いだてん岱明 Q&A、コーパス外拒否、LINE webhook、Vercel 手順  
**Out**: 練習 AI 生成移植、Norwegian 一般論のみ、バイナリ配信、`web/` 統合、リッチメニュー

## コーパス規約

- 単一フォルダ: `input/idaten-corpus/`（ビルド生成・テキストのみ）
- ランタイム索引: `backend/data/rag_index.json`
- `backend` は上記以外のリポジトリパスを読まない
