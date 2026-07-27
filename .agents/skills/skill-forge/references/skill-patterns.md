# Anthropic 5 パターン定義と設計指針

> Anthropic 公式ガイド『The Complete Guide to Building Skills for Claude』に基づく
> 5 つのスキルパターン定義、選定フロー、パターン別設計指針。

---

## Problem-first vs. Tool-first

スキル設計の出発点として、まずオリエンテーションを判定する。

| 分類 | 説明 | 典型例 |
|:---|:---|:---|
| **Problem-first** | ユーザーが課題を述べ、スキルが手段を選択する | bd-skills（「提案書を作って」→ 複数スキルをオーケストレーション） |
| **Tool-first** | ユーザーがツール/環境を持ち、スキルが活用法を教える | databricks（「DLT パイプラインを構築して」→ Databricks の最適設計を指導） |

> ほとんどのスキルはどちらか一方に寄る。この分類がパターン選定の第一指針となる。

---

## Pattern 1: Sequential Workflow Orchestration

### 定義

マルチステッププロセスを特定の順序で実行する。ステップ間に明確な依存関係があり、前ステップの出力が次ステップの入力となる。

### 判定質問

- ステップに明確な順序と依存関係があるか？
- 前のステップの出力が次のステップの入力になるか？

### 設計指針（必須要素）

| 要素 | 説明 | 実装ガイド |
|:---|:---|:---|
| **ステップ間依存の明示** | 各ステップの入力が前ステップの出力であることを図示 | Instructions セクションに ASCII ワークフロー図を配置 |
| **バリデーションゲート** | 各ステップ末にチェックリストで品質ゲートを設置 | ステップごとに 3-8 項目のチェックリスト |
| **ロールバック指示** | 失敗時の差し戻し手順を含める | Troubleshooting に各ステップの失敗時対応を記載 |
| **エントリーポイント分岐** | 中間ステップからの開始を可能にする | Instructions に状態→開始ステップの対応テーブル |

### 既存スキル実証（18 スキル）

| スキル | Sequential の特徴 |
|:---|:---|
| **skill-forge** | Step 1-9 の線形パイプライン、エントリーポイント分岐あり |
| **pdf-convert** | ファイル判定 → 変換 → 品質検証の 3 段階 |
| **distill** | ソース読込 → 構造化 → 蒸留 → 出力の 4 段階 |
| **slide-gen** | ヒアリング → 分析 → slide_plan.json → python-pptx 生成 |
| **bd-skills** | アセスメント → 課題構造化 → 提案書 → DRM の 8 段階 |
| **marketing-context** | 自動収集 → ヒアリング → ペルソナ → ボイス → 競合分析 |
| **seo-analytics** | 技術監査 → AI 検索 → コンテンツ → GA4/GTM → ダッシュボード |
| **data-validation** | テーブル構造 → データ品質 → スキーマ → ルール → 数値の 5 段階 |

---

## Pattern 2: Multi-MCP Coordination

### 定義

複数の外部サービス（MCP サーバー）を跨いだワークフロー。Phase 分離とサービス間のデータ受け渡しが特徴。

### 判定質問

- 複数の外部サービス/MCP を跨ぐか？
- 各サービスへのアクセスが Phase として分離できるか？

### 設計指針（必須要素）

| 要素 | 説明 | 実装ガイド |
|:---|:---|:---|
| **Phase 分離** | 各 MCP/サービスごとに Phase を設ける | Step をサービス単位で分割 |
| **データ受け渡し** | Phase 間のデータフォーマットと受け渡し方法を明示 | 入力/出力テーブルで Phase 間のデータフローを図示 |
| **Phase 間バリデーション** | 次 Phase に移行する前の検証条件 | 各 Phase 末にデータ整合チェック |
| **集中エラーハンドリング** | 各 MCP の障害時の統一対処方針 | Troubleshooting に MCP 別の障害対応を集約 |

### 既存スキル実証

現在該当スキルなし。将来 MCP 統合スキル構築時の参照パターンとして定義。

**候補シナリオ**: Figma MCP → Drive MCP → Linear MCP → Slack MCP のデザインハンドオフ自動化。

---

## Pattern 3: Iterative Refinement

### 定義

出力品質が反復サイクルで段階的に向上する。明確な品質基準と終了条件が必要。

### 判定質問

- 出力品質が反復で向上するか？
- 品質基準を定量的に定義できるか？

### 設計指針（必須要素）

| 要素 | 説明 | 実装ガイド |
|:---|:---|:---|
| **品質基準の明示** | 反復を終了する定量/定性基準 | チェックリストに合格基準を数値で記載 |
| **反復上限** | 無限ループ防止の最大反復回数 | 推奨: 3 回。超過時はユーザーに判断を委ねる |
| **差分ログ** | 各反復での改善内容を記録する仕組み | 反復ごとの変更記録テンプレートを用意 |
| **退出条件** | 「これ以上改善できない」場合の判断基準 | 前回反復との差分が閾値以下なら終了 |

### 既存スキル実証（4 スキル）

| スキル | Iterative の特徴 |
|:---|:---|
| **ad-creative** | 生成 → パフォーマンス分析 → 最適化の反復サイクル |
| **growth-ops** | ファネル分析 → 実験設計 → 計測 → 改善の PDCA |
| **onboarding** | 学習 → クイズ → 弱点分析 → 補強の適応型サイクル |
| **review** | レビュー → 修正 → 再レビューの品質向上ループ |

---

## Pattern 4: Context-aware Tool Selection

### 定義

同じ目的を達成するために、文脈（入力条件・環境・制約）に応じて異なるツールや手法を選択する。

### 判定質問

- 同じ目的を文脈に応じて異なるツール/手法で達成するか？
- 判定条件を Decision Tree で表現できるか？

### 設計指針（必須要素）

| 要素 | 説明 | 実装ガイド |
|:---|:---|:---|
| **Decision Tree** | 文脈 → ツール/手法 の分岐条件を明示 | ASCII で分岐図を描くか、テーブルで条件マトリクスを提示 |
| **フォールバック** | 判定不能時のデフォルト選択肢 | 各分岐の末端に「判定できない場合」のデフォルトを記載 |
| **選択理由の透明化** | なぜそのツールを選んだかをユーザーに説明する仕組み | 出力に「選定理由」セクションを含める |
| **判定条件テーブル** | 条件 × ツール のマトリクスで全パターンを列挙 | references/ に判定マトリクスを格納 |

### 既存スキル実証

現在該当スキルなし。

**候補シナリオ**: ドキュメント変換の統合スキル（PDF/DOCX/PPTX/画像 → 入力形式を自動判定し最適な変換手法を選択）。

---

## Pattern 5: Domain-specific Intelligence

### 定義

ツール操作ではなく、専門知識の提供が主たる価値。書籍・仕様書・ベストプラクティスの知識をエンコードする。

### 判定質問

- ツール操作ではなく専門知識の提供が主価値か？
- 書籍や仕様書に基づく判断基準・ルールが中心か？

### 設計指針（必須要素）

| 要素 | 説明 | 実装ガイド |
|:---|:---|:---|
| **知識ソースの明示** | `metadata.based-on` フィールドで出典を明記 | frontmatter に書誌情報を含める |
| **判断ロジックの埋め込み** | ドメインルールを Decision Framework として組み込む | 各ステップにドメイン固有の判断テーブルを配置 |
| **根拠の出力** | 「なぜそう判断するか」の根拠を出力に含める | 出力テンプレートに「判断根拠」欄を含める |
| **references/ の充実** | 専門知識の詳細を references/ に格納 | Progressive Disclosure の真価を発揮。3-7 ファイルで詳細知識を構造化 |

### 既存スキル実証（8 スキル）

| スキル | Domain-specific の特徴 |
|:---|:---|
| **data-arch** | 6 種アーキテクチャの比較知識、ADS フレームワーク |
| **effective-typescript** | 83 項目のベストプラクティス知識 |
| **robust-python** | 型設計・クラス設計の専門知識 |
| **ui-design** | Refactoring UI の 8 軸ビジュアル分析 |
| **ux-psychology** | Laws of UX 10 法則の心理学知識 |
| **test** | 4 本柱テスト理論の専門知識 |
| **databricks** | Databricks プラットフォーム設計の 6 部構成 |
| **unity-catalog** | Unity Catalog 4 戦略フレームワーク |

---

## パターン分布と選定フロー

### 現在の 30 スキルの分布

| パターン | スキル数 | 比率 | 備考 |
|:---|:---|:---|:---|
| Sequential Workflow | 18 | 60% | 最も汎用的。パイプライン型スキルの標準 |
| Domain-specific Intelligence | 8 | 27% | 書籍ベーススキルの標準。知識の重みが高い |
| Iterative Refinement | 4 | 13% | 最適化・改善サイクル系。マーケティング/学習に多い |
| Context-aware Selection | 0 | 0% | 将来の MCP 統合で登場見込み |
| Multi-MCP Coordination | 0 | 0% | 将来の MCP 統合で登場見込み |

> **注意**: Sequential に 60% が集中している。新スキル設計時は「本当に Sequential か？」を自問し、
> Iterative や Domain-specific の要素を見落としていないか確認すること。

### 選定フローチャート

```
1. 複数の外部サービス（MCP）を跨ぐか？
   → Yes: Pattern 2 (Multi-MCP Coordination)
   → No: 次へ

2. 文脈に応じて異なる手法を選択するか？
   → Yes: Pattern 4 (Context-aware Selection)
   → No: 次へ

3. 反復で出力品質が向上するか？
   → Yes: Pattern 3 (Iterative Refinement)
         ※ Sequential との併用可
   → No: 次へ

4. 専門知識の提供が主たる価値か？
   → Yes: Pattern 5 (Domain-specific Intelligence)
   → No: Pattern 1 (Sequential Workflow)
         ※ 最も汎用的なデフォルト
```

### 複合パターンの例

ほとんどのスキルは 1 つの Primary パターンを持つが、Secondary パターンとの組み合わせもある。

| スキル | Primary | Secondary | 理由 |
|:---|:---|:---|:---|
| **skill-forge** | Sequential | Iterative | パイプラインは Sequential、品質監査（Step 7）は Iterative |
| **review** | Iterative | Domain-specific | レビュー反復が主、レビュー基準は専門知識 |
| **bd-skills** | Sequential | Domain-specific | 案件フローは Sequential、BD 知識が全体の基盤 |
| **marketing-copy** | Sequential | Iterative | コピー制作は Sequential、7 Sweeps は Iterative |
| **data-arch** | Domain-specific | Sequential | 専門知識が主、ADS は Sequential に進行 |
