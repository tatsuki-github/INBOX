# ADR 031: QueryHint → Source / Topic ↔ corpus ハブ強化

## Status

Accepted

## Context

KG は回答本文ではなく「どこを読むか」の地図（ADR 016）。
QueryHint が Topic のみに `search_here` していると、2 hop 減衰後に正解 Source の `refs` が preferred に届きにくい。
また `topic:norwegian` / `topic:pace` などはコーパスハブ（`corpus:repo-docs` 等）への保険リンクが薄かった。

## Decision

1. **QueryHint**: 各ヒントに正本 `source:*` / `corpus:*` を直接紐づけ（`documented_in` / `search_here`）。QueryHint ノード自身に target の `refs` をコピーし 0-hop で mapRefs 可能にする。
2. **SOURCE_GLOBS**: 区間概要・優勝校・コース動画・tamana-weather・ADR 002/008 などを Source として登録。
3. **TOPIC_CORPUS_HUBS**: norwegian/pace/practice/meta/injury/ekiden/calendar と欠落していた corpus ハブを明示リンク。
4. **out-analysis ハブ**: topics に `practice` / `pace` / `calendar` を追加（LINE 衛生化・ペース分析を Topic から辿れるように）。

## Consequences

- QueryHint 23/23 が Source または corpus に直接到達
- なごみ/ジュニアは `corpus:drive-text` へ（aragyoku 直結はしない）
- KG 再生成: `python3 scripts/build_knowledge_graph.py` → `scripts/sync_backend_kg.py`

## Alternatives Considered

- `related_to` を大量追加: 却下 — ランタイム展開対象外（ADR 説明どおり）
- 全 Source を全 Topic に全結合: 却下 — 誤誘導（大会 disambiguation）が増える
