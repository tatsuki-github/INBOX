# ADR 059: 想定質問の定型回答ナレッジ（Prepared Q&A）

- Status: Accepted
- Date: 2026-09-30

## Context

LINE Q&A は RAG / LLM で都度組み立てると、ぶれ・コーチ誘導・根拠ずれが起きやすい。
運用上は「想定される質問にはあらかじめ用意した回答をほぼそのまま返す」方が安定する。
コース動画・ヘルプ等の動的 canned はあるが、件数拡張しづらい。

## Decision

1. 正本 `input/faq/prepared-qa.v1.yaml` に想定質問・言い換え・定型回答・根拠パスを置く。
2. `scripts/sync_prepared_qa.py` が `backend/data/prepared-qa.json` とコーパスへ同梱する。
3. `matchPreparedAnswer` が文体ゆらぎ（正規化・言い換え・トークン類似）でヒットしたら、
   回答本文をほぼそのまま返す（`sources: prepared:<id>`）。
4. 優先順位: 動的 canned（ヘルプ / コース動画・画像）→ Prepared Q&A → 現行 RAG/LLM。
5. 相対年（去年/昨年/今年）はマッチ前に西暦へ展開する。
6. **年を指定しない質問は今年度（defaultYear / 年度）として解釈する。**
   過去年エントリの想定質問には西暦または「去年」等を必ず付ける。
7. 質問側に西暦があり定型側に無い場合は部分一致を強く減点し、年なし定型へ誤吸されないようにする。
8. 正規化後の完全一致は採用。部分一致同士が僅差のときだけヒットさせず RAG へ落とす。
   年なし同士の同点では今年度エントリを優先する。

## Quality bar（回答本文）

ユーザー向け本文に次を入れない:
- リポジトリパス（`input/` `out/` `docs/` `scripts/` 等）や内部ファイル名
- `状態: scheduled` のような運用ラベル、`出典: out/...`、`正本は xxx.md`
- Markdown 表の生ダンプや分析レポート全文の貼り付け
- **リンクでない参考文献**（「徹底対策ガイド 4.16」「大会要項で再確認」など）。
  公開 URL（`https://...`）がある場合だけ載せる

回答は短い事実文＋必要なら公開 URL（Drive / 大会結果）に留める。
**推測・幻覚で埋めない。** 荒玉のチーム結果は transcripts /
`men_full`・`women_full` の順位・総合・区間選手のみを書く（去年＝今年度−1）。
定型未ヒットで LLM が別年を返す事故を避けるため、「結果は？」自然文も収録する。
全件の品質回収: `scripts/polish_prepared_qa_quality.py` /
`scripts/strip_prepared_qa_nonlink_refs.py` → `scripts/sync_prepared_qa.py`。

## Consequences

- ナレッジを増やすほど定型ヒットが増え、生成依存が減る。
- 回答更新は YAML 編集 + sync（推測埋めはしない）。
- 初版は 100 件。以降は同形式で追記（年なし＝今年度ポリシーを維持）。
  生成: `scripts/generate_prepared_qa_bulk.py` /
  `scripts/generate_aragyoku_athlete_sb_qa.py`（荒玉地区選手の年度別SB）/
  `scripts/generate_prepared_qa_knowledge_1000.py`（ナレッジカバー拡充）/
  `scripts/generate_prepared_qa_course_points.py`（コース地点）/
  `scripts/generate_prepared_qa_prefectural_top2.py`（荒玉2位まで→県駅伝出場）/
  `scripts/generate_prepared_qa_daiming_rivals.py`（岱明ライバル校）/
  `scripts/generate_prepared_qa_aragyoku_aliases.py`（荒玉の呼び方揺れ）/
  `scripts/generate_prepared_qa_athlete_all_records.py`（選手全記録=トラック＋駅伝・ロード）/
  `scripts/gap_crush_prepared_1000.py`（未カバー質問を1問ずつ発見→1000件追加、
  `--batch b` で第2バッチ）/
  `scripts/polish_prepared_qa_quality.py`（全件のユーザー向け品質改修）/
  `scripts/generate_prepared_qa_nagomi_team_results.py`（なごみ駅伝チーム別結果）/
  `scripts/refresh_prepared_qa_team_results.py`（荒玉チーム結果・去年/結果は？）/
  `scripts/refresh_prepared_qa_leg_boards.py`（区間順位ボード・去年語順）→
  `scripts/sync_prepared_qa.py`。
  大会名正規化: `backend/src/domain/aragyokuAliases.ts`
  （荒玉中体連駅伝 / 郡市駅伝 / 玉名荒尾中体連駅伝 → 荒玉）。

## Test strategy

- `backend/tests/preparedQa.test.ts`: 正規化 / 言い換え / 年なし＝今年度 / 非ヒット / 件数ロード
- `answerQuestion` 代表問で `prepared:` ソース
- KG Source 登録と `--check`
