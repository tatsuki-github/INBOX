# Delta Lake バージョン別新機能サマリー

> Delta Lake 3.x / 4.x の新機能と互換性情報

---

## 1. Delta Lake 3.3 の主要機能

| 機能 | 説明 | 影響範囲 |
|:---|:---|:---|
| **Identity Column** | 行に一意のオートインクリメント ID を自動割り当て | テーブル設計 |
| **VACUUM LITE** | トランザクションログで高速 VACUUM（従来比 5-10x） | 運用・メンテナンス |
| **Row Tracking Backfill** | 既存テーブルへの Row Tracking 有効化 | データ操作 |
| **Version Checksums** | テーブル状態の検証を強化 | データ品質 |
| **UniForm Iceberg on Existing Tables** | 既存テーブルへのデータ書き換えなしで UniForm 有効化 | 互換性 |
| **Liquid Clustering の改善** | クラスタリングのパフォーマンス向上 | パフォーマンス |

### VACUUM LITE の詳細

- トランザクションログを使用して不要ファイルを特定する
- ディレクトリリスティングが不要になるため、大幅に高速化
- 定期的に VACUUM を実行しているテーブルで最大の効果を発揮
- 初回実行時は通常の VACUUM と同じ速度

### UniForm on Existing Tables

- 既存の Delta テーブルにデータ書き換えなしで UniForm を有効化可能
- `ALTER TABLE ... SET TBLPROPERTIES ('delta.universalFormat.enabledFormats' = 'iceberg')` で有効化
- 以降の書き込み時に Iceberg メタデータが自動生成される

---

## 2. Delta Lake 4.0 の主要機能

| 機能 | 説明 | 影響範囲 |
|:---|:---|:---|
| **Delta Connect** | Spark Connect の完全サポート。リモート Delta 操作 | アーキテクチャ |
| **Coordinated Commits** | 複数クラスタからの安全な同時書き込み | データ操作 |
| **Variant データ型** | スキーマレス半構造化データの高性能格納 | テーブル設計 |
| **Type Widening の拡張** | INT→LONG 等の型拡張をデータ書き換えなしで実行 | スキーマ進化 |
| **Identity Columns** | 行ごとの一意 ID の自動生成 | テーブル設計 |
| **Collations** | 言語・大文字小文字を考慮したソートと比較 | クエリ |

### Coordinated Commits の詳細

```
Writer A ──┐
           │
Writer B ──┤──→ Commit Coordinator ──→ Delta Table
           │      (DynamoDB等)
Writer C ──┘
```

- テーブルに「Commit Coordinator」を指定し、全書き込みを中央管理
- 異なるクラスタ / ジョブからの同時書き込みを安全に調整
- DynamoDB Commit Coordinator が同梱されている
- 高頻度の同時書き込みが発生するユースケースで有効

### Variant データ型の詳細

```sql
-- Variant カラムを持つテーブル
CREATE TABLE events (
  event_id BIGINT,
  event_date DATE,
  payload VARIANT  -- スキーマレスの半構造化データ
)
USING DELTA;

-- Variant データの挿入
INSERT INTO events VALUES (
  1, '2025-01-01',
  PARSE_JSON('{"user": "alice", "action": "click", "metadata": {"browser": "Chrome"}}')
);

-- Variant データのクエリ
SELECT
  event_id,
  payload:user::STRING as user_name,
  payload:metadata:browser::STRING as browser
FROM events;
```

**従来の JSON 文字列格納との比較:**
- パフォーマンス: Variant はバイナリ形式で格納されるため、クエリ時のパースが不要
- 柔軟性: スキーマ定義なしで任意の構造を格納可能
- Data Skipping: Variant 内のフィールドに対しても統計情報を活用可能

### Type Widening

```sql
-- Type Widening の有効化
ALTER TABLE my_table SET TBLPROPERTIES ('delta.enableTypeWidening' = 'true');

-- 型の変更（データ書き換え不要）
ALTER TABLE my_table ALTER COLUMN amount TYPE DECIMAL(20,4);
```

**対応する型変更:**

| 変更元 | 変更先 |
|:---|:---|
| BYTE | SHORT, INT, LONG, DECIMAL, DOUBLE |
| SHORT | INT, LONG, DECIMAL, DOUBLE |
| INT | LONG, DECIMAL, DOUBLE |
| LONG | DECIMAL |
| FLOAT | DOUBLE |
| DATE | TIMESTAMP_NTZ |

---

## 3. Delta Kernel

### 概要

Delta Kernel は Java と Rust で実装されたライブラリ群で、Delta プロトコルの詳細を隠蔽し、シンプルな API で Delta テーブルの読み書きを可能にする。

### アーキテクチャ

```
+-------------------+
|  Your Application |
+-------------------+
         |
+-------------------+
|   Delta Kernel    |  ← シンプルな読み書き API
+-------------------+
         |
+-------------------+
| Engine Interface  |  ← Parquet 読み取り、JSON パース等をプラグイン可能
+-------------------+
```

### 主な利用例

| エンジン | 実装 | 状態 |
|:---|:---|:---|
| DuckDB | delta-kernel-rs | ネイティブ Delta サポート |
| Apache Flink | delta-kernel (Java) | 開発中 |
| カスタムエンジン | delta-kernel API | プラガブル |

---

## 4. OSS Delta Lake と Databricks Delta Lake の機能比較

| 機能 | OSS | Databricks | 備考 |
|:---|:---|:---|:---|
| ACID トランザクション | Yes | Yes | コア機能 |
| タイムトラベル | Yes | Yes | コア機能 |
| スキーマ適用 / 進化 | Yes | Yes | コア機能 |
| OPTIMIZE / VACUUM | Yes | Yes | Databricks は VACUUM LITE 対応 |
| Liquid Clustering | Yes | Yes | Databricks は Predictive Optimization で自動化可能 |
| Deletion Vectors | Yes | Yes | Databricks は Predictive I/O と組み合わせ |
| UniForm | Yes | Yes | Iceberg / Hudi 互換 |
| Delta Sharing | Yes | Yes | Databricks は管理 UI 付き |
| CDF | Yes | Yes | コア機能 |
| Delta Connect | Yes | Yes | 4.0+ |
| Delta Kernel | Yes | Yes | Java / Rust |
| Auto Loader | No | Yes | Databricks 専用 |
| DLT / Expectations | No | Yes | Databricks 専用 |
| Photon Engine | No | Yes | Databricks 専用 |
| Predictive Optimization | No | Yes | Databricks 専用 |
| Low Shuffle Merge | No | Yes | Databricks 専用 |

---

## 5. バージョン互換性マトリクス

| Delta Lake | Spark | Databricks Runtime | 主要な新機能 |
|:---|:---|:---|:---|
| 2.4 | 3.4 | DBR 13.3 LTS | Liquid Clustering GA |
| 3.0 | 3.5 | DBR 14.3 LTS | MERGE 56% 高速化 |
| 3.3 | — | DBR 15.x | VACUUM LITE, UniForm on Existing Tables |
| 4.0 | — | DBR 16.x | Coordinated Commits, Variant, Delta Connect |

**注意:** Databricks Runtime のバージョンと OSS Delta Lake のバージョンは必ずしも 1:1 で対応しない。Databricks は独自のリリースサイクルで Delta Lake の機能を取り込んでいる。
