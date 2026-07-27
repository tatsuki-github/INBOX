# カタログ戦略パターンの詳細と判断基準

Unity Catalog の `catalog.schema.object` 3 レベル名前空間を最適に設計するための
パターン集と判断基準を提供する。

---

## 1. 3 つのカタログ戦略パターン

### パターン 1: 環境別カタログ（Environment-Based）

最もシンプルな戦略。開発ライフサイクルの環境ごとにカタログを分割する。

```
metastore
├── dev              # 開発環境
│   ├── sales           # スキーマ: 営業ドメイン
│   ├── marketing       # スキーマ: マーケティングドメイン
│   └── sandbox         # スキーマ: 個人実験用
├── staging          # ステージング環境
│   ├── sales
│   └── marketing
└── prod             # 本番環境
    ├── sales
    └── marketing
```

| 側面 | 評価 |
|:---|:---|
| **メリット** | シンプル、環境分離が明確、権限管理が容易 |
| **デメリット** | ドメイン横断のアクセス制御が煩雑、大規模組織では1カタログが巨大化 |
| **適用条件** | チーム数 5 以下、テーブル数 1,000 以下、ドメイン境界が曖昧 |
| **進化パス** | スキーマ内をドメインで分離 → 必要に応じてハイブリッドへ |

### パターン 2: ドメイン別カタログ（Domain-Based）

ビジネスドメインごとにカタログを分割する。Data Mesh との親和性が高い。

```
metastore
├── sales            # 営業ドメイン
│   ├── raw             # Raw データ（Bronze 相当）
│   ├── curated         # クレンジング済み（Silver 相当）
│   └── analytics       # 分析用データマート（Gold 相当）
├── marketing        # マーケティングドメイン
│   ├── raw
│   ├── curated
│   └── analytics
├── finance          # 財務ドメイン
│   ├── raw
│   ├── curated
│   └── analytics
└── shared           # 共有データ（マスター、参照データ）
    └── master_data
```

| 側面 | 評価 |
|:---|:---|
| **メリット** | ドメインオーナーシップが明確、Data Mesh 準拠、ドメイン単位の権限管理 |
| **デメリット** | 環境分離はワークスペースバインディングで対応が必要、初期設計の負荷が高い |
| **適用条件** | 明確なドメイン境界、ドメインオーナーシップが確立、Data Mesh 志向 |
| **進化パス** | Delta Sharing でドメイン間データプロダクト共有 |

### パターン 3: ハイブリッド（推奨デフォルト）

環境分離とドメイン分離を組み合わせる。最も柔軟で拡張性が高い。

#### バリエーション A: 環境 × ドメインのフラット構造

```
metastore
├── dev_sales           # 開発 × 営業
├── dev_marketing       # 開発 × マーケティング
├── prod_sales          # 本番 × 営業
├── prod_marketing      # 本番 × マーケティング
└── shared              # 環境横断の共有データ
    └── master_data
```

#### バリエーション B: 環境トップ × ドメインスキーマ

```
metastore
├── dev
│   ├── sales           # スキーマ: 営業ドメイン
│   ├── marketing       # スキーマ: マーケティングドメイン
│   └── sandbox         # スキーマ: 実験用
├── prod
│   ├── sales
│   ├── marketing
│   └── shared_views    # 共有ビュー
└── shared
    └── master_data
```

| 側面 | 評価 |
|:---|:---|
| **メリット** | 環境分離とドメイン分離の両立、段階的に拡張可能 |
| **デメリット** | カタログ数が増えやすい（バリエーション A）、命名規則の徹底が必要 |
| **適用条件** | 中〜大規模組織、環境分離とドメイン分離の両方が必要 |
| **進化パス** | ドメインの成熟度に応じてカタログの分割/統合を調整 |

---

## 2. 判断フロー

```
Q1: ドメイン境界は明確か？
  ├── いいえ → パターン 1（環境別）で開始
  └── はい
       ├── Q2: 環境分離の厳密さは？
       │    ├── 高い（規制産業、金融等） → パターン 3A（環境×ドメインフラット）
       │    └── 中程度 → パターン 3B（環境トップ×ドメインスキーマ）
       └── Q3: Data Mesh を導入するか？
            ├── はい → パターン 2（ドメイン別）
            └── いいえ → パターン 3B（環境トップ×ドメインスキーマ）
```

### 判断に影響する要因

| 要因 | パターン 1 | パターン 2 | パターン 3 |
|:---|:---|:---|:---|
| 組織規模 | 小〜中 | 中〜大 | 中〜大 |
| チーム数 | 1-5 | 5+ | 3+ |
| ドメイン境界 | 曖昧 | 明確 | やや明確 |
| 環境分離要件 | 標準 | ワークスペースで対応 | 厳密 |
| Data Mesh | 不要 | 必要 | 将来的に検討 |
| 初期設計コスト | 低 | 高 | 中 |

---

## 3. スキーマ設計のベストプラクティス

### 3.1 Medallion Architecture との組み合わせ

```
prod (catalog)
├── bronze_salesforce      # Raw: Salesforce からの取り込み
├── bronze_sap             # Raw: SAP からの取り込み
├── bronze_ga4             # Raw: Google Analytics 4 のイベント
├── silver_customers       # Cleansed: 顧客統合テーブル
├── silver_orders          # Cleansed: 注文データ
├── gold_analytics         # Mart: 分析用データマート
├── gold_reporting         # Mart: レポーティング用
└── ml_features            # ML: 特徴量テーブル
```

### 3.2 命名規則テンプレート

| 対象 | パターン | 例 |
|:---|:---|:---|
| カタログ | `{env}` or `{env}_{domain}` | `prod`, `dev_sales` |
| スキーマ（Medallion） | `{layer}_{source}` | `bronze_salesforce` |
| スキーマ（ドメイン） | `{domain}` or `{subdomain}` | `sales`, `marketing` |
| スキーマ（用途） | `{purpose}` | `analytics`, `ml_features`, `sandbox` |
| テーブル | `{entity}` (snake_case) | `customers`, `order_items` |
| ビュー | `v_{entity}` | `v_daily_sales_summary` |
| UDF | `fn_{purpose}` | `fn_mask_email` |
| Volume | `vol_{purpose}` | `vol_model_artifacts` |

### 3.3 shared カタログの設計

環境横断で共有されるデータは `shared` カタログに配置する:

```
shared (catalog)
├── master_data           # マスターデータ（顧客、商品、地域）
│   ├── customers
│   ├── products
│   └── regions
├── reference_data        # 参照データ（コードテーブル、カレンダー）
│   ├── country_codes
│   └── fiscal_calendar
└── data_quality          # データ品質メトリクス
    └── quality_scores
```

---

## 4. アンチパターン

| アンチパターン | 問題点 | 修正方法 |
|:---|:---|:---|
| **プロジェクトごとにカタログ作成** | カタログが爆発的に増加（100+）、管理不能 | 環境 or ドメインでカタログを切り、プロジェクトはスキーマで分離 |
| **1 スキーマにすべて格納** | テーブルの発見性が壊滅、権限の粒度が粗い | Medallion / ドメイン / 用途でスキーマを分離 |
| **個人ユーザーをオーナーに** | 退職・異動時にオーナー不在 | グループをオーナーに設定 |
| **Dev と Prod を同一カタログ** | 誤操作で Prod データを破損するリスク | カタログレベルで環境を分離 |
| **命名規則なし** | 一貫性のない名前が乱立、検索困難 | プロジェクト開始時に命名規則を策定・合意 |
| **過剰なカタログ階層** | `env_domain_team_project` のような深い命名 | 最大 2 要素（環境 × ドメイン）に抑える |

---

## 5. ワークスペースバインディング

特定のカタログを特定のワークスペースに限定する機能:

```
Metastore (ap-northeast-1)
├── dev-workspace      → dev catalog (READ_WRITE)
│                        prod catalog (なし = アクセス不可)
├── prod-workspace     → prod catalog (READ_WRITE)
│                        dev catalog (なし)
└── analytics-workspace → prod catalog (READ_ONLY)
                          shared catalog (READ_ONLY)
```

**設計指針**:
- Prod カタログは Prod ワークスペースに READ_WRITE でバインド
- Analytics ワークスペースには Prod カタログを READ_ONLY でバインド
- Dev カタログは Dev ワークスペースのみにバインド
- shared カタログは必要なワークスペースすべてに READ_ONLY でバインド

---

## 6. Data Mesh + Unity Catalog の実装パターン

### 6.1 フェデレーテッドガバナンス構造

```
中央プラットフォームチーム:
  ├── Metastore 管理
  ├── Storage Credential / External Location 管理
  ├── ABAC ポリシー（Governed Tags）の定義
  ├── 命名規則・セキュリティ標準の策定
  └── Terraform モジュールの提供

ドメインチーム（自律管理）:
  ├── 自ドメインのカタログ/スキーマ管理
  ├── テーブル・ビューの作成と品質管理
  ├── ドメイン固有の権限管理
  ├── Delta Sharing でデータプロダクトを公開
  └── Expectations でデータ品質 SLA を定義
```

### 6.2 Data Mesh 4 原則の Unity Catalog マッピング

| 原則 | Unity Catalog 実装 |
|:---|:---|
| **ドメインオーナーシップ** | ドメイン別カタログ + ドメインオーナーグループ |
| **データ・アズ・ア・プロダクト** | Gold テーブル + Delta Sharing + メタデータ（コメント・タグ） |
| **セルフサービスインフラ** | Terraform モジュール + 標準化されたスキーマテンプレート |
| **フェデレーテッドガバナンス** | 中央の ABAC + ドメイン自律の GRANT/REVOKE |
