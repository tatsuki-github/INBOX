# ADR 020: 大会結果 URL を CSV 索引から LINE 回答へ付与

## 状況

記録 CSV（`参考` / `*URL`）とカレンダー `source.csv` には公式結果ページの URL があるが、
LINE Q&A は `formatForLine` で Markdown リンクを剥がし、プロンプトでもパス／URL を書かせない方針だったため、
結果質問でも公式ページへ飛べなかった（荒玉コース動画の canned Drive URL だけが例外）。

## 決定

1. **ビルド時索引**: `scripts/build_meet_result_urls.py` が記録 CSV + `out/*/source.csv`（公式ホストのみ）から
   `backend/data/meet-result-urls.json` を生成し、Vercel 同梱する。
2. **回答後処理**: LLM／オフライン本文を `formatForLine` したあと、`withMeetResultUrls` が大会名スコアで
   URL を最大 3 件、末尾に `結果ページ:` 付きの素の http(s) 行として追記する（プロンプトに頼らない）。
3. **付与条件**: クエリが結果系（結果／順位／タイム等）かつ大会キューのスコアが閾値以上のときのみ。
   ヒットが無ければ本文のみ（偽 URL 禁止）。
4. **年**: 明示が無ければ `defaultYear`（現行シーズン）を優先。

## 不採用

| 案 | 理由 |
|:---|:-----|
| LLM に URL を書かせる | 幻覚・format 剥がしで不安定 |
| Drive `viewUrl` を返す | ユーザー要求は公式結果ページ。Drive は別系統 |
| 全質問に無差別付与 | 集合時間などの誤誘導になる |

## 結果

- 結果系の大会質問で CSV 由来 URL が LINE 上でタップ可能になる
- 関連: ADR 015, ADR 016, ADR 017
