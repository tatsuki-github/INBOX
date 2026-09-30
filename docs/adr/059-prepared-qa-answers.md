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
6. 質問側に西暦があり定型側に無い場合は部分一致を強く減点し、年なし定型へ誤吸されないようにする。
7. 正規化後の完全一致は採用。部分一致同士が僅差のときだけヒットさせず RAG へ落とす。

## Consequences

- ナレッジを増やすほど定型ヒットが増え、生成依存が減る。
- 回答更新は YAML 編集 + sync（推測埋めはしない）。
- 初版は 100 件。2026-09-30 にナレッジ横断で +1000（計 1100）。
  生成: `scripts/generate_prepared_qa_bulk.py` → `scripts/sync_prepared_qa.py`。

## Test strategy

- `backend/tests/preparedQa.test.ts`: 正規化 / 言い換え / 非ヒット / 1100 件ロード
- `answerQuestion` 代表問で `prepared:` ソース
- KG Source 登録と `--check`
