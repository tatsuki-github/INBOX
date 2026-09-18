# ADR 026: LLM コンテキスト抜粋を 100k 字に拡大

## 状況

ADR 016 / 025 以降、回答精度の天井は「正解コーパス抜粋が LLM コンテキストに載るか」である。
上限は当初 14k → 網羅性強化で 28k だったが、取得幅（topK=16・近傍+32）とセットで、
実質 2〜3 万字程度しか供給できず、長い開催要項・結果・SB 周辺が Truncate で落ちうる。
モデル（`gemini-3.5-flash-lite`）の入力窓にはまだ余裕がある。

## 決定

1. **`RETRIEVAL_BUDGET.maxChars = 100_000`**（`backend/src/rag/budget.ts`）
2. **取得幅も合わせて拡大**し、100k 枠を実質埋められるようにする:
   - topK **64**
   - routeSources **24**
   - perSource **12** / maxChunks **96**
   - neighborRadius **2** / neighborMaxExtra **160**
3. Router の sources 上限も `routeSources` に揃える（循環依存回避のため budget は独立モジュール）
4. **幅拡大に伴うノイズ対策**: ジュニア/なごみ/金栗質問では aragyoku・ekiden-ocr・docs・誤大会フォルダ・荒玉本文チャンクを merge / 近傍拡張で除外（ADR 017 維持）
5. **定型拒否文の混入防止**: コーパス内の「コーチに直接聞いてください」引用チャンクはコンテキストから除外（システムプロンプト側で指示済み）

## 不採用

| 案 | 理由 |
|:---|:---|
| 上限だけ 100k にして topK 据え置き | 供給チャンク不足で枠が空く |
| 無制限 / 全コーパス投入 | ノイズ増大・無料枠トークン・レイテンシ |

## 結果

- Vitest: `RETRIEVAL_BUDGET 100k`（truncate 充填 + 旧 28k 超え）・大会ノイズ除外・拒否定型混入除外を含む回帰 **109 passed**
- `npm run build` 成功
- オフライン評価（2026-09-18）:
  - eval-1000q: **1000/1000 PASS**, missingInfo **0%**
  - eval-unique: **4639/4639 PASS**, missingInfo **0%**

## 関連

- ADR 016（KG 先行）、017（大会 disambiguation）、025（検索精度）
