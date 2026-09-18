# ADR 028: 荒玉駅伝概要 Markdown で区間ペース質問の抜粋を当てる

## 状況

「荒玉駅伝の男子2区を9分でいくとペースはどれくらい？」のような質問では、
区間距離の正本（`docs/aragyoku-ekiden-distance-definitions.md`）が BM25 では当たっても、
preferred 取得が結果板・transcript に偏り、コンテキスト先頭がノイズで埋まった。
距離定義単体には「9分→ペース」の換算例もなく、LLM が算数しづらかった。

## 決定

1. **概要 Markdown** `out/analysis/aragyoku-overview.md` を生成
   - 大会の位置づけ、男女・年度別の区間距離、ペース換算表、FAQ（男子2区 9:00 等）
   - 生成: `scripts/generate_aragyoku_overview.py`（距離は距離定義ドキュメントと同一定数）
2. **`build_idaten_corpus.py`** が再生成時に overview も実行し `out-analysis/` 経由で `rag_index` に載せる
3. **距離・ペース系クエリ**（`ペース|距離|区間|コース|/km|分でいく|分で走`）のときだけ
   `out-analysis/aragyoku-overview.md` と距離定義を preferred 先頭に入れる
4. **pathQueryBonus** で overview / 距離定義 / 歴代平均ペースを加点

## 不採用

| 案 | 理由 |
|:---|:---|
| 全荒玉質問で overview を常時 preferred | 順位・選手質問のコンテキストを圧迫し、オフライン抜粋にパス文字列が混入しやすい |
| LLM に距離を暗記させて算数させる | 年度差（2023以前 vs 2024以降）で誤答しやすい。表を渡す |

## 結果

- 代表質問「男子2区を9分で…」→ 抜粋先頭に FAQ（現行 2.855km → **3:09.1/km**）
- rag_index: overview チャンク追加
- Vitest answer 回帰 + `tests/test_aragyoku_overview.py`

## 関連

- ADR 016（KG 先行）、025（検索精度）、026（100k）、027（チーム別 Markdown）
- `docs/aragyoku-ekiden-distance-definitions.md`
