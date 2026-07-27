# Security Checklist — セキュリティ設計チェックリスト

## 使い方

本チェックリストは Databricks クラウドインフラのセキュリティ設計を体系的に検証するためのものである。
Step 4（ID・セキュリティ設計）および Step 9（Well-Architected レビュー）で使用する。

---

## 1. ネットワークセキュリティ

### 1.1 VPC / VNet 設計

| # | チェック項目 | AWS | Azure | 必須/推奨 |
|:---|:---|:---|:---|:---|
| N-01 | 顧客管理ネットワークを使用している | Customer-Managed VPC | VNet Injection | 本番必須 |
| N-02 | 専用サブネットが適切に設計されている | 2 プライベートサブネット | 2 サブネット + デリゲーション | 必須 |
| N-03 | CIDR 範囲が他のネットワークと重複しない | VPC / Peering 先と確認 | VNet / Peering 先と確認 | 必須 |
| N-04 | DNS が正しく設定されている | DNS ホスト名 + DNS 解決 | Azure DNS（デフォルト） | 必須 |
| N-05 | Secure Cluster Connectivity が有効 | デフォルト有効を確認 | デフォルト有効を確認 | 必須 |

### 1.2 PrivateLink

| # | チェック項目 | AWS | Azure | 必須/推奨 |
|:---|:---|:---|:---|:---|
| N-06 | Front-end PrivateLink が設定されている | VPC Endpoint (Transit VPC) | Private Endpoint (Hub VNet) | 本番必須 |
| N-07 | Back-end PrivateLink が設定されている | VPC Endpoint (Workspace VPC) | Private Endpoint (Spoke VNet) | 本番必須 |
| N-08 | Outbound PrivateLink が設定されている | NCC 構成 | NCC 構成 | 強く推奨 |
| N-09 | Private DNS Zone が正しく設定されている | Private Hosted Zone | Private DNS Zone + VNet リンク | 必須 |

### 1.3 ファイアウォール・アウトバウンド制御

| # | チェック項目 | AWS | Azure | 必須/推奨 |
|:---|:---|:---|:---|:---|
| N-10 | アウトバウンドトラフィックが制御されている | NAT GW + NW Firewall | Azure Firewall + UDR | 推奨 |
| N-11 | Databricks 必須 FQDN が許可されている | Firewall ルール | Application Rule | 必須 |
| N-12 | パブリック IP が無効化されている | SCC で自動 | No Public IP 設定 | 推奨 |
| N-13 | VPC/NSG フローログが有効 | VPC Flow Logs | NSG フローログ | 本番推奨 |

---

## 2. ID・アクセス管理

### 2.1 認証

| # | チェック項目 | AWS | Azure | 必須/推奨 |
|:---|:---|:---|:---|:---|
| I-01 | SSO が設定されている | SAML 2.0 | Entra ID（自動） | 必須 |
| I-02 | MFA が有効化されている | IdP 側で設定 | Conditional Access | 強く推奨 |
| I-03 | SCIM プロビジョニングが設定されている | Entra ID / Okta コネクタ | Entra ID ネイティブ SCIM | 推奨 |
| I-04 | Conditional Access ポリシーが設定されている | IdP 依存 | Entra ID ネイティブ | 推奨 |
| I-05 | Personal Access Token の管理ポリシーがある | PAT の有効期限設定 | PAT の有効期限設定 | 推奨 |

### 2.2 認可

| # | チェック項目 | AWS | Azure | 必須/推奨 |
|:---|:---|:---|:---|:---|
| I-06 | Unity Catalog でアクセス制御されている | 全データオブジェクト | 全データオブジェクト | 必須 |
| I-07 | 最小権限の原則が適用されている | IAM Policy / UC 権限 | RBAC / UC 権限 | 必須 |
| I-08 | クラスタポリシーで制御されている | クラスタ作成の制限 | クラスタ作成の制限 | 推奨 |
| I-09 | サービス認証が適切に設計されている | Cross-Account Role | Access Connector | 必須 |

### 2.3 組織レベルのガードレール

| # | チェック項目 | AWS | Azure | 必須/推奨 |
|:---|:---|:---|:---|:---|
| I-10 | 組織ポリシーが設定されている | SCPs | Azure Policy | 推奨 |
| I-11 | リソース作成が制限されている | リージョン制限 SCPs | リージョン・SKU 制限 Policy | 推奨 |
| I-12 | タグ付けポリシーが適用されている | Tag Policy | Azure Policy (Tagging) | 推奨 |

---

## 3. 暗号化

### 3.1 保存時の暗号化

| # | チェック項目 | AWS | Azure | 必須/推奨 |
|:---|:---|:---|:---|:---|
| E-01 | ストレージ暗号化が有効 | SSE-S3（デフォルト） | Microsoft マネージド（デフォルト） | 必須 |
| E-02 | CMK でストレージが暗号化されている | SSE-KMS | Key Vault CMK | 規制環境必須 |
| E-03 | CMK でディスクが暗号化されている | EBS CMK | マネージドディスク CMK | 規制環境必須 |
| E-04 | CMK で Control Plane データが暗号化されている | KMS CMK | Key Vault CMK | 規制環境推奨 |
| E-05 | CMK でマネージドサービスデータが暗号化されている | KMS CMK | Key Vault CMK（Premium） | 規制環境推奨 |

### 3.2 転送中の暗号化

| # | チェック項目 | AWS | Azure | 必須/推奨 |
|:---|:---|:---|:---|:---|
| E-06 | TLS 1.2 以上が強制されている | デフォルト有効 | デフォルト有効 | 必須 |
| E-07 | PrivateLink でトラフィックが暗号化されている | PrivateLink 設定 | Private Link 設定 | 本番推奨 |

### 3.3 鍵管理

| # | チェック項目 | AWS | Azure | 必須/推奨 |
|:---|:---|:---|:---|:---|
| E-08 | 鍵のローテーションポリシーが設定されている | KMS 自動ローテーション | Key Vault ローテーション | 推奨 |
| E-09 | Key Vault の制約を満たしている | — | 同一リージョン・同一テナント | Azure 必須 |
| E-10 | Soft Delete / Purge Protection が有効 | — | Key Vault 設定 | Azure 推奨 |

---

## 4. データ保護

| # | チェック項目 | 説明 | 必須/推奨 |
|:---|:---|:---|:---|
| D-01 | データ流出防止策が講じられている | アウトバウンド制限、PrivateLink | 推奨 |
| D-02 | シークレットが安全に管理されている | Secret Scope（Key Vault / Databricks） | 必須 |
| D-03 | 機密データにマスキング/トークン化が適用されている | Unity Catalog のカラムマスク | 規制環境推奨 |
| D-04 | Row-Level Security が必要箇所に設定されている | Unity Catalog の行フィルタ | 規制環境推奨 |
| D-05 | バックアップ・リストア手順が整備されている | DR 設計の一部 | 本番必須 |

---

## 5. 監視・監査

| # | チェック項目 | AWS | Azure | 必須/推奨 |
|:---|:---|:---|:---|:---|
| M-01 | 監査ログが有効化されている | Databricks Audit Log + CloudTrail | Databricks Audit Log + Activity Log | 必須 |
| M-02 | ログの長期保存が設定されている | S3 → Glacier | Blob Storage → Archive | 規制環境必須 |
| M-03 | セキュリティアラートが設定されている | CloudWatch Alarms | Azure Monitor Alerts | 推奨 |
| M-04 | 不正アクセス検知が有効 | GuardDuty | Microsoft Defender | 推奨 |
| M-05 | ネットワークトラフィック監視が有効 | VPC Flow Logs | NSG フローログ | 本番推奨 |

---

## 6. コンプライアンス

| # | チェック項目 | 説明 | 必須/推奨 |
|:---|:---|:---|:---|
| C-01 | 対象コンプライアンス認証を確認している | SOC 2, HIPAA, PCI DSS 等 | 必須 |
| C-02 | Compliance Security Profile が必要か判断している | HIPAA 等の規制要件 | 必須 |
| C-03 | BAA が締結されている（HIPAA の場合） | Databricks との BAA | HIPAA 必須 |
| C-04 | データ保持ポリシーが定義されている | 規制に応じた保持期間 | 規制環境必須 |
| C-05 | 定期的なセキュリティ監査が計画されている | 内部/外部監査のスケジュール | 推奨 |

---

## 7. 業界別追加チェック

### 金融サービス

| # | チェック項目 | 必須/推奨 |
|:---|:---|:---|
| FS-01 | SEC/FINRA/MiFID II の監査証跡要件を満たしている | 必須 |
| FS-02 | CMK 暗号化が全レイヤーで有効 | 必須 |
| FS-03 | Lakehouse for FS Blueprints を参照している | 推奨 |

### ヘルスケア

| # | チェック項目 | 必須/推奨 |
|:---|:---|:---|
| HC-01 | HIPAA Compliance Security Profile が有効 | 必須 |
| HC-02 | BAA が締結済み | 必須 |
| HC-03 | PHI データの暗号化とアクセス制御が設計されている | 必須 |

### 製造業

| # | チェック項目 | 必須/推奨 |
|:---|:---|:---|
| MF-01 | IoT データのストリーミング取り込み経路が設計されている | 推奨 |
| MF-02 | OT/IT ネットワーク分離が考慮されている | 推奨 |
