# Phase 5–6: LINE userId 拒否リスト

## 実装

- `domain/deny.ts` — parse / isDenied
- webhook: `source.userId` ログ + 拒否時無応答
- `LINE_DENIED_USER_IDS` env、ADR 018、README 運用手順

## 検証

- `npm test` / `npm run build`（backend）

## 判定

Approved
