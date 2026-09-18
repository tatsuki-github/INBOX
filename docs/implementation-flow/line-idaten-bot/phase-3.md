# Phase 3: アーキテクチャ

詳細は [ADR 015](../../adr/015-line-idaten-qa-backend.md)。

```
backend/
  api/index.ts          # Vercel entry
  src/app.ts            # Express
  src/domain/           # scope, answer, llm
  src/rag/              # BM25 retrieve, prompt
  src/line/             # signature, webhook, reply
  data/rag_index.json
```

Phase 4（UI）: スキップ。
