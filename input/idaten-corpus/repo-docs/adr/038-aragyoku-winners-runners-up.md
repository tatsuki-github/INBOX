# ADR 038: 荒玉駅伝・年度別優勝＋準優勝を正本化し KG で辿る

- Status: Accepted
- Date: 2026-09-19

## Context

「女子の荒玉駅伝の過去5年間の優勝校、準優勝校は？」で優勝だけが返り、準優勝が欠ける。
原因は (1) `winners-by-year.md` が rank=1 のみ、(2) `top2_finish_counts` は回数集計で年度別準優勝に使えない、(3) offline preview 予算が狭く表を切り捨てる、(4) KG QueryHint が優勝のみを指していた。

## Decision

1. `scripts/build_aragyoku_winners_by_year.py` で transcripts の rank=1/2 から `winners-by-year.md` を再生成（直近5年の男女表を先頭に置く）。
2. preferred / retrieve boost / offline preview で `準優勝`・`過去5年` を winners-by-year に寄せ、回数集計を年度別質問では demote。
3. KG に「過去5年の優勝・準優勝」「準優勝校は？」QueryHint を追加し refs を winners-by-year に直結。
4. ADR 016 の「優勝校」記述を優勝＋準優勝に更新。

## Consequences

- 年度別の優勝・準優勝が一文書で答えられる。
- 「2位までの回数」質問は従来どおり top2_finish_counts を使う。
