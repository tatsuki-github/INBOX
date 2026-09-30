# ADR 058: 荒玉駅伝コース図解画像を LINE Image で返す

- Status: Accepted
- Date: 2026-09-30

## Context

「荒玉駅伝のコースの画像は？」「コース図を見せて」などの質問に対し、
テキスト URL だけではトーク内で図解を見られない。男女コース共通ポイント図解は
Drive に公開済みで、結果ボード（ADR 043）・コース動画（ADR 044）と同様に
LINE Image で返したい。

- 正本メタ: `input/aragyoku/course-points.json`（`drive_file_id`）
- ナレッジ: `input/aragyoku/course-points.md`
- Drive: https://drive.google.com/file/d/1j9iRk5WAnNVdMyO_fDJX5MaMAVDrESzG/view

## Decision

1. `scripts/generate_aragyoku_course_images_catalog.py` で
   `backend/data/aragyoku-course-images.json` を生成する。
2. URL は `https://lh3.googleusercontent.com/d/{fileId}`（preview は `=w480`）。
3. `isAragyokuCourseImageQuestion` / canned で Drive URL テキストを返す
   （動画質問・結果ボード質問とは排他。動画キーワード優先）。
4. `selectAragyokuCourseImages` が最大 1 枚を選び、`buildReplyMessages` が
   ボード画像・Video と合算で最大 2 件添付する。
5. KG に QueryHint「荒玉駅伝のコースの画像は？」を登録し、
   `course-points.md` / MediaAsset へ誘導する。
6. `answered` / `offline` のみ添付。

## Consequences

- コース図解の質問でトーク内に画像が表示される。
- Drive 共有が「リンクを知っている人が閲覧可」であることが前提。
- lh3 URL の仕様変更リスクあり（壊れたらカタログ再生成）。

## Test strategy

- 単体: `aragyokuCourseImages.test.ts` / canned matcher
- `buildReplyMessages` の Image 添付・動画との排他
- `backend` の `npm test` / KG `--check`
