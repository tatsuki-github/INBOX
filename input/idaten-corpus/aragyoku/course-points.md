# 荒玉駅伝 男女コース共通ポイント図解

更新日: 2026-09-30。女子1〜5区・男子1〜6区が共有する6地点の図解。

![荒玉駅伝 男女コース共通ポイント（橋の上）](course-points/aragyoku-course-common-points.png)

- [Google Drive の画像](https://drive.google.com/file/d/1j9iRk5WAnNVdMyO_fDJX5MaMAVDrESzG/view?usp=drivesdk)
- [男女コース動画フォルダ](https://drive.google.com/drive/folders/1hR2ouziPiuo6wg7Z0WWJgDuieYakkd9k)
- ローカル画像: `input/aragyoku/course-points/aragyoku-course-common-points.png`
- 構造化距離対応: `input/aragyoku/course-points.json`
- 図の全体図下にあった「D → 1km（橋） → E → A → B → C → D」の経路表示帯は、指定画像の白い範囲に従って削除済み。進行順の情報は本ページの本文に保持。
- 全体図のD・E・A・B・Cのオレンジの文字ラベルから伸びる装飾線は削除し、地点の丸と文字ラベルだけを残す。
- 全体図のD・E付近の道路は一定幅の滑らかな線に修正。女子5区と男子6区の共通ゴールを、EとAの間で南へ分かれる道の先に表示。ゴールの拡大図は追加しない。
- ゴールへの曲がり角は女子5区GPXの約2.54km地点（北緯32.854100、東経130.537978）。全体図の表現は女子5区・男子6区のコース動画に合わせ、分岐からゴールまで南へ真っすぐ描く。橋の1kmマーカーも動画上の曲がり角直前へ寄せた。動画参照フレーム: `input/aragyoku/course-points/women5-video-overview-goal.png`。GPX走行線の座標確認用参照図: `input/aragyoku/course-points/goal-turn-gpx-reference.png`。

## LINE ボット

「荒玉駅伝のコースの画像は？」「コース図を見せて」「共通ポイントの図」などの質問では:

1. テキストで上記 Google Drive の画像 URL を案内する
2. LINE Image で図解 PNG を 1 枚添付する

正本カタログ: `backend/data/aragyoku-course-images.json`（再生成: `python3 scripts/generate_aragyoku_course_images_catalog.py`）

詳細: `docs/adr/058-aragyoku-line-course-images.md`

## 確定した地点情報

- 女子1区の1km地点は**曲がる手前の直線になっている橋の上**。見出しは「女子1区の1km地点（橋の上）」。
- 全体図の橋の点は南西の曲がり角のすぐ手前に表示。A地点はその角を通過した先なので、拡大図には直線部分だけを表示。
- 橋のマーカーは進行方向の先へ寄せ、全体図の「1km（橋）」は吹き出しのない文字ラベルで表示。Eへつながる吹き出しは削除。
- E地点の拡大図には手前の南西の曲がり角を含め、Eの点は曲がった先の東向きの直線上に表示。
- 1周は**4.855km**。
- 男子1区スタートは**Cの145m手前**。北が上の図ではCの東側。男子1区がCを通過するときは0.145km地点。
- 女子4→5区と男子5→6区の中継所は**同じC地点**。中継所の吹き出しはCだけを指す。
- Dは北西の曲がり角から南へ進んだ直線上。全体図でも曲がり角の頂点や北側の道路に置かない。
- 進行順は **D → 1km（橋） → E → A → B → C → D**。
- 実際は中央線のない狭い道。画像内の「道幅は狭め・中央線なし」の説明行は削除済み。

上記はユーザー確認済みの情報。最終画像はシンプルな道路の模式図。ユーザーの最新指定により衛星写真・田畑・水路の背景を省き、道路、地点、進行矢印だけで示す。正確な縮尺を保証するものではない。

## 男女各区の距離対応

| 共通地点 | 女子 | 男子 |
| --- | --- | --- |
| 女子1区の1km地点（橋の上） | 1区 1.0km地点／3区 1.0km地点／5区 1.855km地点 | 1区 2.0km地点／3区 1.0km地点／4区 2.855km地点／6区 1.855km地点 |
| D地点 | 1区 スタート／2区 1.855km・中継／3区 スタート／5区 0.855km地点 | 1区 1.0km地点／2区 2.855km・中継／3区 スタート／4区 1.855km地点／6区 0.855km地点 |
| B地点 | 1区 3.0km・中継／2区 スタート／4区 1.0km地点 | 2区 1.0km地点／3区 3.0km・中継／4区 スタート／5区 1.855km地点 |
| A地点 | 1区 2.0km地点／3区 2.0km・中継／4区 スタート | 1区 3.0km・中継／2区 スタート／3区 2.0km地点／5区 0.855km地点 |
| C地点 | 2区 1.0km地点／4区 2.0km・中継／5区 スタート | 1区 0.145km地点／2区 2.0km地点／4区 1.0km地点／5区 2.855km・中継／6区 スタート |
| E地点 | 1区 1.145km地点／3区 1.145km地点／5区 2.0km地点 | 1区 2.145km地点／3区 1.145km地点／4区 3.0km・中継／5区 スタート／6区 2.0km地点 |

距離は1周4.855kmと各区間距離を基準にした目安。区間の終点と次区間のスタートは同じ中継所。女子は5区までで、Cは女子4→5区・男子5→6区の中継所。

## 出典と作成方法

- 動画案内: `input/aragyoku/course-videos.md`
- 女子各区GPXと動画の距離・地点記号: `scripts/generate_aragyoku_women_course_videos.py`
- 男子1・3〜6区の動画用派生トラック: `scripts/build_aragyoku_men_gpx_from_women.py`（男子2区は実測GPX）。
- ゴール位置: 女子5区GPX終点（北緯32.850179、東経130.536632）。男子6区は同じ女子5区GPXのトラックを用いるため終点も共通。Aより南西側で、南側道路から分かれた先。
- 動画: `web/public/videos/women-leg1.mp4`〜`women-leg5.mp4`、`men-leg1.mp4`〜`men-leg6.mp4`。
- 画像生成: built-in image_gen。曲がる手前の直線の橋・周回距離・男子スタート位置を反映し、衛星写真を使わないシンプルな道路図に変更。
- 生成プロンプト: `output/imagegen/aragyoku-course-common-points-final-prompt.txt`

旧女子専用図やGPS概算の旧版ではなく、この男女版をコース共通ポイントの参照画像として使う。
