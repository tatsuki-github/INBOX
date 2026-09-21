# 荒玉駅伝 コース動画

荒玉駅伝（玉名荒尾中体連駅伝）のコース動画は、男女別の Google ドライブフォルダにある。

## フォルダ

| 区分 | URL |
|:---|:---|
| 女子 | https://drive.google.com/drive/folders/1no2bVU7GeyVbXFsCG8V8uwM0IuaFoOhi |
| 男子 | https://drive.google.com/drive/folders/17MrxiZ_0CsDBgVrS_O3uZm3Oypu70Uoo |

限定公開YouTubeプレイリスト: https://youtube.com/playlist?list=PLfEmEvJWOhLE&si=xNbUO5aLL8ly9axJ

各フォルダに「全区間」と区間別（女子 1〜5区、男子 1〜6区）の mp4 がある。

## LINE ボット

「コース動画はどこ？」「荒玉の女子3区コース映像」などの質問では:

1. テキストで上記フォルダ URL を案内する（性別に応じて片方、または両方）
2. 区間が特定でき、かつ LINE 取得可能なサイズ・形式の動画がある場合、LINE Video を最大 1 件添付する

正本カタログ: `backend/data/aragyoku-course-videos.json`（再生成: `python3 scripts/generate_aragyoku_course_videos_catalog.py`）

詳細: `docs/adr/044-aragyoku-line-course-videos.md`
