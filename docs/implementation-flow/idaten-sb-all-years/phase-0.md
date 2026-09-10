# Phase 0: 作業種別記録 — 中学生 SB 全年度取り込み

| 項目 | 値 |
|:---|:---|
| 作業種別 | `extend`（Lite Path） |
| ゴール | t-tsuchiyama パイプラインの全年度中学生 SB を `input/external` に含める |
| 技術スタック | Python / pytest / knowledge-graph（UI なし） |
| 検証対象 | pytest + `build_knowledge_graph.py --check` |
| Docs Sync | 有効（`docs/adr/` 正本） |
| スキップ | Phase 2/4（UI なし）。Phase 1/3 簡略化 |

## ルーター判定

1. bug-fix? No  
2. perf-only? No  
3. 既存コードベース? Yes → Lite  
4. 破壊的契約変更? No → `extend`
