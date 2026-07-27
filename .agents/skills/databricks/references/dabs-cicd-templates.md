# DABs CI/CD テンプレート

> Databricks Asset Bundles (DABs) の YAML テンプレート、Terraform との Split-Stack 戦略、CI/CD パイプライン構成例をまとめたリファレンス。

---

## 1. DABs の基本構造

### プロジェクトのディレクトリ構成

```
my-data-pipeline/
├── databricks.yml           # メインの Bundle 定義
├── resources/
│   ├── jobs/
│   │   ├── daily_etl.yml    # ETL ジョブ定義
│   │   └── ml_training.yml  # ML 学習ジョブ定義
│   └── pipelines/
│       └── dlt_pipeline.yml # DLT パイプライン定義
├── src/
│   ├── notebooks/
│   │   ├── bronze/
│   │   │   └── ingest.py
│   │   ├── silver/
│   │   │   └── transform.py
│   │   └── gold/
│   │       └── aggregate.py
│   └── pipelines/
│       └── dlt_pipeline.py  # DLT パイプラインコード
├── tests/
│   ├── unit/
│   └── integration/
└── .github/
    └── workflows/
        └── deploy.yml       # CI/CD パイプライン
```

---

## 2. databricks.yml テンプレート

### 基本テンプレート

```yaml
bundle:
  name: my-data-pipeline

# 共通設定
workspace:
  host: ${var.workspace_host}

# インクルード（リソース定義を分割）
include:
  - resources/jobs/*.yml
  - resources/pipelines/*.yml

# 変数定義
variables:
  workspace_host:
    description: "Databricks Workspace URL"
  catalog_name:
    description: "Unity Catalog のカタログ名"
  schema_name:
    description: "Unity Catalog のスキーマ名"

# 環境別のターゲット定義
targets:
  dev:
    default: true
    mode: development
    workspace:
      host: https://dev-workspace.databricks.com
    variables:
      catalog_name: dev_analytics
      schema_name: default

  staging:
    workspace:
      host: https://staging-workspace.databricks.com
    variables:
      catalog_name: staging_analytics
      schema_name: default

  prod:
    workspace:
      host: https://prod-workspace.databricks.com
    variables:
      catalog_name: prod_analytics
      schema_name: default
    permissions:
      - group_name: "data-engineers"
        level: "CAN_MANAGE"
      - group_name: "data-analysts"
        level: "CAN_VIEW"
```

### ETL ジョブ定義（resources/jobs/daily_etl.yml）

```yaml
resources:
  jobs:
    daily_etl:
      name: "[${bundle.target}] Daily ETL Pipeline"
      description: "日次 ETL パイプライン（Bronze → Silver → Gold）"

      schedule:
        quartz_cron_expression: "0 0 8 * * ?"
        timezone_id: "Asia/Tokyo"

      tags:
        team: "data-engineering"
        project: "${bundle.name}"
        environment: "${bundle.target}"

      email_notifications:
        on_failure:
          - "data-team@example.com"

      tasks:
        - task_key: "bronze_ingestion"
          notebook_task:
            notebook_path: ./src/notebooks/bronze/ingest.py
            base_parameters:
              catalog: "${var.catalog_name}"
              schema: "${var.schema_name}"
          new_cluster:
            spark_version: "16.4.x-scala2.12"
            num_workers: 2
            node_type_id: "Standard_D4ds_v5"
            spark_conf:
              "spark.databricks.delta.preview.enabled": "true"

        - task_key: "silver_transform"
          depends_on:
            - task_key: "bronze_ingestion"
          notebook_task:
            notebook_path: ./src/notebooks/silver/transform.py
            base_parameters:
              catalog: "${var.catalog_name}"
              schema: "${var.schema_name}"
          new_cluster:
            spark_version: "16.4.x-scala2.12"
            num_workers: 4
            node_type_id: "Standard_D8ds_v5"
            runtime_engine: "PHOTON"

        - task_key: "gold_aggregate"
          depends_on:
            - task_key: "silver_transform"
          notebook_task:
            notebook_path: ./src/notebooks/gold/aggregate.py
            base_parameters:
              catalog: "${var.catalog_name}"
              schema: "${var.schema_name}"
          new_cluster:
            spark_version: "16.4.x-scala2.12"
            num_workers: 2
            node_type_id: "Standard_D4ds_v5"
            runtime_engine: "PHOTON"
```

### DLT パイプライン定義（resources/pipelines/dlt_pipeline.yml）

```yaml
resources:
  pipelines:
    dlt_etl_pipeline:
      name: "[${bundle.target}] ETL DLT Pipeline"
      target: "${var.catalog_name}.${var.schema_name}"
      development: ${bundle.target == "dev"}

      catalog: "${var.catalog_name}"
      channel: "PREVIEW"

      libraries:
        - notebook:
            path: ./src/pipelines/dlt_pipeline.py

      clusters:
        - label: "default"
          autoscale:
            min_workers: 1
            max_workers: 5
          spark_conf:
            "spark.databricks.delta.preview.enabled": "true"

      continuous: false

      notifications:
        - email_recipients:
            - "data-team@example.com"
          alerts:
            - "on-update-failure"
            - "on-flow-failure"
```

---

## 3. Terraform + DABs の Split-Stack 戦略

### 責務の分離

```
+-------------------+     +-------------------+
| Terraform         |     | DABs              |
| (Infrastructure)  |     | (Application)     |
+-------------------+     +-------------------+
| - Workspace       |     | - Jobs            |
| - VNet/Network    |     | - Pipelines (DLT) |
| - Secret Scopes   |     | - Notebooks       |
| - Storage Account |     | - Schemas         |
| - IAM/RBAC        |     | - Cluster Config  |
| - Metastore       |     | - Permissions     |
| - Catalog (作成)  |     | - Schedules       |
+-------------------+     +-------------------+
```

### Terraform リソース例

```hcl
# Workspace の作成（Azure の場合）
resource "azurerm_databricks_workspace" "this" {
  name                = "${var.org}-${var.env}-${var.region}-ws"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  sku                 = "premium"

  custom_parameters {
    virtual_network_id  = azurerm_virtual_network.this.id
    private_subnet_name = azurerm_subnet.private.name
    public_subnet_name  = azurerm_subnet.public.name
  }
}

# Secret Scope の作成
resource "databricks_secret_scope" "app" {
  name = "${var.env}-app-secrets"
}

resource "databricks_secret" "storage_key" {
  scope        = databricks_secret_scope.app.name
  key          = "storage-account-key"
  string_value = azurerm_storage_account.this.primary_access_key
}

# Cluster Policy の作成
resource "databricks_cluster_policy" "etl" {
  name = "${var.env}-etl-policy"
  definition = jsonencode({
    "spark_version" : {
      "type" : "regex",
      "pattern" : "16\\.4\\.x-.*"
    },
    "autotermination_minutes" : {
      "type" : "range",
      "minValue" : 10,
      "maxValue" : 60,
      "defaultValue" : 30
    },
    "custom_tags.team" : {
      "type" : "fixed",
      "value" : "data-engineering"
    }
  })
}
```

---

## 4. CI/CD パイプライン構成

### GitHub Actions テンプレート

```yaml
# .github/workflows/deploy.yml
name: Deploy Databricks Bundle

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  id-token: write  # Workload Identity Federation 用
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Databricks CLI
        uses: databricks/setup-cli@main

      - name: Validate Bundle
        run: databricks bundle validate
        env:
          DATABRICKS_HOST: ${{ vars.DATABRICKS_HOST_DEV }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN_DEV }}

      - name: Run Unit Tests
        run: pytest tests/unit/ -v

  deploy-staging:
    needs: validate
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - name: Install Databricks CLI
        uses: databricks/setup-cli@main

      - name: Deploy to Staging
        run: databricks bundle deploy --target staging
        env:
          DATABRICKS_HOST: ${{ vars.DATABRICKS_HOST_STAGING }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN_STAGING }}

      - name: Run Integration Tests
        run: databricks bundle run integration_tests --target staging
        env:
          DATABRICKS_HOST: ${{ vars.DATABRICKS_HOST_STAGING }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN_STAGING }}

  deploy-prod:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Install Databricks CLI
        uses: databricks/setup-cli@main

      - name: Deploy to Production
        run: databricks bundle deploy --target prod
        env:
          DATABRICKS_HOST: ${{ vars.DATABRICKS_HOST_PROD }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN_PROD }}
```

### Azure DevOps テンプレート

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: 'ubuntu-latest'

stages:
  - stage: Validate
    jobs:
      - job: ValidateBundle
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.10'

          - script: |
              curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
            displayName: 'Install Databricks CLI'

          - script: databricks bundle validate
            displayName: 'Validate Bundle'
            env:
              DATABRICKS_HOST: $(DATABRICKS_HOST_DEV)
              DATABRICKS_TOKEN: $(DATABRICKS_TOKEN_DEV)

  - stage: DeployStaging
    dependsOn: Validate
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployToStaging
        environment: staging
        strategy:
          runOnce:
            deploy:
              steps:
                - script: |
                    curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
                    databricks bundle deploy --target staging
                  displayName: 'Deploy to Staging'
                  env:
                    DATABRICKS_HOST: $(DATABRICKS_HOST_STAGING)
                    DATABRICKS_TOKEN: $(DATABRICKS_TOKEN_STAGING)

  - stage: DeployProd
    dependsOn: DeployStaging
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployToProd
        environment: production
        strategy:
          runOnce:
            deploy:
              steps:
                - script: |
                    curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
                    databricks bundle deploy --target prod
                  displayName: 'Deploy to Production'
                  env:
                    DATABRICKS_HOST: $(DATABRICKS_HOST_PROD)
                    DATABRICKS_TOKEN: $(DATABRICKS_TOKEN_PROD)
```

---

## 5. 認証のベストプラクティス

### 認証方式の選定

| 方式 | セキュリティ | 推奨度 | 適用シーン |
|:---|:---|:---|:---|
| **Workload Identity Federation** | 最高 | 強く推奨 | GitHub Actions, Azure DevOps |
| **Service Principal + OAuth** | 高 | 推奨 | 汎用的な CI/CD |
| **Personal Access Token (PAT)** | 中 | 非推奨 | 個人の開発環境のみ |

### Workload Identity Federation の設定（GitHub Actions）

```yaml
# GitHub Actions での OIDC 認証
- name: Configure Databricks Auth
  run: |
    databricks configure --host ${{ vars.DATABRICKS_HOST }} \
      --azure-workspace-resource-id ${{ vars.AZURE_WORKSPACE_RESOURCE_ID }}
  env:
    ARM_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
    ARM_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
    ARM_USE_OIDC: true
```

---

## 6. テスト戦略

### テストのレイヤー

| テストレイヤー | 対象 | ツール | 実行タイミング |
|:---|:---|:---|:---|
| **Unit Test** | 変換ロジック | pytest + PySpark | PR 作成時 |
| **Integration Test** | パイプライン全体 | DABs + Staging 環境 | main マージ後 |
| **Data Quality Test** | Expectations | DLT Event Log | パイプライン実行時 |
| **Performance Test** | クエリ性能 | DBSQL Benchmark | リリース前 |

### ユニットテスト例

```python
# tests/unit/test_transform.py
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

def test_silver_transform(spark):
    """Silver 層の型変換が正しく動作すること"""
    schema = StructType([
        StructField("order_id", StringType()),
        StructField("amount", StringType()),
    ])
    data = [("1", "100.50"), ("2", "invalid"), ("3", None)]
    df = spark.createDataFrame(data, schema)

    result = df.withColumn("amount", df["amount"].cast(DoubleType()))

    assert result.filter("amount IS NOT NULL").count() == 1
    assert result.filter("amount IS NULL").count() == 2
```

---

## 7. DABs コマンドリファレンス

| コマンド | 説明 |
|:---|:---|
| `databricks bundle init` | 新しい Bundle プロジェクトを初期化 |
| `databricks bundle validate` | Bundle 定義を検証 |
| `databricks bundle deploy` | Bundle をデプロイ |
| `databricks bundle deploy --target prod` | 指定ターゲットにデプロイ |
| `databricks bundle run <job_name>` | ジョブを実行 |
| `databricks bundle destroy` | デプロイしたリソースを削除 |
| `databricks bundle summary` | Bundle のサマリーを表示 |
