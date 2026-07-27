# DLT Expectations パターン集

> Lakeflow Declarative Pipelines（旧 Delta Live Tables）の Expectations を活用したデータ品質チェックのパターン集。戦略選定、レイヤー別の適用、コード例をまとめたリファレンス。

---

## 1. Expectations の基本

### 3 つの戦略

| 戦略 | SQL 構文 | Python 構文 | 違反時の動作 |
|:---|:---|:---|:---|
| `expect` | `EXPECT (condition)` | `@dlt.expect("name", "condition")` | レコード保持、メトリクスログ |
| `expect_or_drop` | `ON VIOLATION DROP ROW` | `@dlt.expect_or_drop("name", "condition")` | 違反レコードを除外 |
| `expect_or_fail` | `ON VIOLATION FAIL UPDATE` | `@dlt.expect_or_fail("name", "condition")` | パイプラインを停止 |

### 戦略の選定指針

```
データの重要度は？
  ├── 致命的（PK 違反、整合性破壊）-> expect_or_fail
  ├── 重要（不正値、欠損値）      -> expect_or_drop
  └── 参考（品質傾向の監視）      -> expect
```

| 判断基準 | expect | expect_or_drop | expect_or_fail |
|:---|:---|:---|:---|
| 下流への影響 | 低 | 中 | 高 |
| データ損失許容 | 損失なし | 部分的に許容 | 損失不可 |
| 運用負荷 | 低 | 中 | 高（復旧対応） |
| 適用フェーズ | モニタリング期 | 安定運用期 | クリティカル要件 |

---

## 2. レイヤー別の適用パターン

### Bronze → Silver（データ品質の基本検証）

```sql
CREATE OR REFRESH STREAMING TABLE silver_events (
  -- 必須フィールドの存在チェック
  CONSTRAINT valid_event_id
    EXPECT (event_id IS NOT NULL)
    ON VIOLATION DROP ROW,

  -- タイムスタンプの妥当性
  CONSTRAINT valid_timestamp
    EXPECT (event_timestamp IS NOT NULL
            AND event_timestamp >= '2020-01-01'
            AND event_timestamp <= current_timestamp())
    ON VIOLATION DROP ROW,

  -- 型変換の成功チェック
  CONSTRAINT valid_amount
    EXPECT (TRY_CAST(amount AS DOUBLE) IS NOT NULL)
    ON VIOLATION DROP ROW,

  -- 主キーの一意性（致命的）
  CONSTRAINT unique_event_id
    EXPECT (event_id_count = 1)
    ON VIOLATION FAIL UPDATE
)
AS SELECT
  CAST(event_id AS BIGINT) AS event_id,
  CAST(event_timestamp AS TIMESTAMP) AS event_timestamp,
  CAST(amount AS DOUBLE) AS amount,
  event_type,
  user_id,
  COUNT(*) OVER (PARTITION BY event_id) AS event_id_count,
  _ingested_at
FROM STREAM(LIVE.bronze_events);
```

### Silver → Gold（ビジネスルールの検証）

```sql
CREATE OR REFRESH MATERIALIZED VIEW gold_daily_metrics (
  -- ビジネスルール: 売上は正の値
  CONSTRAINT positive_revenue
    EXPECT (total_revenue >= 0),

  -- ビジネスルール: 注文数と顧客数の整合性
  CONSTRAINT orders_ge_customers
    EXPECT (order_count >= unique_customers),

  -- 異常値の検出（参考モニタリング）
  CONSTRAINT reasonable_avg_order
    EXPECT (avg_order_value BETWEEN 1 AND 1000000)
)
AS SELECT
  order_date,
  COUNT(DISTINCT customer_id) AS unique_customers,
  COUNT(*) AS order_count,
  SUM(amount) AS total_revenue,
  AVG(amount) AS avg_order_value
FROM LIVE.silver_orders
GROUP BY order_date;
```

---

## 3. Python での Expectations パターン

### 基本パターン

```python
import dlt
from pyspark.sql.functions import col, current_timestamp

@dlt.table(
    name="silver_transactions",
    comment="品質検証済みのトランザクションデータ"
)
@dlt.expect("valid_id", "transaction_id IS NOT NULL")
@dlt.expect_or_drop("valid_amount", "amount > 0")
@dlt.expect_or_drop("valid_currency", "currency IN ('JPY', 'USD', 'EUR')")
@dlt.expect_or_fail("valid_pk", "pk_count = 1")
def silver_transactions():
    return (
        dlt.read_stream("bronze_transactions")
        .withColumn("amount", col("amount").cast("double"))
        .withColumn("transaction_date", col("transaction_date").cast("date"))
    )
```

### 複数テーブルに共通の Expectations を適用

```python
# 共通の品質ルールを関数化
def common_expectations(df):
    """全テーブルに共通する品質ルール"""
    return df

COMMON_RULES = {
    "not_null_id": "id IS NOT NULL",
    "valid_created_at": "created_at IS NOT NULL AND created_at <= current_timestamp()"
}

@dlt.table(name="silver_users")
@dlt.expect_all(COMMON_RULES)
@dlt.expect_or_drop("valid_email", "email RLIKE '^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+$'")
def silver_users():
    return dlt.read_stream("bronze_users")

@dlt.table(name="silver_products")
@dlt.expect_all(COMMON_RULES)
@dlt.expect_or_drop("valid_price", "price > 0")
def silver_products():
    return dlt.read_stream("bronze_products")
```

### 複合条件の Expectations

```python
@dlt.table(name="silver_orders")
@dlt.expect_all_or_drop({
    "valid_order_id": "order_id IS NOT NULL",
    "valid_amount": "amount > 0",
    "valid_date": "order_date >= '2020-01-01'",
    "valid_status": "status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')"
})
@dlt.expect_all_or_fail({
    "unique_order": "order_count = 1"
})
def silver_orders():
    return (
        dlt.read_stream("bronze_orders")
        .withColumn("amount", col("amount").cast("double"))
        .withColumn("order_date", col("order_date").cast("date"))
    )
```

---

## 4. Dead-Letter テーブルパターン

### SQL による Dead-Letter

```sql
-- 品質違反レコードを隔離
CREATE OR REFRESH STREAMING TABLE dead_letter_events
COMMENT "品質チェックで除外されたイベントレコード"
AS SELECT
  *,
  current_timestamp() AS _quarantined_at,
  CASE
    WHEN event_id IS NULL THEN 'missing_event_id'
    WHEN event_timestamp IS NULL THEN 'missing_timestamp'
    WHEN TRY_CAST(amount AS DOUBLE) IS NULL THEN 'invalid_amount'
    ELSE 'unknown_violation'
  END AS _rejection_reason
FROM STREAM(LIVE.bronze_events)
WHERE event_id IS NULL
   OR event_timestamp IS NULL
   OR TRY_CAST(amount AS DOUBLE) IS NULL;
```

### Dead-Letter テーブルの設計原則

| 原則 | 詳細 |
|:---|:---|
| 全フィールドを保持 | Bronze の生データをそのまま保存 |
| 除外理由を付与 | `_rejection_reason` カラムで原因を特定可能に |
| 隔離日時を記録 | `_quarantined_at` で時系列分析可能に |
| 定期的に棚卸し | 週次/月次で Dead-Letter を分析し、品質ルールを改善 |

---

## 5. 品質メトリクスの監視

### Event Log からの品質メトリクス取得

```sql
-- DLT Event Log から Expectations メトリクスを取得
SELECT
  timestamp,
  details:flow_definition.output_dataset AS table_name,
  details:flow_progress.data_quality.expectations.name AS expectation_name,
  details:flow_progress.data_quality.expectations.dataset AS dataset,
  details:flow_progress.data_quality.expectations.passed_records AS passed,
  details:flow_progress.data_quality.expectations.failed_records AS failed,
  (details:flow_progress.data_quality.expectations.passed_records /
   (details:flow_progress.data_quality.expectations.passed_records +
    details:flow_progress.data_quality.expectations.failed_records)) * 100
    AS pass_rate_pct
FROM event_log(TABLE(my_pipeline))
WHERE event_type = 'flow_progress'
  AND details:flow_progress.data_quality IS NOT NULL;
```

### アラート閾値の設定

| メトリクス | 警告閾値 | 緊急閾値 | 対応 |
|:---|:---|:---|:---|
| 合格率（Pass Rate） | < 99% | < 95% | 品質ルールまたはソースデータの調査 |
| ドロップ率 | > 1% | > 5% | ソースデータの品質劣化を調査 |
| `expect_or_fail` 発動 | 1 回 | - | 即時対応（パイプライン停止中） |
| Dead-Letter 増加率 | 前日比 2 倍 | 前日比 5 倍 | ソースシステムの異常を調査 |

---

## 6. よくあるパターンと注意事項

### ベストプラクティス

| 項目 | 推奨 |
|:---|:---|
| 段階的な厳格化 | 導入初期は `expect` で監視 → 安定後に `expect_or_drop` / `expect_or_fail` に格上げ |
| 命名規則 | `valid_{column}`, `not_null_{column}`, `unique_{column}` |
| ドキュメント化 | 各 Expectation にコメントで背景・理由を記載 |
| テスト | ステージング環境で品質ルールの妥当性を検証してから本番適用 |

### 注意事項

| 注意点 | 詳細 |
|:---|:---|
| `expect_or_fail` の復旧 | パイプライン全体が停止するため、自動再起動の設計が必要 |
| ストリーミングの一意性チェック | ウィンドウ内での一意性チェックは複雑。バッチ処理での検証も検討 |
| 型変換エラー | `TRY_CAST` を使い、変換失敗時に NULL を返す設計にする |
| NULL の扱い | SQL の 3 値論理に注意。`IS NOT NULL` を明示的にチェック |
