# Medallion Architecture 設計パターン

> Bronze / Silver / Gold 各層の設計パターンとコード例

---

## 1. 全体アーキテクチャ

```
Raw Data Sources
      |
      v
+-----------+     +-----------+     +-----------+
|  Bronze   |---->|  Silver   |---->|   Gold    |
| (Raw Data)|     | (Cleansed)|     | (Business)|
|           |     |           |     |           |
| - 生データ  |     | - クレンジ  |     | - 集計    |
| - スキーマ  |     |   ング     |     | - BIモデル |
|   適用     |     | - 正規化   |     | - ML特徴量 |
| - メタデータ |     | - MERGE   |     |           |
|   付与     |     |           |     |           |
+-----------+     +-----------+     +-----------+
     |                 |                 |
  Append Only    CDF Enabled      Read Optimized
```

---

## 2. Bronze 層の設計パターン

### 2.1 設計原則

**Preserve Everything, Transform Nothing** — 全てを保存し、何も変換しない。

| 項目 | 設定 |
|:---|:---|
| 書き込みモード | Append Only |
| スキーマ管理 | `mergeSchema = true`（スキーマ変更に柔軟対応） |
| 品質チェック | 最小限（スキーマ適用のみ） |
| メタデータ | `_ingestion_timestamp`, `_source_file` を付与 |
| 保持期間 | 長め（元データの再処理に備える） |

### 2.2 Auto Loader パターン

```python
# Auto Loader での Bronze 層取り込み
raw_df = spark.readStream.format("cloudFiles") \
  .option("cloudFiles.format", "json") \
  .option("cloudFiles.inferColumnTypes", "true") \
  .option("cloudFiles.schemaLocation", "/mnt/schema/bronze_events") \
  .option("cloudFiles.maxFilesPerTrigger", 1000) \
  .load("/mnt/landing/events/")

# メタデータを付与して Bronze テーブルに書き込み
from pyspark.sql.functions import current_timestamp, input_file_name

raw_df \
  .withColumn("_ingestion_timestamp", current_timestamp()) \
  .withColumn("_source_file", input_file_name()) \
  .writeStream.format("delta") \
  .option("checkpointLocation", "/mnt/checkpoints/bronze_events") \
  .option("mergeSchema", "true") \
  .outputMode("append") \
  .trigger(availableNow=True) \
  .toTable("catalog.bronze.events")
```

### 2.3 Auto Loader のベストプラクティス

| 設定 | 推奨 | 理由 |
|:---|:---|:---|
| ファイル検出モード | 小規模: Directory Listing / 大規模: File Notification | スケーラビリティ |
| スキーマ推論 | `inferColumnTypes = true` | 手動スキーマ管理の負担軽減 |
| スループット制御 | `maxFilesPerTrigger` / `maxBytesPerTrigger` | バックプレッシャー防止 |
| チェックポイント | ライフサイクルポリシー対象外のストレージ | チェックポイント破損防止 |
| エラーハンドリング | `_rescued_data` カラムの活用 | パースエラーの安全な捕捉 |

### 2.4 Bronze テーブルの DDL 例

```sql
CREATE TABLE catalog.bronze.events (
  -- Auto Loader が推論するスキーマ + メタデータ
  _ingestion_timestamp TIMESTAMP,
  _source_file STRING,
  _rescued_data STRING  -- パースエラーの捕捉用
)
USING DELTA
CLUSTER BY (_ingestion_timestamp)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.logRetentionDuration' = 'interval 30 days'
);
```

---

## 3. Silver 層の設計パターン

### 3.1 設計原則

**検証済み・クレンジング済み・正規化済み**データの提供。

| 項目 | 設定 |
|:---|:---|
| 更新方法 | MERGE（Upsert） |
| CDF | 有効化推奨（Gold 層へのインクリメンタル更新） |
| 品質チェック | DLT Expectations で厳格にチェック |
| クラスタリング | ビジネスキーでの Liquid Clustering |
| Deletion Vectors | 有効化推奨 |

### 3.2 MERGE パターン（PySpark）

```python
from delta.tables import DeltaTable

silver_table = DeltaTable.forName(spark, "catalog.silver.customers")

# Bronze から変更データを取得（事前フィルタリング）
bronze_changes = spark.read.table("catalog.bronze.customers") \
  .filter("_ingestion_timestamp >= current_date()")

# MERGE 実行
silver_table.alias("t").merge(
  bronze_changes.alias("s"),
  "t.customer_id = s.customer_id AND t.region = s.region"
).whenMatchedUpdateAll() \
 .whenNotMatchedInsertAll() \
 .execute()
```

### 3.3 MERGE パターン（SQL）

```sql
MERGE INTO catalog.silver.customers t
USING (
  SELECT
    customer_id,
    region,
    name,
    email,
    current_timestamp() as updated_at
  FROM catalog.bronze.customers
  WHERE _ingestion_timestamp >= current_date()
    AND _rescued_data IS NULL  -- パースエラーを除外
) s
ON t.customer_id = s.customer_id AND t.region = s.region
WHEN MATCHED THEN
  UPDATE SET
    t.name = s.name,
    t.email = s.email,
    t.updated_at = s.updated_at
WHEN NOT MATCHED THEN
  INSERT *;
```

### 3.4 DLT Expectations パターン

```python
import dlt

@dlt.table(
  comment="クレンジング済み顧客データ"
)
@dlt.expect("valid_customer_id", "customer_id IS NOT NULL")
@dlt.expect_or_drop("valid_email", "email RLIKE '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'")
@dlt.expect_or_fail("valid_region", "region IN ('JP', 'US', 'EU', 'APAC')")
def silver_customers():
    return dlt.read_stream("bronze_customers") \
      .filter("_rescued_data IS NULL") \
      .select(
        "customer_id", "name", "email", "region",
        "created_at", "updated_at"
      )
```

### 3.5 Silver テーブルの DDL 例

```sql
CREATE TABLE catalog.silver.customers (
  customer_id STRING NOT NULL,
  region STRING NOT NULL,
  name STRING,
  email STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
USING DELTA
CLUSTER BY (customer_id, region)
TBLPROPERTIES (
  'delta.enableDeletionVectors' = 'true',
  'delta.enableChangeDataFeed' = 'true',
  'delta.logRetentionDuration' = 'interval 30 days',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);
```

---

## 4. Gold 層の設計パターン

### 4.1 設計原則

**ビジネス消費に最適化**された非正規化モデル。

| 項目 | 設定 |
|:---|:---|
| 更新方法 | Silver 層の CDF を活用したインクリメンタル集計 |
| データモデル | スター/スノーフレークスキーマ |
| クラスタリング | 分析ディメンションでの Liquid Clustering |
| ファイルサイズ | 大きめ（512MB - 1GB） |

### 4.2 CDF ベースのインクリメンタル集計（SQL）

```sql
-- Silver 層の変更データを読み取り、Gold 層をインクリメンタルに更新
CREATE OR REFRESH STREAMING TABLE catalog.gold.daily_sales AS
SELECT
  order_date,
  product_category,
  region,
  COUNT(*) as total_orders,
  SUM(amount) as total_revenue,
  AVG(amount) as avg_order_value
FROM STREAM(catalog.silver.orders)
GROUP BY order_date, product_category, region;
```

### 4.3 CDF ベースのインクリメンタル集計（PySpark）

```python
# Silver 層から CDF を読み取り
changes_df = spark.readStream.format("delta") \
  .option("readChangeFeed", "true") \
  .table("catalog.silver.orders")

# 変更データを集計して Gold テーブルに書き込み
changes_df \
  .filter("_change_type IN ('insert', 'update_postimage')") \
  .groupBy("order_date", "product_category", "region") \
  .agg(
    count("*").alias("total_orders"),
    sum("amount").alias("total_revenue"),
    avg("amount").alias("avg_order_value")
  ) \
  .writeStream.format("delta") \
  .option("checkpointLocation", "/mnt/checkpoints/gold_daily_sales") \
  .outputMode("complete") \
  .toTable("catalog.gold.daily_sales")
```

### 4.4 マテリアライズドビューパターン

```sql
-- Databricks 環境でのマテリアライズドビュー
CREATE MATERIALIZED VIEW catalog.gold.customer_360 AS
SELECT
  c.customer_id,
  c.name,
  c.email,
  c.region,
  COUNT(o.order_id) as total_orders,
  SUM(o.amount) as lifetime_value,
  MAX(o.order_date) as last_order_date,
  DATEDIFF(current_date(), MAX(o.order_date)) as days_since_last_order
FROM catalog.silver.customers c
LEFT JOIN catalog.silver.orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name, c.email, c.region;
```

### 4.5 Gold テーブルの DDL 例

```sql
CREATE TABLE catalog.gold.daily_sales (
  order_date DATE,
  product_category STRING,
  region STRING,
  total_orders BIGINT,
  total_revenue DECIMAL(18,2),
  avg_order_value DECIMAL(18,2)
)
USING DELTA
CLUSTER BY (order_date, product_category)
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.deletedFileRetentionDuration' = 'interval 7 days'
);
```

---

## 5. 層間のデータフロー設計

### 5.1 バッチパターン

```
Landing Zone → [Auto Loader / Batch] → Bronze
                                          |
                                   [Scheduled Job]
                                          |
                                          v
                                       Silver (MERGE)
                                          |
                                   [Scheduled Job]
                                          |
                                          v
                                       Gold (CDF / Aggregate)
```

### 5.2 ストリーミングパターン

```
Source → [Streaming] → Bronze → [Streaming] → Silver → [Streaming] → Gold
                         |            |            |
                    checkpoint    checkpoint    checkpoint
```

### 5.3 ハイブリッドパターン（推奨）

```
Source → [Streaming] → Bronze
                          |
                   [Micro-batch / Triggered]
                          |
                          v
                       Silver (MERGE + CDF)
                          |
                   [CDF Streaming]
                          |
                          v
                       Gold (Incremental Aggregate)
```

---

## 6. 品質チェック戦略

| 層 | チェック内容 | Expectations モード | 失敗時の動作 |
|:---|:---|:---|:---|
| **Bronze** | スキーマ適用のみ | なし（`_rescued_data` で捕捉） | エラー行を `_rescued_data` に格納 |
| **Silver** | NULL チェック、型チェック、範囲チェック | `expect_or_drop` | 不正行をドロップ |
| **Silver** | クリティカル制約（PK 重複など） | `expect_or_fail` | パイプライン停止 |
| **Gold** | 集計値の妥当性チェック | `expect` | ログに記録（監視用） |
