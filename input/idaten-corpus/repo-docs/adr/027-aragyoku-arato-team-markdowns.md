# ADR 027: 荒尾玉名・荒玉チーム別記録 Markdown で検索ヒット強化

## 状況

荒玉駅伝の細かい質問（区間選手・下位チーム・年度横断）や、荒尾玉名の所属単位のトラック記録質問で、
正解がコーパスにあってもチャンクが散在し BM25 が外れ、「コーチに直接聞いてください」に落ちることがあった。
岱明向けの `taimei-records-2012-2025.md` はあるが、他チーム／所属の一覧 Markdown が無かった。

## 決定

1. **生成スクリプト** `scripts/generate_team_record_markdowns.py`
   - `out/analysis/arato-tamana-teams/{所属}.md` … Notion 中学生記録（2024–2026）を所属別・年度別に全件表
   - `out/analysis/aragyoku-teams/{チーム}.md` … transcripts から荒玉駅伝のチーム別歴代（区間付き）
2. **`build_idaten_corpus.py`** が再生成時に上記を実行し、`out-analysis/` 経由で `rag_index` に載せる
3. **transcript チャンク**を JSON dump から日本語の区間説明に変更し、全チームを要約に含める（上位8止めを廃止）
4. **Router / preferred / path bonus** で `out-analysis/aragyoku-teams`・`arato-tamana-teams` を優先

## 不採用

| 案 | 理由 |
|:---|:---|
| PDF のみ追加 | テキスト検索に弱い |
| ベクトル DB | 運用コスト。チーム単位 Markdown + BM25 で足りる |

## 結果

- 生成: arato-tamana-teams **22** ファイル + aragyoku-teams **17** ファイル（各 INDEX 付き）
- rag_index: **9236** chunks（チーム MD + transcript 日本語化）
- Vitest **111** passed / `npm run build` 成功
- 代表質問「2025年荒玉駅伝男子の菊水の1区は誰？」→ コンテキストに松浦眞大・`aragyoku-teams/菊水.md`
- 再実行:
  - `/opt/miniconda3/bin/python scripts/generate_team_record_markdowns.py`
  - `/opt/miniconda3/bin/python scripts/build_idaten_corpus.py`

## 関連

- ADR 016（KG 先行）、022（SB）、025（検索精度）、026（100k コンテキスト）
