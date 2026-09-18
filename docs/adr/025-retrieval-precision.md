# ADR 025: 検索精度改善（コーパス抜粋の当たり）

## 状況

LINE Q&A は「渡されたコーパス抜粋だけ」を根拠に答える（ADR 016）。
リポジトリに事実があっても、誤 preferred の一律加点（+1000）や選手名ヒット不足、ADR 文書の BM25 汚染などで正解チャンクがコンテキストに載らず、「コーチに直接聞いてください」になる偽陰性が起きうる。

## 決定

1. **`mergeRetrieved`**: 一律 +1000 を廃止。スコア融合 + 弱い preferred は微小ボーナスのみ。日付/名前の強いシグナルとパス一致（ジュニア・なごみ・SB・calendar）で優遇。meet 質問では `repo-docs/` / 誤 aragyoku を減点。
2. **選手名**: `extractAthleteNameHints` を「の」無し・距離語近傍にも拡張。`csvNameRowBoost` を BM25 にも適用。
3. **tokenize**: NFKC・ISO 保全・ストップ語。KG `tokenizeKg` も NFKC + ISO 保全で揃える。
4. **`retrieveBySources`**: ソース内 `Bm25Retriever` でランキング（単純 includes +1 を廃止）。
5. **mapRefs**: `practice/`・Drive `練習/` を追加マップ。Athlete は hint/refs トークンも加点。
6. **評価**: `eval-1000q` / `eval-unique` に `missingInfo`（定型拒否率）集計を追加。オフライン回帰は必須。

## 不採用

| 案 | 理由 |
|:---|:---|
| 埋め込みベクトル DB | 運用コスト。KG + BM25 の精度改善で足りる |
| LLM モデル乗せ替え単体 | 抜粋が外れると効かない |

## 結果

- Vitest: retrieve / answer / mapRefs / clarify / kg 回帰を含む backend 全件パス
- オフライン評価（2026-09-18）:
  - eval-1000q: **1000/1000 PASS**, missingInfo **0/1000 (0%)**
  - eval-unique: **4639/4639 PASS**（missingInfo 集計付き）
- 再実行:
  - `cd backend && npx tsx scripts/eval-1000q/run.ts --offline`
  - `cd backend && npx tsx scripts/eval-unique/run.ts --offline`
  - 任意 LLM: `--llm` で `missingInfo` 率を確認

## 関連

- ADR 016（KG 先行）、017（大会 disambiguation）、022（SB）、023/024（評価バンク）
