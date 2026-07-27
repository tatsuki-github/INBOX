# references/ 設計マトリクス

> 知識ソースの種別に応じた references/ フォルダ構成の設計ガイド。
> SS-6（references/ の画一化）を防止し、ドメイン固有の reference 構成を保証する。

---

## 知識ソース種別と推奨 reference 構成

### Type A: 書籍（体系的知識）

**特徴**: 原則・パターン・判断基準が体系的に整理されている。章構成に対応した reference 設計が有効。

| 推奨 reference 種別 | 目的 | ファイル名例 |
|:---|:---|:---|
| **ドメインパターン集** | 知識ソースのパターン・技法を構造化 | `type-system-patterns.md`, `design-patterns.md` |
| **技法詳細ガイド** | 特定技法の深掘り | `spacing-and-layout.md`, `data-modeling-guide.md` |
| **フレームワーク参照表** | 判断基準・比較表の即時参照 | `laws-quick-reference.md`, `architecture-comparison.md` |
| **チェックリスト** | ドメイン固有の品質基準 | `ethical-design-checklist.md`, `cost-optimization-checklist.md` |

**実証スキル**:

| スキル | 知識ソース | references/ 構成 | ファイル数 |
|:---|:---|:---|:---|
| **ui-design** | Refactoring UI | `visual-hierarchy.md`, `color-system.md`, `spacing-and-layout.md`, `component-patterns.md`, `depth-images-finishing.md`, `icon-catalog.md`, `typography-guide.md` | 7 |
| **data-arch** | Deciphering Data Architectures | `architecture-comparison.md`, `ads-question-templates.md`, `data-modeling-guide.md`, `data-ingestion-guide.md`, `people-and-technology.md` | 5 |
| **ux-psychology** | Laws of UX | `laws-quick-reference.md`, `psychology-concepts.md`, `design-principles-framework.md`, `ux-techniques.md`, `ethical-design-checklist.md` | 5 |
| **effective-typescript** | Effective TypeScript | `type-design-patterns.md`, `code-recipes.md` | 2 |

**設計原則**: 書籍の章構成をそのまま反映するのではなく、**スキルのステップで参照される単位**でファイルを分割する。

---

### Type B: API ガイド / 技術ドキュメント

**特徴**: ツールの使い方、API リファレンス、設定例が中心。機能領域別の分割が有効。

| 推奨 reference 種別 | 目的 | ファイル名例 |
|:---|:---|:---|
| **API/CLI リファレンス** | コマンド・プロパティの即時参照 | `sql-reference.md`, `property-reference.md` |
| **テンプレート集** | 設定ファイル・IaC のテンプレート | `terraform-templates.md`, `dabs-cicd-templates.md` |
| **ユースケースパターン** | 典型的な使用シナリオ | `auto-loader-patterns.md`, `merge-optimization.md` |
| **アーキテクチャパターン** | 構成パターンの比較 | `aws-architecture-patterns.md`, `networking-reference.md` |

**実証スキル**:

| スキル | references/ 構成 | ファイル数 |
|:---|:---|:---|
| **databricks** | `medallion-architecture.md`, `compute-selection-guide.md`, `dlt-expectations-patterns.md`, `auto-loader-patterns.md`, `dabs-cicd-templates.md`, `cost-optimization-checklist.md` | 6 |
| **unity-catalog** | `securable-objects-hierarchy.md`, `privileges-matrix.md`, `catalog-design-patterns.md`, `migration-checklist.md`, `terraform-templates.md`, `sql-reference.md`, `system-tables-queries.md` | 7 |
| **diagram** | `mxcell-structure.md`, `cloud-icons.md`, `style-guide.md` | 3 |

**設計原則**: ツールの**機能領域ごと**にファイルを分割し、各ファイルが単独で参照可能な自己完結型にする。

---

### Type C: ベストプラクティス / フレームワーク

**特徴**: 判断基準、チェックリスト、Decision Framework が中心。プロセスの段階に対応した分割が有効。

| 推奨 reference 種別 | 目的 | ファイル名例 |
|:---|:---|:---|
| **判断マトリクス** | 条件別の選択基準 | `cloud-comparison-matrix.md`, `law-selection-matrix.md` |
| **プロセスフレームワーク** | 段階的な実行手順 | `experiment-frameworks.md`, `hearing-framework.md` |
| **出力テンプレート** | 成果物のテンプレート | `report-templates.md`, `phase1-template.md` |
| **セキュリティ/品質チェック** | 非機能要件の検証 | `security-checklist.md`, `quality-checklist.md` |

**実証スキル**:

| スキル | references/ 構成 | ファイル数 |
|:---|:---|:---|
| **databricks-cloud-arch** | `aws-architecture-patterns.md`, `azure-architecture-patterns.md`, `networking-reference.md`, `cloud-comparison-matrix.md`, `security-checklist.md`, `terraform-modules.md` | 6 |
| **drm** | `drm-rules.md`, `hearing-guide.md`, `phase-definitions.md`, `phase1-template.md`, `phase2-template.md`, `phase6-template.md` | 6 |
| **skill-forge** | `skill-template.md`, `quality-checklist.md`, `gold-standard-analysis.md`, `workflow-quality-checklist.md`, `skill-patterns.md`, `testing-methodology.md`, `reference-design-matrix.md` | 7 |

**設計原則**: **意思決定のタイミング**でファイルを分割する。「いつ・何を判断するか」が明確なファイル構成にする。

---

### Type D: 実践ガイド / プロセス定義

**特徴**: ステップバイステップの手順、ワークフロー定義、チャネル別のガイドラインが中心。

| 推奨 reference 種別 | 目的 | ファイル名例 |
|:---|:---|:---|
| **プレイブック** | 施策の実行手順 | `cro-playbook.md`, `retention-strategies.md` |
| **チャネルガイドライン** | チャネル別の制約・最適化 | `channel-guidelines.md`, `platform-specs.md` |
| **テンプレート集** | 成果物テンプレート | `email-templates.md`, `funnel-analysis-templates.md` |
| **プロセス定義** | 編集・レビュープロセス | `seven-sweeps.md`, `creative-production-guide.md` |

**実証スキル**:

| スキル | references/ 構成 | ファイル数 |
|:---|:---|:---|
| **growth-ops** | `cro-playbook.md`, `experiment-frameworks.md`, `funnel-analysis-templates.md`, `retention-strategies.md`, `creative-production-guide.md` | 5 |
| **marketing-copy** | `copy-frameworks.md`, `channel-guidelines.md`, `email-templates.md`, `seven-sweeps.md` | 4 |

**設計原則**: **実行フェーズごと**にファイルを分割する。「何をするか」が明確なアクション指向のファイル構成にする。

---

## アンチパターン

| # | アンチパターン | 問題 | 対策 |
|:---|:---|:---|:---|
| AP-1 | **3 点セット均一構成** | `patterns.md` / `glossary.md` / `checklist.md` で全スキル同じ構成 | 知識ソースの種別（A/B/C/D）に応じた固有構成にする |
| AP-2 | **汎用ファイル名** | `reference.md`, `guide.md`, `notes.md` | ドメイン名を含める（例: `delta-lake-table-design.md`） |
| AP-3 | **巨大 reference** | 1 ファイルが 500 行を超える | トピック単位で分割（1 ファイル 100-300 行が目安） |
| AP-4 | **SKILL.md の複製** | reference の内容が SKILL.md のステップと重複 | reference は「詳細知識」、SKILL.md は「手順と判断」に分離 |
| AP-5 | **孤立 reference** | SKILL.md からリンクされていない reference ファイル | References テーブルとステップ内リンクで全 reference を接続 |

---

## セルフテスト

スキル完成時に以下の 3 問で references/ の固有性を検証する:

| # | 質問 | 期待回答 | 不合格時のアクション |
|:---|:---|:---|:---|
| ST-1 | **この references/ フォルダを別のスキルに差し替えても違和感がないか？** | **No**（ドメイン固有の構成である） | ファイル名とコンテンツにドメイン固有の用語を追加 |
| ST-2 | **各 reference ファイルのタイトルにドメイン固有の単語が含まれているか？** | **Yes** | `guide.md` → `medallion-architecture.md` のように具体化 |
| ST-3 | **reference のファイル構成は知識ソースの構造を反映しているか？** | **Yes** | 知識ソースの Type（A/B/C/D）を再判定し、推奨構成に合わせる |

> **判定**: ST-1〜ST-3 のうち 1 つでも不合格なら、references/ の再設計を検討する。
