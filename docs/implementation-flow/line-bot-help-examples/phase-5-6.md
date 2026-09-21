# Phase 5–6 完了メモ: LINE bot 使い方・質問例

## 実装
- `backend/src/domain/canned.ts`: `isHelpOrExampleQuestion` / `buildHelpExamplesText` / `help-examples` canned（コース動画より優先）
- `backend/tests/canned.test.ts`: matcher・文面制約・answer short-circuit
- `docs/adr/053-line-bot-help-examples.md`
- `backend/README.md` 追記

## 検証
- `npm test`（backend）
- `npm run build`（backend）

## レビュー判定
- Lite Path: Phase 2/4 スキップ妥当（LINE テキストのみ）
- Critical / Major: 0
- Approved → コミットメッセージ案を最終応答に含める（自動コミットしない）
