# テーブルプロパティリファレンス

> Delta Lake テーブルプロパティの設定値・デフォルト・影響範囲

---

## 1. データレイアウト関連

| プロパティ | デフォルト | 説明 |
|:---|:---|:---|
| `delta.dataSkippingNumIndexedCols` | `32` | Data Skipping の統計情報を収集するカラム数。先頭 N カラムが対象 |
| `delta.dataSkippingStatsColumns` | — | 統計情報を収集する特定カラム名のカンマ区切りリスト（`NumIndexedCols` より優先） |

---

## 2. Deletion Vectors 関連

| プロパティ | デフォルト | 説明 |
|:---|:---|:---|
| `delta.enableDeletionVectors` | `true`（DBR 14.0+） | Deletion Vectors の有効化。UPDATE / DELETE が高速化 |

---

## 3. Change Data Feed 関連

| プロパティ | デフォルト | 説明 |
|:---|:---|:---|
| `delta.enableChangeDataFeed` | `false` | CDF の有効化。有効にすると INSERT / UPDATE / DELETE の変更記録が自動生成される |

---

## 4. 保持期間関連

| プロパティ | デフォルト | 説明 |
|:---|:---|:---|
| `delta.logRetentionDuration` | `interval 30 days` | トランザクションログの保持期間。CDF 利用時は十分な期間を確保する |
| `delta.deletedFileRetentionDuration` | `interval 7 days` | VACUUM が削除する前のファイル保持期間。タイムトラベル可能期間に影響 |

---

## 5. 自動最適化関連

| プロパティ | デフォルト | 説明 |
|:---|:---|:---|
| `delta.autoOptimize.optimizeWrite` | `false` | 書き込み時にファイルサイズを自動最適化。パーティションテーブルの MERGE 時に特に効果的 |
| `delta.autoOptimize.autoCompact` | `false` | 書き込み完了後に自動で小ファイルを結合。Auto Compaction |

---

## 6. Column Mapping 関連

| プロパティ | デフォルト | 説明 |
|:---|:---|:---|
| `delta.columnMapping.mode` | `none` | `name`: カラム名変更・削除を有効化。`id`: 内部 ID ベースのマッピング。`none`: 無効 |
| `delta.minReaderVersion` | `1` | Column Mapping 利用時は `2` 以上が必要 |
| `delta.minWriterVersion` | `2` | Column Mapping 利用時は `5` 以上が必要 |

---

## 7. UniForm 関連

| プロパティ | デフォルト | 説明 |
|:---|:---|:---|
| `delta.universalFormat.enabledFormats` | — | UniForm の有効化。`iceberg` を指定すると Iceberg メタデータを自動生成 |

---

## 8. Predictive Optimization 関連

| プロパティ | デフォルト | 説明 |
|:---|:---|:---|
| `delta.enablePredictiveOptimization` | — | Predictive Optimization の有効化（Databricks 専用） |

---

## 9. Spark セッション設定（テーブルプロパティではない）

以下は `spark.conf.set()` で設定するセッションレベルの設定:

| 設定キー | デフォルト | 説明 |
|:---|:---|:---|
| `spark.databricks.delta.merge.lowShuffle.enabled` | `true`（DBR 10.4+） | Low Shuffle Merge の有効化 |
| `spark.databricks.delta.autoCompact.enabled` | `false` | セッションレベルの Auto Compaction 有効化 |
| `spark.databricks.delta.autoCompact.minNumFiles` | `50` | Auto Compaction のトリガーとなる最小ファイル数 |
| `spark.databricks.delta.autoCompact.maxFileSize` | `134217728`（128MB） | Auto Compaction の出力ファイルサイズ |
| `spark.databricks.delta.optimizeWrite.enabled` | `false` | セッションレベルの Optimized Writes 有効化 |
| `spark.sql.shuffle.partitions` | `200` | シャッフルパーティション数。MERGE のパフォーマンスに影響 |

---

## 10. プロパティの設定方法

### テーブル作成時

```sql
CREATE TABLE my_table (...)
USING DELTA
TBLPROPERTIES (
  'delta.enableDeletionVectors' = 'true',
  'delta.enableChangeDataFeed' = 'true',
  'delta.logRetentionDuration' = 'interval 30 days',
  'delta.deletedFileRetentionDuration' = 'interval 7 days',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);
```

### 既存テーブルへの設定

```sql
ALTER TABLE my_table SET TBLPROPERTIES (
  'delta.enableDeletionVectors' = 'true',
  'delta.enableChangeDataFeed' = 'true'
);
```

### プロパティの確認

```sql
SHOW TBLPROPERTIES my_table;

-- 特定プロパティの確認
SHOW TBLPROPERTIES my_table ('delta.enableDeletionVectors');
```

### プロパティの削除

```sql
ALTER TABLE my_table UNSET TBLPROPERTIES ('delta.autoOptimize.optimizeWrite');
```

---

## 11. 用途別の推奨プロパティセット

### Bronze 層テーブル

```sql
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.logRetentionDuration' = 'interval 30 days'
)
```

### Silver 層テーブル

```sql
TBLPROPERTIES (
  'delta.enableDeletionVectors' = 'true',
  'delta.enableChangeDataFeed' = 'true',
  'delta.logRetentionDuration' = 'interval 30 days',
  'delta.deletedFileRetentionDuration' = 'interval 7 days',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
)
```

### Gold 層テーブル

```sql
TBLPROPERTIES (
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'delta.deletedFileRetentionDuration' = 'interval 7 days'
)
```
