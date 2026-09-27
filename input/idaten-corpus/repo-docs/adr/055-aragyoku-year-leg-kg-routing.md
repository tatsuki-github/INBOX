# ADR 055: 荒玉駅伝の年度別区間記録とKGルーティング

## 状況

チーム別 Markdown は全年の出走者と順位を載せているが、年度横断の区間順位や
「年・チーム・区間」の組み合わせをKGから選ぶノードがなく、区間賞・大会記録など
広い QueryHint が先に選ばれることがあった。

## 決定

1. `input/aragyoku/transcripts/{year}-{gender}.json` を正本とする。
2. `scripts/generate_team_record_markdowns.py` は `out/analysis/aragyoku-years/{year}.md` に、
   男女別・区間別の全チーム結果（総合順位、選手、学年、区間記録、累計、通過順位、区間順位）を生成する。
3. KG は `RelayLegResult` ノードを「年×チーム×区間」で作り、年度別 Markdown に直接つなぐ。
   年度・区間順位一覧は年度別ファイルへ、チーム全体・歴代質問はチーム別ファイルへ誘導する。
4. Python と LINE バックエンドのKGクエリは同じ区間結果優先ルールを持つ。
5. 2025年男子・玉陵3区の選手名は成績表画像で一瀬彪眞と確認し、文字起こしと派生データを更新した。

## 生成と検証

- `python3 scripts/generate_team_record_markdowns.py --aragyoku-only`
- `python3 scripts/build_idaten_corpus.py`
- `python3 scripts/build_knowledge_graph.py`
- `python3 scripts/sync_backend_kg.py`
- 回帰: `tests/test_team_record_markdowns.py`, `tests/test_knowledge_graph.py`,
  `backend/tests/kgQuery.test.ts`
