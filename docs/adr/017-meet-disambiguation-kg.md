# ADR 017: 大会種別ディスambiguation（ジュニア ≠ 荒玉）

## 状況

LINE Q&A で「去年のジュニア駅伝の岱明の結果は？」と聞くと、荒玉駅伝の OCR / transcripts が返ることがあった。
原因は `boostEkidenYearSources` が `/駅伝/` だけで aragyoku ソースを先頭注入していたこと。
ジュニア・なごみ等の固有大会名があっても荒玉が優先され、LLM が誤答しやすい。

## 決定

1. **`detectMeetKind(query)`**（`backend/src/domain/meets.ts`）で大会種別を判定する。
   - `ジュニア` / `県ジュニア` → `junior`
   - `なごみ` / `金栗` → `nagomi`
   - 明示の `荒玉` / `aragyoku` / `中体連`、または固有大会なしの `駅伝`・`優勝`・`歴代` → `aragyoku`
2. **ソースブースト**は種別ごと:
   - `junior` / `nagomi` → `drive-text/大会/` の該大会パスのみ先頭。`aragyoku/*`・`ekiden-ocr/*` は preferred から除外
   - `aragyoku` → 従来どおり winners-by-year + 該当年 transcripts / OCR
3. **KG スコア**で質問に `ジュニア` / `なごみ` があるとき、該当 meet ノードを加点し aragyoku ハブを減点
4. **QueryHint** にジュニア結果向けヒントを追加。meet ノードは `junior_ekiden` / `nagomi` / `aragyoku` トピックと結果ファイル優先 refs
5. **Router** プロンプトと fallback スコアも同ルールに合わせる

## 不採用

| 案 | 理由 |
|:---|:---|
| 駅伝ブーストを全廃 | 荒玉の「去年の優勝校」等が退行する |
| 大会名ごとにハードコード canned 回答 | 結果は年次で変わり、コーパス正本を活かせない |

## 結果

- Vitest: ジュニア質問で junior / 岱明の結果ソース、荒玉回帰維持
- 関連: ADR 016
