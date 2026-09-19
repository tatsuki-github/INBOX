# 作業種別記録: KG 強化による backend 回答精度向上

## 判定結果

- **作業種別**: extend
- **実行パス**: Lite
- **リダイレクト先**: なし
- **検証対象パッケージ**: backend（Python KG builder/query 含む。frontend 変更なし）

## Docs Sync 設定（Phase 0d）

| 項目 | 記録 |
|:-----|:-----|
| **Docs Sync** | 有効（`docs/` が正本。`specs/` なし） |
| **Docs Root(s)** | docs |
| **マッピング参照** | README インデックス + `docs/adr/` 慣例 |
| **ADR 永続化先** | `docs/adr/`（次番号 046） |

## 判定根拠（4 問）

| # | 質問 | 回答 | 根拠 |
|:--|:-----|:-----|:-----|
| 1 | 再現可能な不具合か？ | No | 単一の期待 vs 実際ではなく、探索地図の被覆不足による精度向上要求 |
| 2 | 新機能なし・改善のみか？ | No | 分析ダイジェストの Source 自動登録・QueryHint・mapRefs 年次修正を含む既存 KG の拡張 |
| 3 | 既存コードベースへの変更か？ | Yes | `scripts/knowledge_graph/` と `backend/src/kg/` |
| 4 | 契約破壊 / レガシー統合か？ | 非破壊拡張 | KG JSON はノード追加。rag_index / LINE API 契約は不変 |

## Lite Path スキップ記録

| Phase | 実行 | スキップ理由 |
|:------|:-----|:-------------|
| 1 | 簡略化 | 既存 ADR 016/025/031/036 と probe-v7 ギャップが調査入力になる |
| 2 | スキップ | UI なし（LINE テキスト回答の探索地図のみ） |
| 3 | 簡略化 | 既存 3 層（KG builder / mapRefs / query scoring）に差分追加。ADR 1 本 + テスト戦略 |
| 4 | スキップ | 新規ビジュアルなし |
| 5 | 実行 | TDD（mapRefs・KG query）+ 既存 backend 回帰 |
| 6 | 実行 | 既存振る舞い退行なしを含む |

## ゴール

保護者・部員が LINE で学校別平均・優勝差・チーム区間・所属全記録・トラック周長を聞いたとき、KG が正本ダイジェスト（`out-analysis/`・`practice/`）へ誘導し、誤ソースやコーチ誘導を減らす。

## 技術スタック（上書き）

- Python 3（`scripts/knowledge_graph/`、`.venv` / `uv`）
- backend: Express + TypeScript + Vitest（KG ランタイムは `backend/data/knowledge-graph.json` のみ）

## 検証対象

- backend: `npm test` / `npm run lint` / `npm run build`
- Python: `tests/test_knowledge_graph.py`（`.venv`）

## QE0

- スコープを「KG 被覆 + mapRefs + スコア同期」に限定。retrieve/answer の preferred ハードコード増殖は Out of Scope（既存 ADR 036 ブーストは維持）。
- 1 ワークフローに収まる（コンポーネント < 10、主要ファイル < 10）。
- ベクトル DB 導入はしない（ADR 016）。

## R0

- **Approved** — extend 判定妥当。Phase 2/4 スキップは UI 非接触のため合理。Docs Sync は `docs/adr/`。
