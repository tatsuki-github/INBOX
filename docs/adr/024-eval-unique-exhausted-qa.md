# ADR 024: ユニーク想定質問の枯渇評価（コーパス根拠）

## 状況

ADR 023 の 10×100（1000問）評価は通過したが、バンク内のユニーク質問は約 684 件に留まり、コーパス事実（SB 行×距離・日程・大会 URL・荒玉など）を出し切れていなかった。
「ユニークな質問がもう考えられない」まで伸ばし、全問がリポジトリ根拠で合格する状態を目標にする。

## 決定

1. **枯渇バンク**: `backend/data/eval-unique/questions.json`
   - コーパス事実から機械生成（SB 全行×距離、カレンダー×3 言い回し、meets、荒玉、clarify、OOS、練習既知）
   - 生成: `python3 backend/scripts/eval-unique/generate_bank.py`
   - 評価: `cd backend && npx tsx scripts/eval-unique/run.ts --offline`
2. **本ラウンドでの回答改善**
   - clarify: 1 文字姓・互換漢字（﨑）・Ext B（𠮷）・ラテン名（FESTUS）・カタカナ（ヴ）を選手名として認識
   - clarify / 名前ヒント: 「今の自己ベスト」の「今」を選手名と誤認しない
   - 検索: SB CSV は `名前,` 行頭完全一致を強くブースト（森 vs 森本）
   - 指名付き PB では 3000m 予想ランキング等の drive-text を preferred から外し、SB を優先

## 結果

- ユニーク質問 **4639** 件（ラウンド 464、最終ラウンド 9 問）を生成し、ユニークを枯渇とみなす
- 2026-09-18: オフライン評価 **4639/4639 PASS**

## 関連

- ADR 021（clarify）、ADR 022（SB）、ADR 023（200/1000 評価）
