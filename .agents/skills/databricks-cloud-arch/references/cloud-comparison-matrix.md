# Cloud Comparison Matrix — AWS vs Azure 機能差分表

## 1. サービス形態・基本情報

| 項目 | AWS | Azure |
|:---|:---|:---|
| **サービス形態** | AWS Marketplace から利用 | ファーストパーティサービス（Microsoft 共同開発） |
| **課金** | AWS 課金 + Databricks 課金 | Azure 統合課金 |
| **サポート** | Databricks サポート | Microsoft + Databricks 共同サポート |
| **機能リリース** | 先行リリースが多い | 後追い（差は縮小傾向） |
| **パフォーマンス** | ベースライン | 最大 21.1% 高速（Microsoft 発表） |

---

## 2. ネットワーク設計

| 機能 | AWS | Azure |
|:---|:---|:---|
| **顧客管理ネットワーク** | Customer-Managed VPC | VNet Injection |
| **サブネット要件** | 2 プライベートサブネット | 2 サブネット（public/private） |
| **デリゲーション** | なし | `Microsoft.Databricks/workspaces` |
| **DNS 要件** | DNS ホスト名・解決を有効化（見落とし多い） | 標準 Azure DNS |
| **PrivateLink** | AWS PrivateLink（3 タイプ） | Azure Private Link（3 タイプ） |
| **PrivateLink タイプ** | Front-end / Back-end / Outbound | Front-end / Back-end / Outbound |
| **ファイアウォール** | Security Group + NAT GW + NW Firewall | NSG（自動管理）+ Azure Firewall |
| **Hub-Spoke** | Transit VPC + VPC Peering / TGW | Hub VNet + VNet Peering |
| **オンプレミス接続** | Direct Connect / VPN | ExpressRoute / VPN |
| **SCC** | デフォルト有効 | デフォルト有効 |

---

## 3. ストレージ

| 機能 | AWS | Azure |
|:---|:---|:---|
| **オブジェクトストレージ** | Amazon S3 | Azure Data Lake Storage Gen2 |
| **プライベート接続** | S3 VPC Endpoint（Gateway） | Service Endpoints / Private Endpoints |
| **Storage Credential** | IAM Cross-Account Role | Access Connector（Managed Identity） |
| **レガシー方式** | Instance Profile | Service Principal |
| **暗号化** | SSE-S3 / SSE-KMS | Microsoft マネージド / CMK（Key Vault） |
| **バケット命名注意** | ドット（.）禁止推奨 | HNS 有効化必須 |
| **DR 用レプリケーション** | Cross-Region Replication（CRR） | GRS / RA-GRS |

---

## 4. ID・認証管理

| 機能 | AWS | Azure |
|:---|:---|:---|
| **SSO** | SAML 2.0（Okta / Entra ID 等） | Entra ID（自動統合） |
| **SCIM** | Entra ID / Okta / OneLogin 等 | Entra ID ネイティブ SCIM |
| **MFA** | IdP 側で設定 | Conditional Access で強制 |
| **Conditional Access** | IdP 依存 | Entra ID ネイティブ |
| **サービス認証** | IAM Role / Cross-Account Trust | Access Connector / Managed Identity |
| **組織ガードレール** | Service Control Policies（SCPs） | Azure Policy |

---

## 5. セキュリティ・暗号化

| 機能 | AWS | Azure |
|:---|:---|:---|
| **CMK（ストレージ）** | AWS KMS（SSE-KMS） | Azure Key Vault |
| **CMK（ディスク）** | AWS KMS | Azure Key Vault |
| **CMK（Control Plane）** | AWS KMS | Azure Key Vault（Premium 必須） |
| **CMK（マネージドサービス）** | AWS KMS | Azure Key Vault（Premium 必須） |
| **Key Vault 制約** | リージョン制限なし | 同一リージョン・同一テナント |
| **監査ログ** | CloudTrail | Azure Activity Log |
| **ネットワークログ** | VPC Flow Logs | NSG フローログ |
| **リソース構成監視** | AWS Config | Azure Policy |
| **Compliance Profile** | 対応 | 対応 |

---

## 6. IaC・CI/CD

| 機能 | AWS | Azure |
|:---|:---|:---|
| **Terraform Provider** | 完全対応 | 完全対応 |
| **クラウド固有 IaC** | CloudFormation | ARM / Bicep |
| **DABs** | 完全対応 | 完全対応 |
| **CI/CD ツール** | GitHub Actions / CodePipeline | GitHub Actions / Azure DevOps |
| **Workload Identity** | GitHub OIDC / IAM Role | Workload Identity Federation |
| **Quickstart テンプレート** | CloudFormation テンプレート | ARM クイックスタート |

---

## 7. エコシステム連携

| 機能 | AWS | Azure |
|:---|:---|:---|
| **カタログ連携** | Glue Data Catalog（Lakehouse Federation） | Purview / Microsoft Fabric |
| **BI 連携** | Tableau / QuickSight（弱い） | Power BI（ネイティブコネクタ） |
| **DWH 連携** | Redshift（Federation） | Synapse Analytics（SQL DW コネクタ） |
| **ストリーミング** | Kinesis | Event Hub |
| **シークレット管理** | Secrets Manager / Databricks Secret | Azure Key Vault ネイティブ |

---

## 8. コスト最適化

| 機能 | AWS | Azure |
|:---|:---|:---|
| **Spot 利用** | Spot Instance | Spot VM |
| **予約割引（VM）** | Reserved Instances / Savings Plans | Azure Reserved Instances |
| **予約割引（DBU）** | Reserved Capacity | DBU コミットメント割引 |
| **消費コミットメント** | — | MACC（Azure Consumption Commitment） |
| **Serverless** | GA | GA |
| **Photon** | 対応 | 対応 |

---

## 9. DR・可用性

| 機能 | AWS | Azure |
|:---|:---|:---|
| **データレプリケーション** | S3 Cross-Region Replication | GRS / RA-GRS |
| **メタデータ同期** | API / Terraform | API / Terraform |
| **コード同期** | Databricks Repos（Git） | Databricks Repos（Git） |
| **マルチリージョン** | 対応（リージョンごとにメタストア） | 対応（リージョンごとにメタストア） |

---

## 10. コンプライアンス

| 認証 | AWS | Azure |
|:---|:---|:---|
| SOC 2 Type II | 対応 | 対応 |
| HIPAA | 対応 | 対応 |
| PCI DSS | 対応 | 対応 |
| ISO 27001 | 対応 | 対応 |
| FedRAMP | 対応 | 対応 |
| ISMAP | — | — |

---

## 11. クラウド選定ガイド

| 選ぶべきケース | 推奨クラウド | 理由 |
|:---|:---|:---|
| AWS エコシステムが主体 | **AWS** | 既存 VPC・IAM・S3 との統合がスムーズ |
| 最新機能を先行利用したい | **AWS** | Databricks の新機能は AWS で先行リリースされる傾向 |
| 複雑な IAM 要件がある | **AWS** | IAM の柔軟性が高い |
| Microsoft エコシステムが主体 | **Azure** | Power BI、M365、Entra ID との統合が優秀 |
| MACC を活用したい | **Azure** | Databricks コストを Azure 消費コミットメントに充当 |
| Entra ID 統合が重要 | **Azure** | SSO 自動統合、Conditional Access が標準 |
| M&A でマルチクラウドが不可避 | **両方** | Delta Sharing でクロスクラウドデータ共有 |
| 地理的・規制要件で分散 | **両方** | Unity Catalog + Delta Sharing で統合ガバナンス |
