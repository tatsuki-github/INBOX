# ADR 022: 中学生 SB CSV を全所属・行単位で Q&A に載せる

## 状況

LINE Q&A のコーパスは `中学生SB_岱明.csv`（岱明フィルタ）だけを同梱し、しかも CSV を 900 字で機械分割していた。
そのため他校選手の SB が答えられず、行の途中で切れて選手名と記録が別チャンクに分かれることがあった。

## 決定

1. `scripts/build_idaten_corpus.py` は `input/external/sb/middle-school/wide/中学生SB.csv` を **全行** `sb/中学生SB.csv` として同梱する（岱明限定をやめる）。
2. `sb/` と `drive-text/記録データベース/` の CSV は **1 行 = 1 チャンク**（ヘッダ繰り返し）で索引化する。
3. 記録質問では `answer.ts` が `sb/`・記録データベースを preferred sources にブーストする。
4. KG ref `input/external/sb/middle-school/wide/中学生SB.csv` を `sb/中学生SB.csv` にマップする。

## 不採用

| 案 | 理由 |
|:---|:-----|
| by-year 全年度を同梱 | 約 25MB。現行シーズン wide で十分。年度横断は別スライス |
| LLM に CSV 全体を渡す | トークン超過。行チャンク + BM25 で足りる |

## 結果

- 他校を含む中学生 SB の氏名質問で行データがヒットする
- 関連: ADR 012, ADR 015, ADR 016
