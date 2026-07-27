# AWS Architecture Patterns — Databricks on AWS デプロイパターン集

## 1. デプロイアーキテクチャ概要

Databricks on AWS は **Control Plane** と **Compute Plane（Data Plane）** の 2 層アーキテクチャで構成される。

### Control Plane（Databricks 管理）
- Databricks の AWS アカウント内で運用されるバックエンドサービス群
- Web アプリケーション、REST API、ジョブスケジューラ、ノートブック管理、クラスタマネージャを含む
- ノートブックコマンド・ワークスペース設定は Control Plane に保存され、保存時に暗号化

### Classic Compute Plane（顧客管理）
- 顧客の AWS アカウント内にデプロイされるコンピュートリソース
- Apache Spark クラスタが顧客の VPC 内で稼働
- データ処理は顧客アカウント内で完結（Databricks アカウントにデータが送信されることはない）

### Serverless Compute Plane（Databricks 管理）
- Databricks アカウント内で稼働するサーバーレスコンピュート
- SQL Warehouse、ノートブック、ジョブ等が対象
- Control Plane との通信はクラウドバックボーン経由（パブリックインターネット非経由）

---

## 2. VPC 設計パターン

### パターン A: Databricks マネージド VPC（PoC・開発向け）

```
  Databricks が VPC を自動作成・管理
  ┌──────────────────────┐
  │ Managed VPC          │
  │ ├── Subnet A         │
  │ └── Subnet B         │
  │     (Databricks 管理) │
  └──────────────────────┘
```

- **利点**: 設定不要、即座に開始可能
- **制限**: PrivateLink 非対応、アウトバウンド制御が限定的
- **推奨**: PoC・初期開発のみ

### パターン B: Customer-Managed VPC（本番環境推奨）

```
  顧客が VPC を作成・管理
  ┌──────────────────────┐
  │ Customer-Managed VPC │
  │ ├── Private Subnet A │
  │ ├── Private Subnet B │
  │ ├── Security Group   │
  │ └── NAT Gateway      │
  └──────────────────────┘
```

- **要件**:
  - DNS ホスト名・DNS 解決が有効であること（**最も多い見落とし**）
  - 2 つの専用プライベートサブネット
  - セキュリティグループの適切な設定
- **利点**: 完全なネットワーク制御、PrivateLink 対応
- **推奨**: すべての本番環境

### Customer-Managed VPC のサブネット要件

| 項目 | 要件 |
|:---|:---|
| サブネット数 | 2（異なる AZ に配置推奨） |
| サブネットタイプ | プライベート（パブリック IP なし） |
| CIDR 範囲 | /17〜/26 推奨（ワーカーノード数に応じて） |
| DNS | `enableDnsHostnames` = true, `enableDnsSupport` = true |
| 重複不可 | Databricks VPC の CIDR と重複しないこと |

---

## 3. PrivateLink 構成パターン

### 3 タイプの PrivateLink

| タイプ | VPC Endpoint 配置 | 接続先 |
|:---|:---|:---|
| **Front-end（Inbound）** | Transit VPC | Workspace Web UI / REST API |
| **Back-end（Classic Compute）** | Workspace VPC | Control Plane REST API / SCC リレー |
| **Outbound（Serverless）** | Databricks アカウント → 顧客リソース | S3、RDS 等 |

### 推奨構成: Transit VPC パターン

```
                    ┌─────────────────┐
                    │  Control Plane  │
                    │  (Databricks    │
                    │   AWS Account)  │
                    └────────┬────────┘
                             │ PrivateLink (Back-end)
                    ┌────────┴────────┐
  ユーザー ────→    │  Transit VPC    │
  (PrivateLink      │  (Inbound EP)   │
   Front-end)       └────────┬────────┘
                             │ VPC Peering / Transit GW
                    ┌────────┴────────┐
                    │ Workspace VPC   │
                    │ (Customer-      │
                    │  Managed)       │
                    │ ┌─────────────┐ │
                    │ │ Private     │ │
                    │ │ Subnet A    │ │──→ S3 (VPC Endpoint)
                    │ │ Private     │ │
                    │ │ Subnet B    │ │──→ Other AWS Services
                    │ └─────────────┘ │
                    └─────────────────┘
```

### VPC Peering vs Transit Gateway

| 項目 | VPC Peering | Transit Gateway |
|:---|:---|:---|
| 接続数 | 1:1 | ハブ型（多対多） |
| 複雑度 | 低い | 中〜高い |
| コスト | データ転送のみ | アタッチメント + データ転送 |
| 推奨ケース | ワークスペース数が少ない | 複数 VPC を接続する大規模構成 |

---

## 4. Secure Cluster Connectivity（SCC）

新規ワークスペースではデフォルトで有効:
- 顧客 VPC にオープンポートが存在しない
- クラスタノードにパブリック IP が付与されない
- HTTPS（ポート 443）のセキュアトンネルで Control Plane に接続

---

## 5. S3 連携パターン

### Unity Catalog によるストレージアクセス管理

1. **Storage Credential**: IAM Cross-Account Role を設定
   - Databricks の AWS アカウントとの信頼関係
   - `sts:ExternalId` 条件キーでセキュリティ強化
2. **External Location**: Storage Credential + S3 パスの組み合わせ
   - 外部テーブル、外部ボリューム、マネージドストレージに使用

### S3 VPC Endpoint（Gateway 型）

- VPC 内から S3 へのプライベートアクセスを実現
- データがパブリックインターネットを経由しない
- ルートテーブルに自動追加

### ベストプラクティス

- S3 バケット名にドット（`.`）を使わない
- CloudFormation Quickstart テンプレートの活用
- 複数メタストアから同一パスへのアクセスを避ける
- Instance Profile ではなく Unity Catalog Storage Credential を使用（レガシー移行）

---

## 6. IAM 設計パターン

### Cross-Account Role（推奨）

```
Databricks AWS Account ──trust──→ Customer AWS Account
                                    └── IAM Role
                                         └── S3 Access Policy
```

- Principal に Databricks の ARN を指定
- `sts:ExternalId` でセキュリティ強化
- ロールチェーンではなく直接のロール引き受けを使用

### Service Control Policies（SCPs）

組織レベルで以下を強制:
- 特定リージョン以外でのリソース作成を禁止
- 暗号化されていないストレージの作成を禁止
- パブリック IP の付与を禁止

---

## 7. コスト最適化パターン

| 手法 | 効果 | 注意点 |
|:---|:---|:---|
| **Spot Instance** | 最大 90% 削減 | 回収リスクあり → デコミッショニング有効化 |
| **Reserved Capacity** | 20-60% 削減 | 予測可能なワークロードに限定 |
| **Savings Plans** | 汎用的な割引 | コンピュートの柔軟性を維持 |
| **Serverless SQL Warehouse** | 起動コスト削減 | DBU 単価は高いがアイドルコスト削減 |
| **Photon** | 処理時間 2-8 倍高速化 | SQL ワークロードで最も効果的 |
| **クラスタプール** | 起動時間短縮 | 事前にインスタンスを確保 |
| **オートスケーリング** | 需要に応じた調整 | min/max ワーカーを適切に設定 |

---

## 8. AWS Glue Data Catalog 連携

### Lakehouse Federation

Unity Catalog の Catalog Federation 機能で Glue Data Catalog と連携:
1. Connection オブジェクトを作成（Service Credential 指定）
2. 一時的なセッション資格情報で Glue クライアントを作成
3. テーブル・スキーマのメタデータを取得
4. データへの一時的なアクセス資格情報を取得
5. クエリ実行

### ネットワーク要件
- データプレーンと Glue Data Catalog 間にプライベート接続が必要
- Interface VPC Endpoint を使用

---

## 9. セキュリティ設計チェックリスト（AWS）

| カテゴリ | 項目 | 推奨 |
|:---|:---|:---|
| ネットワーク | Customer-Managed VPC | 本番必須 |
| ネットワーク | PrivateLink（全 3 タイプ） | 本番必須 |
| ネットワーク | SCC 有効化 | 全環境で有効 |
| 暗号化 | S3 SSE-KMS（CMK） | 規制環境で必須 |
| 暗号化 | EBS CMK | 規制環境で必須 |
| 暗号化 | Control Plane CMK | 規制環境で推奨 |
| ID | Cross-Account Role（Unity Catalog） | 全環境で推奨 |
| ID | SCPs | 組織レベルで推奨 |
| 監視 | CloudTrail | 全環境で有効 |
| 監視 | VPC Flow Logs | 本番で推奨 |
| コンプライアンス | Compliance Security Profile | HIPAA 等で必須 |
