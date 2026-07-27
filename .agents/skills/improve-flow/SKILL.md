---
name: improve-flow
description: >
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
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: workflow
  pattern: "sequential"
  secondary-pattern: "iterative"
  based-on: "prompt-craft 設計手法に基づくマルチスキル統合改善ワークフロー"
---

# Skill: Improve Flow（既存機能・見た目の改善 一気通貫ワークフロー）

> **白紙ではなく、現物を磨け — 診断なき改善は単なる破壊だ**

## Instructions

### 品質ゲートサマリー

> **原則**: 各フェーズのチェックリスト通過後、**review スキルによるフェーズレビュー**を必ず実施する。
> レビューで Approved を得てから次のフェーズに進む。Rejected の場合は該当フェーズを修正し、再レビューを行う。

| ゲート | Phase 間 | 通過条件 | 不合格時 |
|:---|:---|:---|:---|
| G-0 | 0 → R0 → 1 | 改善スコープ・成功基準・Before 状態の記録が完了 | スコープを再定義 |
| G-1 | 1 → R1 → 2 | 診断結果（課題リスト）が証拠付き・重大度分類済みで出力済み | 診断継続 |
| G-2 | 2 → R2 → 3 | 改善課題が優先付き・ADR 1 本以上・改善ロードマップ確定 | 分析継続 |
| G-3 | 3 → R3 → 4 | 改善設計書（UX/UI 仕様・アーキ変更計画）が完成 | 設計継続 |
| G-4 | 4 → R4 → 5 | UI/ビジュアル改善の実装完了・デザイントークン準拠確認 | Phase 4 継続 |
| G-5 | 5 → R5 → 6 | コード改善完了・型エラー 0・リグレッションチェック通過 | Phase 5 継続 |
| G-6 | 6 (Final) | Before/After で改善が定量的に証明・Critical=0, Major=0 | 差し戻し（最大 2 回） |

> **R0〜R5** は各フェーズ末の review スキルによるフェーズレビューを示す。

### ワークフロー全体像

```
既存機能・見た目への改善要求（自然言語）
  │
  ▼
Phase 0: ワークフロー初期化 ──────── 改善スコープ・成功基準・Before 状態記録
  │
  ▼
★ R0: フェーズレビュー ──────────── [review] ─ スコープ・成功基準の妥当性
  │     ├─ Approved ──→ Phase 1 へ
  │     └─ Rejected ──→ Phase 0 修正
  ▼
Phase 1: 現状診断 ────────────────── [bug-finder] + [ux-psychology（診断モード）]
  │
  ▼
★ R1: フェーズレビュー ──────────── [review] ─ 診断結果の証拠・網羅性
  │     ├─ Approved ──→ Phase 2 へ
  │     └─ Rejected ──→ Phase 1 継続
  ▼
Phase 2: 改善課題分析・優先付け ──── [decision-framework] + [deep-research]
  │
  ▼
★ R2: フェーズレビュー ──────────── [review] ─ 優先付けの合理性・ADR 検証
  │     ├─ Approved ──→ Phase 3 へ
  │     └─ Rejected ──→ Phase 2 修正
  ▼
Phase 3: 改善設計 ───────────────── [software-architecture] + [ux-psychology（設計モード）] + [ui-design]
  │
  ▼
★ R3: フェーズレビュー ──────────── [review] ─ 設計書の完全性・整合性
  │     ├─ Approved ──→ Phase 4 へ
  │     └─ Rejected ──→ Phase 3 修正
  ▼
Phase 4: UI/ビジュアル改善実装 ───── [front-design] + [ui-design]
  │
  ▼
★ R4: フェーズレビュー ──────────── [review] ─ ビジュアル品質・WCAG 準拠
  │     ├─ Approved ──→ Phase 5 へ
  │     └─ Rejected ──→ Phase 4 修正
  ▼
Phase 5: コード改善実装 ─────────── [effective-typescript] + [bug-triage-fix]
  │
  ▼
★ R5: フェーズレビュー ──────────── [review] ─ コード品質・リグレッション安全性
  │     ├─ Approved ──→ Phase 6 へ
  │     └─ Rejected ──→ Phase 5 修正
  ▼
Phase 6: 最終統合レビュー ─────────── [review] ─ Before/After 定量比較・全横断検証
  │     ├─ Approved ──→ 完成
  │     └─ Rejected ──→ 該当 Phase に差し戻し（Iterative）
  ▼
改善完了（Before/After レポート）
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| 改善対象 | 既存コード・UI・機能の場所 | 「src/components/Dashboard.tsx」「決済フォーム」 |
| 改善目標（任意） | 何を良くしたいか | 「離脱率を下げたい」「表示速度を上げたい」「見た目を統一したい」 |
| 改善ドメイン（任意） | UX / UI / コード / パフォーマンス / アクセシビリティ | 「UX と UI を両方改善したい」 |
| プロジェクト情報（任意） | 技術スタック・デザインシステムの有無 | 「Next.js + Tailwind CSS、デザインシステムなし」 |

### 出力

| 出力 | Phase | 形式 |
|:---|:---|:---|
| 診断レポート（Before） | Phase 1 | Markdown |
| 改善優先度マップ + ADR | Phase 2 | Markdown |
| 改善設計書（UX/UI/アーキ） | Phase 3 | Markdown |
| 改善実装コード（UI/ビジュアル） | Phase 4 | CSS / TSX |
| 改善実装コード（コード品質） | Phase 5 | TypeScript / TSX |
| Before/After 比較レポート | Phase 6 | Markdown |
| フェーズレビュー結果 | R0〜R5 | Markdown |

各 Phase の出力テンプレートは [phase-output-templates.md](references/phase-output-templates.md) を参照。

> **ワークフロー原則**: 「現状を正確に知らずに改善しない」「優先付けなしに手を動かさない」「リグレッション確認なしに終わらない」。

---

## Phase 0: ワークフロー初期化

改善要求を受け取り、スコープ・成功基準・Before 状態を確定させる。

### 0a. 改善スコープの定義

| 確認項目 | デフォルト |
|:---|:---|
| **改善対象**: ファイル / 機能 / 画面を特定できるか？ | 調査して特定する |
| **改善ドメイン**: UX / UI / コード品質 / パフォーマンス / アクセシビリティ？ | 全ドメインを診断 |
| **技術スタック**: 既存プロジェクトの技術構成は？ | Next.js + TypeScript + Tailwind |
| **デザインシステム**: 既存のデザイントークン・ガイドラインはあるか？ | なし（診断後に整理） |
| **改善の優先順位**: ユーザー影響 / 技術的負債 / 見た目のどれが最も重要？ | ユーザー影響 > 技術的負債 > 見た目 |

### 0b. 成功基準の定義

改善の「完了」を検証可能な基準で定義する。Before/After の比較に使う。

| 成功基準の軸 | 例 |
|:---|:---|
| **UX**: 操作ステップ数・エラー発生率・離脱ポイントの変化 | 「入力エラーが発生する箇所がゼロになる」 |
| **UI**: WCAG AA 準拠・コントラスト比・視覚的階層の改善 | 「全色が CSS 変数で定義され、ハードコードなし」 |
| **コード品質**: 型エラー数・any 使用数・循環依存の解消 | 「any が 0 件、enum が 0 件になる」 |
| **パフォーマンス**: LCP / FID / CLS の改善目標値 | 「LCP が 2.5 秒以内になる」 |
| **アクセシビリティ**: WCAG AA 全項目通過 | 「aria-label が全インタラクティブ要素に付与される」 |

### 0c. フェーズスキップ判定

| 条件 | スキップ対象 |
|:---|:---|
| バックエンド API のみの改善 | Phase 4（UI/ビジュアル実装）をスキップ |
| 既存デザインシステムに完全準拠済み | Phase 4 を簡略化 |
| UI/ビジュアルのみの改善要求 | Phase 5 のコード品質改善を簡略化 |
| コード品質のみの改善要求 | Phase 4 の UI 実装をスキップ |
| パフォーマンスのみの改善 | Phase 3-4 の UI/UX 設計を簡略化、Phase 5 に集中 |

> **原則**: スキップ判定は Phase 0 で行い、理由を記録する。迷ったらスキップしない。

### 0d. Before 状態の記録

改善前の現状を記録する。これが Phase 6 の Before/After 比較の基準となる。

| 記録項目 | 内容 |
|:---|:---|
| **コードスナップショット** | 改善対象ファイルの現在のコードを確認・記録 |
| **課題の仮説** | ユーザーが「改善したい」と感じている症状の言語化 |
| **スコープ境界** | 改善対象に含めるもの / 含めないもの |

**チェックリスト**:
- [ ] 改善対象（ファイル / 機能 / 画面）を特定・記録した
- [ ] 改善ドメインを決定した（UX / UI / コード / パフォーマンス / アクセシビリティ）
- [ ] 成功基準を検証可能な形で定義した（最低 1 項目）
- [ ] フェーズスキップの判定を行い、理由を記録した
- [ ] Before 状態（コード・現状症状）を記録した

### R0: フェーズレビュー（review に委譲）

| レビュー観点 | 検証内容 |
|:---|:---|
| **スコープ妥当性** | 改善スコープが 1 ワークフローに収まる規模か |
| **成功基準の検証可能性** | Before/After で定量比較できる基準になっているか |
| **スキップ判定の合理性** | フェーズスキップの理由が合理的か |
| **Before 状態の正確性** | 改善前の現状が正確に記録されているか |

**判定**: Approved → Phase 1 へ、Rejected → Phase 0 の指摘箇所を修正し再レビュー

---

## Phase 1: 現状診断（bug-finder + ux-psychology（診断モード）に委譲）

> **「病名なき処方は毒だ」 — まず何が壊れているかを証拠付きで特定せよ**

### 1a. コード・技術的問題の診断（bug-finder に委譲）

改善対象のコードを bug-finder で能動スキャンし、潜在的な問題を特定する。
詳細な診断観点は [improvement-domains.md](references/improvement-domains.md) の「コード診断」セクションを参照。

| 診断カテゴリ | 確認内容 | 重大度 |
|:---|:---|:---|
| **型安全性** | any 使用、型アサーション、enum、null 安全性 | High |
| **ロジックバグ** | 境界値処理、エラーハンドリング、条件分岐漏れ | High |
| **パフォーマンス問題** | N+1 レンダリング、不要な再レンダリング、メモ化漏れ | Medium |
| **アーキテクチャ問題** | 循環依存、責務過多コンポーネント、デッドコード | Medium |
| **セキュリティ問題** | XSS、CSRF、PII 漏洩の危険性 | Critical |

### 1b. UX 上の問題の診断（ux-psychology 診断モードに委譲）

**診断モード**（評価・改善提案フェーズ）：Laws of UX の 10 法則を評価基準として現状の UX を評価する。
Phase 3 の**設計モード**（改善策を設計）とは目的が異なる。

| 診断観点 | 適用法則 | 症状例 |
|:---|:---|:---|
| **認知負荷過多** | Miller's Law, Hick's Law | 「選択肢が多すぎてどれか選べない」 |
| **メンタルモデル不一致** | Jakob's Law | 「他のサービスと操作が違って戸惑う」 |
| **フィッツ法則違反** | Fitts's Law | 「ボタンが小さすぎてタップできない」 |
| **ピーク体験の欠如** | Peak-End Rule | 「完了後に達成感がない」 |
| **応答遅延** | Doherty Threshold | 「クリックしても反応が遅い」 |

### 1c. UI/ビジュアル問題の診断

| 診断観点 | チェック内容 |
|:---|:---|
| **視覚的階層** | Primary / Secondary / Tertiary の 3 段階が欠如していないか |
| **カラーシステム** | ハードコード色値が使われていないか、コントラスト比は AA 以上か |
| **スペーシング** | 制約スケール（4px ベース）からの逸脱がないか |
| **コンポーネント統一性** | 同じ役割のコンポーネントが複数の見た目で存在していないか |
| **アクセシビリティ** | aria-label, semantic HTML, prefers-reduced-motion 対応があるか |

**チェックリスト**:
- [ ] コード診断（bug-finder）を実施し、重大度別に課題を分類した
- [ ] UX 診断（ux-psychology）を実施し、違反している Law を特定した
- [ ] UI/ビジュアル診断を実施し、デザイントークンの問題を特定した
- [ ] 各課題に証拠（ファイル:行番号 or 操作手順）を付けた
- [ ] パフォーマンス問題があれば、現状のメトリクス（LCP 等）を記録した

**→ Phase 2 への受け渡し**: 診断レポート（課題リスト + 重大度 + 証拠）

### R1: フェーズレビュー（review に委譲）

| レビュー観点 | 検証内容 |
|:---|:---|
| **診断の網羅性** | コード・UX・UI の全ドメインが診断されているか（スコープ内） |
| **証拠の具体性** | 各課題にファイル:行番号または操作手順が付いているか |
| **重大度分類の妥当性** | Critical/High/Medium/Low の分類が適切か |
| **偽陽性のチェック** | 「問題に見えるが実は意図的な実装」が除外されているか |

**判定**: Approved → Phase 2 へ、Rejected → Phase 1 の指摘箇所を修正し再レビュー

---

## Phase 2: 改善課題分析・優先付け（decision-framework + deep-research に委譲）

> **「全てを同時に直す」は全てを壊す — Impact × Effort で最高の改善順序を選べ**

### 2a. 改善課題の整理と優先付け（decision-framework に委譲）

Phase 1 の診断結果を入力とし、Impact × Effort マトリクスで改善課題を優先付けする。
詳細なマトリクスと判定基準は [improvement-priority-matrix.md](references/improvement-priority-matrix.md) を参照。

| 優先度 | Impact | Effort | アクション |
|:---|:---|:---|:---|
| **P1（今すぐ）** | High | Low | Phase 4-5 でまず実施 |
| **P2（次に）** | High | High | Phase 4-5 で計画的に実施 |
| **P3（余力で）** | Low | Low | Phase 4-5 の後半または次サイクル |
| **P4（保留）** | Low | High | このワークフローでは扱わない |

### 2b. ベストプラクティス調査（deep-research に委譲）

診断で特定した課題の解決策を調査する。調査は「標準」レベルで十分（徹底調査は不要）。

| 調査項目 | 目的 |
|:---|:---|
| **改善手法** | 特定された課題の業界標準的な解決策 |
| **類似ケース** | 同様の改善を行った事例・パターン |
| **技術的制約** | 採用予定の改善手法の制約・落とし穴 |

### 2c. 意思決定記録（ADR）

主要な改善方針の決定を ADR として記録する（最低 1 本）。

```markdown
## ADR-001: <改善方針のタイトル>

### 状況
<なぜこの決定が必要か>

### 決定
<採用する改善アプローチ>

### 理由
<なぜこのアプローチを選んだか>

### 不採用オプション
<検討したが不採用にした選択肢と理由>

### 影響
<この決定によるリグレッションリスクと対策>
```

### 2d. 改善ロードマップの確定

このワークフローで対応する改善と対応しない改善を明確に分ける。

**チェックリスト**:
- [ ] 全課題が Impact × Effort で優先付けされている
- [ ] P1・P2 課題のみがこのワークフローのスコープに含まれている
- [ ] P4 課題（Low Impact, High Effort）が明示的に除外されている
- [ ] ベストプラクティス調査の結果が改善方針に反映されている
- [ ] ADR が 1 本以上記録されている（改善根拠の記録）
- [ ] リグレッションリスクを ADR に記録した

**→ Phase 3 への受け渡し**: 改善優先度マップ + ADR + 改善ロードマップ

### R2: フェーズレビュー（review に委譲）

| レビュー観点 | 検証内容 |
|:---|:---|
| **優先付けの合理性** | Impact × Effort の判定がビジネス・ユーザー影響を適切に反映しているか |
| **スコープの適切性** | P4 課題が正しく除外されているか、P1-P2 が現実的な量か |
| **ADR の品質** | 判断根拠と不採用理由が具体的か、リグレッションリスクが記載されているか |
| **調査の十分性** | ベストプラクティス調査が改善設計に活用できる質か |

**判定**: Approved → Phase 3 へ、Rejected → Phase 2 の指摘箇所を修正し再レビュー

---

## Phase 3: 改善設計（software-architecture + ux-psychology（設計モード）+ ui-design に委譲）

> **改善設計は「現物の制約の中でベストを出す」— 完璧な設計より実現可能な改善を**

### 3a. アーキテクチャ・コード設計の改善（software-architecture に委譲）

Phase 2 の優先課題から、コード構造の改善設計を行う。既存アーキテクチャを尊重し、最小変更で最大効果を狙う。

| 改善対象 | 設計アクション |
|:---|:---|
| **責務過多コンポーネント** | コンポーネント分割設計（UI / ロジック / データ層） |
| **型安全性の欠如** | タグ付きユニオン型・ブランド型への移行設計 |
| **パフォーマンス問題** | メモ化戦略・データフェッチ最適化・コード分割計画 |
| **循環依存** | 依存関係の整理・モジュール境界の再設計 |

### 3b. UX 改善設計（ux-psychology 設計モードに委譲）

**設計モード**（改善策の設計）：Phase 1 の診断結果を受けて、Laws of UX に基づき改善策を具体的に設計する。
Phase 1 の「診断モード」で特定された違反箇所を「どう直すか」を設計する。

| 設計観点 | 設計内容 |
|:---|:---|
| **認知負荷の最適化** | Hick's Law → 選択肢のグルーピング・段階的開示設計 |
| **インタラクション改善** | Fitts's Law → タッチターゲットサイズ・配置の再設計 |
| **感情設計** | Peak-End Rule → ポジティブピーク（完了時の演出）の設計 |
| **応答性改善** | Doherty Threshold → ローディング状態・スケルトン UI の設計 |
| **倫理チェック** | ダークパターン・過度な行動操作がないか確認 |

### 3c. UI/ビジュアル改善設計（ui-design に委譲）

| 設計観点 | 設計内容 |
|:---|:---|
| **視覚的階層の再設計** | Primary / Secondary / Tertiary の 3 段階を明確化 |
| **デザイントークンの整理** | CSS 変数でカラー・スペーシング・シャドウを定義 |
| **コンポーネント統一** | 不統一なコンポーネントを Refactoring UI 原則で統一設計 |
| **アクセシビリティ設計** | WCAG AA 準拠・コントラスト比・モーション対応 |

**チェックリスト**:
- [ ] コード構造の改善設計が完成している（変更ファイルリスト・分割計画）
- [ ] UX 改善設計が完成している（Laws of UX に基づく改善案）
- [ ] UI/ビジュアル改善設計が完成している（デザイントークン定義・コンポーネント設計）
- [ ] 設計変更がリグレッションを引き起こさないか確認した
- [ ] Phase 2 の優先度マップ（P1-P2）と設計のカバレッジが一致している

**→ Phase 4 への受け渡し**: 改善設計書（UX 改善策・UI 仕様・デザイントークン）

### R3: フェーズレビュー（review に委譲）

| レビュー観点 | 検証内容 |
|:---|:---|
| **Phase 1 課題との対応** | 診断で発見した課題が設計でカバーされているか |
| **設計の実現可能性** | 既存アーキテクチャ・デザインシステムとの整合性 |
| **UX 改善の論理的根拠** | Laws of UX に基づいた改善設計になっているか |
| **デザイントークンの完全性** | CSS 変数で全色・スペーシングが定義されているか |
| **リグレッションリスク** | 変更によるリグレッションリスクが評価されているか |

**判定**: Approved → Phase 4 へ、Rejected → Phase 3 の指摘箇所を修正し再レビュー

---

## Phase 4: UI/ビジュアル改善実装（front-design + ui-design に委譲）

> **Refactoring UI の原則で「良いデザインは選択肢を制限することで生まれる」**

### 4a. デザイントークンの実装

Phase 3 で設計したデザイントークンを CSS 変数として実装する。
実装パターンは [improvement-domains.md](references/improvement-domains.md) の「UI/ビジュアル改善ドメイン」を参照。

**品質基準**: ハードコード色値禁止・WCAG AA コントラスト比 4.5:1 以上・タッチターゲット 44px 以上

### 4b. コンポーネントの UI 改善実装

Phase 3 の設計に基づき、各コンポーネントの UI を実装する。

**UI スニペットの活用**:
`snippets/html/ui/` の検証済みスニペットを積極活用する。HTML スニペットをベースに、出力先の言語・フレームワークに合わせて実装する。
スニペットには Refactoring UI + Laws of UX の設計原則が組み込まれている。

| 改善対象コンポーネント | 実装方針 |
|:---|:---|
| 既存コンポーネントの修正 | デザイントークンを使用するよう修正。構造は変えない |
| スニペットで置換できるもの | スニペットをベースにプロジェクトのデザイントークンでカスタマイズ |
| 新しく設計したコンポーネント | Refactoring UI 原則に従い新規実装 |

### 4c. レスポンシブ改善

Mobile First → Tablet（768px）→ Desktop（1024px+）。
モバイルファーストで実装し、ブレイクポイントで拡張する。

**チェックリスト**:
- [ ] 全カラーが CSS 変数（デザイントークン）で実装されている（ハードコードなし）
- [ ] WCAG AA コントラスト比 4.5:1 以上を全色で満たしている
- [ ] タッチターゲットが 44px 以上になっている
- [ ] スペーシングが 4px ベースの制約スケールに従っている
- [ ] prefers-reduced-motion に対応している
- [ ] レスポンシブ対応が最低 2 ブレイクポイントで実装されている
- [ ] 活用可能な UI スニペット（`snippets/html/ui/`）を適用した
- [ ] Phase 3 の UI/ビジュアル改善設計と実装が一致している

**→ Phase 5 への受け渡し**: 改善済み CSS / マークアップ（出力先のスタックに応じたコンポーネント）

### R4: フェーズレビュー（review に委譲）

| レビュー観点 | 検証内容 |
|:---|:---|
| **デザイントークン準拠** | ハードコード色値がなく、CSS 変数が正しく使われているか |
| **WCAG AA 準拠** | コントラスト比・タッチターゲット・モーション対応 |
| **Phase 3 設計との一致** | 改善設計書の UI 仕様が実装に反映されているか |
| **視覚的統一性** | コンポーネント間のスタイルが統一されているか |
| **レスポンシブ** | モバイル・デスクトップ両方で適切に表示されるか |

**判定**: Approved → Phase 5 へ、Rejected → Phase 4 の指摘箇所を修正し再レビュー

---

## Phase 5: コード改善実装（effective-typescript + bug-triage-fix に委譲）

> **有効な状態のみ表現する型で、バグが生まれる余地を塞げ**

### 5a. 型設計の改善（effective-typescript に委譲）

Phase 1 で発見した型安全性の問題を修正する。
改善パターン詳細は [improvement-domains.md](references/improvement-domains.md) の「コード品質改善ドメイン」を参照。

**核心ルール**: タグ付きユニオンで状態を表現・`any` → `unknown` + 型ガード・`enum` → リテラルユニオン・
パブリック API に戻り値型を明示・`switch` 文に `never` 型の網羅性チェック

### 5b. バグの修正（bug-triage-fix に委譲）

Phase 1 で発見した P1（Critical/High）バグを修正する。P2 Medium は可能なら修正、P3 Low は次サイクルへ。

### 5c. パフォーマンス改善の実装

Phase 1 で診断されたパフォーマンス問題を実装で解消する。
実装パターン詳細は [improvement-domains.md](references/improvement-domains.md) の「パフォーマンス改善ドメイン」を参照。

### 5d. リグレッションチェック

改善実装がスコープ外の機能に影響を与えていないかを確認する。
詳細なチェック項目は [regression-risk-checklist.md](references/regression-risk-checklist.md) を参照。

**チェックリスト**:
- [ ] `any` が改善対象コード内でゼロになっている
- [ ] `enum` が改善対象コード内でゼロになっている
- [ ] Phase 1 発見の P1 バグが全て修正されている
- [ ] 型エラーが 0 件
- [ ] パブリック API に戻り値型が明示されている
- [ ] `switch` 文に `never` 型の網羅性チェックがある
- [ ] リグレッションチェックリストを実施し、問題がないことを確認した
- [ ] Phase 0 の成功基準（コード品質軸）を満たしている

**→ Phase 6 への受け渡し**: 全改善コード + Phase 0 の成功基準

### R5: フェーズレビュー（review に委譲）

| レビュー観点 | 検証内容 |
|:---|:---|
| **型安全性の改善** | any/enum ゼロ・タグ付きユニオン・never 網羅性チェック |
| **バグ修正の完全性** | P1 課題が全て修正済みか、修正が適切か |
| **パフォーマンス改善の実装** | 設計した最適化が正しく実装されているか |
| **リグレッション安全性** | 改善対象外のコードに影響がないか |
| **Phase 3 設計準拠** | コード改善設計と実装が一致しているか |

**判定**: Approved → Phase 6 へ、Rejected → Phase 5 の指摘箇所を修正し再レビュー

---

## Phase 6: 最終統合レビュー（review に委譲）

> **Before と After を並べ、改善が証明できなければ完了ではない**

R0〜R5 の各フェーズレビューを経た成果物を、全 Phase 横断で統合的に最終検証する。
ここでは **Phase 間の整合性**・**成功基準の達成**・**Before/After の定量比較**を検証する。

### 6a. 成功基準の達成検証

| Phase 0 の成功基準 | Before | After | 達成 |
|:---|:---|:---|:---|
| UX 成功基準（操作ステップ等） | <Before値> | <After値> | Yes/No |
| UI 成功基準（コントラスト等） | <Before値> | <After値> | Yes/No |
| コード成功基準（any 数等） | <Before値> | <After値> | Yes/No |
| パフォーマンス成功基準（LCP等） | <Before値> | <After値> | Yes/No |

### 6b. 設計ドキュメントレビュー（review Part A）

| 基準 | チェック内容 |
|:---|:---|
| **A-1 要件カバレッジ** | Phase 0 の成功基準が全て達成されているか |
| **A-2 章間整合性** | Phase 1 の診断 → Phase 2 の優先付け → Phase 3 の設計 → Phase 4-5 の実装が一貫しているか |
| **A-3 数値の妥当性** | Before/After の比較数値が正確か |
| **A-4 可読性** | 改善の意図と結果が第三者に伝わるか |

### 6c. コードレビュー（review Part B）

| 基準 | チェック内容 |
|:---|:---|
| **B-1 Semantic Drift** | 実装が Phase 3 の改善設計から逸脱していないか |
| **B-2 Accounting Integrity** | 数値計算の精度（パフォーマンスメトリクスの計測精度） |
| **B-3 Edge Case Attack** | 改善で新たに生まれた境界値の問題がないか |
| **B-4 Privacy Violation** | 改善過程でPII がログ等に混入していないか |
| **B-5 Performance** | 改善でパフォーマンスが悪化していないか |

### 6d. 差し戻しフロー（Iterative パターン）

| レビュー結果 | アクション |
|:---|:---|
| **Approved**（成功基準達成・Critical=0, Major=0） | ワークフロー完了 |
| **Rejected — コード品質** | Phase 5 に差し戻し → 修正 → R5 再レビュー → Phase 6 再実行 |
| **Rejected — 設計不整合** | Phase 3 or 4 に差し戻し → 修正 → 該当 R レビュー → 後続 Phase 再実行 |
| **Rejected — 成功基準未達** | Phase 2 に差し戻し → 優先度見直し → 以降全再実行 |

> **原則**: 最終統合レビューでの差し戻しは最大 2 回。3 回必要な場合は Phase 0 のスコープ定義に問題がある。

**チェックリスト**:
- [ ] Phase 0 の全成功基準が Before/After で達成を確認できる
- [ ] 設計ドキュメントレビュー A-1〜A-4 に全て合格
- [ ] コードレビュー B-1〜B-5 に全て合格
- [ ] Critical 指摘 = 0 件
- [ ] Major 指摘 = 0 件（全件修正済み）
- [ ] Before/After 比較レポートが完成している

---

## Examples

### Example 1: 管理画面ダッシュボードの視認性・操作性改善

```
「管理画面のダッシュボードが見づらくて使いにくい。改善してほしい」

→ Phase 0: 対象=Dashboard.tsx, 改善ドメイン=UX+UI, 成功基準=「重要指標が 3 秒以内に把握できる」
→ R0: Approved
→ Phase 1: bug-finder「ハードコード色値 12 箇所、型エラー 3 件」
         ux-psychology「Miller's Law 違反（カード 9 個で認知過負荷）、Von Restorff 欠如（重要数値が目立たない）」
         UI「視覚的階層が 1 段階のみ、スペーシングが不統一」
→ R1: Approved
→ Phase 2: P1「カード削減（High Impact, Low Effort）」ADR「ダッシュボードカードを 7 個以内に制限」
→ R2: Approved
→ Phase 3: Miller's Law適用でカード 5 個に集約、Von Restorff で主要KPIを強調、
         CSS変数でカラーシステム設計
→ R3: Approved
→ Phase 4: CSS変数実装、KPIカードのビジュアル改善（コントラスト強化・スペーシング統一）
→ R4: Approved
→ Phase 5: ハードコード色値→CSS変数置換、型エラー 3 件修正、any 削除
→ R5: Approved
→ Phase 6: Before/After「KPI 把握時間: 8秒→2秒」→ Approved
```

### Example 2: フォーム離脱率改善（UX 中心）

```
「サインアップフォームの離脱率が 60% もある。UX を改善したい」

→ Phase 0: 対象=SignupForm.tsx, 改善ドメイン=UX, 成功基準=「離脱率 30% 以下」
→ R0: Approved
→ Phase 1: ux-psychology「Postel's Law 違反（バリデーションが厳格すぎる）」
         「Miller's Law 違反（1画面 9 フィールド）」「Peak-End Rule 欠如（完了演出なし）」
→ R1: Approved
→ Phase 2: P1「フィールド削減 + バリデーション改善（High Impact, Low Effort）」
→ R2: Approved
→ Phase 3: 2ステップ分割設計（必須のみ → 任意）、リアルタイムバリデーション設計、完了アニメーション設計
→ R3: Approved
→ Phase 4: Stepperコンポーネント実装、バリデーション状態のビジュアル改善、Toast完了演出
→ R4: Approved
→ Phase 5: FormState タグ付きユニオン型に移行（isValid + isSubmitting フラグ廃止）
→ R5: Approved
→ Phase 6: Before/After「離脱率: 60%→28%」→ Approved
```

### Example 3: TypeScript 型安全性リファクタリング

```
「このコードベース、any だらけで型エラーが怖くて触れない。型安全にして」

→ Phase 0: 対象=src/features/order/, 改善ドメイン=コード品質, 成功基準=「any=0, enum=0」
→ R0: Approved
→ Phase 1: bug-finder「any 23 箇所、enum 5 件、boolean フラグ地獄 8 箇所」
→ R1: Approved
→ Phase 2: P1「enum→リテラルユニオン移行（High Impact, Low Effort）」
         P1「boolean フラグ→タグ付きユニオン移行（High Impact, Medium Effort）」
→ R2: Approved
→ Phase 3: OrderStatus タグ付きユニオン設計、型ガード関数設計
→ R3: Approved
→ Phase 4: UI変更なし（スキップ）
→ Phase 5: enum 5件→リテラルユニオン置換、boolean フラグ→タグ付きユニオン移行、any→unknown+型ガード
→ R5: B-3 Major「null 未処理が 2 箇所残存」→ 修正 → 再レビュー → Approved
→ Phase 6: Before/After「any: 23→0, enum: 5→0, 型エラー: 0 維持」→ Approved
```

### Example 4: レスポンシブデザインの修正・改善

```
「スマホで見ると崩れまくってる。モバイル対応をちゃんとして」

→ Phase 0: 対象=全画面コンポーネント, 改善ドメイン=UI, 成功基準=「モバイルで全画面がレイアウト崩れなし」
→ R0: Approved
→ Phase 1: UI「タッチターゲット 12px（44px未満）、横スクロール発生、固定幅 px 多数」
→ R1: Approved
→ Phase 2: P1「固定幅→相対値置換（High Impact, Low Effort）」「タッチターゲット修正（High, Low）」
→ R2: Approved
→ Phase 3: Mobile First 設計方針確定、768px / 1024px ブレイクポイント設計
→ R3: Approved
→ Phase 4: px→clamp()/rem置換、タッチターゲット 44px 以上に修正、横スクロール解消
→ R4: Approved
→ Phase 5: 型変更なし（スキップ）
→ Phase 6: Before/After「全画面でレイアウト崩れゼロ確認」→ Approved
```

### Example 5: パフォーマンス（表示速度）改善

```
「商品一覧ページの表示が遅い。LCP が 6 秒もかかってる」

→ Phase 0: 対象=ProductList.tsx + API, 改善ドメイン=パフォーマンス, 成功基準=「LCP 2.5 秒以内」
→ R0: Approved
→ Phase 1: bug-finder「N+1 クエリ 1 件、全商品を一度に取得（1000件）」
         ux-psychology「Doherty Threshold 違反（6秒はユーザー離脱閾値超え）」
→ R1: Approved
→ Phase 2: P1「ページネーション導入（High Impact, Medium Effort）」
         P1「N+1クエリ解消（High, Low）」ADR「ページネーション方式はカーソル式を採用」
→ R2: Approved
→ Phase 3: カーソルページネーション設計、Skeleton UI 設計（Doherty Threshold対応）
→ R3: Approved
→ Phase 4: Skeleton UIコンポーネント実装、ローディング状態ビジュアル実装
→ R4: Approved
→ Phase 5: N+1クエリ修正、カーソルページネーション実装、React.memo適用
→ R5: Approved
→ Phase 6: Before/After「LCP: 6.0秒→1.8秒」→ Approved
```

### Example 6: アクセシビリティ（WCAG AA）対応

```
「このサービス、アクセシビリティが全然ダメ。WCAG AA に準拠させて」

→ Phase 0: 対象=全UIコンポーネント, 改善ドメイン=アクセシビリティ, 成功基準=「WCAG AA 全項目通過」
→ R0: Approved
→ Phase 1: UI「コントラスト比 2.1:1（AA基準 4.5:1未満）、aria-label 欠如、キーボード操作不可」
→ R1: Approved
→ Phase 2: P1「コントラスト比修正（High, Low）」P1「aria-label 追加（High, Low）」
→ R2: Approved
→ Phase 3: カラーシステム再設計（AA準拠値）、aria 属性設計、focus 管理設計
→ R3: Approved
→ Phase 4: コントラスト比修正（CSS変数でカラー再定義）、focus-visible スタイル実装
→ R4: Approved
→ Phase 5: aria-label/role 属性追加、キーボードイベントハンドラ実装
→ R5: Approved
→ Phase 6: Before/After「WCAG AA: 未準拠→全項目通過」→ Approved
```

### Example 7: 通知システムのUX・見た目のブラッシュアップ

```
「通知センター、なんか古臭くて使いにくい。全体的にブラッシュアップしてほしい」

→ Phase 0: 対象=Notification関連コンポーネント, 改善ドメイン=UX+UI, 成功基準=「既読率向上・視覚的統一」
→ R0: Approved
→ Phase 1: ux-psychology「Von Restorff 欠如（未読・既読の区別が薄い）」「Doherty 問題（既読処理が遅い）」
         UI「影のエレベーション不統一、仕上げ（空の状態）の欠如」
→ R1: Approved
→ Phase 2: P1「未読・既読の視覚差別化（High, Low）」P2「空の状態デザイン（Medium, Low）」
→ R2: Approved
→ Phase 3: Von Restorff原則で未読バッジ設計、Doherty対応の楽観的更新設計、空の状態設計
→ R3: Approved
→ Phase 4: 未読・既読スタイル差別化実装、アニメーション改善、空の状態コンポーネント
→ R4: Approved
→ Phase 5: 楽観的更新実装（既読処理の即時反映）、NotificationType タグ付きユニオン型
→ R5: Approved
→ Phase 6: Before/After 確認 → Approved
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| 改善対象が広すぎて 1 ワークフローに収まらない | Phase 0 のスコープ定義が大きすぎ | コンポーネント単位・機能単位に分割して個別実行 |
| Phase 1 の診断で課題が多すぎる | スコープが広すぎる or 技術的負債が多い | Phase 0 に戻り対象を絞る。または Phase 2 の優先付けで P4 を大量除外 |
| implementation-flow と improve-flow のどちらを使うか迷う | 作業種別が曖昧 | [implementation-flow Phase 0c](../implementation-flow/SKILL.md) の 4 問で判定。Q2 Yes → improve-flow。新機能あり → implementation-flow |
| パフォーマンス改善のみなのに implementation-flow が起動 | Phase 0c 未実施 | perf-only → improve-flow へリダイレクト（implementation-flow Phase 0c Q2） |
| Phase 1 と Phase 3 で ux-psychology を両方使う意味がわからない | 役割の違いが不明確 | Phase 1 は「何が壊れているか診断」、Phase 3 は「どう直すか設計」—目的が異なる |
| 改善実装でリグレッションが発生した | 影響範囲の見積もりが不十分 | Phase 2 の ADR にリグレッションリスクを記録する習慣をつける。[regression-risk-checklist.md](references/regression-risk-checklist.md) を使う |
| Phase 4（UI）と Phase 5（コード）の順序が逆では？ | UI 改善の前に型安全にすべきでは？ | UI 改善のベースになる型定義は Phase 3 で設計済み。実装は UI（ビジュアル）→コード（ロジック）の順が自然 |
| 成功基準が「定量的に比較できない」形になってしまう | Phase 0 で基準の定義が甘い | 「ユーザーが感じた」等の定性基準を避ける。数値・件数・チェックリスト通過で定義する |
| Before/After の記録を忘れて比較できなくなった | Phase 0 の Before 記録を怠った | Phase 6 で気づいた場合は git diff や診断レポートから再構成する |
| 全ドメイン（UX/UI/コード/パフォーマンス）を同時に改善しようとする | スコープクリープ | Phase 0 で改善ドメインを 1-2 個に絞る。残りは次サイクルで対応 |
| Phase 2 の優先付けで全て P1 になってしまう | Impact / Effort の基準が不明確 | [improvement-priority-matrix.md](references/improvement-priority-matrix.md) の判定基準を使う。全部が重要なら、最も Impact が高いものを選ぶ |
| コード改善でテストが壊れる | テストが実装の詳細に依存していた | テストのリファクタリングも Phase 5 のスコープに含める |
| デザイントークン導入でスタイルが全体的に変わってしまう | 既存のハードコード値がトークンと異なる | Phase 3 でトークン定義時に既存値との差異を確認し、段階的に移行する |

---

## References

| ファイル | 内容 |
|:---|:---|
| [improvement-domains.md](references/improvement-domains.md) | 改善ドメイン（UX/UI/コード/パフォーマンス/アクセシビリティ）別の診断観点・改善パターン |
| [phase-output-templates.md](references/phase-output-templates.md) | 各フェーズの成果物テンプレート（診断レポート・ADR・Before/After 比較表） |
| [improvement-priority-matrix.md](references/improvement-priority-matrix.md) | 改善課題の Impact × Effort 優先付けマトリクスと判定基準 |
| [regression-risk-checklist.md](references/regression-risk-checklist.md) | リグレッションリスク管理チェックリスト（改善実装時の安全確認） |

---

## Related Skills

| スキル | 関係 | 連携シナリオ |
|:---|:---|:---|
| **implementation-flow** | リダイレクト / エスカレーション | Phase 0c Q2 で `perf-only` と判定 → 本スキルが正。Phase 2 で新規コンポーネント追加が必要と判明 → implementation-flow Lite `extend` へエスカレーション。改善後に新機能追加 → Full Path を後続実行 |
| **bug-finder** | 委譲先（Phase 1） | Phase 1 でコード全体を能動スキャンし、潜在バグの診断結果を課題リストとして受け取る |
| **bug-triage-fix** | 委譲先（Phase 5） | Phase 5 で bug-finder が発見した P1 バグを個別に根本原因特定・修正する |
| **ux-psychology** | 委譲先（Phase 1・3） | Phase 1 では診断モードで UX 評価、Phase 3 では設計モードで Laws of UX に基づく改善策を設計する |
| **ui-design** | 委譲先（Phase 3・4） | Phase 3 でコンポーネント UI の改善設計、Phase 4 で Refactoring UI 原則に基づく実装 |
| **front-design** | 委譲先（Phase 4） | Phase 4 でビジュアル戦略・デザイントークン（CSS 変数）の実装を担当 |
| **effective-typescript** | 委譲先（Phase 5） | Phase 5 で Effective TypeScript 83 項目に基づく型安全性の改善実装を担当 |
| **software-architecture** | 委譲先（Phase 3） | Phase 3 でアーキテクチャ問題の改善設計（コンポーネント分割・依存関係整理）を担当 |
| **decision-framework** | 委譲先（Phase 2） | Phase 2 で改善課題の Impact × Effort 優先付けと ADR による意思決定記録を担当 |
| **deep-research** | 委譲先（Phase 2） | Phase 2 で特定課題の解決ベストプラクティスを「標準」レベルで調査する |
| **review** | ゲートキーパー（R0〜R5, Phase 6） | 各フェーズの品質ゲート（R0〜R5）と最終統合レビュー（Phase 6）を担当 |
