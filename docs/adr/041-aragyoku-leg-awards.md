# ADR 041: 荒玉駅伝の区間賞・区間順位正本

- Status: Accepted
- Date: 2026-09-19

## Context

「2025年の荒玉駅伝の区間賞の名前と学年は？」のような質問が弱い。
既存ルートは次の誤りを起こしやすかった。

1. `aragyoku_meet_records.md`（ボード上部の**歴代区間記録**）と混同する
2. `focus_teams` / `winners-by-year` / OCR に散らばり、当日の区間1位一覧が埋もれる
3. transcript JSON の `split_rank` / `name` / `grade` はあるが、検索用の人が読める正本がない

## Decision

1. `scripts/generate_aragyoku_leg_awards.py` で `input/aragyoku/transcripts/*.json` から
   `out/analysis/aragyoku_leg_awards.md` を生成する。
   - 区間賞 = `split_rank == 1`（同タイムは併記）
   - `split_rank` が全年欠損の年度は区間タイムから再計算
   - 区間別上位3も同文書に載せる（「区間順位」「○区2位」用）
2. `preferredSources` / `narrowExhaustiveSources` で `区間賞|区間順` を検出したら
   `aragyoku_leg_awards.md` を先頭に置く。`meet_records` や focus/winners には流さない。
3. `pathQueryBonus` / `digestPinForQuery` / offline preview 針で該当年セクションを優先する。
4. KG に AnalysisDoc + FAQ を追加する。

## Consequences

- 区間賞・区間順位質問は名前・学年・所属が正本から答えられる。
- 歴代区間記録ボード質問は引き続き `meet_records`。
- corpus / KG 再生成後に反映される（`build_idaten_corpus.py` が生成スクリプトを呼ぶ）。

## Test strategy

- ドメイン: `preferredSources` の順序（単体）
- 振る舞い: `answer.test.ts` で LLM prompt / offline preview に `leg_awards` と選手名が載ること
- ピラミッド: 単体中心（統合は answer 経路で兼ねる）
