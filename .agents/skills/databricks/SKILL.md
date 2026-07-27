---
name: databricks
description: >
  Databricks プラットフォームの設計・構築を包括的に支援するスキル。
  Workspace 構成、コンピュート選定（Classic/Serverless/Photon）、Medallion Architecture、
  DLT/Lakeflow パイプライン設計、MLflow/Model Serving、DBSQL 最適化、
  CI/CD（DABs + Terraform）、コスト最適化を一貫してガイドする。
  Use when user says「Databricksの設計をして」「Medallion Architectureを設計して」
  「DLTパイプラインを構築して」「Databricksのコスト最適化」「DBSQLを最適化して」
  「MLflowの設定をして」「Databricksのワークスペースを設計して」「Lakeflowを構成して」
  「Databricksのベストプラクティス」。
  Do NOT use for: クラウドインフラ設計全般（→ diagram + 各クラウドスキル）、
  Delta Lake テーブルの物理設計・チューニング専門（→ data-arch）、
  Unity Catalog のガバナンスポリシー専門設計（→ data-arch + review）。
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: data-platform
---

# Skill: Databricks（Databricks プラットフォーム設計・構築）

> **Lakehouse の力を引き出す設計図を描け — Workspace からコスト最適化まで一気通貫**

## Instructions

### ワークフロー内の位置

```
要件定義 → [databricks] → パイプライン実装 → 運用・最適化
               ↓
          Workspace 構成 / コンピュート選定 / Medallion Architecture
          DLT パイプライン / ML・AI 設計 / DBSQL 最適化
          CI/CD（DABs + Terraform）/ コスト最適化
```

### 入力

| 入力 | 例 |
|:---|:---|
| ワークロード要件 | 「日次 500GB の JSON ログを取り込む」 |
| チーム情報 | 「SQL 中心のチーム 5 名」 |
| クラウド環境 | 「Azure、既存 ADLS Gen2 あり」 |
| 既存 Databricks 環境 | 「Classic Cluster で運用中、コスト削減したい」 |
| ビジネス要件 | 「99.9% 可用性、GDPR 準拠」 |

### 出力

| 出力 | 形式 |
|:---|:---|
| Workspace 構成設計書 | Markdown（環境分離・命名規則・フォルダ構造） |
| コンピュート選定表 | Markdown テーブル（ワークロード別のタイプ・サイジング） |
| Medallion Architecture 定義 | Markdown + ASCII 図（Bronze/Silver/Gold） |
| DLT パイプライン設計書 | Markdown + コード例（Expectations・スケジュール） |
| CI/CD 構成 | YAML テンプレート（DABs + Terraform Split-Stack） |
| コスト最適化レポート | チェックリスト（削減施策と期待効果） |

---

## Step 1: 要件ヒアリング

プロジェクトの全体像を把握し、設計方針を決定するための情報を収集する。

### 1a. ワークロード特性の特定

以下の質問でワークロードを分類する:

| 質問 | 選択肢 | 設計への影響 |
|:---|:---|:---|
| 主要ワークロードは？ | ETL / 分析 / ML/AI / 混合 | コンピュート戦略・ステップの分岐 |
| データソースの種類は？ | ファイル / DB / SaaS / ストリーミング | インジェスション方式の選定 |
| データ量と増加率は？ | 日次 GB / TB 単位 | クラスターサイジング・コスト見積 |
| 処理頻度は？ | リアルタイム / ニアリアルタイム / バッチ | ストリーミング vs バッチ判断 |
| レイテンシ要件は？ | 秒 / 分 / 時 | コンピュートタイプの選定 |

### 1b. 環境・制約の確認

| 項目 | 確認内容 |
|:---|:---|
| クラウドプロバイダー | AWS / Azure / GCP（マルチクラウドの有無） |
| 既存 Databricks 環境 | 有無、現在のバージョン、課題 |
| セキュリティ要件 | ネットワーク分離、暗号化、コンプライアンス |
| 予算制約 | 月額予算、DBU 購入モデル（コミット / PAYG） |
| チーム構成 | DE / DS / Analyst の比率、SQL / Python の習熟度 |

### 1c. 設計スコープの確定

ヒアリング結果から、後続ステップの実行判断を行う:

| ステップ | 実行条件 |
|:---|:---|
| Step 2: Workspace 構成 | 常に実行 |
| Step 3: コンピュート戦略 | 常に実行 |
| Step 4: データパイプライン | ETL ワークロードがある場合 |
| Step 5: データ品質 | DLT を採用する場合 |
| Step 6: ML/AI 設計 | ML/AI ワークロードがある場合 |
| Step 7: SQL 分析最適化 | 分析・BI ワークロードがある場合 |
| Step 8: 運用・CI/CD | 常に実行 |

**チェックリスト**:
- [ ] 主要ワークロードタイプを特定した
- [ ] データソースの種類と量を把握した
- [ ] クラウドプロバイダーと既存環境を確認した
- [ ] セキュリティ・コンプライアンス要件を確認した
- [ ] チームのスキルセットを把握した
- [ ] 後続ステップの実行/スキップを判断した

---

## Step 2: Workspace 構成設計

Databricks Workspace の環境分離、命名規則、フォルダ構造を設計する。

### 2a. 環境分離戦略

| パターン | 構成 | 推奨シーン |
|:---|:---|:---|
| **サブスクリプション分離** | Dev / Staging / Prod を別アカウントに配置 | エンタープライズ（推奨） |
| **ワークスペース分離** | 同一アカウント内で Workspace を分離 | 中規模チーム |
| **フォルダ分離** | 単一 Workspace 内でフォルダベース分離 | 小規模・PoC |

### 2b. 命名規則の設計

環境・リソースの命名規則を統一する:

```
{org}-{env}-{region}-{resource_type}-{name}

例:
  acme-prod-japaneast-ws-analytics      # Workspace
  acme-prod-japaneast-cluster-etl       # Cluster
  acme-dev-japaneast-wh-adhoc           # SQL Warehouse
```

### 2c. Unity Catalog 名前空間設計

```
Unity Catalog Metastore
  └── {env}_{domain}        # Catalog（例: prod_sales）
       └── {layer}          # Schema（例: bronze, silver, gold）
            └── {table}     # Table（例: orders, customers）
```

| 設計パターン | Catalog 命名 | 適用シーン |
|:---|:---|:---|
| **環境 x ドメイン** | `prod_sales`, `dev_marketing` | 標準的な組織 |
| **環境単位** | `prod`, `dev`, `staging` | 小規模組織 |
| **ドメイン単位** | `sales`, `marketing`, `finance` | 環境分離がサブスクリプションレベル |

### 2d. フォルダ・リポジトリ構成

`/Repos/{team}/{project}/` 配下に `notebooks/` (bronze/silver/gold)、`pipelines/`、`tests/`、`databricks.yml` (DABs) を配置する。

**チェックリスト**:
- [ ] 環境分離パターンを選定し、その理由を記載した
- [ ] 命名規則を定義し、全リソースタイプに適用した
- [ ] Unity Catalog の Catalog/Schema 階層を設計した
- [ ] フォルダ・リポジトリ構成を定義した
- [ ] Blast Radius（障害影響範囲）を考慮した分離になっている

---

## Step 3: コンピュート戦略設計

ワークロード特性に応じた最適なコンピュートタイプとサイジングを決定する。
詳細な選定マトリクスは [compute-selection-guide.md](references/compute-selection-guide.md) を参照。

### 3a. コンピュートタイプの選定

| コンピュートタイプ | 用途 | コスト特性 | 推奨シーン |
|:---|:---|:---|:---|
| **Serverless SQL Warehouse** | SQL 分析・BI | DBU 単価高、管理コスト低 | ダッシュボード、アドホック分析 |
| **Serverless Jobs** | ETL・バッチ処理 | 起動時間ゼロ、DBU 課金 | 短時間ジョブ、頻繁な起動停止 |
| **Classic Job Cluster** | ETL・バッチ処理 | VM + DBU | 長時間バッチ、Spot 活用 |
| **Classic All-Purpose** | 対話的開発 | VM + DBU（常時起動注意） | Notebook 開発、デバッグ |
| **SQL Warehouse (Classic)** | SQL 分析 | VM + DBU | Serverless 未対応リージョン |

### 3b. Photon Engine の適用判断

| ワークロード | Photon 推奨度 | 理由 |
|:---|:---|:---|
| 大量集約・結合（100GB+） | 強く推奨 | 3x-8x の高速化、TCO 80% 削減可能 |
| Delta Lake 読み書き | 推奨 | ネイティブ最適化が有効 |
| SQL Warehouse | デフォルト有効 | 追加設定不要 |
| UDF / RDD 処理 | 非推奨 | Photon 非対応の API |
| 2 秒以下の軽量クエリ | 効果薄 | オーバーヘッドが支配的 |

### 3c. DBR バージョン選定

| 環境 | 推奨バージョン | 理由 |
|:---|:---|:---|
| 本番 | DBR 16.4 LTS | 安定性とサポート期間の保証 |
| ML 本番 | DBR 16.4 ML LTS | MLflow, PyTorch 等プリインストール |
| 開発・検証 | 最新 LTS または最新 GA | 新機能の検証 |
| Spark 4 検証 | DBR 17.0+ | Scala 2.13 移行の準備 |

### 3d. オートスケーリング設定

| パラメータ | 推奨値 | 説明 |
|:---|:---|:---|
| `min_workers` | 1-2 | 最小構成でコスト抑制 |
| `max_workers` | ピーク時の必要数 | ワークロードに応じて設定 |
| `autotermination_minutes` | 30-60 | アイドル時の自動停止 |
| Spot インスタンス比率 | 50-80% | バッチジョブで積極活用 |

**チェックリスト**:
- [ ] ワークロード別にコンピュートタイプを選定した
- [ ] Photon の適用/非適用を判断し、理由を記載した
- [ ] DBR バージョンを環境別に選定した
- [ ] オートスケーリングと自動停止を設計した
- [ ] Spot インスタンスの適用可否を判断した
- [ ] コスト見積（月額 DBU 概算）を算出した

---

## Step 4: データパイプライン設計

Medallion Architecture に基づくデータパイプラインを設計する。
詳細は [medallion-architecture.md](references/medallion-architecture.md) を参照。

### 4a. Medallion Architecture の層定義

各レイヤーの責務を明確に定義する:

```
Raw Sources          Bronze              Silver              Gold
+-----------+    +------------+    +-------------+    +-----------+
| Files     |--->| Raw Data   |--->| Validated   |--->| Business  |
| Kafka     |    | Minimal    |    | Cleansed    |    | Aggregated|
| APIs      |    | Transform  |    | Normalized  |    | Optimized |
| Databases |    | Append-only|    | Deduplicated|    | Star/Snow |
+-----------+    +------------+    +-------------+    +-----------+
                   STRING 型中心     品質チェック済      消費最適化
                   スキーマ変更耐性   ストリーミング読込   プロジェクト別
```

| レイヤー | 責務 | 禁止事項 |
|:---|:---|:---|
| **Bronze** | 生データの忠実な保存、メタデータ付与 | データクレンジング、フィルタリング |
| **Silver** | 品質検証、重複排除、正規化 | ビジネスロジック集約、直接インジェスション |
| **Gold** | ビジネス集約、Star/Snowflake Schema | 生データの保持 |

### 4b. インジェスション方式の選定

| ソースタイプ | 推奨方式 | 設定ポイント |
|:---|:---|:---|
| クラウドストレージ上のファイル | Auto Loader (`cloudFiles`) | File Events モード推奨 |
| SaaS アプリケーション | Lakeflow Connect | 管理されたコネクタを活用 |
| データベース（CDC） | Lakeflow Connect / Debezium | 変更データキャプチャ |
| ストリーミング（Kafka） | Structured Streaming | チェックポイント必須 |
| REST API | カスタム Notebook + Jobs | レート制限の考慮 |

Auto Loader の詳細パターンは [auto-loader-patterns.md](references/auto-loader-patterns.md) を参照。

### 4c. 変換方式の選定

| パターン | 推奨ツール | 適用シーン |
|:---|:---|:---|
| 宣言的パイプライン | Lakeflow Declarative Pipelines (DLT) | 品質管理が重要、標準的な ETL |
| SQL 中心の変換 | dbt + Databricks | SQL チームが主体 |
| 複雑なオーケストレーション | Lakeflow Jobs | マルチタスク依存関係管理 |
| Python ベースの変換 | PySpark + Notebooks | カスタムロジックが多い |

### 4d. パイプラインの実行モード

| モード | 説明 | 推奨シーン |
|:---|:---|:---|
| **Triggered** | スケジュールまたはイベント駆動 | 定時バッチ処理 |
| **Continuous** | 常時実行でデータを処理 | リアルタイム要件 |
| **availableNow** | 現時点の未処理データをすべて処理して停止 | コスト効率の高いマイクロバッチ |

**チェックリスト**:
- [ ] Bronze/Silver/Gold 各レイヤーの責務を定義した
- [ ] データソース別にインジェスション方式を選定した
- [ ] 変換ツール（DLT / dbt / PySpark）を選定した
- [ ] パイプラインの実行モードを決定した
- [ ] Bronze → Silver 間のストリーミング読み込みを設計した
- [ ] Dead-Letter テーブル（エラーレコード隔離）を設計した

---

## Step 5: データ品質ルール設計

DLT Expectations を活用した宣言的データ品質チェックを設計する。
詳細なパターンは [dlt-expectations-patterns.md](references/dlt-expectations-patterns.md) を参照。

### 5a. Expectations 戦略の選定

品質ルールごとに違反時のアクション戦略を決定する:

| 戦略 | 違反時の動作 | 適用シーン |
|:---|:---|:---|
| `expect` | レコードを保持、メトリクスをログ | 警告レベル（NULL 率のモニタリング等） |
| `expect_or_drop` | 違反レコードを除外 | 重要だが停止不要（重複排除等） |
| `expect_or_fail` | パイプラインを停止 | 不正データが完全に許容不可（PK 違反等） |

### 5b. レイヤー別の品質ルール設計

| レイヤー | 品質ルールの例 | 推奨戦略 |
|:---|:---|:---|
| **Bronze → Silver** | NOT NULL チェック、型変換成功 | `expect_or_drop` |
| **Bronze → Silver** | 主キーの一意性 | `expect_or_fail` |
| **Silver → Gold** | ビジネスルール（金額 > 0 等） | `expect_or_drop` |
| **Silver → Gold** | 参照整合性 | `expect` |

### 5c. 品質メトリクスの監視

| メトリクス | 説明 | アラート閾値の目安 |
|:---|:---|:---|
| 合格率（Pass Rate） | Expectation を満たしたレコードの割合 | 95% 未満で警告 |
| ドロップ率 | `expect_or_drop` で除外されたレコード割合 | 5% 超で調査 |
| 失敗回数 | `expect_or_fail` による停止回数 | 1 回でも即時対応 |
| データ到着遅延 | 予定時刻からの遅延 | SLA に応じて設定 |

**チェックリスト**:
- [ ] テーブルごとに Expectations を定義した
- [ ] 違反時のアクション戦略（expect / drop / fail）を選定した
- [ ] レイヤー間の品質ルールを段階的に設計した
- [ ] Dead-Letter テーブルで除外レコードを保存する設計にした
- [ ] 品質メトリクスの監視とアラート閾値を設定した

---

## Step 6: ML/AI 設計

MLflow を中心とした ML ライフサイクルと Model Serving を設計する。
ML/AI ワークロードがない場合はこのステップをスキップする。

### 6a. MLflow 実験追跡の設計

| 項目 | 設計内容 |
|:---|:---|
| Experiment 命名 | `/{team}/{project}/{model_name}` |
| ログ対象 | パラメータ、メトリクス、アーティファクト、データバージョン |
| モデルレジストリ | Unity Catalog Model Registry（推奨） |
| ステージ管理 | None → Staging → Production の 3 段階 |

### 6b. Model Serving の設計

| パターン | 方式 | 適用シーン |
|:---|:---|:---|
| リアルタイム推論 | Mosaic AI Model Serving (REST API) | 低レイテンシ要件（< 100ms） |
| バッチ推論 | Spark ジョブ | 大量データの定期予測 |
| Feature Serving 連携 | Feature Store + Model Serving | 特徴量の自動ルックアップ |

### 6c. Feature Store と Mosaic AI

| 設計項目 | 内容 |
|:---|:---|
| Feature テーブル | Unity Catalog 管理の Delta テーブル |
| オンラインストア | リアルタイム推論用のキャッシュ |
| RAG | Vector Search + Agent Framework |
| AI エージェント | Agent Framework + Agent Bricks |
| AI ゲートウェイ | AI Gateway（統一的なモデルアクセス） |

**チェックリスト**:
- [ ] MLflow Experiment の命名規則と構成を定義した
- [ ] Model Registry の管理方針を決定した（Unity Catalog 推奨）
- [ ] Model Serving のパターンを選定した
- [ ] Feature Store / Mosaic AI の活用方針を定義した

---

## Step 7: SQL 分析最適化

DBSQL のパフォーマンスとコストを最適化する。
分析・BI ワークロードがない場合はこのステップをスキップする。

### 7a. SQL Warehouse のサイジング

| サイズ | ユースケース | 同時実行数の目安 |
|:---|:---|:---|
| 2X-Small ~ Small | 軽量ダッシュボード、少数ユーザー | 1-5 |
| Medium | 標準的な分析ワークロード | 5-20 |
| Large ~ X-Large | 大量データの集約・複雑な結合 | 20+ |

### 7b. クエリパフォーマンス最適化

| 最適化手法 | 説明 | 適用条件 |
|:---|:---|:---|
| **Liquid Clustering** | 適応型クラスタリング（手動パーティション不要） | Delta Lake 3.0+ |
| **Materialized View** | 集計結果のキャッシュ | 頻繁にアクセスされる集計 |
| **Predictive Optimization** | 自動的な OPTIMIZE/VACUUM | Serverless 環境 |
| **Z-Order** | カラム指定の最適化（Liquid 未対応時） | レガシーテーブル |

### 7c. ダッシュボード設計

| 設計原則 | 説明 |
|:---|:---|
| クエリの事前集計 | Gold テーブルにダッシュボード用ビューを準備 |
| フィルタの最適化 | クラスタリングキーに沿ったフィルタ設計 |
| 更新頻度の設定 | ビジネス要件に応じたリフレッシュ間隔 |
| AI/BI Genie の活用 | ビジネスユーザー向けの自然言語分析 |

**チェックリスト**:
- [ ] SQL Warehouse のサイズを決定した
- [ ] Liquid Clustering の適用対象テーブルを特定した
- [ ] Materialized View の候補を洗い出した
- [ ] ダッシュボードのクエリパフォーマンスを考慮した Gold テーブル設計にした
- [ ] Spill Rate の監視設計を組み込んだ

---

## Step 8: 運用・CI/CD 設計

DABs + Terraform による CI/CD と、コスト最適化・モニタリングを設計する。
詳細なテンプレートは [dabs-cicd-templates.md](references/dabs-cicd-templates.md)、
コスト最適化は [cost-optimization-checklist.md](references/cost-optimization-checklist.md) を参照。

### 8a. Split-Stack 戦略（Terraform + DABs）

**Terraform** が Workspace / VNet / Secret Scopes / Storage / IAM を管理し、**DABs** が Jobs / Pipelines / Notebooks / Schemas / Cluster Config を管理する。インフラとアプリケーションのパイプラインを完全に分離し、Notebook の変更がネットワーク設定を破壊しないよう保護する。

### 8b. DABs の構成設計

| 設計項目 | 推奨方針 |
|:---|:---|
| Bundle 構成 | プロジェクト単位で 1 Bundle |
| ターゲット | `dev` / `staging` / `prod` の 3 環境 |
| 認証 | Workload Identity Federation（推奨） |
| CI/CD ツール | GitHub Actions / Azure DevOps |

### 8c. コスト最適化の 6 大テクニック

| テクニック | 期待効果 | 実施方法 |
|:---|:---|:---|
| オートスケーリング | 40-60% 削減 | `min_workers` / `max_workers` の適切な設定 |
| Spot インスタンス | 最大 90% 削減 | バッチ処理・Worker ノードに適用 |
| 自動停止 | アイドルコスト排除 | `autotermination_minutes: 30-60` |
| クラスターポリシー | ガバナンス強化 | コンピュートリソースの種類・サイズを制限 |
| ライトサイジング | 過剰プロビジョニング排除 | メトリクスに基づくサイズ調整 |
| Photon Engine | 3x-8x 高速化 | DBU 消費量の削減 |

### 8d. モニタリング・アラート設計

| 監視対象 | ツール | アラート条件 |
|:---|:---|:---|
| ジョブの成功/失敗 | Lakeflow Jobs | 失敗時に即時通知 |
| DLT パイプラインの品質 | Expectations メトリクス | 合格率低下時 |
| コスト | カスタムタグ + Budget Alert | 月額予算の 80% 到達時 |
| SQL Warehouse パフォーマンス | Warehouse Advisor Dashboard | Spill Rate 上昇時 |
| データ到着遅延 | カスタムモニタリング | SLA 超過時 |

### 8e. セキュリティ設計

ネットワークは VNet Injection + Private Link、認証は Workload Identity Federation、シークレットは Terraform で Secret Scope 管理、アクセス制御は Unity Catalog ABAC + 最小権限を推奨。

**チェックリスト**:
- [ ] Terraform と DABs の責務分離を設計した
- [ ] DABs の Bundle 構成とターゲット環境を定義した
- [ ] CI/CD パイプライン（ビルド・テスト・デプロイ）を設計した
- [ ] コスト最適化テクニックの適用可否を判断した
- [ ] モニタリング・アラートの設計を行った
- [ ] セキュリティ設計（ネットワーク・認証・シークレット）を行った
- [ ] カスタムタグによるコスト帰属の設計を行った

---

## Step 9: レビュー・最適化チェックリスト

設計全体をレビューし、ベストプラクティスとの適合を確認する。

以下の 4 領域を網羅的に検証する:

| 領域 | 主なチェック項目 |
|:---|:---|
| **アーキテクチャ** | 環境分離の Blast Radius、命名規則の一貫性、Unity Catalog 階層、DBR LTS 採用 |
| **パイプライン** | Medallion 層間責務、Bronze の忠実な保存、Silver 直接インジェスション禁止、Expectations 戦略、Dead-Letter |
| **コスト** | Serverless vs Classic 根拠、オートスケーリング、自動停止、Spot 活用、Photon 判断 |
| **運用** | CI/CD 設計、Terraform/DABs 分離、モニタリング・アラート、セキュリティ、コスト帰属タグ |

**チェックリスト**:
- [ ] 全ステップの設計成果物を確認した
- [ ] ベストプラクティスとの乖離を特定した
- [ ] 改善提案をリスト化した
- [ ] ユーザーにレビュー結果を提示し、承認を得た

---

## Examples

### Example 1: 新規 Databricks 環境の全体設計

```
「Azure 上に Databricks 環境を新規構築したい。日次 200GB の販売データを取り込んで分析したい」

-> Step 1（Azure, バッチ ETL + 分析, 200GB/日）
-> Step 2（Dev/Staging/Prod サブスクリプション分離）
-> Step 3（ETL: Serverless Jobs, 分析: Serverless SQL WH）
-> Step 4（Auto Loader -> DLT -> Gold）-> Step 5（Expectations 設計）
-> Step 7（Medium WH, Liquid Clustering）-> Step 8（DABs + Terraform CI/CD）
-> Step 9（レビュー・最適化提案）
```

### Example 2: 既存環境のコスト最適化

```
「Classic Cluster で運用中だが、月額コストが高すぎる」

-> Step 1（コスト内訳、ワークロード特性のヒアリング）
-> Step 3（バッチ -> Serverless Jobs、分析 -> Serverless SQL WH、All-Purpose -> 自動停止確認）
-> Step 8c（Spot 導入、オートスケーリング見直し）-> Step 9（削減効果の試算）
```

### Example 3: DLT パイプラインの設計

```
「S3 に到着する JSON ログファイルを DLT で処理したい」

-> Step 1（AWS, JSON, 日次数百ファイル, ニアリアルタイム）
-> Step 4（Bronze: Auto Loader File Events、Silver: DLT 型変換・重複排除、Gold: Materialized View）
-> Step 5（Bronze->Silver: expect_or_drop、Silver->Gold: expect）
-> Step 8（DABs 定義と Jobs スケジュール）
```

### Example 4: ML パイプラインの構築

```
「MLflow で実験管理して、モデルをリアルタイムサービングしたい」

-> Step 1（モデル種別、レイテンシ要件、推論データ量）
-> Step 3（DBR 16.4 ML LTS, GPU インスタンス）
-> Step 4（Silver -> Feature テーブルのパイプライン）
-> Step 6（MLflow Experiment、UC Model Registry、Mosaic AI Serving、Feature Store）
-> Step 8（モデルデプロイ CI/CD）
```

### Example 5: SQL 分析環境の最適化

```
「DBSQL のクエリが遅い。ダッシュボードの応答を改善したい」

-> Step 1（Warehouse サイズ、クエリパターン、Spill 状況の確認）
-> Step 7（Warehouse サイジング見直し、Liquid Clustering 導入、Materialized View 化、Gold テーブル改善）
-> Step 9（パフォーマンス改善レビュー）
```

### Example 6: マルチクラウド Databricks の統合設計

```
「AWS と Azure の両方で Databricks を使いたい。統一的に管理したい」

-> Step 1（マルチクラウドの理由、データ配置、レイテンシ要件）
-> Step 2（クラウド別 Workspace + UC Metastore 共有、命名規則にプロバイダー含む）
-> Step 3（AWS: i3/r5 系、Azure: L/E 系のコンピュート選定）
-> Step 8（DABs ターゲットのクラウド別定義、Terraform モジュール分離）
-> Step 9（マルチクラウド固有のリスクレビュー）
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| クラスター起動に時間がかかる | Classic Cluster の Cold Start | Serverless への移行、または Cluster Pools の活用を検討する |
| DLT パイプラインが頻繁に失敗する | `expect_or_fail` の閾値が厳しすぎる | 品質ルールを見直し、段階的に `expect` → `expect_or_drop` → `expect_or_fail` を適用する |
| SQL Warehouse でクエリが Spill する | Warehouse サイズ不足またはクエリ非効率 | Warehouse Advisor Dashboard で Spill Rate を確認し、サイズアップまたはクエリ最適化を行う |
| コストが予算を大幅に超過する | All-Purpose Cluster の常時起動や Spot 未活用 | 自動停止の設定、Spot インスタンスの導入、Serverless への移行を段階的に実施する |
| Auto Loader がファイルを検出しない | File Events の通知設定ミス | Directory Listing モードにフォールバックし、`cloudFiles.backfillInterval` を設定する |
| Bronze → Silver でスキーマエラーが発生する | ソースのスキーマ変更に未対応 | Bronze で `STRING`/`VARIANT` 型での取り込みを徹底し、Silver での型変換で対応する |
| Unity Catalog の権限が複雑になりすぎる | テーブル単位の個別設定が増加 | ABAC（タグベース）のポリシーに移行し、カタログ/スキーマレベルで統一的に管理する |
| DABs デプロイが環境間で異なる結果になる | ターゲット定義の不備 | `databricks.yml` のターゲット設定を見直し、環境変数ではなく明示的な設定を使用する |
| Photon を有効化しても速くならない | UDF/RDD を多用しているワークロード | Photon 対応の DataFrame/SQL API に書き換えるか、Photon を無効化して Classic エンジンを使用する |
| Serverless の DBU コストが Classic より高い | 短時間ジョブで頻繁に起動停止 | ジョブの統合やスケジュールの見直し、Classic + Spot との TCO 比較を行う |
| Spark 4 移行でライブラリ互換性エラーが出る | Scala 2.12 依存のライブラリ | DBR 16.4 LTS（Scala 2.12）に留まり、ライブラリの 2.13 対応を待つか代替を検討する |
| ML モデルのサービングレイテンシが高い | モデルサイズが大きい、Feature 取得が遅い | モデルの軽量化、Feature Store のオンラインストア活用、バッチ推論への切り替えを検討する |

---

## References

| ファイル | 内容 |
|:---|:---|
| [medallion-architecture.md](references/medallion-architecture.md) | Bronze/Silver/Gold の設計パターンとコード例 |
| [compute-selection-guide.md](references/compute-selection-guide.md) | コンピュートタイプ選定マトリクスとサイジング指針 |
| [dlt-expectations-patterns.md](references/dlt-expectations-patterns.md) | DLT Expectations のパターン集とコード例 |
| [cost-optimization-checklist.md](references/cost-optimization-checklist.md) | コスト最適化チェックリストと削減施策 |
| [dabs-cicd-templates.md](references/dabs-cicd-templates.md) | DABs YAML テンプレートと CI/CD 構成例 |
| [auto-loader-patterns.md](references/auto-loader-patterns.md) | Auto Loader の構成パターンとベストプラクティス |

---

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **data-arch** | 上流 | データアーキテクチャの全体設計。Databricks 上の実装設計は本スキルが担当 |
| **diagram** | 連携 | Databricks アーキテクチャ構成図の生成。本スキルの設計結果を図面化する |
| **review** | 検証 | 本スキルで生成した設計ドキュメントの品質レビュー |
| **test** | 連携 | Databricks パイプラインのテスト戦略策定。Notebook テストの設計に連携 |
| **data-validation** | 連携 | Expectations で定義した品質ルールの妥当性検証 |
| **effective-typescript** | 連携 | Databricks Apps（Node.js）の TypeScript 実装時のベストプラクティス |
| **robust-python** | 連携 | PySpark / MLflow の Python 実装時のベストプラクティス |
