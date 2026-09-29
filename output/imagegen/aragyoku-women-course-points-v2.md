# 荒玉駅伝 女子コースの共通ポイント

女子1〜5区のコース動画と、その作成に使われたGPXを照合した図解。
女子1区の1km地点付近、D・B・A・Cの5地点はいずれも複数区間が通る。

| 地点 | 女子各区から見た距離・役割 |
| --- | --- |
| 女子1区の1km地点付近 | 女子1区 1.0km／女子3区 約1.0km／女子5区 約1.85km |
| D | 女子1区スタート／女子2区 1.855km・中継／女子3区スタート／女子5区 約0.86km |
| B | 女子1区 3.0km・中継／女子2区スタート／女子4区 約1.0km |
| A | 女子1区 約2.0km／女子3区 2.0km・中継／女子4区スタート |
| C | 女子2区 約1.0km／女子4区 2.0km・中継／女子5区スタート |

## 根拠

- 動画案内: `input/aragyoku/course-videos.md`
- 動画カタログ: `backend/data/aragyoku-course-videos.json`
- 実際に参照した映像: `web/public/videos/women-leg1.mp4`、`web/public/videos/women-leg2.mp4`
- 女子動画フォルダ: https://drive.google.com/drive/folders/1no2bVU7GeyVbXFsCG8V8uwM0IuaFoOhi
- 元GPX: `/Users/t-tsuchiyama/Downloads/荒玉駅伝女子1区.gpx`〜`荒玉駅伝女子5区.gpx`
- 地点記号と正式距離の対応: `scripts/generate_aragyoku_women_course_videos.py` の `CHECKPOINTS`、`WOMEN_OFFICIAL_METRES`
- 作業用の計算結果: `work/aragyoku-point-reference/points.json`

## 距離の扱い

動画作成スクリプトと同様に、各GPXの累積距離を公式区間距離へ比例補正した。
中継所は区間の始終点で対応付け、途中通過は同じ地点へ最も近いGPX線分を照合した。
GPXの始終点には数mの記録差があるため、中継の出発は0kmとして扱う。
公式区間距離は女子1区3,000m、2区1,855m、3区2,000m、4区2,000m、5区3,000m。

途中通過の計算値は、女子1区1km地点付近で女子3区995.7m・女子5区1,853.9m、Dで女子5区863.2m、Bで女子4区999.7m、Aで女子1区2,003.5m、Cで女子2区998.4m。
画像では読みやすく丸め、「約」と表示した。地図は北が上。1km地点は南西の曲がり角の直前付近。

生成方法: built-in image_gen。生成プロンプトは隣接する `aragyoku-women-course-points-v2-prompt.txt` に保存。
