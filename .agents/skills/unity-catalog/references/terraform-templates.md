# Terraform リソース定義のテンプレート集

Databricks Terraform Provider を使用した Unity Catalog リソースの IaC テンプレート。

---

## 1. Foundation（基盤リソース）

### 1.1 Storage Credential

#### Azure（Managed Identity）

```hcl
resource "databricks_storage_credential" "main" {
  name    = "main-storage-cred"
  comment = "Primary storage credential for Unity Catalog"

  azure_managed_identity {
    access_connector_id = azurerm_databricks_access_connector.main.id
  }
}
```

#### AWS（IAM Role）

```hcl
resource "databricks_storage_credential" "main" {
  name    = "main-storage-cred"
  comment = "Primary storage credential for Unity Catalog"

  aws_iam_role {
    role_arn = aws_iam_role.unity_catalog.arn
  }
}
```

#### GCP（Service Account）

```hcl
resource "databricks_storage_credential" "main" {
  name    = "main-storage-cred"
  comment = "Primary storage credential for Unity Catalog"

  databricks_gcp_service_account {}
}
```

### 1.2 External Location

```hcl
resource "databricks_external_location" "raw_data" {
  name            = "raw-data"
  url             = "abfss://raw@${var.storage_account_name}.dfs.core.windows.net/"
  credential_name = databricks_storage_credential.main.name
  comment         = "Raw data external location"
}

resource "databricks_external_location" "curated_data" {
  name            = "curated-data"
  url             = "abfss://curated@${var.storage_account_name}.dfs.core.windows.net/"
  credential_name = databricks_storage_credential.main.name
  comment         = "Curated data external location"
}
```

---

## 2. Catalog / Schema

### 2.1 Catalog

```hcl
# 本番カタログ
resource "databricks_catalog" "prod" {
  name         = "prod"
  comment      = "Production catalog"
  storage_root = databricks_external_location.curated_data.url

  properties = {
    environment = "production"
    managed_by  = "platform_team"
  }
}

# 開発カタログ
resource "databricks_catalog" "dev" {
  name    = "dev"
  comment = "Development catalog"

  properties = {
    environment = "development"
    managed_by  = "platform_team"
  }
}

# 共有カタログ
resource "databricks_catalog" "shared" {
  name    = "shared"
  comment = "Shared master and reference data"

  properties = {
    environment = "shared"
    managed_by  = "platform_team"
  }
}
```

### 2.2 Schema

```hcl
# Medallion Architecture スキーマ
resource "databricks_schema" "bronze_salesforce" {
  catalog_name = databricks_catalog.prod.name
  name         = "bronze_salesforce"
  comment      = "Raw data from Salesforce"
}

resource "databricks_schema" "silver_sales" {
  catalog_name = databricks_catalog.prod.name
  name         = "silver_sales"
  comment      = "Cleansed and transformed sales data"
}

resource "databricks_schema" "gold_analytics" {
  catalog_name = databricks_catalog.prod.name
  name         = "gold_analytics"
  comment      = "Analytics data mart"
}

resource "databricks_schema" "ml_features" {
  catalog_name = databricks_catalog.prod.name
  name         = "ml_features"
  comment      = "ML feature tables"
}

# スキーマの動的生成（for_each 活用）
variable "prod_schemas" {
  type = map(object({
    comment = string
  }))
  default = {
    bronze_salesforce = { comment = "Raw data from Salesforce" }
    bronze_sap        = { comment = "Raw data from SAP" }
    silver_sales      = { comment = "Cleansed sales data" }
    gold_analytics    = { comment = "Analytics data mart" }
    gold_reporting    = { comment = "Reporting data mart" }
    ml_features       = { comment = "ML feature tables" }
  }
}

resource "databricks_schema" "prod_schemas" {
  for_each     = var.prod_schemas
  catalog_name = databricks_catalog.prod.name
  name         = each.key
  comment      = each.value.comment
}
```

### 2.3 ワークスペースバインディング

```hcl
resource "databricks_catalog_workspace_binding" "prod_to_prod_ws" {
  securable_name = databricks_catalog.prod.name
  workspace_id   = var.prod_workspace_id
  binding_type   = "BINDING_TYPE_READ_WRITE"
}

resource "databricks_catalog_workspace_binding" "prod_to_analytics_ws" {
  securable_name = databricks_catalog.prod.name
  workspace_id   = var.analytics_workspace_id
  binding_type   = "BINDING_TYPE_READ_ONLY"
}
```

---

## 3. Access Control（権限管理）

### 3.1 databricks_grants（宣言的管理）

**注意**: `databricks_grants` はオブジェクトの全権限を宣言的に管理する。
Terraform に記述されていない権限は削除される。

```hcl
# カタログレベルの権限
resource "databricks_grants" "prod_catalog" {
  catalog = databricks_catalog.prod.name

  grant {
    principal  = "platform_admins"
    privileges = ["MANAGE"]
  }

  grant {
    principal  = "data_engineers"
    privileges = ["USE_CATALOG", "CREATE_SCHEMA"]
  }

  grant {
    principal  = "data_analysts"
    privileges = ["USE_CATALOG", "BROWSE"]
  }

  grant {
    principal  = "data_scientists"
    privileges = ["USE_CATALOG"]
  }
}

# スキーマレベルの権限
resource "databricks_grants" "gold_analytics" {
  schema = "${databricks_catalog.prod.name}.${databricks_schema.gold_analytics.name}"

  grant {
    principal  = "data_engineers"
    privileges = ["USE_SCHEMA", "CREATE_TABLE", "CREATE_VOLUME"]
  }

  grant {
    principal  = "data_analysts"
    privileges = ["USE_SCHEMA", "SELECT"]
  }

  grant {
    principal  = "data_scientists"
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}

# ML スキーマの権限
resource "databricks_grants" "ml_features" {
  schema = "${databricks_catalog.prod.name}.${databricks_schema.ml_features.name}"

  grant {
    principal  = "data_engineers"
    privileges = ["USE_SCHEMA", "CREATE_TABLE"]
  }

  grant {
    principal  = "data_scientists"
    privileges = ["USE_SCHEMA", "CREATE_TABLE", "CREATE_MODEL", "SELECT"]
  }
}
```

### 3.2 databricks_grant（部分管理）

既存の権限に影響を与えずに、特定の権限のみ追加・変更する場合:

```hcl
resource "databricks_grant" "analysts_select" {
  schema     = "${databricks_catalog.prod.name}.gold_analytics"
  principal  = "data_analysts"
  privileges = ["USE_SCHEMA", "SELECT"]
}
```

### 3.3 External Location の権限

```hcl
resource "databricks_grants" "raw_data_location" {
  external_location = databricks_external_location.raw_data.name

  grant {
    principal  = "data_engineers"
    privileges = ["CREATE_EXTERNAL_TABLE", "READ_FILES", "WRITE_FILES"]
  }
}
```

---

## 4. Delta Sharing

### 4.1 Share

```hcl
resource "databricks_share" "partner_share" {
  name = "partner_sales_data"

  object {
    name                        = "prod.gold_analytics.daily_sales"
    data_object_type            = "TABLE"
    history_data_sharing_status = "ENABLED"
  }

  object {
    name             = "prod.gold_analytics.product_catalog"
    data_object_type = "TABLE"
  }
}
```

### 4.2 Recipient

```hcl
# Databricks-to-Databricks
resource "databricks_recipient" "partner_corp" {
  name                             = "partner_corp"
  sharing_code                     = var.partner_sharing_code
  authentication_type              = "DATABRICKS"
  data_recipient_global_metastore_id = var.partner_metastore_id
}

# Open Sharing
resource "databricks_recipient" "external_partner" {
  name                = "external_partner"
  authentication_type = "TOKEN"
}
```

### 4.3 Share の権限付与

```hcl
resource "databricks_grants" "partner_share" {
  share = databricks_share.partner_share.name

  grant {
    principal  = databricks_recipient.partner_corp.name
    privileges = ["SELECT"]
  }
}
```

---

## 5. Lakehouse Federation

### 5.1 Connection

```hcl
resource "databricks_connection" "postgresql" {
  name            = "pg_operational_db"
  connection_type = "POSTGRESQL"
  comment         = "Connection to operational PostgreSQL database"

  options = {
    host     = var.pg_host
    port     = "5432"
    user     = var.pg_user
    password = var.pg_password
  }
}
```

### 5.2 Foreign Catalog

```hcl
resource "databricks_catalog" "pg_catalog" {
  name            = "pg_operational"
  connection_name = databricks_connection.postgresql.name
  comment         = "Federated catalog for PostgreSQL operational DB"
}
```

---

## 6. モジュール構成例

### 6.1 ディレクトリ構成

```
terraform/
├── modules/
│   ├── uc-foundation/
│   │   ├── main.tf           # Storage Credential, External Location
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── uc-catalog/
│   │   ├── main.tf           # Catalog, Schema
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── uc-access-control/
│   │   ├── main.tf           # Grants
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── uc-sharing/
│       ├── main.tf           # Share, Recipient, Connection
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   └── prod/
│       ├── main.tf
│       ├── terraform.tfvars
│       └── backend.tf
└── README.md
```

### 6.2 ルートモジュールの呼び出し例

```hcl
module "uc_foundation" {
  source               = "../../modules/uc-foundation"
  storage_account_name = var.storage_account_name
  access_connector_id  = var.access_connector_id
}

module "uc_catalog" {
  source     = "../../modules/uc-catalog"
  depends_on = [module.uc_foundation]

  catalogs = var.catalogs
  schemas  = var.schemas
}

module "uc_access_control" {
  source     = "../../modules/uc-access-control"
  depends_on = [module.uc_catalog]

  grants = var.grants
}
```

---

## 7. 重要な注意点

| 注意点 | 説明 |
|:---|:---|
| **databricks_grants vs databricks_grant** | `grants` は宣言的（未記載の権限を削除）、`grant` は追加的（既存権限に影響なし） |
| **depends_on** | Foundation → Catalog → Grants の順序依存を明示する |
| **state 管理** | Terraform state で Unity Catalog のドリフト検出が可能 |
| **権限管理の API** | Grants はワークスペースレベル API を使用（アカウントレベルではない） |
| **機密情報** | パスワード等は `var` + Terraform Vault 連携で管理。HCL にハードコードしない |
