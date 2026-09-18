# Phase 3（簡略）: 大会結果 URL

## 構成

```
scripts/build_meet_result_urls.py  → backend/data/meet-result-urls.json
backend/src/domain/meetResultUrls.ts  → find / append / withMeetResultUrls
backend/src/domain/answer.ts          → finalizeAnswerText で付与
```

## ADR

- 永続: `docs/adr/020-meet-result-urls.md`
- テスト戦略: ドメイン単体（`meetResultUrls.test.ts`）が主。answer は deps 注入で必要なら拡張。
  ピラミッド: 単体 ≫ 統合。E2E なし。
