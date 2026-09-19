# ADR 032: 選手名曖昧性解消とランキング／所属全記録の正本ブースト

## Status

Accepted

## Context

LINE Q&A で次の失敗が再現していた。

1. 「高田麻那の記録」で岱明の **高田麻由** が混ざる（姓一致・コーパス上の出現頻度差）
2. 「荒玉駅伝の2位までに入った学校と回数」で表の一部しか返らない
3. 荒玉地区 3000m 最速／男子1500m SB トップ20／ATRC 全記録が、コーパスにあるのに **コーチ誘導** になる

原因は (a) 高校生 SB（`SBデータベース.csv`）がコーパス未収録、(b) 集計ダイジェスト未生成／未インデックス、(c) 近同名ペナルティ無し、(d) ランキング質問のプレビュー幅不足、(e) preferred sources がダイジェストを先頭にしない、だった。

## Decision

1. **正本ダイジェスト**（`out/analysis/`）:
   - `athletes/takada-mana.md`
   - `aragyoku_top2_finish_counts.md`
   - `2026_aragyoku_men_3000m_sb_ranking.md`
   - `2026_aragyoku_men_1500m_sb_individual_top20.md`
   - 既存 `arato-tamana-teams/ATRC.md`
2. **コーパス**: `build_idaten_corpus.py` が `out/analysis` を `out-analysis/` にコピーし、加えて `sb/SBデータベース.csv`（高校生含む）を取り込む
3. **retrieve**: フルネーム完全一致ブースト + 近同名（同姓異名）ペナルティ。空 Drive stub（`_EMPTY.md`）はブロック
4. **answer**: 上記ダイジェストを preferred sources 先頭に。ランキング／全記録／回数質問は offline プレビュー幅を拡大
5. **KG**: QueryHint + Source ノードで同質問をダイジェストへ誘導
6. **回帰**: `backend/tests/answer.test.ts` / `retrieve.test.ts` + `eval-gaps` round 6

## Consequences

- 麻那／麻由の混同が減る（完全一致を優先）
- 地区ランキング・所属全記録がコーチ誘導ではなくコーパス抜粋で返る
- 類似質問（「一番速い」「トップ20」「全記録」「2位以内の回数」）も同じ経路

## Alternatives Considered

- LLM に「同姓は別人」とだけ指示: 却下 — 検索段階で麻由が勝つと抜粋に載る
- SBデータベースのみでランキングをその場計算: 却下 — オフライン応答と再現性のためダイジェスト正本を採用
