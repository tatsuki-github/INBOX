---
name: unity-catalog
description: >
  Unity Catalog の設計・構築・移行を包括的に支援するスキル。
  カタログ/スキーマ設計（環境別・ドメイン別・ハイブリッド戦略）、
  アクセス制御（GRANT/REVOKE、ABAC、Row Filter、Column Mask）、
  外部データ連携（Lakehouse Federation、Delta Sharing）、
  AI/ML アセット管理、Hive Metastore からの移行計画、
  Terraform IaC、System Tables 運用を一貫してガイドする。
  Use when user says「Unity Catalogを設計して」「カタログ戦略を決めて」
  「UCのアクセス制御を設計して」「HiveからUCに移行したい」
  「Delta Sharingを設定して」「UCのTerraformを書いて」
  「Row Filterを設計して」「ABACポリシーを設計して」「UCの権限設計」。
  Do NOT use for: クラウドインフラ設計（→ databricks-cloud-arch）、
  Delta Lake テーブル設計・最適化（→ delta-lake）。
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: data-platform
---

# Skill: Unity Catalog（統合データ・AI ガバナンス設計）

> **データとAIのガバナンスを一元化せよ — Unity Catalog で組織のデータ資産を統治する**

## Instructions

### ワークフロー内の位置

```
要件定義 → [unity-catalog] → Terraform IaC / 運用設計 → review
                 ↓
            ・カタログ/スキーマ設計書
            ・アクセス制御マトリクス
            ・外部連携設計書
            ・移行計画書
            ・Terraform テンプレート
            ・運用ダッシュボード定義
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| データ基盤の現状 | 既存の Hive Metastore やストレージ構成 | 「Hive に 500 テーブルある」 |
| ガバナンス要件 | セキュリティ・コンプライアンス要件 | 「PII を部門別に制御したい」 |
| 組織構造 | チーム・部門とデータドメインの関係 | 「営業・マーケ・財務の 3 部門」 |
| クラウド環境 | Azure / AWS / GCP の構成情報 | 「Azure の East Japan リージョン」 |
| 既存設計ドキュメント | 過去のアーキテクチャ設計書 | data-arch スキルの出力 |

### 出力

| 出力 | 形式 | 説明 |
|:---|:---|:---|
| カタログ/スキーマ設計書 | Markdown + ASCII 図 | 3 レベル名前空間の構造定義 |
| アクセス制御マトリクス | Markdown テーブル | グループ × オブジェクト × 権限のマトリクス |
| 外部連携設計書 | Markdown | External Location / Federation / Sharing の定義 |
| 移行計画書 | Markdown + チェックリスト | Hive → UC の段階的移行スケジュール |
| Terraform テンプレート | HCL コードブロック | IaC リソース定義 |
| 運用設計書 | Markdown + SQL | System Tables クエリと監視設計 |

---

## Step 1: 要件の整理

データ基盤の現状、ガバナンス要件、組織構造を体系的に把握する。

### 1a. データ基盤の現状把握

| 確認項目 | 質問例 | 記録すべき内容 |
|:---|:---|:---|
| **Metastore 構成** | 「現在 Hive Metastore を使っている？」 | HMS の有無、テーブル数、データベース数 |
| **ストレージ構成** | 「データは ADLS Gen2？S3？」 | クラウドプロバイダー、ストレージアカウント、コンテナ構成 |
| **ワークスペース構成** | 「ワークスペースはいくつある？」 | ワークスペース数、リージョン、用途 |
| **データ量・テーブル数** | 「テーブル数と総データ量は？」 | テーブル数、ボリューム、データ総量 |
| **既存のアクセス制御** | 「現在の権限管理はどうしている？」 | テーブル ACL、パスベース、IAM ロール |

### 1b. ガバナンス要件の特定

| 要件カテゴリ | 確認事項 |
|:---|:---|
| **セキュリティ** | PII の存在、暗号化要件、ネットワーク制限 |
| **コンプライアンス** | GDPR、個人情報保護法、業界固有の規制 |
| **監査** | アクセスログの保持期間、監査対象の範囲 |
| **データ分類** | 機密レベルの定義（Public / Internal / Confidential / Restricted） |

### 1c. 組織構造のマッピング

ユーザーから以下の情報を収集し、データドメインと組織の対応表を作成する:

- **部門・チーム構成**: データを生成・消費するチーム
- **ロール定義**: データエンジニア、アナリスト、サイエンティスト、管理者
- **データドメイン**: ドメインとオーナーシップの対応関係
- **外部共有**: 社外パートナーとのデータ共有の有無

**チェックリスト**:
- [ ] 既存の Metastore 構成とテーブル数を把握した
- [ ] クラウドプロバイダーとストレージ構成を確認した
- [ ] ガバナンス・コンプライアンス要件を特定した
- [ ] データドメインと組織の対応表を作成した
- [ ] 既存のアクセス制御の仕組みを把握した

---

## Step 2: カタログ/スキーマ設計

3 レベル名前空間（`catalog.schema.object`）の構造を設計する。
設計パターンの詳細は [catalog-design-patterns.md](references/catalog-design-patterns.md) を参照。

### 2a. カタログ戦略の選定

Step 1 で収集した情報をもとに、最適なカタログ戦略を選定する:

| 戦略 | 構造例 | 適用条件 |
|:---|:---|:---|
| **環境別** | `dev` / `staging` / `prod` | 小〜中規模、チーム数が少ない |
| **ドメイン別** | `sales` / `marketing` / `finance` | Data Mesh 志向、ドメインオーナーシップが明確 |
| **ハイブリッド** | `prod_sales` / `dev_marketing` / `shared` | 大規模組織、環境分離とドメイン分離の両方が必要 |

**推奨**: 環境ベースのカタログで開始し、スキーマ内をドメインで組織化し、スケールに応じてハイブリッドへ進化させる。

### 2b. 命名規則の策定

以下の命名規則をユーザーと合意する:

| 対象 | 規則 | 例 |
|:---|:---|:---|
| カタログ | `{env}` または `{env}_{domain}` | `prod`, `dev_sales` |
| スキーマ | `{layer}_{source}` または `{domain}` | `bronze_salesforce`, `analytics` |
| テーブル | `{entity}` （スネークケース） | `customers`, `order_items` |
| ビュー | `v_{entity}` または `{entity}_view` | `v_daily_sales` |

**注意**: Unity Catalog のオブジェクト名はすべて小文字で格納される。名前の最大長は 255 文字。

### 2c. Managed vs External の判断

| 判断基準 | Managed を選択 | External を選択 |
|:---|:---|:---|
| 新規テーブル | デフォルトで Managed | — |
| 既存データ | — | 既存ストレージのデータにガバナンスを適用 |
| 外部共有 | — | 他システムからのアクセスが必要 |
| フォーマット | Delta Lake のみ | CSV, JSON, Parquet 等の多様なフォーマット |
| DROP 時 | データも削除してよい | データを保持したい |

### 2d. カタログ構造の ASCII 図作成

設計結果を ASCII 図で可視化し、ユーザーと合意する。例:

```
metastore (ap-northeast-1)
├── dev          ← bronze_*, silver_*, sandbox
├── prod         ← bronze_*, silver_*, gold_*, ml_features
└── shared       ← master_data
```

**チェックリスト**:
- [ ] カタログ戦略を 3 パターンから選定し、理由を明記した
- [ ] 命名規則をテーブルで定義し、ユーザーと合意した
- [ ] Managed vs External の判断基準を各テーブル群に適用した
- [ ] カタログ構造を ASCII 図で可視化した
- [ ] アンチパターン（カタログ乱立、1 スキーマ集約、個人オーナー）を回避した

---

## Step 3: アクセス制御設計

グループ設計、権限マトリクス、データ保護（Row Filter / Column Mask / ABAC）を設計する。
権限の詳細は [privileges-matrix.md](references/privileges-matrix.md)、SQL 構文は [sql-reference.md](references/sql-reference.md) を参照。

### 3a. グループ設計

アカウントレベルグループをロールベースで設計する:

| グループ名 | 説明 | 想定メンバー |
|:---|:---|:---|
| `data_platform_admins` | Metastore / カタログの管理者 | プラットフォームチーム |
| `data_engineers` | パイプライン構築、テーブル作成 | データエンジニアリングチーム |
| `data_analysts` | データ参照、ダッシュボード作成 | 分析チーム |
| `data_scientists` | ML モデル開発、Feature Store 利用 | ML チーム |
| `{domain}_owners` | ドメイン固有のデータ管理 | ドメインオーナー |

**原則**:
- プロダクション環境のオーナーシップは必ずグループに割り当てる（個人不可）
- ワークスペースローカルグループではなくアカウントレベルグループを使用する
- サービスプリンシパルをジョブ実行に使用する

### 3b. 権限マトリクスの作成

カタログ × グループの権限マトリクスを作成する:

| オブジェクト | platform_admins | data_engineers | data_analysts | data_scientists |
|:---|:---|:---|:---|:---|
| `prod` カタログ | MANAGE | USE_CATALOG, CREATE_SCHEMA | USE_CATALOG | USE_CATALOG |
| `prod.gold_*` スキーマ | MANAGE | USE_SCHEMA, CREATE_TABLE | USE_SCHEMA, SELECT | USE_SCHEMA, SELECT |
| `prod.ml_*` スキーマ | MANAGE | USE_SCHEMA | SELECT | USE_SCHEMA, CREATE_TABLE, CREATE_MODEL |
| `dev` カタログ | MANAGE | ALL_PRIVILEGES | USE_CATALOG, USE_SCHEMA, SELECT | ALL_PRIVILEGES |

### 3c. Row Filter / Column Mask の適用判断

| 保護対象 | 手法 | 適用条件 |
|:---|:---|:---|
| 部門別の行制限 | Row Filter | 部門ごとに閲覧可能な行が異なる |
| PII カラム（SSN、メール等） | Column Mask | センシティブ情報を権限に応じて秘匿 |
| 機密レベル別の一括制御 | ABAC | タグベースでスケーラブルに制御したい |

**判断フロー**:
1. まず GRANT/REVOKE でオブジェクト単位の制御を設計する
2. 行レベルの制御が必要な場合 → Row Filter を追加
3. カラム単位の秘匿が必要な場合 → Column Mask を追加
4. 大規模にスケールする場合 → ABAC（Governed Tags + ポリシー）を導入

**チェックリスト**:
- [ ] アカウントレベルグループをロールベースで設計した
- [ ] カタログ × グループの権限マトリクスを作成した
- [ ] 最小権限の原則を適用した
- [ ] Row Filter / Column Mask の適用対象を特定した
- [ ] ABAC の導入要否を判断し、理由を明記した
- [ ] サービスプリンシパルのジョブ実行設計を含めた

---

## Step 4: 外部連携設計

External Location、Lakehouse Federation、Delta Sharing の設計を行う。
Securable Objects の階層は [securable-objects-hierarchy.md](references/securable-objects-hierarchy.md) を参照。

### 4a. External Location / Storage Credential の設計

既存のクラウドストレージに Unity Catalog のガバナンスを適用する:

| 設計項目 | 内容 |
|:---|:---|
| **Storage Credential** | クラウド別の資格情報（Azure: Managed ID / AWS: IAM Role / GCP: SA） |
| **External Location** | ストレージパスとアクセス制御の粒度を決定 |
| **粒度の判断** | コンテナ単位 vs サブディレクトリ単位（アクセス制御の要件で決定） |

### 4b. Lakehouse Federation の接続先設計

外部データソースへのフェデレーションクエリが必要な場合:

| 接続先 | 用途 | Connection タイプ |
|:---|:---|:---|
| PostgreSQL | 運用 DB の参照 | `postgresql` |
| SQL Server | 基幹システム連携 | `sqlserver` |
| Snowflake | 既存 DWH の並行利用 | `snowflake` |

**注意**: Lakehouse Federation は読み取り専用。書き込みが必要な場合は ETL パイプラインを構築する。

### 4c. Delta Sharing の設計

組織間でのデータ共有が必要な場合:

| 共有方式 | 適用条件 |
|:---|:---|
| **Databricks-to-Databricks** | 双方が Databricks ワークスペースを持つ |
| **Open Sharing** | 受信者が Databricks を持たない |
| **Marketplace** | 不特定多数への公開データプロダクト |

Share / Recipient の設計:
- Share はビジネスユースケース単位でグルーピングする
- Recipient は組織・パートナー単位で定義する
- 共有するテーブルは Gold レイヤーのみに限定する（Raw データは共有しない）

**チェックリスト**:
- [ ] Storage Credential のクラウド別設計を完了した
- [ ] External Location の粒度を決定し、一覧表を作成した
- [ ] Lakehouse Federation の接続先と用途を特定した（該当する場合）
- [ ] Delta Sharing の Share / Recipient を設計した（該当する場合）
- [ ] 外部連携のセキュリティリスクを評価した

---

## Step 5: AI/ML アセット設計

ML モデル、Feature Store、Volumes の Unity Catalog 上の構成を設計する。
該当しない場合はこのステップをスキップする。

### 5a. モデルレジストリの名前空間設計

Unity Catalog 統合の MLflow Model Registry を設計する:

```
prod (catalog)
├── ml (schema)
│   ├── fraud_detection_model    (MODEL)
│   ├── churn_prediction_model   (MODEL)
│   └── recommendation_model     (MODEL)
└── ml_features (schema)
    ├── customer_features         (TABLE - Feature Table)
    └── transaction_features      (TABLE - Feature Table)
```

| 設計方針 | 説明 |
|:---|:---|
| **スキーマ分離** | ML モデルは専用スキーマ（`ml`）に配置 |
| **環境分離** | `dev.ml` で実験、`prod.ml` にプロモート |
| **権限** | Data Scientists に `CREATE_MODEL`、Analysts には `SELECT`（推論利用） |

### 5b. Feature Store / Volumes の構成

| 項目 | 設計指針 |
|:---|:---|
| **Feature Table** | Unity Catalog のテーブルとして `ml_features` スキーマに集約 |
| **オンデマンド特徴量** | Python UDF で推論時にリアルタイム計算 |
| **Managed Volume** | モデルアーティファクト、ライブラリ（JAR / wheel） |
| **External Volume** | 画像、音声等の非構造化学習データ |

**チェックリスト**:
- [ ] モデルレジストリの名前空間を設計した
- [ ] Feature Store と Volumes の構成を定義した
- [ ] ML アセットへのアクセス権限を Step 3 の権限マトリクスに統合した

---

## Step 6: 移行計画

Hive Metastore から Unity Catalog への移行戦略を策定する。
新規構築の場合はこのステップをスキップする。
チェックリストの詳細は [migration-checklist.md](references/migration-checklist.md) を参照。

### 6a. UCX による現状アセスメント

Databricks Labs の UCX ツールでワークスペースを自動評価する:

| アセスメント項目 | 確認内容 |
|:---|:---|
| **テーブルインベントリ** | HMS テーブルの一覧、フォーマット、サイズ |
| **権限マッピング** | 既存のテーブル ACL → UC GRANT への変換 |
| **コード互換性** | ノートブック・ジョブの UC 非互換箇所 |
| **グループ移行** | ワークスペースレベル → アカウントレベルグループ |

### 6b. 移行方式の選定

| 方式 | 手法 | メリット | デメリット |
|:---|:---|:---|:---|
| **Soft Migration** | HMS Federation で UC に接続 | コード変更不要、低リスク | 一部機能が制限される |
| **Hard Migration** | SYNC / CLONE / CTAS でデータ移行 | UC の全機能を活用可能 | コード修正が必要 |

**推奨**: まず Soft Migration で UC を有効化し、並行期間を設けた後、段階的に Hard Migration へ移行する。

### 6c. 段階的移行スケジュール

| フェーズ | 期間目安 | 内容 |
|:---|:---|:---|
| **Phase 1: 準備** | 2-4 週 | UCX アセスメント、Storage Credential / External Location 作成、グループ移行 |
| **Phase 2: 並行運用** | 4-8 週 | Soft Migration（HMS Federation）、新テーブルは UC に作成 |
| **Phase 3: 本移行** | 4-12 週 | Hard Migration（SYNC / CLONE）、コード修正、テスト |
| **Phase 4: HMS リタイア** | 2-4 週 | HMS 参照の完全除去、クリーンアップ |

**チェックリスト**:
- [ ] UCX アセスメントの実行計画を策定した
- [ ] 移行方式（Soft / Hard / 段階的）を選定した
- [ ] テーブルの移行優先度を決定した（重要度 × 複雑度）
- [ ] 並行運用期間のテスト計画を作成した
- [ ] ロールバック手順を定義した
- [ ] Delta Lake Time Travel が移行されない点をユーザーに説明した

---

## Step 7: IaC・運用設計

Terraform による宣言的管理と System Tables を活用した運用設計を行う。
Terraform テンプレートは [terraform-templates.md](references/terraform-templates.md)、
運用クエリは [system-tables-queries.md](references/system-tables-queries.md) を参照。

### 7a. Terraform モジュール構成

Unity Catalog リソースを Terraform で管理するモジュール構成:

```
terraform/
├── modules/
│   ├── uc-foundation/       # Storage Credential, External Location
│   ├── uc-catalog/          # Catalog, Schema, Grants
│   ├── uc-access-control/   # グループ、権限マトリクス
│   └── uc-sharing/          # Delta Sharing, Federation
├── environments/
│   ├── dev/
│   └── prod/
└── main.tf
```

| リソース | Terraform タイプ | 管理方針 |
|:---|:---|:---|
| Storage Credential | `databricks_storage_credential` | foundation モジュール |
| External Location | `databricks_external_location` | foundation モジュール |
| Catalog | `databricks_catalog` | catalog モジュール |
| Schema | `databricks_schema` | catalog モジュール |
| Grants | `databricks_grants` | access-control モジュール |

**注意**: `databricks_grants` はオブジェクトの全権限を宣言的に管理する（指定外の権限は削除される）。既存権限に影響を与えたくない場合は `databricks_grant` を使用する。

### 7b. System Tables による監視設計

| 監視対象 | System Table | クエリの目的 |
|:---|:---|:---|
| アクセス監査 | `system.access.audit` | 不正アクセスの検出、コンプライアンス対応 |
| コスト管理 | `system.billing.usage` | DBU 消費量の分析、予算管理 |
| リネージ | `system.lineage.table_lineage` | テーブル間の依存関係の把握 |
| 棚卸し | `information_schema.tables` + `audit` | 未使用テーブルの特定 |

### 7c. 棚卸し・クリーンアップの自動化

| ジョブ | 実行頻度 | 内容 |
|:---|:---|:---|
| 未使用テーブル検出 | 週次 | 90 日以上アクセスのないテーブルを一覧化 |
| オーナー不在検出 | 月次 | オーナーが退職・異動したオブジェクトを特定 |
| クォータ監視 | 日次 | リソースクォータの使用率を監視 |
| 権限棚卸し | 四半期 | 過剰な権限を付与されているグループの検出 |

**チェックリスト**:
- [ ] Terraform モジュール構成を設計した
- [ ] `databricks_grants` vs `databricks_grant` の使い分けを決定した
- [ ] System Tables の有効化を確認した
- [ ] 監視ダッシュボードの設計（クエリ + 可視化）を完了した
- [ ] 棚卸しジョブの実行スケジュールを策定した

---

## Step 8: レビュー

設計全体のセキュリティレビューとベストプラクティス照合を実施する。

### 8a. セキュリティレビュー

| レビュー項目 | 確認内容 | 判定基準 |
|:---|:---|:---|
| 最小権限の原則 | 各グループに必要最小限の権限のみ付与されているか | 不要な `ALL_PRIVILEGES` がない |
| PII 保護 | センシティブデータに Row Filter / Column Mask が適用されているか | PII カラムが特定・保護されている |
| 環境分離 | Dev / Prod の権限が適切に分離されているか | Dev の権限が Prod に波及しない |
| オーナーシップ | Prod 環境のオーナーがグループに割り当てられているか | 個人ユーザーがオーナーでない |
| 監査ログ | System Tables が有効化され、監査クエリが準備されているか | `system.access.audit` がクエリ可能 |

### 8b. ベストプラクティスチェックリスト

Databricks 公式ベストプラクティスとの照合:

- [ ] 1 リージョンに 1 Metastore の原則を遵守している
- [ ] カタログ戦略が組織規模に適合している
- [ ] アカウントレベルグループを使用している（ワークスペースローカル不可）
- [ ] サービスプリンシパルでジョブを実行する設計になっている
- [ ] External Location の粒度がアクセス制御要件に合致している
- [ ] Terraform で宣言的管理が実現できる構成になっている
- [ ] 命名規則が一貫しており、小文字のみを使用している

### 8c. 設計ドキュメントの最終確認

| 確認項目 | 状態 |
|:---|:---|
| カタログ/スキーマ設計の ASCII 図 | |
| 権限マトリクス（全グループ × 全カタログ） | |
| Row Filter / Column Mask の適用対象一覧 | |
| External Location / Credential の一覧 | |
| 移行計画とスケジュール（該当する場合） | |
| Terraform モジュール構成と主要リソース定義 | |
| 監視・棚卸しの運用設計 | |

**チェックリスト**:
- [ ] セキュリティレビューの全項目を確認した
- [ ] ベストプラクティスチェックリストを照合した
- [ ] 設計ドキュメントの完全性を確認した
- [ ] ユーザーに設計の概要と次のアクションを説明した
- [ ] review スキルでのクリティカルレビューを推奨した

---

## Examples

### Example 1: 中規模組織の Unity Catalog 新規設計

```
「3 部門（営業・マーケ・財務）の Databricks 環境に Unity Catalog を導入したい」

→ Step 1 で組織構造とデータドメインをヒアリング
→ Step 2 で環境別カタログ（dev / staging / prod）を選定
  スキーマは Medallion × ドメインのハイブリッド構成
→ Step 3 でロールベースのグループ設計と権限マトリクスを作成
→ Step 4 で ADLS Gen2 の External Location を設計
→ Step 7 で Terraform テンプレートを生成
→ Step 8 でセキュリティレビューを実施
```

### Example 2: Hive Metastore からの段階的移行

```
「Hive に 500 テーブルある。UC に移行したいが、ダウンタイムは最小限に」

→ Step 1 で既存 HMS の構成を詳細に把握
→ Step 2 で UC 側のカタログ/スキーマ構造を設計
→ Step 3 で既存の権限を UC の GRANT に変換するマッピングを作成
→ Step 6 で段階的移行計画を策定
  Phase 1: UCX アセスメント → Phase 2: Soft Migration → Phase 3: Hard Migration
→ Step 7 で Terraform による UC リソース管理を設計
→ Step 8 で移行計画のリスクレビューを実施
```

### Example 3: PII データの行レベル・列レベルセキュリティ設計

```
「顧客テーブルに PII があり、部門ごとにアクセスを制御したい」

→ Step 1 で PII カラムの特定とアクセス要件を整理
→ Step 3b で部門別の権限マトリクスを作成
→ Step 3c で Row Filter（部門フィルタ）と Column Mask（SSN / メール秘匿）を設計
  SQL UDF の定義例を提供
→ Step 7 で Terraform による Row Filter / Column Mask の管理を設計
→ Step 8 でコンプライアンス要件との照合を実施
```

### Example 4: Delta Sharing による組織間データ共有

```
「パートナー企業に売上データを安全に共有したい」

→ Step 1 で共有要件（共有先、データ範囲、頻度）を整理
→ Step 2 で共有用の Gold テーブルを設計
→ Step 4c で Delta Sharing の Share / Recipient を設計
  Databricks-to-Databricks vs Open Sharing の選定
→ Step 3 で共有データへのアクセス権限を設計
→ Step 8 で共有データのセキュリティレビューを実施
```

### Example 5: Data Mesh + Unity Catalog の実装設計

```
「Data Mesh を導入したい。Unity Catalog でどう実現する？」

→ Step 1 で組織のドメイン構造とデータプロダクトの候補を特定
→ Step 2 でドメイン別カタログ戦略を設計
  各ドメインに raw / curated / analytics のスキーマを配置
→ Step 3 でフェデレーテッドガバナンス（中央 + ドメイン自律）の権限設計
→ Step 4c で Delta Sharing によるドメイン間データプロダクト共有を設計
→ Step 7 で Terraform によるセルフサービスインフラを設計
→ Step 8 で Data Mesh 4 原則との照合レビューを実施
```

### Example 6: Terraform による Unity Catalog の IaC 管理

```
「UC のリソースを Terraform で管理したい。テンプレートが欲しい」

→ Step 1 で対象リソース（Catalog / Schema / Grants / External Location）を特定
→ Step 2 で設計済みのカタログ構造を確認
→ Step 3 で権限マトリクスを Terraform の databricks_grants に変換
→ Step 7a で Terraform モジュール構成を設計
→ Step 7 で HCL コードを生成（references/terraform-templates.md を参照）
→ Step 8 で Terraform plan による差分確認手順を案内
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| カタログ数が爆発的に増加して管理不能 | プロジェクトごとにカタログを作成するアンチパターン | カタログ戦略を環境別またはドメイン別に再設計する。スキーマレベルでの分離を検討する |
| ワークスペースローカルグループに GRANT できない | Unity Catalog はアカウントレベルグループのみ対応 | SCIM プロビジョニングでアカウントレベルグループに移行する。IdP との同期を設定する |
| Row Filter / Column Mask が想定通りに動作しない | SQL UDF の定義ミスまたは関数の引数型不一致 | UDF を単独でテストし、返り値の型と引数の型が正しいか確認する |
| Terraform apply で権限が予期せず削除される | `databricks_grants` の宣言的管理が既存権限を上書き | 全権限を Terraform で管理するか、`databricks_grant` に切り替えて部分管理にする |
| Lakehouse Federation のクエリが遅い | 外部データソースの全データを Databricks 側で処理 | プッシュダウンフィルタを活用する。頻繁にアクセスするデータは ETL で取り込む |
| 移行後に Delta Lake Time Travel が使えない | CLONE / CTAS ではヒストリーが移行されない | 移行前にヒストリーの保持要件を確認し、必要に応じてアーカイブを作成する |
| External Location の権限エラー | Storage Credential のスコープ不足 | Storage Credential が対象パスへのアクセス権を持つか確認する。Managed ID / IAM Role の権限を見直す |
| カタログ間でテーブルを移動できない | Unity Catalog はカタログ間の ALTER TABLE 非対応 | CTAS（CREATE TABLE AS SELECT）でコピーし、元テーブルを DROP する |
| オーナー不在のオブジェクトが放置されている | 個人ユーザーをオーナーに設定してしまった | Metastore 管理者がオーナーをグループに変更する。棚卸しジョブで定期検出する |
| リソースクォータに到達した | テーブル / スキーマ数がデフォルト上限に達した | 不要なオブジェクトをクリーンアップする。必要に応じて Databricks サポートにクォータ引き上げを依頼する |
| ABAC ポリシーが意図通りに適用されない | Governed Tags の伝播ルールの誤解 | タグの階層的継承を確認する。親オブジェクトのタグが子に正しく伝播しているかを検証する |
| Information Schema のクエリが空結果を返す | クエリ実行ユーザーにアクセス権がない | Information Schema は権限のあるオブジェクトのみ返す。対象カタログの USE_CATALOG を確認する |

---

## References

| ファイル | 内容 |
|:---|:---|
| [securable-objects-hierarchy.md](references/securable-objects-hierarchy.md) | Securable Objects の完全な階層と権限一覧 |
| [privileges-matrix.md](references/privileges-matrix.md) | オブジェクトタイプ別の権限マトリクス |
| [catalog-design-patterns.md](references/catalog-design-patterns.md) | カタログ戦略パターンの詳細と判断基準 |
| [terraform-templates.md](references/terraform-templates.md) | Terraform リソース定義のテンプレート集 |
| [migration-checklist.md](references/migration-checklist.md) | Hive → UC 移行チェックリスト |
| [sql-reference.md](references/sql-reference.md) | GRANT/REVOKE、Row Filter、Column Mask 等の SQL 構文 |
| [system-tables-queries.md](references/system-tables-queries.md) | System Tables を活用した運用クエリ集 |

---

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **data-arch** | 前工程 | データアーキテクチャ選定の結果を受けて Unity Catalog の設計に反映する |
| **diagram** | 補完 | Unity Catalog のアーキテクチャ図、権限フロー図、移行計画図を生成する |
| **review** | 検証 | Unity Catalog 設計書のクリティカルレビュー（セキュリティ・ベストプラクティス照合） |
| **data-validation** | 検証 | Data Quality ルール（Expectations）の妥当性検証 |
