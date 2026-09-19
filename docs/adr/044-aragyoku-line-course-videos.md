# ADR 044: 荒玉駅伝コース動画を LINE Video で返す

- Status: Accepted
- Date: 2026-09-19

## Context

コース動画の質問に対し、これまで Drive フォルダ URL のテキスト案内のみだった。
男女別フォルダに全区間・区間別 mp4 があり、結果ボード画像（ADR 043）と同様に
トーク内で直接再生したい。

- 女子: https://drive.google.com/drive/folders/1no2bVU7GeyVbXFsCG8V8uwM0IuaFoOhi
- 男子: https://drive.google.com/drive/folders/17MrxiZ_0CsDBgVrS_O3uZm3Oypu70Uoo

LINE Messaging API の Video は HTTPS の mp4（≤200MB）とプレビュー画像 URL が必要。

調査結果:

- `lh3.googleusercontent.com/d/{id}` は動画でも JPEG サムネ → `previewImageUrl`
- `drive.usercontent.google.com/download?id={id}&export=download` は区間動画（〜45MB）で
  `video/mp4`、全区間（150MB+/229MB）は virus-scan 用 HTML → LINE 不可
- 男子全区間はサイズも 200MB 超

## Decision

1. `scripts/generate_aragyoku_course_videos_catalog.py` で
   `backend/data/aragyoku-course-videos.json` を生成する。
2. HEAD で `Content-Type: video/mp4` かつ size ≤ 200MB のときだけ `lineEligible: true`。
3. `selectAragyokuCourseVideos(question)`:
   - `isAragyokuCourseVideoQuestion` のときのみ
   - 女子のみ → 女子 / それ以外（男子・両方・なし）→ 男子（最大 1 件）
   - `N区` あり → その区間 / なし → 全区間
   - `lineEligible` でない・カタログ無し（例: 女子6区）→ Video なし
4. `buildReplyMessages` がテキストのあとに Video を最大 1 件付け、合計 ≤ 5。
5. canned テキストは性別に応じたフォルダ URL（未指定時は男女両方）。
6. `answered` / `offline` のみ添付。

## Consequences

- 区間指定の質問ではトーク内で動画が再生できる。
- 全区間は現状 LINE 添付不可（テキストの Drive 案内のみ）。再ホストすれば別 ADR。
- Drive 共有が「リンクを知っている人が閲覧可」であることが前提。
- usercontent / lh3 の仕様変更リスクあり（壊れたらカタログ再生成）。

## Test strategy

- 単体: `aragyokuCourseVideos.test.ts`（性別・区間・eligible・max1）
- canned / `buildReplyMessages` の Video 添付・スキップ
- `backend` の `npm test` / `npm run build`
