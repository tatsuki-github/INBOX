# 調査レポート: KG 強化による backend 回答精度向上

## ユーザーストーリー

いだてん岱明の保護者・部員として、記録・駅伝・練習の具体的な数字を聞きたい。なぜなら、コーパスにあるのにコーチ誘導や別ファイルの抜粋になると信頼できないからだ。

## 受け入れ条件

1. [ ] 「女子800mで岱明の上位3人平均は？」の KG `corpus_sources` に `2026_women_800m_1500m_pb_school_ranking.md` が含まれる
2. [ ] 「2025年岱明男子の優勝との差は？」の KG が `aragyoku_2024_2025_focus_teams.md` を返す
3. [ ] 「菊水の荒玉駅伝の1区は誰？」の KG が `aragyoku-teams/菊水.md` を返す
4. [ ] 「金栗PROJECT所属選手の全記録」の KG が `arato-tamana-teams/金栗PROJECT.md` を返し、なごみ大会ハブへ誤誘導しない
5. [ ] `out/daiming-practice-menus-kpace.md` と `out/2026/practice.json` がコーパス `practice/` の実在パスへ map される
6. [ ] 既存ジュニア／なごみ／荒玉歴代の KG 回帰が Green

## 受け入れ条件 → テストマッピング

| # | 受け入れ条件 | テスト種別 | 対象層 | テスト意図 |
|:--|:-------------|:-----------|:-------|:-----------|
| 1 | 学校別平均 | 単体(TDD) | kg query | digest 正本へ 0-hop |
| 2 | 優勝差 | 単体(TDD) | kg query | focus 分析へ。meet_records ボードではない |
| 3 | 菊水 1 区 | 単体(TDD) | kg query | チーム MD ラベル一致 |
| 4 | 金栗PROJECT | 単体(TDD) | kg query | なごみ減点から PROJECT を除外 |
| 5 | practice mapRefs | 単体(TDD) | mapRefs | 年次 JSON / kpace の実在パス |
| 6 | ジュニア回帰 | 回帰 | kgQuery.test.ts | 既存 AC 維持 |

## スコープ

| In Scope | Out of Scope |
|:---------|:-------------|
| KG Source 自動登録（`out/analysis/**/*.md`） | ベクトル DB |
| QueryHint 追加（学校別平均・優勝差・所属全記録・トラック周長） | rag_index 再チャンク |
| mapRefs の practice 年次パス修正 | answer.ts preferred ハードコードの追加増殖 |
| query.ts / query.py スコア同期（金栗PROJECT、digest ブースト） | frontend |
| KG 再生成 + `sync_backend_kg.py` | 新規コーパス本文 |

## 依存関係

- ADR 016（KG 先行）、031（QueryHint→Source）、036（学校別 PB / 優勝差）、027（チーム MD）
- ランタイムは `backend/data/*` のみ（ADR 015）

## 影響ドキュメント一覧

| 変更予定コード | 更新対象 doc | 操作 |
|:---------------|:-------------|:-----|
| `scripts/knowledge_graph/builder.py` | `docs/adr/046-*.md` / README KG 節 | 新規 ADR + 追記 |
| `backend/src/kg/mapRefs.ts` / `query.ts` | 同上 | 更新 |
| KG JSON | 生成物（コミット対象） | 再生成 |

## 技術調査結果

### 類似実装パターン

- QueryHint に target Source の refs をコピーし 0-hop で mapRefs（ADR 031）
- チーム別 MD はコーパスにあるが KG Source が ATRC と focus 数校のみ → ラベル一致が起きない
- `mapRefToCorpusSource("out/2026/practice.json")` が `practice/practice.json` になり、実体 `practice/practice.2026.json` と不一致

### 技術的制約・注意点

- QueryHint ID は index 依存。テストは ID ではなく refs / corpus_sources を検証する
- 「金栗」はなごみ駅伝の別名と `金栗PROJECT` 所属が衝突する
- ベクトル DB は不採用（運用コスト）

### UX パターン参考

- LINE はプレーンテキスト。本スライスは探索先精度のみ（UI 変更なし）

## 回帰テスト要件

| 既存機能 | 回帰テスト方針 | 対象テスト |
|:---------|:---------------|:-----------|
| 日付→カレンダー | 既存 Green | `kgQuery.test.ts` 9/20 |
| ジュニア ≠ 荒玉 | 既存 Green | ジュニア駅伝ケース |
| GZ / 閾値 | 既存 Green | QueryHint GZ |
| 玉名付属 alias | 既存 Green | focus_teams |

## QE1

- AC を検証可能な KG 出力（corpus_sources / refs）に限定し、LLM 文面は本スライス外とした。
- 金栗 PROJECT となごみの衝突を AC4 に明示。

## R1

- **Approved** — AC 6 件、テストマッピング完備、In/Out が Phase 0 ゴールと一致。
