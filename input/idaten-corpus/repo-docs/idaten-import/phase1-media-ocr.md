# Phase 1 — 要求（メディア・OCR）

## ユーザーストーリー
コーチとして、荒玉駅伝の歴代結果画像と文字起こしをリポジトリから辿りたい。なぜなら勝つための戦術・ペース比較に一次情報が必要だから。

## 受け入れ条件
1. 駅伝歴代の構造化 OCR（または同等テキスト）が 27 件ローカルにある
2. 分析 PDF（荒玉男子/女子/関係図）がバイナリ＋OCR で保存されている
3. フォト画像バイナリが保存され、`media-manifest.json` にパスがある
4. KG に `MediaAsset` と `topic:ekiden` があり、refs にローカルパスが含まれる
5. `pytest` と `build_knowledge_graph.py --check` が通る

## Out of Scope
- Notion attachment の自動バイナリ取得が MCP で不可能な場合の手動アップロード待ち（メタ＋OCR は先行）
- 動画バイナリ、市販書籍全文
