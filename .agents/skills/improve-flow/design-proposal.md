# improve-flow スキル設計案

## 概要
- スキル名: `improve-flow`
- カテゴリ: workflow
- キャッチフレーズ: **「白紙ではなく、現物を磨け — 診断なき改善は単なる破壊だ」**
- Primary パターン: P1 Sequential Workflow
- Secondary パターン: P3 Iterative Refinement
- Problem-first（課題起点）

## implementation-flow との対比（境界定義）

| 項目 | implementation-flow | improve-flow |
|:---|:---|:---|
| 目的 | 新機能の追加 | 既存機能・見た目の改善 |
| 起点 | 要件定義（白紙から） | 現状診断（現物から） |
| 主なフェーズ | 調査→UX設計→アーキ→UI→実装 | 診断→課題分析→改善設計→実装 |
| スコープリスク | スコープ定義 | リグレッション管理 |
| 成功基準 | 受け入れ条件の充足 | Before/After の定量比較 |

## description（frontmatter 用）
既存機能・見た目の改善要求を入力とし、現状診断・課題分析・改善設計・実装・検証を
一気通貫で実行する統合ワークフロー。bug-finder による潜在バグ検出、
ux-psychology による UX 評価、ui-design + front-design によるビジュアル改善、
software-architecture によるコード設計見直し、effective-typescript による型安全実装、
decision-framework による改善優先付け、deep-research によるベストプラクティス調査を
最適な順序で連鎖させる。各フェーズ完了後に review スキルによるフェーズレビューを必ず実施し、
Approved を得てから次フェーズに進む「レビュー駆動改善」方式を採用。
新機能追加ではなく既存の質を高めることに特化。
Use when user says「このUIを改善して」「既存機能をリファクタリングして」
「UXを洗練させたい」「コードの品質を上げて」「パフォーマンスを改善して」
「アクセシビリティを改善して」「見た目をブラッシュアップして」
「既存機能をより使いやすくして」「improve-flow で改善して」
「コードをきれいにしたい」「デザインを磨きたい」。
Do NOT use for: 新機能の追加（→ implementation-flow）、特定バグの修正のみ（→ bug-triage-fix）、
デザインのみの改善（→ ui-design / front-design）、調査のみ（→ deep-research）。

## ステップ構成（8 フェーズ）

| Phase | 内容 | 使用スキル |
|:---|:---|:---|
| Phase 0 | ワークフロー初期化・改善スコープ定義 | — |
| R0 | フェーズレビュー | review |
| Phase 1 | 現状診断（コード・UX・UI・パフォーマンス） | bug-finder + ux-psychology |
| R1 | フェーズレビュー | review |
| Phase 2 | 改善課題分析・優先付け | decision-framework + deep-research |
| R2 | フェーズレビュー | review |
| Phase 3 | 改善設計（アーキ・UX・UI） | software-architecture + ux-psychology + ui-design |
| R3 | フェーズレビュー | review |
| Phase 4 | UI/ビジュアル改善実装 | front-design + ui-design |
| R4 | フェーズレビュー | review |
| Phase 5 | コード改善実装 | effective-typescript + bug-triage-fix |
| R5 | フェーズレビュー | review |
| Phase 6 | 最終統合レビュー + Before/After 検証 | review |

## 品質ゲートサマリー

| ゲート | Phase 間 | 通過条件 |
|:---|:---|:---|
| G-0 | 0 → R0 → 1 | 改善スコープと成功基準が定義済み |
| G-1 | 1 → R1 → 2 | 診断結果（課題リスト）が証拠付きで出力済み |
| G-2 | 2 → R2 → 3 | 改善課題が優先付きで整理され、ADR 1 本以上記録済み |
| G-3 | 3 → R3 → 4 | 改善設計書（UI 仕様 / アーキ変更計画）が完成 |
| G-4 | 4 → R4 → 5 | UI/ビジュアル改善の実装完了・デザイントークン準拠 |
| G-5 | 5 → R5 → 6 | コード改善実装完了・型エラー 0 |
| G-6 | 6 (Final) | Before/After で改善が定量的に証明できる |

## references/ 構成
- `improvement-domains.md` — 改善ドメイン（UX/UI/コード/パフォーマンス）別の診断観点と改善パターン
- `phase-output-templates.md` — 各フェーズの成果物テンプレート（診断レポート・ADR・Before/After 比較表）
- `improvement-priority-matrix.md` — 改善課題の Impact × Effort 優先付けマトリクス
- `regression-risk-checklist.md` — リグレッションリスク管理チェックリスト

## Examples 案（6 個以上）
1. 管理画面のダッシュボードの視認性・操作性を改善する
2. フォーム入力フローの離脱率を下げる UX 改善
3. TypeScript コードの型安全性を高めるリファクタリング
4. レスポンシブデザインの対応不足を修正・改善
5. 商品一覧ページのパフォーマンス（表示速度）改善
6. アクセシビリティ（WCAG AA）準拠への改善
7. 通知システムの UX・見た目のブラッシュアップ
8. 既存コンポーネントライブラリの統一性・品質改善

## Related Skills
- implementation-flow: 対比（新機能追加 vs. 既存改善）
- bug-triage-fix: 改善の一部（バグ修正）で連携
- review: 各フェーズのゲートキーパー
- ui-design: Phase 3-4 で委譲
- ux-psychology: Phase 1・3 で委譲
- effective-typescript: Phase 5 で委譲
- bug-finder: Phase 1 で委譲
- software-architecture: Phase 3 で委譲
- decision-framework: Phase 2 で委譲
- deep-research: Phase 2 で委譲
- front-design: Phase 4 で委譲
