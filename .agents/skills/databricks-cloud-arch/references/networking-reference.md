# Networking Reference — ネットワーク設計リファレンス

## 1. Hub-Spoke トポロジ設計

### AWS: Transit VPC + Workspace VPC

```
                        ┌─────────────────────┐
                        │   Control Plane      │
                        │   (Databricks AWS)   │
                        └──────────┬──────────┘
                                   │ PrivateLink
                                   │ (Back-end)
  ┌────────────────────────────────┴──────────────────────────────────┐
  │                      Transit VPC (Hub)                            │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
  │  │ Inbound      │  │ NAT Gateway  │  │ VPN / Direct │           │
  │  │ PrivateLink  │  │              │  │ Connect      │           │
  │  │ Endpoint     │  │              │  │              │           │
  │  └──────────────┘  └──────────────┘  └──────┬───────┘           │
  └──────────┬─────────────────┬────────────────┘──────────────────┘
             │ VPC Peering     │ VPC Peering     │ VPN
             │ / TGW           │ / TGW           │
  ┌──────────┴──────┐ ┌───────┴───────┐ ┌───────┴───────┐
  │ Workspace VPC   │ │ Workspace VPC │ │ On-premises   │
  │ (Dev)           │ │ (STG)         │ │ Network       │
  │ ┌────┐ ┌────┐  │ │               │ │               │
  │ │SubA│ │SubB│  │ │               │ │               │
  │ └────┘ └────┘  │ │               │ │               │
  └─────────────────┘ └───────────────┘ └───────────────┘
```

### Azure: Hub VNet + Spoke VNet

```
              ┌────────────────────────────────────────┐
              │           Hub VNet                      │
              │  ┌────────────┐  ┌────────────────┐   │
              │  │ Azure FW   │  │ ExpressRoute / │   │
              │  │            │  │ VPN Gateway    │   │
              │  └────────────┘  └───────┬────────┘   │
              │  ┌────────────┐          │            │
              │  │Private DNS │  ┌───────┴────────┐   │
              │  │Zone        │  │ Azure Bastion  │   │
              │  └────────────┘  └────────────────┘   │
              └──────────┬─────────────────────────────┘
                         │ VNet Peering
           ┌─────────────┼─────────────┐
           │             │             │
  ┌────────┴───────┐ ┌───┴──────────┐ ┌┴──────────────┐
  │ Spoke VNet     │ │ Spoke VNet   │ │ Spoke VNet    │
  │ (Dev WS)       │ │ (STG WS)     │ │ (PRD WS)      │
  │ ┌─────┐┌─────┐│ │              │ │               │
  │ │Pub  ││Priv ││ │              │ │               │
  │ │Sub  ││Sub  ││ │              │ │               │
  │ └─────┘└─────┘│ │              │ │               │
  └────────────────┘ └──────────────┘ └───────────────┘
```

---

## 2. PrivateLink 構成パターン

### 共通: 3 タイプの PrivateLink

| # | タイプ | 方向 | 目的 |
|:---|:---|:---|:---|
| 1 | **Front-end（Inbound）** | ユーザー → Workspace | Web UI・REST API をプライベートに |
| 2 | **Back-end（Classic Compute）** | クラスタ → Control Plane | クラスタ通信をプライベートに |
| 3 | **Outbound（Serverless）** | Serverless → 顧客リソース | サーバーレスからのデータアクセスをプライベートに |

### 本番環境での推奨設定

| タイプ | 推奨 | 理由 |
|:---|:---|:---|
| Front-end | **必須** | ユーザーアクセスをプライベート化 |
| Back-end | **必須** | クラスタ通信をプライベート化 |
| Outbound | **強く推奨** | サーバーレス環境のセキュリティ確保 |

### AWS PrivateLink 構成の流れ

1. Transit VPC に VPC Endpoint を作成（Front-end）
2. Workspace VPC に VPC Endpoint を作成（Back-end）
3. Databricks Account Console で PrivateLink 設定を有効化
4. ワークスペースを PrivateLink 対応で再作成（または更新）
5. DNS レコードを設定（Private Hosted Zone）

### Azure Private Link 構成の流れ

1. Hub VNet に Private Endpoint を作成（Front-end）
2. Spoke VNet に Private Endpoint を作成（Back-end）
3. Private DNS Zone を作成しリンク
4. ワークスペースの Public Network Access を無効化
5. Serverless 用に NCC（Network Connectivity Configuration）を設定

---

## 3. サブネット設計ガイド

### AWS サブネット設計

| 項目 | 推奨値 | 備考 |
|:---|:---|:---|
| サブネット数 | 2 | 異なる AZ に配置推奨 |
| タイプ | プライベート | パブリック IP なし |
| CIDR（小規模） | /24（254 IP） | 〜120 ノード |
| CIDR（中規模） | /20（4,094 IP） | 〜2,000 ノード |
| CIDR（大規模） | /17（32,766 IP） | 〜16,000 ノード |
| DNS | `enableDnsHostnames` = true | **見落とし注意** |
| DNS | `enableDnsSupport` = true | **見落とし注意** |

### Azure サブネット設計

| 項目 | 推奨値 | 備考 |
|:---|:---|:---|
| サブネット数 | 2（public + private） | 名称は任意 |
| 最小 CIDR | /26（64 IP） | 最小構成 |
| 推奨 CIDR | /24 以上 | 本番環境 |
| デリゲーション | `Microsoft.Databricks/workspaces` | 必須 |
| NSG | ワークスペースごとに固有 | 推奨 |

### IP アドレス計算

各クラスタノードは 2 つの IP アドレスを消費する（1 ノードにつき public + private サブネットで 1 つずつ）。
必要な IP 数 = 最大同時ノード数 × 2 + 予備（20%）

---

## 4. DNS 設計

### AWS での DNS 設計

| コンポーネント | 設定 |
|:---|:---|
| VPC DNS | `enableDnsHostnames` = true, `enableDnsSupport` = true |
| Private Hosted Zone | Databricks ワークスペースドメインの解決 |
| Route 53 Resolver | ハイブリッド DNS（オンプレミス連携） |

### Azure での DNS 設計

| コンポーネント | 設定 |
|:---|:---|
| Private DNS Zone | `privatelink.azuredatabricks.net` |
| VNet リンク | Hub VNet と各 Spoke VNet にリンク |
| DNS Forwarder | オンプレミス DNS との連携 |

---

## 5. ファイアウォール設計

### AWS: アウトバウンド制御

```
  Workspace VPC
  └── Private Subnet
       └── Route Table
            └── 0.0.0.0/0 → NAT Gateway
                              └── (Optional) Network Firewall
```

- Security Group: インバウンドは同一 SG 内のみ許可
- NAT Gateway: アウトバウンドインターネットアクセス
- Network Firewall: FQDN ベースのフィルタリング

### Azure: アウトバウンド制御

```
  Spoke VNet (Databricks)
  └── DB Subnet
       └── UDR (User Defined Route)
            └── 0.0.0.0/0 → Azure Firewall (Hub VNet)
```

- NSG: Databricks 自動管理ルール + カスタムルール
- UDR: Azure Firewall 経由にルーティング
- Azure Firewall: FQDN ベースのアプリケーションルール

### Databricks 必須アウトバウンド先

Databricks クラスタが正常に動作するために、以下の接続先への通信を許可する必要がある:
- Databricks Control Plane のエンドポイント
- クラウドプロバイダのメタデータサービス
- ストレージサービス（S3 / ADLS Gen2）
- パッケージリポジトリ（必要に応じて）

具体的な FQDN リストはリージョンごとに異なるため、Databricks ドキュメントを参照すること。

---

## 6. Serverless ネットワークセキュリティ

### Network Connectivity Configuration（NCC）

- アカウントレベルのリージョナル構成
- Private Endpoint の作成とファイアウォール有効化を大規模に管理
- 安定した IP アドレスリストを提供

### ネットワークポリシー

- サーバーレスコンピュートが接続できるリソースを制御
- NCC と組み合わせてきめ細かいアクセス制御

### Outbound PrivateLink（サーバーレス）

| クラウド | 接続先 | 設定 |
|:---|:---|:---|
| AWS | S3、RDS 等 | NCC で Private Endpoint を構成 |
| Azure | ADLS Gen2、Key Vault 等 | NCC で Private Endpoint を構成 |

---

## 7. ネットワーク設計判断フロー

```
1. 環境は？
   ├── PoC・開発 → マネージド VPC/VNet（デフォルト）
   └── 本番 → Customer-Managed VPC / VNet Injection
                │
2. PrivateLink は必要？
   ├── はい → 全 3 タイプを設計
   └── いいえ → SCC のみ（非推奨：本番では PrivateLink 推奨）
                │
3. オンプレミス接続は？
   ├── あり → Hub-Spoke + VPN/ExpressRoute/DirectConnect
   └── なし → Hub-Spoke（ファイアウォール + DNS のみ）
                │
4. 複数ワークスペースは？
   ├── あり → Transit VPC/Hub VNet + 各 Spoke
   └── 1 つ → 単一 VPC/VNet + PrivateLink
                │
5. サーバーレスは使用？
   ├── はり → NCC + Outbound PrivateLink を設計
   └── なし → Classic Compute のみの設計
```
