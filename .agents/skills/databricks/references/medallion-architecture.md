# Medallion Architecture 設計パターン

> Bronze/Silver/Gold の各レイヤーの設計原則、実装パターン、コード例をまとめたリファレンス。

---

## 1. アーキテクチャ全体像

```
Raw Sources          Bronze              Silver              Gold
+-----------+    +------------+    +-------------+    +-----------+
| Files     |--->| Raw Data   |--->| Validated   |--->| Business  |
| Kafka     |    | Minimal    |    | Cleansed    |    | Aggregated|
| APIs      |    | Transform  |    | Normalized  |    | Optimized |
| Databases |    | Append-only|    | Deduplicated|    | Star/Snow |
+-----------+    +------------+    +-------------+    +-----------+
                   STRING 型中心     品質チェック済      消費最適化
                   スキーマ変更耐性   ストリーミング読込   プロジェクト別
```

---

## 2. Bronze Layer（生データ層）

### 設計原則

| 原則 | 詳細 |
|:---|:---|
| **忠実な保存** | ソースデータをそのまま保存する（Single Source of Truth） |
| **型安全より柔軟性** | フィールドを `STRING`, `VARIANT`, `BINARY` で保存 |
| **イミュータブル** | 一度書き込んだデータは変更しない（Append-only） |
| **メタデータ付与** | 取り込み時刻、ソース情報、ファイルパスを付加 |
| **処理を最小限に** | クレンジングやバリデーションは行わない |

### 禁止事項

- データのフィルタリングやクレンジング
- 型変換（ソースの型をそのまま保持）
- ビジネスロジックの適用
- レコードの削除や更新（Append-only を厳守）

### コード例（DLT - SQL）

```sql
-- Auto Loader による Bronze テーブル
CREATE OR REFRESH STREAMING TABLE bronze_orders
COMMENT "販売注文の生データ（ソースからの忠実な取り込み）"
TBLPROPERTIES ("quality" = "bronze")
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  _metadata.file_modification_time AS _file_modified_at,
  current_timestamp() AS _ingested_at
FROM cloud_files(
  "/mnt/landing/orders/",
  "json",
  map("cloudFiles.inferColumnTypes", "false")
);
```

### コード例（DLT - Python）

```python
import dlt
from pyspark.sql.functions import current_timestamp, input_file_name

@dlt.table(
    name="bronze_orders",
    comment="販売注文の生データ",
    table_properties={"quality": "bronze"}
)
def bronze_orders():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.inferColumnTypes", "false")
        .option("cloudFiles.schemaLocation", "/mnt/schema/orders/")
        .load("/mnt/landing/orders/")
        .withColumn("_source_file", input_file_name())
        .withColumn("_ingested_at", current_timestamp())
    )
```

---

## 3. Silver Layer（検証済みデータ層）

### 設計原則

| 原則 | 詳細 |
|:---|:---|
| **品質担保** | 型変換、NULL チェック、重複排除を実施 |
| **正規化** | エンティティ単位でテーブルを設計 |
| **ストリーミング読み込み** | Bronze からのデータ取得はストリーミングを推奨 |
| **非集約** | 各レコードの検証済み表現を保持（集約は Gold で行う） |
| **エラー隔離** | 不正レコードは Dead-Letter テーブルに退避 |

### 禁止事項

- 外部ソースからの直接インジェスション（必ず Bronze を経由）
- ビジネスレベルの集約処理
- プロジェクト固有のロジック適用

### コード例（DLT - SQL）

```sql
-- Silver テーブル（品質チェック + 型変換）
CREATE OR REFRESH STREAMING TABLE silver_orders (
  CONSTRAINT valid_order_id
    EXPECT (order_id IS NOT NULL)
    ON VIOLATION DROP ROW,
  CONSTRAINT valid_amount
    EXPECT (CAST(amount AS DOUBLE) > 0)
    ON VIOLATION DROP ROW,
  CONSTRAINT valid_date
    EXPECT (order_date IS NOT NULL AND order_date >= '2020-01-01')
    ON VIOLATION DROP ROW
)
COMMENT "品質検証済みの販売注文データ"
TBLPROPERTIES ("quality" = "silver")
AS SELECT
  CAST(order_id AS BIGINT) AS order_id,
  CAST(customer_id AS BIGINT) AS customer_id,
  CAST(amount AS DOUBLE) AS amount,
  CAST(order_date AS DATE) AS order_date,
  CAST(product_id AS BIGINT) AS product_id,
  CAST(quantity AS INT) AS quantity,
  _ingested_at
FROM STREAM(LIVE.bronze_orders);
```

### Dead-Letter パターン

```sql
-- 品質違反レコードを隔離するテーブル
CREATE OR REFRESH STREAMING TABLE dead_letter_orders
COMMENT "品質チェックで除外された注文レコード"
TBLPROPERTIES ("quality" = "dead_letter")
AS SELECT
  *,
  current_timestamp() AS _quarantined_at,
  CASE
    WHEN order_id IS NULL THEN 'missing_order_id'
    WHEN CAST(amount AS DOUBLE) <= 0 THEN 'invalid_amount'
    WHEN order_date IS NULL THEN 'missing_date'
    ELSE 'unknown'
  END AS _rejection_reason
FROM STREAM(LIVE.bronze_orders)
WHERE order_id IS NULL
   OR CAST(amount AS DOUBLE) <= 0
   OR order_date IS NULL;
```

---

## 4. Gold Layer（ビジネス活用層）

### 設計原則

| 原則 | 詳細 |
|:---|:---|
| **消費最適化** | 読み取り性能を最優先で設計 |
| **非正規化** | 結合を最小化した Star/Snowflake Schema |
| **プロジェクト別** | ビジネスドメインごとにデータベースを分離 |
| **集約** | ビジネスメトリクスの事前計算 |

### コード例（DLT - SQL）

```sql
-- Gold テーブル（日次売上集計）
CREATE OR REFRESH MATERIALIZED VIEW gold_daily_revenue
COMMENT "日次売上レポート"
TBLPROPERTIES ("quality" = "gold")
AS SELECT
  order_date,
  COUNT(DISTINCT customer_id) AS unique_customers,
  COUNT(*) AS order_count,
  SUM(amount) AS total_revenue,
  AVG(amount) AS avg_order_value,
  SUM(quantity) AS total_quantity
FROM LIVE.silver_orders
GROUP BY order_date;

-- Gold テーブル（顧客 360 ビュー）
CREATE OR REFRESH MATERIALIZED VIEW gold_customer_360
COMMENT "顧客の購買行動サマリー"
TBLPROPERTIES ("quality" = "gold")
AS SELECT
  customer_id,
  COUNT(*) AS lifetime_orders,
  SUM(amount) AS lifetime_value,
  AVG(amount) AS avg_order_value,
  MIN(order_date) AS first_order_date,
  MAX(order_date) AS last_order_date,
  DATEDIFF(MAX(order_date), MIN(order_date)) AS customer_tenure_days
FROM LIVE.silver_orders
GROUP BY customer_id;
```

---

## 5. レイヤー間のデータフロー設計

### ストリーミング vs バッチの選定基準

| 基準 | ストリーミング推奨 | バッチ推奨 |
|:---|:---|:---|
| データ到着パターン | 継続的に到着 | 定時に一括到着 |
| レイテンシ要件 | 分単位以下 | 時間単位で許容 |
| データ量 | 大量・高頻度 | 小量・低頻度 |
| Bronze → Silver | 推奨 | 小規模データセットでは可 |
| Silver → Gold | 集約パターンに依存 | Materialized View で代替可 |

### Liquid Clustering の適用

```sql
-- Silver テーブルに Liquid Clustering を適用
ALTER TABLE silver_orders
CLUSTER BY (order_date, customer_id);

-- Gold テーブルに Liquid Clustering を適用
ALTER TABLE gold_daily_revenue
CLUSTER BY (order_date);
```

Liquid Clustering は手動パーティション設計を不要にし、クエリパターンに応じて自動的にデータ配置を最適化する。Delta Lake 3.0 以降で利用可能。

---

## 6. テーブル設計のベストプラクティス

### 命名規則

```
{layer}_{domain}_{entity}

例:
  bronze_sales_orders        # Bronze: 販売注文
  silver_sales_orders        # Silver: 検証済み販売注文
  gold_sales_daily_revenue   # Gold: 日次売上集計
  dead_letter_sales_orders   # Dead-Letter: 除外された注文
```

### メタデータカラムの標準化

| カラム名 | レイヤー | 説明 |
|:---|:---|:---|
| `_source_file` | Bronze | ソースファイルのパス |
| `_ingested_at` | Bronze | 取り込み日時 |
| `_file_modified_at` | Bronze | ソースファイルの最終更新日時 |
| `_quarantined_at` | Dead-Letter | 隔離日時 |
| `_rejection_reason` | Dead-Letter | 除外理由 |

### SCD Type 2 対応（変更履歴の管理）

```sql
-- DLT の APPLY CHANGES を使った SCD Type 2
APPLY CHANGES INTO LIVE.silver_customers
FROM STREAM(LIVE.bronze_customers)
KEYS (customer_id)
SEQUENCE BY updated_at
STORED AS SCD TYPE 2;
```

DLT 2025 アップデートにより、SCD Type 2 の重複レコード統合が自動化されている。
