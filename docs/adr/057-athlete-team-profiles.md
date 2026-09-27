# ADR 057: 選手・チームプロフィールと大会記録の接続

## Status

Accepted

## Context

大会結果・SB は大会や年度ごとの資料にあり、選手の学年・所属やチーム構成を横断して検索しにくい。大会記録と基本情報を同じ検索経路で扱うため、プロフィール用 JSON を導入する。

## Decision

1. `input/athlete-team-profiles.json` は `scripts/build_athlete_team_profiles.py` で生成する。
2. 2026年度の岱明プロフィールは、Notion `いだてん岱明生徒` の氏名・学年を起点にする。2026年記録は `out/analysis/notion_records_2026.json` から、氏名・所属（岱明 / 岱明中）・学年が一致する行だけを結び付ける。過去記録は所属別正本 `out/analysis/arato-tamana-teams/岱明中.md` から、氏名が完全一致し年度差と学年差が一致する行だけを結び付ける。
3. 選手プロフィールには Notion ページ ID を識別子として持たせ、学年は年度とセットで扱う。曖昧一致や名前だけの推測で記録を結び付けない。
4. `scripts/build_idaten_corpus.py` はプロフィール JSON を `profiles/athlete-team-profiles.json` に含め、チーム1件・選手1人ごとにチャンク化して BM25 索引へ入れる。各選手チャンクにはその選手に照合済みの大会記録と結果 URL を含める。
5. Knowledge Graph は選手・チームノードを JSON / 記録ソースへ接続し、プロフィールやチーム構成の質問を同 JSON にルーティングする。
6. プロフィールは氏名・学年・所属・競技記録に限定し、連絡先や健康情報は含めない。ソーススナップショットを更新した後にコーパスと KG を再生成する。

## Consequences

- 選手名から、年度・所属を確認したうえで2024年度・2026年度の大会記録と結果 URL をまとめて検索できる（対象者の記録がある年度のみ）。
- 同姓同名の可能性がある場合、氏名だけでの自動統合はしない。
- 現在の生成対象は2026年度岱明の15人。別チーム・年度は対応する正本データを確認してから拡張する。

## Regeneration

```bash
python3 scripts/build_idaten_corpus.py
python3 scripts/build_knowledge_graph.py
python3 scripts/sync_backend_kg.py
```
