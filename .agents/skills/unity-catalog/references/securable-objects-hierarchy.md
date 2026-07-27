# Securable Objects の階層と権限一覧

Unity Catalog の Securable Objects（セキュリティ保護可能なオブジェクト）の完全な階層構造と、
各オブジェクトに適用可能な権限を定義する。

---

## 1. 完全な階層構造

```
METASTORE（トップレベルコンテナ）
│
├── CATALOG（第1レベル: 組織単位）
│   └── SCHEMA（第2レベル: データベース相当）
│       ├── TABLE
│       │   ├── Managed Table（Unity Catalog がデータを完全管理）
│       │   ├── External Table（ユーザーがデータのライフサイクルを管理）
│       │   ├── Foreign Table（Lakehouse Federation 経由の外部テーブル）
│       │   ├── Streaming Table（DLT ストリーミングテーブル）
│       │   ├── Online Table（低レイテンシー推論用）
│       │   └── Feature Table（Feature Store テーブル）
│       ├── VIEW
│       │   ├── Standard View（SQL ビュー）
│       │   └── Dynamic View（行/列レベルセキュリティの旧方式）
│       ├── MATERIALIZED VIEW（DLT マテリアライズドビュー）
│       ├── VOLUME
│       │   ├── Managed Volume（非表形式データの完全管理）
│       │   └── External Volume（既存ストレージへのガバナンス適用）
│       ├── FUNCTION（SQL / Python UDF）
│       └── MODEL（MLflow 登録モデル）
│
├── EXTERNAL LOCATION（クラウドストレージパスのマッピング）
├── STORAGE CREDENTIAL（ストレージアクセスの資格情報）
├── SERVICE CREDENTIAL（外部サービスアクセスの資格情報）
├── CONNECTION（Lakehouse Federation 用の接続定義）
│
├── SHARE（Delta Sharing: 共有するテーブルの論理グループ）
├── RECIPIENT（Delta Sharing: データ受信者の定義）
├── PROVIDER（Delta Sharing: データ提供者の定義）
│
├── CLEAN ROOM（クリーンルーム環境）
└── EXTERNAL METADATA（外部メタデータ定義）
```

---

## 2. 権限の継承モデル

Unity Catalog の権限は**階層的に継承**される:

```
METASTORE
  │ ← CREATE CATALOG 等の Metastore レベル権限
  ▼
CATALOG
  │ ← USE_CATALOG, CREATE SCHEMA（カタログ配下すべてに波及）
  ▼
SCHEMA
  │ ← USE_SCHEMA, CREATE TABLE（スキーマ配下すべてに波及）
  ▼
TABLE / VIEW / VOLUME / FUNCTION / MODEL
    ← SELECT, MODIFY 等のオブジェクトレベル権限
```

**継承の原則**:
- 上位レベルで付与した権限は、配下のすべてのオブジェクトに自動適用される
- `USE_CATALOG` がないとカタログ配下のすべてにアクセスできない
- `USE_SCHEMA` がないとスキーマ配下のすべてにアクセスできない
- 下位レベルで権限を明示的に付与しても、上位の `USE_*` がなければアクセス不可

---

## 3. オブジェクト別の詳細

### 3.1 Catalog

| 属性 | 説明 |
|:---|:---|
| **名前空間** | Metastore 直下 |
| **用途** | データの第1レベルの組織化単位 |
| **ストレージ** | オプションで Managed Storage Location を指定可能 |
| **バインディング** | 特定のワークスペースに限定可能 |

### 3.2 Schema

| 属性 | 説明 |
|:---|:---|
| **名前空間** | `catalog.schema` |
| **用途** | データベース相当の論理コンテナ |
| **ストレージ** | オプションで Managed Storage Location を指定（カタログのデフォルトを上書き） |

### 3.3 Table

| サブタイプ | 説明 | フォーマット |
|:---|:---|:---|
| **Managed** | Unity Catalog がデータを完全管理 | Delta Lake（Iceberg は Public Preview） |
| **External** | メタデータのみ UC 管理 | Delta, CSV, JSON, Avro, Parquet, ORC, Text |
| **Foreign** | Lakehouse Federation 経由 | 外部データソースのフォーマット |
| **Streaming** | DLT ストリーミングテーブル | Delta Lake |
| **Online** | 低レイテンシー推論用 | 自動管理 |
| **Feature** | Feature Store テーブル | Delta Lake |

### 3.4 Volume

| サブタイプ | 説明 | 用途 |
|:---|:---|:---|
| **Managed** | UC がデータを完全管理 | ML アーティファクト、ライブラリ |
| **External** | 既存ストレージにガバナンス適用 | 画像、動画、PDF、IoT データ |

### 3.5 Delta Sharing オブジェクト

| オブジェクト | 説明 |
|:---|:---|
| **Share** | 共有するテーブルの論理グループ |
| **Recipient** | データ受信者（組織 / パートナー） |
| **Provider** | データ提供者の参照 |

---

## 4. 権限付与の主体

権限を付与（GRANT）できるのは以下のいずれか:

| 主体 | 説明 |
|:---|:---|
| **Metastore 管理者** | Metastore のすべてのオブジェクトに対して権限を管理可能 |
| **オブジェクトオーナー** | 所有するオブジェクトとその子オブジェクトに対して権限を管理可能 |
| **MANAGE 権限保持者** | 対象オブジェクトに対して権限を管理可能 |
| **親オブジェクトのオーナー** | 子オブジェクトに対して権限を管理可能 |

---

## 5. オブジェクト名の制約

| 制約 | 値 |
|:---|:---|
| 最大文字数 | 255 文字 |
| 大文字/小文字 | すべて小文字で格納 |
| 使用可能文字 | 英数字、アンダースコア、ハイフン |
| 予約語 | SQL 予約語はバッククォートでエスケープ |

---

## 6. リソースクォータ

| リソース | デフォルト上限 |
|:---|:---|
| テーブル / スキーマ | 10,000 |
| テーブル / メタストア | 1,000,000 |
| スキーマ / カタログ | 10,000 |
| カタログ / メタストア | 1,000 |
| External Location / メタストア | 500 |
| Storage Credential / メタストア | 200 |
| Share / メタストア | 500 |
| Recipient / メタストア | 500 |

一部のクォータは Databricks サポートに依頼して引き上げ可能。
`GetQuota` API でクォータ使用量を監視できる。
