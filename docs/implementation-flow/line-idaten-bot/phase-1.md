# Phase 1（簡略）: 要求 — LINE いだてん岱明 Q&A

## ユーザーストーリー

指導者・いだてん岱明関係者として、LINE 公式アカウントにテキストで質問し、岱明の練習・駅伝・記録・名簿についてコーパス根拠の回答を得たい。無関係な話題には答えてほしくない。

## 受け入れ条件

1. 署名不正の `POST /webhook` は 401
2. コーパス外質問は拒否定型（LLM 非呼び出し）
3. 荒玉駅伝・岱明関連の質問は索引ヒットを根拠に回答（またはオフライン抜粋）
4. ランタイム読取は `input/idaten-corpus` 由来の `rag_index.json` のみ
5. 別 Vercel（Root=`backend`）でデプロイ可能

## テストマッピング

| AC | テスト |
|:---|:---|
| 1 | `tests/webhook.test.ts` / `signature.test.ts` |
| 2 | `tests/scope.test.ts` / `answer.test.ts` / `webhook.test.ts` |
| 3 | `tests/retrieve.test.ts` / `answer.test.ts` |
| 4 | `tests/retrieve.test.ts`（corpus フィールド） |
| 5 | README 手順（手動） |
