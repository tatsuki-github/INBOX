# Phase 0–6: 不明情報の案内文を「コーチに直接聞いてください。」へ

| 項目 | 値 |
|:---|:---|
| 作業種別 | `extend`（Lite Path） |
| ゴール | コーパスに無い／不明な事実のユーザー向け文言を「コーパスに情報がありません」から「コーチに直接聞いてください。」に変更 |
| 検証 | `backend` npm test / build |
| Docs Sync | `docs/adr/015`・`backend/README.md`・本ディレクトリ |

## 変更

- `MISSING_INFO_MESSAGE` を `backend/src/rag/prompt.ts` に定義
- LLM system prompt とオフライン空ヒット回答の両方で同一文言を使用
- 天気等の `OUT_OF_SCOPE_MESSAGE` は変更しない（対象外）

## 検証

- answer テスト: 空 retrieve → コーチ文言、system prompt にコーチ文言
- `npm test` / `npm run build`
