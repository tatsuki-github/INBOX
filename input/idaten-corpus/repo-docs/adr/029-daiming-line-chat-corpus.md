# ADR 029: 岱明 LINE トークを衛生化してコーパスに載せる

## 状況

保護者グループ「岱明中長距離」と指導者グループの LINE に、
銀マット・合同練習会・集合場所・朝練・引率分担など運用上の一次情報がある。
カレンダーや Drive に無い連絡が多く、LINE Q&A が「コーチに直接聞いて」に落ちやすかった。
一方で生トークには電話番号・住所・人物評などが含まれ、そのまま RAG に載せるのは不適切。

## 決定

1. **衛生化 Markdown** を `out/analysis/line-chats/` に置く
   - `daiming-parents.md` / `daiming-staff.md` / `INDEX.md`
   - 運用・大会・集合の連絡を優先。性格・人物評は載せない（別途削除方針と整合）
2. **任意の生ログ**は `input/external/line/raw/`（`.gitignore`）に置き、
   `scripts/ingest_line_exports.py` で電話番号・郵便番号・住所をマスクして再生成できる
3. **`build_idaten_corpus.py`** 経由で `out-analysis/line-chats` を `rag_index` に載せる
4. **Router / preferred / path bonus** で岱明の連絡系クエリ時に `line-chats` を優先

## 不採用

| 案 | 理由 |
|:---|:---|
| 生トーク全文をコミット | PII・人物評リスク |
| Notion だけに転記 | LINE 固有の集合・マット連絡が落ちる |

## 結果

- 代表質問「岱明の銀マットのサイズは？」→ `line-chats` 抜粋（180cm 等）
- Vitest / pytest で ingest・answer 回帰

## 関連

- ADR 015（LINE Q&A）、016（KG）、028（荒玉概要）
