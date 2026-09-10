# 荒玉中体連駅伝歴代 media

目的: 結果ボード画像と文字起こしをローカルに置き、ナレッジグラフからパス参照できるようにする。

## 現状
- **構造化 OCR**: `ocr/*.md` — Notion 行プロパティ（岱明順位・記録・気温など）を全 27 件分保存済み
- **画像バイナリ**: Notion MCP が attachment をバイナリ配布できないため **未取得**。Drive フォルダ `荒玉駅伝歴代` も空
- 取得後は `{year}-{男子|女子}.png` を同ディレクトリに置き、`.meta.json` の `binary_saved` を更新する

## パス規約
| 種別 | パス |
|:---|:---|
| 画像 | `input/external/notion/media/ekiden-history/{year}-{性別}.png` |
| メタ | 同名 `.meta.json` |
| OCR | `ocr/{year}-{性別}.md` |
| 行データ | `input/external/notion/databases/荒玉中体連駅伝歴代/rows.json` |

## KG
`media-manifest.json` → MediaAsset ノード。トピック `ekiden` / `athlete_records`。
