---
name: databricks-cloud-arch
description: >
  Databricks の AWS/Azure クラウドインフラアーキテクチャを設計するスキル。
  VPC/VNet 設計、PrivateLink 構成、ストレージ連携（S3/ADLS Gen2）、
  IAM/Entra ID 認証設計、CMK 暗号化、Hub-Spoke ネットワーク、
  マルチワークスペース戦略、Terraform IaC、DR 設計、コスト最適化を包括的にガイドする。
  Use when user says「DatabricksのVPCを設計して」「Azure DatabricksのPrivate Linkを構成して」
  「DatabricksのTerraformを書いて」「Databricksのネットワーク設計」
  「DatabricksのDR戦略を設計して」「DatabricksのAWSアーキテクチャ」
  「DatabricksのAzureデプロイ設計」「マルチワークスペースを設計して」
  「DatabricksのIaC設計」。
  Do NOT use for: Databricks プラットフォーム機能の設計（→ databricks）、
  Delta Lake テーブル設計（→ delta-lake）、Unity Catalog 設計（→ unity-catalog）。
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: data-platform
---

# Skill: Databricks Cloud Architecture（クラウドインフラアーキテクチャ設計）

> **クラウドの土台なくしてレイクハウスは建たない — ネットワーク・セキュリティ・IaC を設計せよ**

## Instructions

### ワークフロー内の位置

```
要件ヒアリング → [databricks-cloud-arch] → databricks / delta-lake / unity-catalog
                        ↓
                  設計成果物
                  ・ネットワークアーキテクチャ図
                  ・セキュリティ設計書
                  ・Terraform モジュール構成
                  ・コスト見積もり
                  ・DR 設計書
                        ↓
                  diagram（構成図生成）
                  review（設計レビュー）
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| クラウドプロバイダ | AWS / Azure / マルチクラウド | 「Azure でデプロイしたい」 |
| ワークロード要件 | ETL、SQL、ML、Streaming の構成 | 「バッチ ETL と SQL Warehouse が中心」 |
| セキュリティ要件 | コンプライアンス、暗号化、ネットワーク隔離 | 「HIPAA 準拠が必要」 |
| 規模 | ユーザー数、データ量、ワークスペース数 | 「100 名、10TB/月、3 ワークスペース」 |
| 既存インフラ | オンプレミス接続、既存 VPC/VNet | 「ExpressRoute で接続したい」 |

### 出力

| 出力 | 形式 | 説明 |
|:---|:---|:---|
| ネットワーク設計書 | Markdown + ASCII 図 | VPC/VNet トポロジ、PrivateLink 構成 |
| セキュリティ設計書 | Markdown テーブル | 暗号化・認証・コンプライアンス設計 |
| Terraform 構成 | HCL コード | モジュール分割された IaC テンプレート |
| コスト見積もり | Markdown テーブル | DBU・VM・ストレージのコスト試算 |
| DR 設計書 | Markdown | RTO/RPO 定義、レプリケーション戦略 |

---

## Step 1: 要件ヒアリング

プロジェクトの基本要件を体系的に収集する。

### 1a. クラウドプロバイダの選定

| 判断軸 | AWS を選ぶケース | Azure を選ぶケース |
|:---|:---|:---|
| エコシステム | AWS サービスが主体 | Microsoft 365 / Power BI が主体 |
| ID 管理 | IAM + Okta 等の IdP | Entra ID で統合管理 |
| コスト | Savings Plans 活用 | MACC（Azure 消費コミットメント）活用 |
| 機能リリース | 最新機能を先行利用したい | Azure ネイティブ統合を重視 |
| 既存インフラ | AWS VPC が既にある | Azure VNet / ExpressRoute が既にある |

### 1b. ワークロード特性の把握

| 項目 | 確認内容 | 設計への影響 |
|:---|:---|:---|
| データ量 | 日次/月次の増分データ量 | ストレージ容量・ネットワーク帯域 |
| ユーザー数 | 同時接続ユーザー数 | ワークスペースサイズ・クラスタ構成 |
| ワークロード種別 | ETL / SQL / ML / Streaming | コンピュートタイプ・コスト構造 |
| SLA 要件 | 可用性・RTO/RPO | DR 戦略・冗長構成 |

### 1c. コンプライアンス要件の確認

対象業界の規制を確認し、Compliance Security Profile の必要性を判断する:
- 金融: PCI DSS、SOX、FINRA
- 医療: HIPAA（BAA 締結が必要）
- 公共: FedRAMP、ISMAP
- 汎用: SOC 2 Type II、ISO 27001

**チェックリスト**:
- [ ] クラウドプロバイダが決定されている（AWS / Azure / 両方）
- [ ] ワークロード種別と規模が把握されている
- [ ] コンプライアンス要件が洗い出されている
- [ ] 既存インフラとの統合要件が確認されている
- [ ] SLA 要件（可用性・RTO/RPO）が定義されている

---

## Step 2: ネットワークアーキテクチャ設計

VPC/VNet トポロジと PrivateLink 構成を設計する。
詳細なパターンは [networking-reference.md](references/networking-reference.md) を参照。

### 2a. VPC/VNet 方式の決定

| 環境 | AWS | Azure |
|:---|:---|:---|
| **PoC・開発** | Databricks マネージド VPC | Managed VNet（デフォルト） |
| **本番環境** | Customer-Managed VPC（推奨） | VNet Injection（推奨） |

本番環境では必ず顧客管理のネットワークを採用する。

### 2b. Hub-Spoke トポロジの設計

AWS / Azure ともに Hub-Spoke アーキテクチャを推奨。Hub にファイアウォール・VPN Gateway・Private DNS Zone を配置し、Spoke に各ワークスペースの VPC/VNet を配置する。

### 2c. PrivateLink 構成

AWS / Azure ともに 3 タイプの PrivateLink を設計する:

| タイプ | 方向 | 本番での推奨 |
|:---|:---|:---|
| **Front-end（Inbound）** | ユーザー → Workspace | 必須 |
| **Back-end（Classic Compute）** | クラスタ → Control Plane | 必須 |
| **Outbound（Serverless）** | Serverless → 顧客リソース | 強く推奨 |

### 2d. サブネット設計

| 項目 | AWS 要件 | Azure 要件 |
|:---|:---|:---|
| サブネット数 | 2（プライベート） | 2（public / private） |
| サブネットサイズ | /17〜/26 推奨 | /26 以上推奨 |
| DNS | ホスト名・DNS 解決を有効化 | — |
| デリゲーション | — | `Microsoft.Databricks/workspaces` |

### 2e. ファイアウォール・アウトバウンド制御

- **AWS**: Security Group + NAT Gateway + Network Firewall
- **Azure**: NSG（Databricks 自動管理ルール）+ Azure Firewall

**チェックリスト**:
- [ ] VPC/VNet 方式が環境ごとに決定されている
- [ ] Hub-Spoke トポロジが設計されている
- [ ] PrivateLink の 3 タイプすべてが検討されている
- [ ] サブネットの CIDR 範囲が他のネットワークと重複していない
- [ ] ファイアウォールのアウトバウンドルールが定義されている
- [ ] オンプレミス接続（VPN / ExpressRoute / Direct Connect）が考慮されている

---

## Step 3: ストレージ・データアクセス設計

S3 / ADLS Gen2 とのストレージ連携を設計する。
AWS / Azure 各パターンの詳細は [aws-architecture-patterns.md](references/aws-architecture-patterns.md) および [azure-architecture-patterns.md](references/azure-architecture-patterns.md) を参照。

### 3a. Unity Catalog ストレージ構成

Unity Catalog の Storage Credential と External Location で管理する:

| コンポーネント | AWS | Azure |
|:---|:---|:---|
| **Storage Credential** | IAM Cross-Account Role | Access Connector（Managed Identity） |
| **External Location** | `s3://bucket/path` | `abfss://container@account.dfs.core.windows.net/path` |
| **レガシー方式** | Instance Profile（非推奨） | Service Principal（非推奨） |

### 3b. ストレージ接続パターン

| パターン | AWS | Azure |
|:---|:---|:---|
| プライベート接続 | S3 VPC Endpoint（Gateway） | Service Endpoints / Private Endpoints |
| 暗号化 | SSE-S3 / SSE-KMS | Microsoft マネージド / CMK |
| ファイアウォール | S3 Bucket Policy | ストレージアカウント ファイアウォール |

### 3c. ベストプラクティス

- S3 バケット名にドット（`.`）を使わない（SSL 証明書検証失敗の原因）
- ADLS Gen2 では階層型名前空間（HNS）を有効化する
- 複数メタストアから同一パスへのアクセスを避ける
- Storage Credential の権限は最小限に設定する

**チェックリスト**:
- [ ] Storage Credential が Unity Catalog の推奨方式で設計されている
- [ ] External Location のパス設計が完了している
- [ ] ストレージへのプライベート接続が設計されている
- [ ] 暗号化方式が決定されている
- [ ] バケット / ストレージアカウントの命名規則が定められている

---

## Step 4: ID・セキュリティ設計

認証・認可・暗号化・コンプライアンスを設計する。
セキュリティチェックリストの完全版は [security-checklist.md](references/security-checklist.md) を参照。

### 4a. 認証・ID 管理

| 項目 | AWS | Azure |
|:---|:---|:---|
| SSO | SAML 2.0（Okta / Entra ID 等） | Entra ID（自動統合） |
| SCIM | Entra ID / Okta コネクタ | Entra ID ネイティブ SCIM |
| MFA | IdP 側で設定 | Conditional Access で強制 |
| サービス認証 | IAM Cross-Account Role | Access Connector（Managed Identity） |

### 4b. CMK（顧客管理キー）暗号化

| 暗号化対象 | AWS（KMS） | Azure（Key Vault） |
|:---|:---|:---|
| ストレージ（DBFS ルート） | SSE-KMS | Blob Storage CMK |
| マネージドサービスデータ | CMK 対応 | CMK 対応（Premium 必須） |
| マネージドディスク | CMK 対応 | CMK 対応（Premium 必須） |
| Control Plane データ | CMK 対応 | CMK 対応 |

### 4c. 組織レベルのガードレール

- **AWS**: Service Control Policies（SCPs）、CloudTrail、AWS Config
- **Azure**: Azure Policy（VNet Injection 必須化、CMK 必須化、パブリック IP 禁止）

### 4d. コンプライアンスプロファイル

Compliance Security Profile は HIPAA 等の規制要件に対応する追加セキュリティ設定を有効化する。
適用が必要な場合は、ワークスペース作成時に有効化する。

**チェックリスト**:
- [ ] SSO / SCIM によるユーザーの自動プロビジョニングが設計されている
- [ ] CMK 暗号化の対象と鍵管理方針が決定されている
- [ ] 組織レベルのガードレール（SCPs / Azure Policy）が定義されている
- [ ] コンプライアンスプロファイルの要否が判断されている
- [ ] 転送中の暗号化（TLS 1.2+）が確認されている
- [ ] VPC Flow Logs / NSG フローログの有効化が計画されている

---

## Step 5: ワークスペース・環境戦略

マルチワークスペース構成と Dev/STG/PRD の分離方針を設計する。

### 5a. ワークスペース分割方針

| 分割基準 | 説明 | 推奨ケース |
|:---|:---|:---|
| **環境別（Dev/STG/PRD）** | 環境ごとに分離 | すべての組織で推奨 |
| **LOB 別（事業部門）** | 部門ごとに Dev/STG/PRD セット | 大規模組織、部門間の独立性が高い |
| **規制別** | コンプライアンス要件ごとに分離 | 金融（PCI DSS）、医療（HIPAA） |

### 5b. Unity Catalog による統合ガバナンス

- リージョンごとに 1 メタストアを全ワークスペースで共有
- カタログ・スキーマレベルでのデータ分離
- ワークスペース間でのアクセス制御は Unity Catalog の権限で管理

### 5c. 環境ごとの設計パラメータ

| 項目 | Dev | STG | PRD |
|:---|:---|:---|:---|
| クラスタサイズ | 小規模（2 ワーカー） | 中規模（4 ワーカー） | 本番相当（8+ ワーカー） |
| データ | サンプルデータ | 本番相当データ | 本番データ |
| アクセス | 開発者全員 | CI/CD + QA | 制限付き |
| Spot 比率 | 高い | 中程度 | 低い（安定優先） |

**チェックリスト**:
- [ ] ワークスペース分割方針が決定されている
- [ ] Unity Catalog メタストアの配置が設計されている
- [ ] 環境ごとのリソースパラメータが定義されている
- [ ] カタログ・スキーマの命名規則が統一されている
- [ ] クラスタポリシーによるリソース制御が設計されている

---

## Step 6: IaC・CI/CD 設計

Terraform と DABs を組み合わせたインフラ管理と継続的デリバリーを設計する。
Terraform モジュール構成の詳細は [terraform-modules.md](references/terraform-modules.md) を参照。

### 6a. IaC ツールの使い分け

| 対象 | 推奨ツール | 理由 |
|:---|:---|:---|
| クラウドインフラ（VPC/VNet） | Terraform | クラウドリソースの完全な管理 |
| Databricks ワークスペース | Terraform（databricks provider） | 宣言的なワークスペース管理 |
| Unity Catalog | Terraform（databricks provider） | メタストア・カタログの一元管理 |
| ジョブ・パイプライン | DABs（Databricks Asset Bundles） | ワークロードの CI/CD に最適 |
| Azure 固有リソース | ARM/Bicep（Terraform と併用） | Azure ネイティブ機能の活用 |

### 6b. Terraform モジュール構成

`modules/networking`（VPC/VNet、PrivateLink）、`modules/workspace`（ワークスペース）、`modules/unity-catalog`（メタストア）、`modules/security`（CMK、IAM）、`modules/monitoring`（ログ、アラート）に分割し、`environments/dev|staging|production` でパラメータ化する。詳細なコードテンプレートは [terraform-modules.md](references/terraform-modules.md) を参照。

### 6c. CI/CD パイプライン設計

| フェーズ | アクション | ツール |
|:---|:---|:---|
| 開発 | ローカル開発 → Feature Branch | Git + DABs |
| PR | コードレビュー + 自動テスト | GitHub Actions / Azure DevOps |
| STG | Main マージ → 自動デプロイ | DABs + Terraform |
| PRD | STG テスト通過 → 承認付きデプロイ | DABs + Terraform |

### 6d. 認証のベストプラクティス

- **Workload Identity Federation** を最優先（シークレット管理が不要）
- Service Principal / IAM Role による CI/CD パイプライン認証
- 環境変数による設定のパラメータ化

**チェックリスト**:
- [ ] Terraform と DABs の責務分担が明確になっている
- [ ] Terraform モジュールが機能単位で分割されている
- [ ] tfstate のリモートバックエンドが設計されている
- [ ] CI/CD パイプラインのフローが定義されている
- [ ] 認証方式が Workload Identity Federation を優先している
- [ ] 環境ごとの変数ファイルが設計されている

---

## Step 7: コスト最適化設計

DBU コスト、VM コスト、ストレージコストを最適化する戦略を設計する。
AWS / Azure の差分比較は [cloud-comparison-matrix.md](references/cloud-comparison-matrix.md) を参照。

### 7a. コンピュートコスト最適化

| 手法 | 効果 | 適用ワークロード |
|:---|:---|:---|
| **Spot Instance / Spot VM** | 最大 90% 削減 | バッチ ETL、非クリティカルジョブ |
| **Reserved Capacity / RI** | 20-60% 削減 | 予測可能な長期ワークロード |
| **Serverless** | 起動コスト削減 + 自動スケール | SQL Warehouse、アドホッククエリ |
| **Photon エンジン** | 処理時間短縮 → DBU 削減 | SQL ワークロード |
| **オートスケーリング** | 需要に応じた動的調整 | すべてのワークロード |

### 7b. ストレージコスト最適化

- ライフサイクルポリシーで古いデータをアーカイブ層に移行
- Delta Lake の OPTIMIZE / VACUUM で不要ファイルを削除
- 不要なスナップショットの定期クリーンアップ

### 7c. コスト管理とモニタリング

- DBU 消費の可視化とアラート設定
- クラスタの自動終了タイムアウト設定
- 不要リソースの定期棚卸し

### 7d. Azure 固有: MACC 活用

Azure では MACC（Microsoft Azure Consumption Commitment）に Databricks コストを充当可能。
企業契約がある場合は MACC の活用を優先検討する。

**チェックリスト**:
- [ ] ワークロード別のコンピュート戦略（Spot / Reserved / Serverless）が決定されている
- [ ] クラスタの自動終了タイムアウトが設定されている
- [ ] ストレージのライフサイクルポリシーが設計されている
- [ ] DBU 消費の監視・アラートが計画されている
- [ ] コスト見積もりが作成されている

---

## Step 8: DR・運用設計

災害復旧戦略と日常運用の監視・ログ管理を設計する。

### 8a. DR 戦略の選定

| 戦略 | RTO | RPO | コスト | 推奨ケース |
|:---|:---|:---|:---|:---|
| **Active-Passive** | 数時間 | 分〜時間 | 中 | ほとんどの本番環境 |
| **Active-Active** | 分 | ほぼリアルタイム | 高 | ミッションクリティカル |
| **Pilot Light** | 時間 | 時間 | 低 | コスト重視 |

### 8b. レプリケーション対象

| カテゴリ | 対象 | 方法 |
|:---|:---|:---|
| データ | S3 / ADLS のデータ | Cross-Region Replication / GRS |
| メタデータ | Unity Catalog | API / Terraform 同期 |
| コード | ノートブック、アプリ | Git Repos（Databricks Repos） |
| 設定 | クラスタ、ジョブ、権限 | Terraform / REST API |
| シークレット | 暗号化キー、接続情報 | KMS / Key Vault のレプリケーション |

### 8c. 監視・ログ管理

| 監視対象 | ツール | アラート基準 |
|:---|:---|:---|
| クラスタヘルス | System Tables / CloudWatch / Azure Monitor | クラスタ障害、長時間実行ジョブ |
| DBU 消費 | Databricks Account Console | 予算閾値超過 |
| セキュリティ | CloudTrail / Azure Activity Log | 不正アクセス試行 |
| ネットワーク | VPC Flow Logs / NSG フローログ | 異常トラフィック |

### 8d. 運用自動化

- Terraform による DR 環境の完全な再現性を確保
- 定期的な DR テスト（Failover / Failback）の実施
- ランブック（運用手順書）の整備

**チェックリスト**:
- [ ] DR 戦略（Active-Passive / Active-Active）が選定されている
- [ ] レプリケーション対象と方法が定義されている
- [ ] 監視・アラートの設計が完了している
- [ ] DR テストのスケジュールが計画されている
- [ ] ランブックが整備されている（または整備計画がある）

---

## Step 9: Well-Architected レビュー

設計全体を Databricks Well-Architected Framework の 7 つの柱で検証する。

### 9a. レビューチェックリスト

| 柱 | 主な確認事項 | 対応ステップ |
|:---|:---|:---|
| **Data Governance** | Unity Catalog の設計、アクセス制御 | Step 3, 5 |
| **Interoperability** | オープンフォーマット、Federation 対応 | Step 3 |
| **Operational Excellence** | IaC、CI/CD、監視体制 | Step 6, 8 |
| **Security** | 暗号化、ネットワーク隔離、ID 管理 | Step 2, 4 |
| **Reliability** | DR 設計、HA 構成 | Step 8 |
| **Performance** | コンピュート最適化、キャッシング | Step 7 |
| **Cost Optimization** | Spot/Reserved、サーバーレス活用 | Step 7 |

### 9b. クラウド別の追加チェック

**AWS 固有**:
- Secure Cluster Connectivity（SCC）が有効か
- Customer-Managed VPC の DNS 設定が正しいか
- S3 バケットポリシーが最小権限か

**Azure 固有**:
- VNet Injection のサブネットデリゲーションが正しいか
- Azure Policy でガバナンスが強制されているか
- Key Vault のリージョン・テナント制約を満たしているか

### 9c. 設計ドキュメントの出力

以下の成果物を最終的に整理して出力する:
1. ネットワークアーキテクチャ図（ASCII または diagram スキル連携）
2. セキュリティ設計書
3. Terraform モジュール構成
4. コスト見積もりテーブル
5. DR 設計書

**チェックリスト**:
- [ ] Well-Architected の 7 つの柱すべてが検証されている
- [ ] クラウド固有のチェック項目が確認されている
- [ ] 設計成果物がすべて出力されている
- [ ] ユーザーに成果物の利用方法を説明している

---

## Examples

### Example 1: AWS での本番環境ネットワーク設計

```
「Databricks on AWS の本番ネットワークを設計して。PrivateLink 必須」

→ Step 1 でクラウド = AWS、本番環境、PrivateLink 必須を確認
→ Step 2 で Customer-Managed VPC + Hub-Spoke 構成を設計
  - Transit VPC（Hub）: Inbound PrivateLink EP、NAT Gateway
  - Workspace VPC（Spoke）: 2 プライベートサブネット
  - Back-end PrivateLink でクラスタ → Control Plane を隔離
→ Step 4 で IAM Cross-Account Role + SCC を設計
→ Step 9 で Well-Architected レビューを実施
→ ネットワークアーキテクチャ図を ASCII で出力
```

### Example 2: Azure Hub-Spoke + VNet Injection 構成

```
「Azure Databricks を Hub-Spoke で設計して。ExpressRoute 接続あり」

→ Step 1 でクラウド = Azure、ExpressRoute 接続要件を確認
→ Step 2 で Hub-Spoke 構成を設計
  - Hub VNet: Azure Firewall、VPN Gateway、Private DNS Zone
  - Spoke VNet（Dev/STG/PRD）: VNet Injection + サブネットデリゲーション
  - Private Link（Front-end + Back-end + Outbound）を設計
→ Step 4 で Entra ID + Conditional Access を設計
→ Step 6 で Terraform + ARM/Bicep のハイブリッド IaC を設計
→ diagram スキルと連携して draw.io 構成図を出力
```

### Example 3: マルチワークスペース + Unity Catalog 統合

```
「3 事業部 × Dev/STG/PRD のワークスペース構成を設計して」

→ Step 1 で 3 LOB × 3 環境 = 9 ワークスペースの規模を確認
→ Step 5 で LOB 別 + 環境別の分割方針を設計
  - 各 LOB に Dev/STG/PRD ワークスペースセットを割り当て
  - Unity Catalog: 1 リージョン 1 メタストア、LOB 別カタログ
  - クラスタポリシーでリソース制御
→ Step 3 で Storage Credential / External Location を LOB 別に設計
→ Step 6 で Terraform モジュールのパラメータ化を設計
→ ワークスペース構成図とカタログ設計書を出力
```

### Example 4: HIPAA 準拠のセキュリティ設計

```
「医療系データ基盤。HIPAA 準拠の Databricks 設計をして」

→ Step 1 で HIPAA コンプライアンス要件を確認
→ Step 2 で完全なネットワーク隔離を設計（PrivateLink 必須）
→ Step 4 で Compliance Security Profile を有効化
  - CMK 暗号化（全レイヤー）
  - BAA（Business Associate Agreement）の締結確認
  - 監査ログの長期保存
→ Step 4c で SCPs / Azure Policy でガバナンスを強制
→ Step 8 で DR 設計（PHI データの暗号化レプリケーション）
→ セキュリティ設計書 + コンプライアンスチェックリストを出力
```

### Example 5: Terraform によるインフラ自動化

```
「Databricks の Terraform モジュールを設計して。Dev/STG/PRD 3 環境」

→ Step 1 で 3 環境のパラメータ差分を確認
→ Step 6 で Terraform モジュール構成を設計
  - modules/networking: VPC/VNet + PrivateLink
  - modules/workspace: Databricks ワークスペース
  - modules/unity-catalog: メタストア + カタログ
  - modules/security: CMK + IAM/Entra ID
  - environments/: dev / staging / production の変数ファイル
→ Step 6c で CI/CD パイプラインを設計（GitHub Actions）
→ Step 6d で Workload Identity Federation を設定
→ Terraform コードテンプレートとディレクトリ構成図を出力
```

### Example 6: DR 戦略の設計と DR テスト計画

```
「Databricks の DR 戦略を設計して。RTO 4 時間、RPO 1 時間」

→ Step 1 で RTO 4h / RPO 1h の SLA 要件を確認
→ Step 8a で Active-Passive 戦略を選定
→ Step 8b でレプリケーション対象を定義
  - データ: S3 Cross-Region Replication / Azure GRS
  - メタデータ: Unity Catalog の API 同期（1 時間間隔）
  - コード: Git Repos で自動同期
  - 設定: Terraform による再構築
→ Step 8c で監視・アラート設計
→ Step 8d で DR テスト計画（四半期ごとの Failover テスト）を策定
→ DR 設計書 + テスト計画書を出力
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| Customer-Managed VPC でクラスタが起動しない | DNS ホスト名・DNS 解決が無効 | VPC 設定で両方を有効化する。AWS の最も多い見落としポイント |
| PrivateLink 接続がタイムアウトする | Private DNS Zone の設定不備 | Hub VNet / VPC に適切な DNS Zone を作成し、VNet リンクを設定する |
| VNet Injection でサブネットエラーが発生する | デリゲーション未設定またはサイズ不足 | `Microsoft.Databricks/workspaces` デリゲーションを設定し、/26 以上を確保する |
| S3 External Location で SSL エラーが発生する | バケット名にドット（.）を使用 | ドットを含まないバケット名に移行する。Delta Sharing で問題が発生する |
| CMK 暗号化の設定に失敗する（Azure） | Key Vault のリージョンまたはテナントが不一致 | ワークスペースと同一リージョン・同一 Entra ID テナントに Key Vault を配置する |
| Terraform apply が権限エラーで失敗する | Service Principal / IAM Role の権限不足 | Databricks Provider の必要権限を確認し、最小権限で付与する |
| DR フェイルオーバー後にメタデータが古い | Unity Catalog メタストアの同期が非リアルタイム | メタストア同期の頻度を RTO/RPO に合わせて調整する。API / Terraform による自動同期を構築する |
| Spot Instance が頻繁に回収されて処理が失敗する | 可用性の低いインスタンスタイプを使用 | デコミッショニングを有効化し、複数のインスタンスタイプをフォールバックに設定する |
| Azure Firewall でクラスタが通信できない | Databricks の必須 FQDN がブロックされている | Databricks が公開する必須アウトバウンド先をファイアウォールルールに追加する |
| マルチワークスペースで権限が同期されない | ワークスペース間で個別に権限を設定している | Unity Catalog のカタログ / スキーマレベルで権限を一元管理する |
| Serverless Compute から顧客リソースに接続できない | NCC / ネットワークポリシー未設定 | Network Connectivity Configuration で Private Endpoint を作成し、ファイアウォールを設定する |
| CI/CD パイプラインで認証が切れる | Service Principal のシークレット有効期限切れ | Workload Identity Federation に移行し、シークレット管理を不要にする |

---

## References

| ファイル | 内容 |
|:---|:---|
| [aws-architecture-patterns.md](references/aws-architecture-patterns.md) | AWS デプロイパターン集（VPC 設計、PrivateLink、IAM、S3 連携） |
| [azure-architecture-patterns.md](references/azure-architecture-patterns.md) | Azure デプロイパターン集（VNet Injection、Private Link、Entra ID、ADLS Gen2） |
| [cloud-comparison-matrix.md](references/cloud-comparison-matrix.md) | AWS vs Azure 機能差分表（ネットワーク、セキュリティ、コスト、IaC） |
| [networking-reference.md](references/networking-reference.md) | ネットワーク設計リファレンス（Hub-Spoke 構成図、PrivateLink 接続パターン） |
| [security-checklist.md](references/security-checklist.md) | セキュリティ設計チェックリスト（暗号化、ネットワーク、ID 管理、コンプライアンス） |
| [terraform-modules.md](references/terraform-modules.md) | Terraform モジュール構成テンプレート（AWS/Azure 両対応、DABs 連携） |

---

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **databricks** | 後続 | クラウドインフラの上に構築する Databricks プラットフォーム機能の設計 |
| **delta-lake** | 後続 | ストレージ設計の上に構築する Delta Lake テーブル設計 |
| **unity-catalog** | 後続 | ワークスペース戦略の上に構築する Unity Catalog ガバナンス設計 |
| **diagram** | 連携 | 設計したアーキテクチャの draw.io 構成図を生成 |
| **data-arch** | 前工程 | データアーキテクチャ全体の選定・設計（レイクハウス vs DWH 等） |
| **review** | 検証 | 設計成果物の Well-Architected レビュー |
