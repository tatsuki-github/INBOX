# 調査レポート: 大会結果 URL 回答付与

## ユーザーストーリー
保護者／コーチとして、大会結果の質問をしたら公式結果ページの URL も欲しい。なぜなら本文だけでは確認・共有しづらいからだ。

## 受け入れ条件
1. [x] 「熊本市選手権の結果」等で回答末尾に CSV 由来の http(s) URL が含まれる
2. [x] URL が無い大会では従来どおり本文のみ（偽 URL を作らない）
3. [x] Markdown リンク剥がし後も **素の URL 行は残る**
4. [x] 荒玉コース動画 canned URL は退行しない
5. [x] backend `npm test` / `npm run build` 合格

## テストマッピング

| # | AC | テスト | 層 |
|:--|:---|:-------|:---|
| 1 | URL 付与 | 単体 TDD | meetResultUrls + answer |
| 2 | 欠落時 | 単体 | meetResultUrls |
| 3 | format 保持 | 単体 | format.test |
| 4 | canned | 既存 | canned / answer |
| 5 | verify | npm | backend |

## スコープ

| In | Out |
|:---|:----|
| 索引生成・回答末尾付与 | Drive `viewUrl` / Google Docs リンク |
| 結果系クエリでの付与 | 全質問への無差別 URL |
| ADR 020 | frontend |

## 技術アプローチ
- ビルド時に CSV → `backend/data/meet-result-urls.json`
- `findMeetResultUrls(query)` で大会名スコアリング
- `answerQuestion` が LLM/offline 後に URL を追記（プロンプトに頼らない）
