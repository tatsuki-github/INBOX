# Agent instructions (INBOX)

このリポジトリについて質問に答える・変更するときは、次の手順を守ること。

## ナレッジグラフ優先の回答

リポジトリには **検索ルート地図** として `out/knowledge-graph.json` がある。
これは全文の複製ではなく、「何がどこにあるか」のノード／エッジである。

### 必須手順

1. まずナレッジグラフを使う。
   - 読む: `out/knowledge-graph.json`
   - 可視化: `out/knowledge-graph.html`（構造確認用）
     - GitHub のファイル画面では動きません
     - 推奨: `python3 scripts/open_knowledge_graph.py`
   - 印刷用: `out/knowledge-graph.pdf`（HTML と同タイミングで生成）
   - または実行:  
     `python3 scripts/query_knowledge_graph.py --question "<ユーザーの問い>"`
2. 返ってきた **refs（ファイルパス）** を優先して開く。
3. ヒット箇所の **周辺コンテキスト** を使って回答する（ファイル全体を要約しすぎない）。
4. 回答に根拠パスを含める（例: `input/events.2026.yaml`, `out/2026/practice.json`）。
5. KG に無い領域だけ、通常のリポジトリ探索にフォールバックする。

### やってはいけないこと

- KG を無視して最初から広範な grep / 全ファイル読解から始めること（フォールバック時を除く）
- KG の `hint` だけを根拠に断定すること（必ず `refs` 先を読む）

## カレンダー更新と KG 再生成

- `python3 scripts/generate_calendar.py --year YYYY`（または `--all-years`）の成功後、自動で KG が再生成される。
- 手動再生成: `python3 scripts/build_knowledge_graph.py`
- CI: `.github/workflows/knowledge-graph.yml` がコミット済み KG の鮮度を `--check` で検証する。
  ソースを変えたら KG を再生成してコミットすること。

## 外部データ（いだてん岱明）

Notion・Google ドライブ由来のスナップショットは `input/external/` にある。
探索はまず `input/external/INDEX.md`（および drive/notion/github の INDEX）から。
詳細: `docs/adr/010-external-idaten-import.md`

## 関連ドキュメント

- `README.md`（ナレッジグラフ節）
- `docs/data-model.md`
- `docs/ai-practice-generation.md`（練習生成用 RAG は別系統。KG と併用）
