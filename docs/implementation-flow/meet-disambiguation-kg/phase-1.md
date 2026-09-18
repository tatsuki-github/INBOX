# Phase 1: 要求分析 — 大会種別誤誘導の解消

## ユーザーストーリー

保護者・部員として、大会名を含む質問をしたとき、別大会（特に荒玉）の結果ではなく、その大会の岱明データが返ってほしい。誤情報は信頼を損なうから。

## 受け入れ条件

| # | 条件 | テスト |
|:---|:---|:---|
| AC1 | 「去年のジュニア駅伝の岱明の結果」の取得ソースに `ジュニア` / `岱明の結果` が含まれ、`aragyoku/*`・`ekiden-ocr/*` が含まれない | `answer.test.ts` 単体 |
| AC2 | 「なごみ駅伝の開催要項」で aragyoku transcripts が先頭ブーストされない | `answer.test.ts` 単体 |
| AC3 | 「去年の荒玉駅伝の優勝校」は従来どおり 2025 優勝校コンテキストを維持 | `answer.test.ts` 回帰 |
| AC4 | KG がジュニア質問で junior meet ノード / 岱明の結果 corpus を返す | `kgQuery.test.ts` |
| AC5 | `detectMeetKind` が ジュニア / なごみ / 荒玉 を正しく分類 | `meets.test.ts` |

## In / Out of Scope

| In | Out |
|:---|:---|
| meet 検出・ソースブースト・KG スコア / QueryHint | 新大会データの追加 OCR |
| router / canned の誤誘導修正 | UI |

## 技術アプローチ

`boostEkidenYearSources` の `/駅伝/` 過大マッチをやめ、`detectMeetKind` で大会種別を判定してからブースト先を分岐する。
