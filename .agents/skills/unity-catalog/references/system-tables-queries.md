# System Tables を活用した運用クエリ集

Unity Catalog の System Tables（`system` カタログ）を活用した
監視・監査・コスト管理・棚卸しのための SQL クエリ集。

---

## 1. System Tables の概要

| スキーマ | テーブル | 用途 |
|:---|:---|:---|
| `system.access` | `audit` | 監査ログ（ユーザーアクション） |
| `system.billing` | `usage` | DBU 消費量 |
| `system.billing` | `list_prices` | SKU 別の単価情報 |
| `system.compute` | `clusters` | クラスター構成・利用状況 |
| `system.lineage` | `table_lineage` | テーブル間のリネージ |
| `system.lineage` | `column_lineage` | カラム間のリネージ |
| `system.storage` | `predictive_optimization_operations_history` | 予測最適化の履歴 |

**前提**: System Tables の有効化が必要。アカウント管理者が有効化する。

---

## 2. 監査ログクエリ

### 2.1 直近の Unity Catalog イベント

```sql
-- 直近 7 日間の UC 関連イベント
SELECT
  event_time,
  user_identity.email AS user_email,
  action_name,
  request_params.full_name_arg AS object_name,
  response.status_code
FROM system.access.audit
WHERE service_name = 'unityCatalog'
  AND event_date >= current_date() - INTERVAL 7 DAYS
ORDER BY event_time DESC
LIMIT 200;
```

### 2.2 権限変更の追跡

```sql
-- GRANT / REVOKE の履歴
SELECT
  event_time,
  user_identity.email AS granted_by,
  action_name,
  request_params.securable_type AS object_type,
  request_params.securable_full_name AS object_name,
  request_params.principal AS grantee,
  request_params.changes AS privilege_changes
FROM system.access.audit
WHERE action_name IN ('updatePermissions', 'grantPermission', 'revokePermission')
  AND event_date >= current_date() - INTERVAL 30 DAYS
ORDER BY event_time DESC;
```

### 2.3 テーブルアクセスの監査

```sql
-- 特定テーブルへのアクセス履歴
SELECT
  event_time,
  user_identity.email AS user_email,
  action_name,
  source_ip_address,
  request_params.operation AS operation_type
FROM system.access.audit
WHERE request_params.full_name_arg = 'prod.gold_analytics.daily_sales'
  AND event_date >= current_date() - INTERVAL 30 DAYS
ORDER BY event_time DESC;
```

### 2.4 失敗したアクセスの検出

```sql
-- 権限エラーの検出（セキュリティ監査用）
SELECT
  event_time,
  user_identity.email AS user_email,
  action_name,
  request_params.full_name_arg AS object_name,
  response.error_message
FROM system.access.audit
WHERE response.status_code != '200'
  AND service_name = 'unityCatalog'
  AND event_date >= current_date() - INTERVAL 7 DAYS
ORDER BY event_time DESC;
```

### 2.5 ユーザー別アクティビティサマリー

```sql
-- ユーザー別の UC 操作回数（月次）
SELECT
  user_identity.email AS user_email,
  action_name,
  COUNT(*) AS action_count
FROM system.access.audit
WHERE service_name = 'unityCatalog'
  AND event_date >= date_trunc('month', current_date())
GROUP BY 1, 2
ORDER BY 3 DESC;
```

---

## 3. コスト管理クエリ

### 3.1 月次 DBU 使用量

```sql
-- 月次 DBU 消費量（SKU 別）
SELECT
  date_trunc('month', usage_date) AS month,
  sku_name,
  SUM(usage_quantity) AS total_dbu
FROM system.billing.usage
WHERE usage_date >= '2026-01-01'
GROUP BY 1, 2
ORDER BY 1, 2;
```

### 3.2 ワークスペース別コスト

```sql
-- ワークスペース別の月次コスト
SELECT
  date_trunc('month', u.usage_date) AS month,
  u.workspace_id,
  u.sku_name,
  SUM(u.usage_quantity) AS total_dbu,
  SUM(u.usage_quantity * p.pricing.default) AS estimated_cost_usd
FROM system.billing.usage u
JOIN system.billing.list_prices p
  ON u.sku_name = p.sku_name
  AND u.usage_date BETWEEN p.price_start_time AND COALESCE(p.price_end_time, '2099-12-31')
WHERE u.usage_date >= current_date() - INTERVAL 90 DAYS
GROUP BY 1, 2, 3
ORDER BY 5 DESC;
```

### 3.3 日次コストトレンド

```sql
-- 日次の DBU 使用量トレンド（異常検知用）
SELECT
  usage_date,
  SUM(usage_quantity) AS daily_dbu,
  AVG(SUM(usage_quantity)) OVER (
    ORDER BY usage_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS rolling_7day_avg
FROM system.billing.usage
WHERE usage_date >= current_date() - INTERVAL 30 DAYS
GROUP BY 1
ORDER BY 1;
```

---

## 4. リネージクエリ

### 4.1 テーブルリネージ

```sql
-- 特定テーブルの上流テーブルを追跡
SELECT
  source_table_full_name,
  target_table_full_name,
  event_time
FROM system.lineage.table_lineage
WHERE target_table_full_name = 'prod.gold_analytics.daily_sales'
ORDER BY event_time DESC;
```

### 4.2 カラムリネージ

```sql
-- 特定カラムのソースを追跡
SELECT
  source_table_full_name,
  source_column_name,
  target_table_full_name,
  target_column_name,
  event_time
FROM system.lineage.column_lineage
WHERE target_table_full_name = 'prod.gold_analytics.daily_sales'
  AND target_column_name = 'revenue'
ORDER BY event_time DESC;
```

### 4.3 影響分析

```sql
-- ソーステーブル変更の影響範囲を把握
SELECT DISTINCT
  target_table_full_name AS affected_table
FROM system.lineage.table_lineage
WHERE source_table_full_name = 'prod.bronze_salesforce.accounts'
ORDER BY 1;
```

---

## 5. 棚卸し・クリーンアップクエリ

### 5.1 未使用テーブルの検出

```sql
-- 90 日以上アクセスされていないテーブル
SELECT
  t.table_catalog,
  t.table_schema,
  t.table_name,
  t.table_type,
  t.created,
  MAX(a.event_time) AS last_accessed
FROM prod.information_schema.tables t
LEFT JOIN system.access.audit a
  ON a.request_params.full_name_arg =
     CONCAT(t.table_catalog, '.', t.table_schema, '.', t.table_name)
  AND a.action_name IN ('getTable', 'commandSubmit')
  AND a.event_date >= current_date() - INTERVAL 180 DAYS
GROUP BY 1, 2, 3, 4, 5
HAVING MAX(a.event_time) < current_timestamp() - INTERVAL 90 DAYS
   OR MAX(a.event_time) IS NULL
ORDER BY last_accessed NULLS FIRST;
```

### 5.2 オーナー不在のオブジェクト検出

```sql
-- オーナーが直近 30 日間ログインしていないテーブル
SELECT
  t.table_catalog,
  t.table_schema,
  t.table_name,
  t.table_owner
FROM prod.information_schema.tables t
WHERE t.table_owner NOT IN (
  SELECT DISTINCT user_identity.email
  FROM system.access.audit
  WHERE event_date >= current_date() - INTERVAL 30 DAYS
)
ORDER BY t.table_catalog, t.table_schema, t.table_name;
```

### 5.3 テーブルサイズの把握

```sql
-- スキーマ別のテーブル数とサイズ
SELECT
  table_catalog,
  table_schema,
  COUNT(*) AS table_count,
  SUM(data_source_format = 'DELTA') AS delta_tables,
  SUM(data_source_format != 'DELTA') AS non_delta_tables
FROM prod.information_schema.tables
WHERE table_type = 'MANAGED'
GROUP BY 1, 2
ORDER BY 3 DESC;
```

### 5.4 権限の棚卸し

```sql
-- 過剰な権限を持つグループの検出
SELECT
  grantee,
  privilege_type,
  COUNT(*) AS grant_count
FROM prod.information_schema.table_privileges
GROUP BY 1, 2
HAVING COUNT(*) > 100
ORDER BY 3 DESC;
```

### 5.5 スキーマ別オブジェクト数

```sql
-- スキーマ別のオブジェクト数一覧
SELECT
  table_schema,
  table_type,
  COUNT(*) AS object_count
FROM prod.information_schema.tables
GROUP BY 1, 2
ORDER BY 1, 3 DESC;
```

---

## 6. 運用ダッシュボード用クエリ

### 6.1 日次サマリー

```sql
-- Unity Catalog 日次運用サマリー
SELECT
  current_date() AS report_date,
  (SELECT COUNT(*) FROM prod.information_schema.schemata) AS total_schemas,
  (SELECT COUNT(*) FROM prod.information_schema.tables) AS total_tables,
  (SELECT COUNT(*) FROM prod.information_schema.volumes) AS total_volumes,
  (SELECT COUNT(DISTINCT user_identity.email)
   FROM system.access.audit
   WHERE event_date = current_date()
     AND service_name = 'unityCatalog') AS active_users_today,
  (SELECT COUNT(*)
   FROM system.access.audit
   WHERE event_date = current_date()
     AND service_name = 'unityCatalog'
     AND response.status_code != '200') AS failed_requests_today;
```

### 6.2 週次トレンド

```sql
-- 週次のテーブル作成・削除数
SELECT
  date_trunc('week', event_time) AS week,
  SUM(CASE WHEN action_name = 'createTable' THEN 1 ELSE 0 END) AS tables_created,
  SUM(CASE WHEN action_name = 'deleteTable' THEN 1 ELSE 0 END) AS tables_deleted
FROM system.access.audit
WHERE service_name = 'unityCatalog'
  AND event_date >= current_date() - INTERVAL 90 DAYS
GROUP BY 1
ORDER BY 1;
```
