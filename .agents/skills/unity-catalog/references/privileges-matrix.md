# オブジェクトタイプ別の権限マトリクス

Unity Catalog の各 Securable Object に対して適用可能な権限（Privilege）の完全な一覧。

---

## 1. 権限一覧（アルファベット順）

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限を一括付与（メタ権限） |
| `APPLY_TAG` | オブジェクトへのタグ適用を許可 |
| `BROWSE` | Catalog Explorer でのブラウズを許可（データ読み取りなし） |
| `CREATE CATALOG` | カタログの作成を許可 |
| `CREATE CONNECTION` | Lakehouse Federation 接続の作成を許可 |
| `CREATE EXTERNAL LOCATION` | External Location の作成を許可 |
| `CREATE EXTERNAL TABLE` | External テーブルの作成を許可 |
| `CREATE EXTERNAL VOLUME` | External ボリュームの作成を許可 |
| `CREATE FUNCTION` | UDF の作成を許可 |
| `CREATE MANAGED STORAGE` | Managed ストレージの作成を許可 |
| `CREATE MATERIALIZED VIEW` | マテリアライズドビューの作成を許可 |
| `CREATE MODEL` | ML モデルの登録を許可 |
| `CREATE PROVIDER` | Delta Sharing プロバイダーの作成を許可 |
| `CREATE RECIPIENT` | Delta Sharing レシピエントの作成を許可 |
| `CREATE SCHEMA` | スキーマの作成を許可 |
| `CREATE SHARE` | Delta Sharing シェアの作成を許可 |
| `CREATE STORAGE CREDENTIAL` | Storage Credential の作成を許可 |
| `CREATE TABLE` | Managed テーブルの作成を許可 |
| `CREATE VOLUME` | Managed ボリュームの作成を許可 |
| `EXECUTE` | 関数の実行を許可 |
| `EXTERNAL USE SCHEMA` | 外部エンジンからのスキーマアクセスを許可 |
| `MANAGE` | オブジェクトの管理（権限付与含む）を許可 |
| `MODIFY` | テーブルデータの追加・更新・削除を許可 |
| `READ FILES` | External Location からのファイル読み取りを許可 |
| `READ VOLUME` | ボリュームからのファイル読み取りを許可 |
| `REFRESH` | マテリアライズドビューのリフレッシュを許可 |
| `SELECT` | テーブル / ビューのデータ読み取りを許可 |
| `SET SHARE PERMISSION` | Share の権限設定を許可 |
| `USE_CATALOG` | カタログへのアクセスを許可（配下オブジェクトの前提条件） |
| `USE_SCHEMA` | スキーマへのアクセスを許可（配下オブジェクトの前提条件） |
| `WRITE FILES` | External Location へのファイル書き込みを許可 |
| `WRITE VOLUME` | ボリュームへのファイル書き込みを許可 |

---

## 2. オブジェクトタイプ別の適用可能権限

### 2.1 Metastore レベル

| 権限 | 説明 |
|:---|:---|
| `CREATE CATALOG` | カタログの作成 |
| `CREATE CONNECTION` | Lakehouse Federation 接続の作成 |
| `CREATE EXTERNAL LOCATION` | External Location の作成 |
| `CREATE PROVIDER` | Delta Sharing プロバイダーの作成 |
| `CREATE RECIPIENT` | Delta Sharing レシピエントの作成 |
| `CREATE SHARE` | Share の作成 |
| `CREATE STORAGE CREDENTIAL` | Storage Credential の作成 |
| `MANAGE` | Metastore 全体の管理 |
| `SET SHARE PERMISSION` | Share 権限の管理 |

### 2.2 Catalog レベル

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限 |
| `APPLY_TAG` | タグの適用 |
| `BROWSE` | Catalog Explorer でのブラウズ |
| `CREATE SCHEMA` | スキーマの作成 |
| `MANAGE` | カタログの管理 |
| `USE_CATALOG` | カタログへのアクセス |

### 2.3 Schema レベル

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限 |
| `APPLY_TAG` | タグの適用 |
| `CREATE FUNCTION` | UDF の作成 |
| `CREATE MATERIALIZED VIEW` | マテリアライズドビューの作成 |
| `CREATE MODEL` | ML モデルの登録 |
| `CREATE TABLE` | テーブルの作成 |
| `CREATE VOLUME` | ボリュームの作成 |
| `EXTERNAL USE SCHEMA` | 外部エンジンからのアクセス |
| `MANAGE` | スキーマの管理 |
| `USE_SCHEMA` | スキーマへのアクセス |

### 2.4 Table / View レベル

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限 |
| `APPLY_TAG` | タグの適用 |
| `MODIFY` | データの追加・更新・削除（Table のみ） |
| `SELECT` | データの読み取り |

### 2.5 Materialized View レベル

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限 |
| `APPLY_TAG` | タグの適用 |
| `REFRESH` | マテリアライズドビューのリフレッシュ |
| `SELECT` | データの読み取り |

### 2.6 Volume レベル

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限 |
| `READ VOLUME` | ファイルの読み取り |
| `WRITE VOLUME` | ファイルの書き込み |

### 2.7 Function レベル

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限 |
| `EXECUTE` | 関数の実行 |

### 2.8 Model レベル

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限 |
| `APPLY_TAG` | タグの適用 |
| `EXECUTE` | モデルの推論実行 |

### 2.9 External Location レベル

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限 |
| `BROWSE` | ブラウズ |
| `CREATE EXTERNAL TABLE` | 外部テーブルの作成 |
| `CREATE EXTERNAL VOLUME` | 外部ボリュームの作成 |
| `CREATE MANAGED STORAGE` | Managed ストレージの作成 |
| `READ FILES` | ファイルの読み取り |
| `WRITE FILES` | ファイルの書き込み |

### 2.10 Storage Credential レベル

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限 |
| `CREATE EXTERNAL LOCATION` | External Location の作成 |
| `CREATE EXTERNAL TABLE` | 外部テーブルの作成（Direct） |

### 2.11 Connection レベル

| 権限 | 説明 |
|:---|:---|
| `ALL_PRIVILEGES` | すべての適用可能な権限 |
| `CREATE FOREIGN CATALOG` | Foreign Catalog の作成 |
| `USE CONNECTION` | 接続の使用 |

### 2.12 Share レベル

| 権限 | 説明 |
|:---|:---|
| `SELECT` | Share のデータ読み取り（Recipient 向け） |

---

## 3. ロール別の推奨権限パターン

### 3.1 Platform Admin（プラットフォーム管理者）

```sql
-- Metastore レベル
GRANT CREATE CATALOG ON METASTORE TO `platform_admins`;
GRANT CREATE EXTERNAL LOCATION ON METASTORE TO `platform_admins`;
GRANT CREATE STORAGE CREDENTIAL ON METASTORE TO `platform_admins`;

-- 全カタログに対して MANAGE
GRANT MANAGE ON CATALOG prod TO `platform_admins`;
GRANT MANAGE ON CATALOG dev TO `platform_admins`;
```

### 3.2 Data Engineer（データエンジニア）

```sql
-- カタログ・スキーマレベル
GRANT USE_CATALOG ON CATALOG prod TO `data_engineers`;
GRANT USE_SCHEMA, CREATE_TABLE, CREATE_VOLUME ON SCHEMA prod.bronze_* TO `data_engineers`;
GRANT USE_SCHEMA, CREATE_TABLE ON SCHEMA prod.silver_* TO `data_engineers`;

-- Dev 環境は広範な権限
GRANT ALL_PRIVILEGES ON CATALOG dev TO `data_engineers`;
```

### 3.3 Data Analyst（データアナリスト）

```sql
-- 読み取り専用
GRANT USE_CATALOG ON CATALOG prod TO `data_analysts`;
GRANT USE_SCHEMA, SELECT ON SCHEMA prod.gold_analytics TO `data_analysts`;
GRANT USE_SCHEMA, SELECT ON SCHEMA prod.gold_reporting TO `data_analysts`;
```

### 3.4 Data Scientist（データサイエンティスト）

```sql
-- ML 関連の権限
GRANT USE_CATALOG ON CATALOG prod TO `data_scientists`;
GRANT USE_SCHEMA, SELECT ON SCHEMA prod.gold_analytics TO `data_scientists`;
GRANT USE_SCHEMA, CREATE_TABLE, CREATE_MODEL ON SCHEMA prod.ml TO `data_scientists`;
GRANT USE_SCHEMA, CREATE_TABLE ON SCHEMA prod.ml_features TO `data_scientists`;

-- Dev 環境
GRANT ALL_PRIVILEGES ON CATALOG dev TO `data_scientists`;
```

---

## 4. 権限設計の重要な注意点

| 注意点 | 説明 |
|:---|:---|
| **USE_CATALOG / USE_SCHEMA は前提条件** | SELECT を付与しても USE_CATALOG + USE_SCHEMA がなければアクセス不可 |
| **ALL_PRIVILEGES は動的** | 新しい権限タイプが追加されると自動的に含まれる。Prod 環境での使用は慎重に |
| **権限は明示的に付与** | デフォルトではオーナー以外に権限はない |
| **ワークスペースローカルグループは使用不可** | Unity Catalog ではアカウントレベルグループのみ |
| **サービスプリンシパル** | ジョブの自動実行にはサービスプリンシパルを使用する |
