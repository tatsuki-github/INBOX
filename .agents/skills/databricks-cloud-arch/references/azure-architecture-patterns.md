# Azure Architecture Patterns — Databricks on Azure デプロイパターン集

## 1. デプロイアーキテクチャ概要

Azure Databricks は **Microsoft のファーストパーティサービス** として、Azure と深い統合を持つ。
データプレーンは顧客のサブスクリプション内にデプロイされる。

---

## 2. VNet デプロイパターン

### パターン A: Managed VNet（デフォルト）

```
  Microsoft が VNet を自動管理
  ┌────────────────────────────┐
  │ Managed Resource Group     │
  │ (ロック状態)                │
  │ ├── Managed VNet           │
  │ ├── Managed NSG            │
  │ └── Root Storage Account   │
  └────────────────────────────┘
```

- VNet と NSG は Microsoft が管理し、顧客は変更不可
- マネージドリソースグループは完全にロックされている
- Private Endpoint 作成のみ許可
- **推奨**: PoC・開発のみ

### パターン B: VNet Injection（本番環境推奨）

```
  顧客が VNet を管理
  ┌────────────────────────────┐
  │ Customer VNet              │
  │ ├── Public Subnet          │
  │ │   (Delegation:           │
  │ │    Microsoft.Databricks) │
  │ ├── Private Subnet         │
  │ │   (Delegation:           │
  │ │    Microsoft.Databricks) │
  │ ├── NSG (Databricks 自動   │
  │ │   管理 + カスタムルール)  │
  │ └── Service Endpoints      │
  └────────────────────────────┘
```

- **要件**:
  - 2 つの専用サブネット（public / private）
  - サブネットデリゲーション: `Microsoft.Databricks/workspaces`
  - /26 以上の CIDR サイズ推奨
  - ワークスペースごとに固有の NSG を推奨

### Managed VNet vs VNet Injection 比較

| 項目 | Managed VNet | VNet Injection |
|:---|:---|:---|
| VNet 管理 | Microsoft | 顧客 |
| NSG 管理 | Microsoft（ロック） | Databricks 自動管理 + カスタムルール |
| Private Link | 制限あり | 完全対応 |
| Service Endpoints | 不可 | 可能 |
| オンプレミス接続 | 不可 | VPN / ExpressRoute で可能 |
| アウトバウンド制御 | 不可 | Azure Firewall で可能 |
| データ流出防止 | 限定的 | 完全対応 |

---

## 3. ネットワーク設計パターン

### Hub-Spoke アーキテクチャ（Microsoft 推奨）

```
              ┌──────────────────┐
              │ On-premises      │
              │ Network          │
              └──────┬───────────┘
                     │ ExpressRoute / VPN
              ┌──────┴───────────┐
              │   Hub VNet       │
              │ ┌──────────────┐ │
              │ │ Azure FW     │ │
              │ │ VPN Gateway  │ │
              │ │ Private DNS  │ │
              │ │ Bastion      │ │
              │ └──────────────┘ │
              └──────┬───────────┘
                     │ VNet Peering
         ┌───────────┼───────────┐
         │           │           │
  ┌──────┴──────┐ ┌──┴────────┐ ┌┴───────────┐
  │ Spoke VNet  │ │ Spoke VNet│ │ Spoke VNet │
  │ (Dev WS)    │ │ (STG WS)  │ │ (PRD WS)   │
  │ ┌─────────┐ │ │           │ │            │
  │ │DB Sub   │ │ │           │ │            │
  │ │A / B    │ │ │           │ │            │
  │ └─────────┘ │ │           │ │            │
  └─────────────┘ └───────────┘ └────────────┘
```

### Hub VNet の構成要素

| コンポーネント | 役割 |
|:---|:---|
| **Azure Firewall** | アウトバウンドトラフィックのフィルタリング |
| **VPN Gateway** | オンプレミス VPN 接続 |
| **ExpressRoute Gateway** | 専用回線接続 |
| **Private DNS Zone** | Private Link の名前解決 |
| **Azure Bastion** | 管理アクセス |

### Private Link 接続タイプ

| タイプ | 方向 | 説明 |
|:---|:---|:---|
| **Front-end（Inbound）** | ユーザー → Workspace | Web UI / REST API のプライベート化 |
| **Back-end（Classic Compute）** | クラスタ → Control Plane | REST API / SCC リレーのプライベート化 |
| **Outbound（Serverless）** | Serverless → 顧客リソース | ADLS Gen2 等へのプライベート接続 |

### NSG 設計

- Databricks はサブネットデリゲーションを通じて NSG ルールを自動管理
- 追加のカスタムルールは顧客が設定可能
- **ワークスペースごとに固有の NSG を推奨**（共有 NSG は非推奨）

---

## 4. ADLS Gen2 連携パターン

### 接続パターン

| パターン | セキュリティ | 複雑度 |
|:---|:---|:---|
| **Service Endpoints** | 中（サブネット制限） | 低 |
| **Private Endpoints** | 高（完全プライベート） | 中 |
| **Access Connector** | 高（Managed Identity） | 低 |

### Unity Catalog ストレージ管理

```
Access Connector for Azure Databricks
          │ (Managed Identity)
          ↓
Unity Catalog Storage Credential
          │
          ↓
External Location
  └── abfss://container@account.dfs.core.windows.net/path
          │
          ↓
ADLS Gen2 Storage Account
  └── Hierarchical Namespace (HNS) 有効
```

### ベストプラクティス

- **階層型名前空間（HNS）を有効化**: ADLS Gen2 の必須要件
- **Managed Identity を優先**: Service Principal よりキー管理が不要
- **ファイアウォールルール**: Databricks サブネットのみからのアクセスを許可
- **Service Endpoints + ファイアウォール**: VNet Injection 環境で最もシンプルな構成

---

## 5. Entra ID 連携パターン

### SSO（シングルサインオン）
- Azure Databricks は Entra ID による SSO を**自動的に使用**
- 追加設定なしでエンタープライズ認証が有効

### SCIM プロビジョニング
- Entra ID から Databricks へのユーザー・グループ自動同期
- アカウントレベルとワークスペースレベルの SCIM コネクタ
- SCIM API によるプログラマティックな管理

### Conditional Access（条件付きアクセス）
- MFA（多要素認証）の要求
- デバイスコンプライアンスの確認
- ネットワーク場所ベースのアクセス制御
- リスクベースのポリシー

---

## 6. Azure Key Vault 連携

### CMK（顧客管理キー）暗号化

| 対象 | 説明 | 要件 |
|:---|:---|:---|
| マネージドサービスデータ | ノートブックソース、対話型結果 | Premium 必須 |
| DBFS ルートストレージ | Blob Storage 暗号化 | Premium 必須 |
| マネージドディスク | クラスタノード一時ディスク | Premium 必須 |

### Key Vault の制約

- ワークスペースと**同一リージョン・同一 Entra ID テナント**に配置
- 異なるサブスクリプションは許容
- **Soft Delete** と **Purge Protection** を有効化

### シークレット管理

- Azure Key Vault-backed Secret Scope で安全にシークレットを管理
- Access Connector 経由でアクセス

---

## 7. コスト最適化パターン（Azure 固有）

| 手法 | 説明 | 効果 |
|:---|:---|:---|
| **Azure Reserved Instances** | VM レベルの割引 | 20-60% 削減 |
| **DBU コミットメント割引** | Databricks DBU の予約割引 | 予測可能なコスト削減 |
| **MACC** | Databricks コストを Azure 消費コミットメントに充当 | 契約活用 |
| **Spot VM** | 低優先度 VM | 最大 90% 削減 |
| **Serverless SQL Warehouse** | 自動スケール + アイドル終了 | 起動コスト削減 |
| **オートスケーリング** | 動的ワーカー数調整 | 無駄削減 |

---

## 8. Azure サービス連携

### Power BI 連携

| 接続モード | 説明 | 推奨コンピュート |
|:---|:---|:---|
| **DirectQuery** | リアルタイムクエリ | SQL Warehouse |
| **Import** | スケジュール更新 | SQL Warehouse / クラスタ |

- Arrow Database Connectivity (ADBC) ドライバーをサポート
- SQL Warehouse が DirectQuery モードでの推奨コンピュート

### Synapse Analytics 連携

- SQL Data Warehouse コネクタ（SQL DW）を使用
- Azure Blob Storage と PolyBase による効率的なデータ転送

### Microsoft Fabric 連携

- Unity Catalog と Microsoft Fabric のメタデータ統合
- OneLake との連携

---

## 9. Azure Policy による ガバナンス

| ポリシー | 効果 |
|:---|:---|
| VNet Injection の必須化 | Managed VNet でのワークスペース作成を禁止 |
| CMK 暗号化の必須化 | 暗号化なしのワークスペースを禁止 |
| パブリック IP の禁止 | No Public IP 設定を強制 |
| SKU 制限 | Premium のみを許可（コンプライアンス要件） |
| リージョン制限 | 許可されたリージョンのみ |

---

## 10. セキュリティ設計チェックリスト（Azure）

| カテゴリ | 項目 | 推奨 |
|:---|:---|:---|
| ネットワーク | VNet Injection | 本番必須 |
| ネットワーク | Private Link（全 3 タイプ） | 本番必須 |
| ネットワーク | Azure Firewall | 本番推奨 |
| ネットワーク | No Public IP | 全環境推奨 |
| 暗号化 | CMK（マネージドサービス） | 規制環境で必須 |
| 暗号化 | CMK（ディスク） | 規制環境で必須 |
| 暗号化 | CMK（DBFS） | 規制環境で推奨 |
| ID | Entra ID SSO | 全環境で有効（自動） |
| ID | Conditional Access | 全環境で推奨 |
| ID | SCIM プロビジョニング | 全環境で推奨 |
| ガバナンス | Azure Policy | 組織レベルで推奨 |
| 監視 | Activity Log | 全環境で有効 |
| 監視 | NSG フローログ | 本番で推奨 |
| コンプライアンス | Compliance Security Profile | HIPAA 等で必須 |
