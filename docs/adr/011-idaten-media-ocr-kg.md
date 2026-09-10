# ADR 011: いだてん岱明メディア（画像・OCR）とナレッジグラフ参照

## 状況
荒玉駅伝で勝つために、結果ボード画像・分析 PDF・練習フォトを LLM / 人が辿れる必要がある。ADR 010 は巨大バイナリをスタブ優先としていたが、**駅伝結果画像は本文相当の一次情報**であり、パスを KG に載せれば LLM が必要時に読める。

## 決定
1. **優先メディアをバイナリ保存する**
   - 荒玉中体連駅伝歴代の結果画像（Notion 添付）→ `input/external/notion/media/ekiden-history/{year}-{性別}.png`
   - 分析 PDF（荒玉男子/女子/関係図）→ `input/external/drive/shared/分析/*.pdf`（≤8MB）
   - 共有フォトの画像（動画はスタブ継続可）→ `input/external/drive/shared/フォト/**`
2. **OCR / 文字起こしを併置する**
   - `{stem}.ocr.md` または `ocr/{stem}.md`
   - 駅伝歴代は画像未取得時でも Notion 行プロパティから構造化文字起こしを必ず置く
3. **索引** `input/external/media-manifest.json` に path / OCR / topic / binary_saved を列挙する
4. **ナレッジグラフ**
   - `MediaAsset` ノード（refs = ローカルパス、hint に OCR パス）
   - Topic `ekiden` を追加し QueryHint「荒玉駅伝の歴代は？」を登録
5. **未取得バイナリ**は meta に attachment ID を残し、Drive フォルダ `荒玉駅伝歴代` への手動/追従アップロードで埋める

## 不採用
| 案 | 理由 |
|:---|:---|
| 全フォト動画もバイナリ | サイズ肥大。画像優先 |
| OCR のみで画像不要 | 順位表の読み取り・検証に原画が必要 |
| KG に画像 base64 埋め込み | グラフ肥大・差分ノイズ |

## テスト戦略
- `media-manifest.json` 存在・駅伝 OCR 27 件・分析 PDF 3 件
- KG に `MediaAsset` / `topic:ekiden` / 駅伝 QueryHint
- `build_knowledge_graph.py --check`
