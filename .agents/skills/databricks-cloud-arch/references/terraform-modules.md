# Terraform Modules — Terraform モジュール構成テンプレート

## 1. 推奨ディレクトリ構成

```
terraform/
├── modules/
│   ├── networking/          ← VPC/VNet、PrivateLink、ファイアウォール
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── workspace/           ← Databricks ワークスペース
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── unity-catalog/       ← メタストア、カタログ、スキーマ
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── security/            ← CMK、IAM/Entra ID、シークレット
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── monitoring/          ← ログ、アラート、ダッシュボード
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   ├── dev/
│   │   ├── main.tf          ← モジュール呼び出し
│   │   ├── variables.tf
│   │   ├── terraform.tfvars  ← 環境固有の値
│   │   └── backend.tf
│   ├── staging/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   └── production/
│       ├── main.tf
│       ├── variables.tf
│       ├── terraform.tfvars
│       └── backend.tf
└── global/                   ← 環境横断リソース（Unity Catalog メタストア等）
    ├── main.tf
    ├── variables.tf
    └── backend.tf
```

---

## 2. AWS 用モジュール構成

### 2.1 modules/networking（AWS）

```hcl
# modules/networking/aws/main.tf

# Customer-Managed VPC
resource "aws_vpc" "databricks" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true  # 必須: 見落とし注意
  enable_dns_support   = true  # 必須: 見落とし注意

  tags = merge(var.tags, {
    Name = "${var.prefix}-databricks-vpc"
  })
}

# プライベートサブネット A
resource "aws_subnet" "databricks_a" {
  vpc_id            = aws_vpc.databricks.id
  cidr_block        = var.subnet_a_cidr
  availability_zone = var.az_a

  tags = merge(var.tags, {
    Name = "${var.prefix}-databricks-subnet-a"
  })
}

# プライベートサブネット B
resource "aws_subnet" "databricks_b" {
  vpc_id            = aws_vpc.databricks.id
  cidr_block        = var.subnet_b_cidr
  availability_zone = var.az_b

  tags = merge(var.tags, {
    Name = "${var.prefix}-databricks-subnet-b"
  })
}

# セキュリティグループ
resource "aws_security_group" "databricks" {
  vpc_id = aws_vpc.databricks.id

  # Databricks 内部通信（同一 SG）
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.prefix}-databricks-sg"
  })
}

# S3 VPC Endpoint (Gateway)
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = aws_vpc.databricks.id
  service_name = "com.amazonaws.${var.region}.s3"
}

# NAT Gateway
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id

  tags = merge(var.tags, {
    Name = "${var.prefix}-nat-gw"
  })
}
```

### 2.2 modules/workspace（AWS）

```hcl
# modules/workspace/aws/main.tf

# Databricks MWS ネットワーク設定
resource "databricks_mws_networks" "this" {
  provider           = databricks.mws
  account_id         = var.databricks_account_id
  network_name       = "${var.prefix}-network"
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  security_group_ids = [var.security_group_id]
}

# Databricks ワークスペース
resource "databricks_mws_workspaces" "this" {
  provider       = databricks.mws
  account_id     = var.databricks_account_id
  workspace_name = "${var.prefix}-workspace"
  aws_region     = var.region

  credentials_id           = var.credentials_id
  storage_configuration_id = var.storage_configuration_id
  network_id              = databricks_mws_networks.this.network_id

  # PrivateLink 設定
  dynamic "private_access_settings_id" {
    for_each = var.enable_private_link ? [1] : []
    content {
      private_access_settings_id = var.private_access_settings_id
    }
  }
}
```

---

## 3. Azure 用モジュール構成

### 3.1 modules/networking（Azure）

```hcl
# modules/networking/azure/main.tf

# Spoke VNet (Databricks 用)
resource "azurerm_virtual_network" "databricks" {
  name                = "${var.prefix}-databricks-vnet"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = [var.vnet_cidr]

  tags = var.tags
}

# Public サブネット（サブネットデリゲーション付き）
resource "azurerm_subnet" "public" {
  name                 = "${var.prefix}-public-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.databricks.name
  address_prefixes     = [var.public_subnet_cidr]

  delegation {
    name = "databricks-delegation"
    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
      ]
    }
  }
}

# Private サブネット（サブネットデリゲーション付き）
resource "azurerm_subnet" "private" {
  name                 = "${var.prefix}-private-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.databricks.name
  address_prefixes     = [var.private_subnet_cidr]

  delegation {
    name = "databricks-delegation"
    service_delegation {
      name = "Microsoft.Databricks/workspaces"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
        "Microsoft.Network/virtualNetworks/subnets/prepareNetworkPolicies/action",
        "Microsoft.Network/virtualNetworks/subnets/unprepareNetworkPolicies/action",
      ]
    }
  }
}

# NSG（ワークスペースごとに固有）
resource "azurerm_network_security_group" "databricks" {
  name                = "${var.prefix}-databricks-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

# VNet Peering（Hub → Spoke）
resource "azurerm_virtual_network_peering" "hub_to_spoke" {
  name                      = "hub-to-${var.prefix}"
  resource_group_name       = var.hub_resource_group_name
  virtual_network_name      = var.hub_vnet_name
  remote_virtual_network_id = azurerm_virtual_network.databricks.id

  allow_forwarded_traffic = true
  allow_gateway_transit   = true
}

# VNet Peering（Spoke → Hub）
resource "azurerm_virtual_network_peering" "spoke_to_hub" {
  name                      = "${var.prefix}-to-hub"
  resource_group_name       = var.resource_group_name
  virtual_network_name      = azurerm_virtual_network.databricks.name
  remote_virtual_network_id = var.hub_vnet_id

  allow_forwarded_traffic = true
  use_remote_gateways     = true
}
```

### 3.2 modules/workspace（Azure）

```hcl
# modules/workspace/azure/main.tf

# Azure Databricks ワークスペース（VNet Injection）
resource "azurerm_databricks_workspace" "this" {
  name                        = "${var.prefix}-databricks-ws"
  location                    = var.location
  resource_group_name         = var.resource_group_name
  sku                         = "premium"  # CMK / Unity Catalog に必須
  managed_resource_group_name = "${var.prefix}-databricks-managed-rg"

  custom_parameters {
    virtual_network_id                                   = var.vnet_id
    public_subnet_name                                   = var.public_subnet_name
    public_subnet_network_security_group_association_id   = var.public_nsg_association_id
    private_subnet_name                                  = var.private_subnet_name
    private_subnet_network_security_group_association_id  = var.private_nsg_association_id
    no_public_ip                                         = true
  }

  tags = var.tags
}
```

---

## 4. 共通モジュール

### 4.1 modules/unity-catalog

```hcl
# modules/unity-catalog/main.tf

# メタストアの作成
resource "databricks_metastore" "this" {
  name          = "${var.prefix}-metastore"
  storage_root  = var.storage_root
  region        = var.region
  force_destroy = false
}

# ワークスペースへのメタストア割り当て
resource "databricks_metastore_assignment" "this" {
  for_each     = toset(var.workspace_ids)
  workspace_id = each.value
  metastore_id = databricks_metastore.this.id
}

# カタログの作成
resource "databricks_catalog" "this" {
  for_each = var.catalogs
  name     = each.key
  comment  = each.value.comment
}

# スキーマの作成
resource "databricks_schema" "this" {
  for_each     = var.schemas
  catalog_name = each.value.catalog_name
  name         = each.key
  comment      = each.value.comment
}
```

### 4.2 modules/security

```hcl
# modules/security/main.tf

# AWS: Storage Credential（Cross-Account Role）
resource "databricks_storage_credential" "aws" {
  count = var.cloud == "aws" ? 1 : 0
  name  = "${var.prefix}-storage-credential"

  aws_iam_role {
    role_arn = var.iam_role_arn
  }
}

# Azure: Storage Credential（Access Connector）
resource "databricks_storage_credential" "azure" {
  count = var.cloud == "azure" ? 1 : 0
  name  = "${var.prefix}-storage-credential"

  azure_managed_identity {
    access_connector_id = var.access_connector_id
  }
}

# External Location
resource "databricks_external_location" "this" {
  for_each        = var.external_locations
  name            = each.key
  url             = each.value.url
  credential_name = var.cloud == "aws" ? databricks_storage_credential.aws[0].name : databricks_storage_credential.azure[0].name
}
```

---

## 5. 環境別変数ファイル

### environments/dev/terraform.tfvars

```hcl
prefix      = "dev"
environment = "development"
region      = "ap-northeast-1"  # AWS の場合
# location  = "japaneast"       # Azure の場合

# ネットワーク
vpc_cidr         = "10.1.0.0/16"
subnet_a_cidr    = "10.1.1.0/24"
subnet_b_cidr    = "10.1.2.0/24"
enable_private_link = false  # 開発環境では任意

# コンピュート
default_num_workers = 2
enable_spot        = true
spot_percentage    = 100

# タグ
tags = {
  Environment = "dev"
  Project     = "databricks-platform"
  ManagedBy   = "terraform"
}
```

### environments/production/terraform.tfvars

```hcl
prefix      = "prd"
environment = "production"
region      = "ap-northeast-1"

# ネットワーク
vpc_cidr         = "10.3.0.0/16"
subnet_a_cidr    = "10.3.1.0/24"
subnet_b_cidr    = "10.3.2.0/24"
enable_private_link = true  # 本番環境では必須

# コンピュート
default_num_workers = 8
enable_spot        = true
spot_percentage    = 30  # 本番は On-Demand 比率を高く

# タグ
tags = {
  Environment = "production"
  Project     = "databricks-platform"
  ManagedBy   = "terraform"
}
```

---

## 6. リモート状態管理

### AWS: S3 Backend

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "databricks/dev/terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
```

### Azure: Blob Storage Backend

```hcl
# backend.tf
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "myterraformstate"
    container_name       = "tfstate"
    key                  = "databricks/dev/terraform.tfstate"
  }
}
```

---

## 7. DABs との連携

### Terraform と DABs の責務分担

```
Terraform                          DABs
─────────────────────────          ─────────────────────
VPC / VNet                         ジョブ定義
PrivateLink                        ノートブック
ワークスペース                      DLT パイプライン
Unity Catalog メタストア            ML モデルサービング
Storage Credential                 ワークフロー
IAM / Entra ID
CMK 暗号化
監視・ログ
```

### DABs の環境別設定（databricks.yml）

```yaml
bundle:
  name: my-data-pipeline

targets:
  dev:
    workspace:
      host: ${DEV_WORKSPACE_HOST}
    default_catalog: dev_catalog
    resources:
      jobs:
        etl_job:
          clusters:
            - num_workers: 2
              node_type_id: "${DEV_NODE_TYPE}"
  staging:
    workspace:
      host: ${STG_WORKSPACE_HOST}
    default_catalog: staging_catalog
    resources:
      jobs:
        etl_job:
          clusters:
            - num_workers: 4
  production:
    workspace:
      host: ${PRD_WORKSPACE_HOST}
    default_catalog: prod_catalog
    resources:
      jobs:
        etl_job:
          clusters:
            - num_workers: 8
            - policy_id: "${PRD_CLUSTER_POLICY_ID}"
```

---

## 8. Terraform ベストプラクティス

| # | プラクティス | 説明 |
|:---|:---|:---|
| 1 | モジュール化 | 機能単位で独立進化可能に |
| 2 | 環境変数パラメータ化 | ハードコーディングを排除 |
| 3 | リモート状態管理 | S3 / Blob Storage で tfstate 管理 |
| 4 | ロック機構 | DynamoDB / Blob Lease で並行制御 |
| 5 | バージョン固定 | Provider と Terraform のバージョンを固定 |
| 6 | Plan → Apply | 必ず plan を確認してから apply |
| 7 | Import / Exporter | 既存リソースの Terraform 化 |
| 8 | Workspace Identity | CI/CD は Workload Identity Federation |
