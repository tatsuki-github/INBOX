# ADR 029: 岱明 LINE トークを衛生化してコーパスに載せる

## 状況

保護者グループ「岱明中長距離」と指導者グループの LINE に、
銀マット・合同練習会・集合場所・朝練・引率分担など運用上の一次情報がある。
さらに有田大将（ゆくゆく岱明で指導）との DM には、分割走・補強・荒玉準備・合同練習の
指導相談がまとまっており、カレンダーや Drive だけでは落ちる。
一方で生トークには電話番号・住所・人物評などが含まれ、そのまま RAG に載せるのは不適切。

## 決定

1. **衛生化 Markdown** を `out/analysis/line-chats/` に置く
   - `daiming-parents.md` / `daiming-staff.md` / `arita-taisho.md` / `INDEX.md`
   - 運用・大会・集合・指導方針を優先。性格・人物評・詳細傷病は載せない
2. **任意の生ログ**は `input/external/line/raw/`（`.gitignore`）に置き、
   `scripts/ingest_line_exports.py` で電話番号・郵便番号・住所をマスクして再生成できる
   - 有田メモはキュレーション優先（生ログが無くても curated MD を保持）
3. **`build_idaten_corpus.py`** 経由で `out-analysis/line-chats` を `rag_index` に載せる
4. **Router / preferred / path bonus** で岱明の連絡・有田系クエリ時に `line-chats` を優先
5. **KG** に `line-chats` Source と QueryHint（銀マット／有田・補強）を登録する

## 不採用

| 案 | 理由 |
|:---|:---|
| 生トーク全文をコミット | PII・人物評リスク |
| Notion だけに転記 | LINE 固有の集合・マット・指導相談が落ちる |

## 結果

- 代表質問「岱明の銀マットのサイズは？」→ `line-chats` 抜粋（180cm 等）
- 「有田の補強・分割走」→ `arita-taisho.md`
- Vitest / pytest で ingest・answer 回帰

## 関連

- ADR 015（LINE Q&A）、016（KG）、028（荒玉概要）
