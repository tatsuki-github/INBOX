# eval-line SUMMARY

- 目的: LINE `line-chats`（parents / staff / arita）の未網羅質問を発見して潰す
- ランナー: `cd backend && npx tsx scripts/eval-line/run.ts --offline`
- バンク: `backend/data/eval-line/questions.json`
- 2026-09-18: **46/46 PASS**（オフライン根拠）
- 主な修正:
  - `boostDaimingLineSources` で digest を具体パス優先
  - 地点分担・有田指導時に荒玉 overview / transcripts を抑制
  - `previewForOffline` を質問キーワード窓に対応
  - digests 先頭に FAQ 要約・要点を追加
