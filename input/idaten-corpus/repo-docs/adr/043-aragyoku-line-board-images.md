# ADR 043: 荒玉駅伝該当年の結果ボードを LINE Image で返す

- Status: Accepted
- Date: 2026-09-19

## Context

特定年の荒玉駅伝質問（区間賞・順位など）に対し、テキスト回答だけでは結果ボードを
見られない。公開 Drive フォルダに結果画像がある。

- フォルダ: https://drive.google.com/drive/folders/1XRxBeG1wkG3c92Y-h5ycPgbBL7Ep1ief
- ファイル ID 正本: `input/aragyoku/transcripts/{year}-{gender}.json` の `source_drive_id`

LINE Messaging API は `type: "image"` で HTTPS 直リンクの画像を返せる（リンク文字列ではない）。

## Decision

1. `scripts/generate_aragyoku_board_images_catalog.py` で
   `backend/data/aragyoku-board-images.json` を生成する。
2. URL は `https://lh3.googleusercontent.com/d/{fileId}`（preview は `=w480`）。
   Drive の `uc?export=` は 303 が多く LINE 取得に不向きなため不採用。
3. `selectAragyokuBoardImages(question)`:
   - 荒玉/中体連 + 特定年（西暦 or 去年/今年）のときのみ
   - 男子のみ → 1 枚 / 女子のみ → 1 枚 / 性別なし → 最大 2 枚（男女）
   - 複数年 → 最新年を 1 つ
4. `buildReplyMessages` がテキストのあとに Image メッセージを付け、合計 ≤ 5。
5. `answered` / `offline` のみ添付。`refused` には付けない。

## Consequences

- 該当年の質問で結果ボードがトーク内にそのまま表示される。
- Drive の共有設定が「リンクを知っている人が閲覧可」であることが前提。
- lh3 URL の仕様変更リスクあり（壊れたらカタログ再生成 or URL 形式の見直し）。

## Test strategy

- 単体: `aragyokuBoardImages.test.ts`（性別・年・max2・reply 組み立て）
- 統合: 既存 webhook テストは退行なし（画像なし経路）
