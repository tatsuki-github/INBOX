# GRANT/REVOKE、Row Filter、Column Mask 等の SQL 構文リファレンス

Unity Catalog で頻繁に使用する SQL 構文の包括的なリファレンス。

---

## 1. GRANT / REVOKE

### 1.1 基本構文

```sql
-- 権限の付与
GRANT privilege_types ON securable_object TO principal;

-- 権限の取り消し
REVOKE privilege_types ON securable_object FROM principal;

-- 現在の権限を表示
SHOW GRANTS ON securable_object;
SHOW GRANTS TO principal;
```

### 1.2 Metastore レベル

```sql
-- カタログ作成権限
GRANT CREATE CATALOG ON METASTORE TO `platform_admins`;

-- External Location 作成権限
GRANT CREATE EXTERNAL LOCATION ON METASTORE TO `platform_admins`;

-- Storage Credential 作成権限
GRANT CREATE STORAGE CREDENTIAL ON METASTORE TO `platform_admins`;

-- Delta Sharing 関連
GRANT CREATE SHARE ON METASTORE TO `data_sharing_admins`;
GRANT CREATE RECIPIENT ON METASTORE TO `data_sharing_admins`;
GRANT CREATE PROVIDER ON METASTORE TO `data_sharing_admins`;
GRANT SET SHARE PERMISSION ON METASTORE TO `data_sharing_admins`;
```

### 1.3 Catalog レベル

```sql
-- カタログへのアクセス許可（必須の前提条件）
GRANT USE_CATALOG ON CATALOG prod TO `data_engineers`;

-- スキーマ作成権限
GRANT USE_CATALOG, CREATE SCHEMA ON CATALOG prod TO `data_engineers`;

-- ブラウズのみ（データ読み取りなし）
GRANT USE_CATALOG, BROWSE ON CATALOG prod TO `data_viewers`;

-- 全権限（Dev 環境向け）
GRANT ALL PRIVILEGES ON CATALOG dev TO `data_engineers`;

-- 管理権限
GRANT MANAGE ON CATALOG prod TO `platform_admins`;
```

### 1.4 Schema レベル

```sql
-- スキーマへのアクセス + データ読み取り
GRANT USE_SCHEMA, SELECT ON SCHEMA prod.gold_analytics TO `data_analysts`;

-- テーブル作成権限（ETL パイプライン用）
GRANT USE_SCHEMA, CREATE TABLE, CREATE VOLUME ON SCHEMA prod.bronze TO `data_engineers`;

-- ML 関連の権限
GRANT USE_SCHEMA, CREATE TABLE, CREATE MODEL ON SCHEMA prod.ml TO `data_scientists`;

-- 外部エンジンからのアクセス許可
GRANT EXTERNAL USE SCHEMA ON SCHEMA prod.gold_analytics TO `external_query_users`;
```

### 1.5 Table / View レベル

```sql
-- 読み取り権限（個別テーブル）
GRANT SELECT ON TABLE prod.gold_analytics.daily_sales TO `reporting_team`;

-- 書き込み権限
GRANT SELECT, MODIFY ON TABLE prod.silver.customers TO `data_engineers`;

-- 権限の取り消し
REVOKE MODIFY ON TABLE prod.silver.customers FROM `data_engineers`;
```

### 1.6 その他のオブジェクト

```sql
-- Volume の権限
GRANT READ VOLUME ON VOLUME prod.ml.model_artifacts TO `data_scientists`;
GRANT WRITE VOLUME ON VOLUME prod.ml.model_artifacts TO `ml_engineers`;

-- Function の実行権限
GRANT EXECUTE ON FUNCTION prod.utils.mask_email TO `data_engineers`;

-- Model の権限
GRANT EXECUTE ON MODEL prod.ml.fraud_detection TO `data_scientists`;

-- External Location の権限
GRANT READ FILES, WRITE FILES ON EXTERNAL LOCATION `raw-data` TO `data_engineers`;
GRANT CREATE EXTERNAL TABLE ON EXTERNAL LOCATION `raw-data` TO `data_engineers`;
```

---

## 2. Row Filter（行レベルセキュリティ）

### 2.1 Row Filter 関数の作成

```sql
-- リージョンベースのフィルタ
CREATE OR REPLACE FUNCTION prod.utils.region_filter(region_col STRING)
RETURN IF(
  IS_ACCOUNT_GROUP_MEMBER('japan_team'),
  TRUE,
  region_col = 'GLOBAL'
);

-- 部門ベースのフィルタ
CREATE OR REPLACE FUNCTION prod.utils.department_filter(dept_col STRING)
RETURN
  IS_ACCOUNT_GROUP_MEMBER('all_data_access')
  OR IS_ACCOUNT_GROUP_MEMBER(CONCAT(dept_col, '_team'));

-- マルチ条件フィルタ
CREATE OR REPLACE FUNCTION prod.utils.sensitive_data_filter(
  sensitivity_level STRING,
  owner_dept STRING
)
RETURN CASE
  WHEN IS_ACCOUNT_GROUP_MEMBER('data_admins') THEN TRUE
  WHEN sensitivity_level = 'PUBLIC' THEN TRUE
  WHEN IS_ACCOUNT_GROUP_MEMBER(CONCAT(owner_dept, '_team')) THEN TRUE
  ELSE FALSE
END;
```

### 2.2 Row Filter の適用

```sql
-- テーブルへの適用
ALTER TABLE prod.sales.orders
SET ROW FILTER prod.utils.region_filter ON (region);

-- 複数カラムを使用するフィルタ
ALTER TABLE prod.hr.employees
SET ROW FILTER prod.utils.sensitive_data_filter ON (sensitivity_level, department);

-- Row Filter の削除
ALTER TABLE prod.sales.orders DROP ROW FILTER;
```

### 2.3 Row Filter の確認

```sql
-- テーブルに適用されている Row Filter を確認
DESCRIBE EXTENDED prod.sales.orders;

-- テスト（フィルタの動作確認）
SELECT * FROM prod.sales.orders;  -- 現在のユーザーのフィルタが適用される
```

---

## 3. Column Mask（列マスキング）

### 3.1 Column Mask 関数の作成

```sql
-- SSN のマスキング
CREATE OR REPLACE FUNCTION prod.utils.mask_ssn(ssn_col STRING)
RETURN IF(
  IS_ACCOUNT_GROUP_MEMBER('hr_full_access'),
  ssn_col,
  CONCAT('XXX-XX-', RIGHT(ssn_col, 4))
);

-- メールアドレスのマスキング
CREATE OR REPLACE FUNCTION prod.utils.mask_email(email_col STRING)
RETURN IF(
  IS_ACCOUNT_GROUP_MEMBER('pii_viewers'),
  email_col,
  CONCAT(LEFT(email_col, 2), '***@', SPLIT(email_col, '@')[1])
);

-- 電話番号のマスキング
CREATE OR REPLACE FUNCTION prod.utils.mask_phone(phone_col STRING)
RETURN IF(
  IS_ACCOUNT_GROUP_MEMBER('customer_service'),
  phone_col,
  CONCAT('***-****-', RIGHT(phone_col, 4))
);

-- 給与のマスキング（数値型）
CREATE OR REPLACE FUNCTION prod.utils.mask_salary(salary_col DECIMAL(10,2))
RETURN IF(
  IS_ACCOUNT_GROUP_MEMBER('hr_managers'),
  salary_col,
  NULL
);

-- 住所のマスキング（部分秘匿）
CREATE OR REPLACE FUNCTION prod.utils.mask_address(address_col STRING)
RETURN IF(
  IS_ACCOUNT_GROUP_MEMBER('logistics_team'),
  address_col,
  REGEXP_REPLACE(address_col, '\\d+', '***')
);
```

### 3.2 Column Mask の適用

```sql
-- 単一カラムへの適用
ALTER TABLE prod.hr.employees
SET COLUMN MASK prod.utils.mask_ssn ON (ssn);

-- 複数カラムへの適用
ALTER TABLE prod.hr.employees
SET COLUMN MASK prod.utils.mask_email ON (email);

ALTER TABLE prod.hr.employees
SET COLUMN MASK prod.utils.mask_salary ON (salary);

ALTER TABLE prod.hr.employees
SET COLUMN MASK prod.utils.mask_phone ON (phone_number);

-- Column Mask の削除
ALTER TABLE prod.hr.employees ALTER COLUMN ssn DROP MASK;
```

---

## 4. タグ操作

### 4.1 タグの設定・変更・削除

```sql
-- テーブルにタグを設定
ALTER TABLE prod.sales.customers
SET TAGS ('pii' = 'true', 'domain' = 'sales', 'sensitivity' = 'high');

-- スキーマにタグを設定
ALTER SCHEMA prod.sales
SET TAGS ('owner_team' = 'sales_engineering', 'data_tier' = 'gold');

-- カタログにタグを設定
ALTER CATALOG prod
SET TAGS ('environment' = 'production', 'managed_by' = 'platform_team');

-- カラムにタグを設定
ALTER TABLE prod.hr.employees ALTER COLUMN ssn SET TAGS ('pii_type' = 'ssn');

-- タグの削除
ALTER TABLE prod.sales.customers UNSET TAGS ('sensitivity');
```

---

## 5. オブジェクト管理

### 5.1 Catalog / Schema の管理

```sql
-- カタログの作成
CREATE CATALOG IF NOT EXISTS prod
COMMENT 'Production catalog'
MANAGED LOCATION 'abfss://managed@storage.dfs.core.windows.net/prod';

-- スキーマの作成
CREATE SCHEMA IF NOT EXISTS prod.gold_analytics
COMMENT 'Analytics data mart';

-- オーナーの変更
ALTER CATALOG prod SET OWNER TO `platform_admins`;
ALTER SCHEMA prod.gold_analytics SET OWNER TO `analytics_team`;
ALTER TABLE prod.gold_analytics.daily_sales SET OWNER TO `analytics_team`;

-- コメントの設定
COMMENT ON CATALOG prod IS 'Production environment catalog';
COMMENT ON TABLE prod.gold_analytics.daily_sales IS 'Daily aggregated sales metrics';
COMMENT ON COLUMN prod.gold_analytics.daily_sales.revenue IS 'Total revenue in JPY';
```

### 5.2 External Location / Storage Credential

```sql
-- External Location の作成
CREATE EXTERNAL LOCATION IF NOT EXISTS `raw-data`
URL 'abfss://raw@storageaccount.dfs.core.windows.net/'
WITH (STORAGE CREDENTIAL `main-storage-cred`)
COMMENT 'Raw data storage location';

-- External テーブルの作成
CREATE TABLE prod.bronze.external_customers
USING DELTA
LOCATION 'abfss://raw@storageaccount.dfs.core.windows.net/customers/';
```

### 5.3 Volume の管理

```sql
-- Managed Volume の作成
CREATE VOLUME IF NOT EXISTS prod.ml.model_artifacts
COMMENT 'ML model checkpoints and configurations';

-- External Volume の作成
CREATE EXTERNAL VOLUME IF NOT EXISTS prod.ml.training_images
LOCATION 'abfss://ml@storage.dfs.core.windows.net/training-images'
COMMENT 'Training image datasets';
```

---

## 6. Delta Sharing

### 6.1 Share の管理

```sql
-- Share の作成
CREATE SHARE IF NOT EXISTS partner_sales_data
COMMENT 'Sales data shared with partner organization';

-- テーブルを Share に追加
ALTER SHARE partner_sales_data ADD TABLE prod.gold_analytics.daily_sales;
ALTER SHARE partner_sales_data ADD TABLE prod.gold_analytics.product_catalog;

-- Share からテーブルを削除
ALTER SHARE partner_sales_data REMOVE TABLE prod.gold_analytics.product_catalog;

-- Share の一覧表示
SHOW SHARES;
SHOW ALL IN SHARE partner_sales_data;
```

### 6.2 Recipient の管理

```sql
-- Recipient の作成（Databricks-to-Databricks）
CREATE RECIPIENT IF NOT EXISTS partner_corp
USING ID '<sharing_identifier>'
COMMENT 'Partner Corporation';

-- Share へのアクセス権付与
GRANT SELECT ON SHARE partner_sales_data TO RECIPIENT partner_corp;

-- Recipient の一覧表示
SHOW RECIPIENTS;
```

---

## 7. Lakehouse Federation

```sql
-- Connection の作成
CREATE CONNECTION IF NOT EXISTS pg_operational
TYPE POSTGRESQL
OPTIONS (
  host 'pgserver.example.com',
  port '5432',
  user 'reader',
  password secret('scope', 'pg_password')
)
COMMENT 'Connection to operational PostgreSQL database';

-- Foreign Catalog の登録
CREATE FOREIGN CATALOG IF NOT EXISTS pg_operational
USING CONNECTION pg_operational
COMMENT 'Federated catalog for PostgreSQL';

-- フェデレーテッドクエリ
SELECT * FROM pg_operational.public.customers WHERE region = 'JP';
```

---

## 8. Information Schema クエリ

```sql
-- テーブル一覧
SELECT table_catalog, table_schema, table_name, table_type, comment
FROM prod.information_schema.tables
ORDER BY table_schema, table_name;

-- カラム情報
SELECT table_name, column_name, data_type, is_nullable, comment
FROM prod.information_schema.columns
WHERE table_schema = 'gold_analytics';

-- 権限情報
SELECT grantor, grantee, table_schema, table_name, privilege_type
FROM prod.information_schema.table_privileges
WHERE grantee = 'data_analysts';

-- Volume 一覧
SELECT volume_catalog, volume_schema, volume_name, volume_type, comment
FROM prod.information_schema.volumes;
```
