# Auto Loader 構成パターン

> Auto Loader（`cloudFiles`）を活用したインクリメンタルなファイル取り込みの構成パターン、ベストプラクティス、コード例をまとめたリファレンス。

---

## 1. Auto Loader の基本

### 概要

Auto Loader はクラウドストレージに到着する新しいデータファイルをインクリメンタルかつ効率的に処理する Structured Streaming ソース。`cloudFiles` フォーマットとして動作する。

### ファイル検出モード

| モード | 仕組み | コスト | 推奨度 |
|:---|:---|:---|:---|
| **File Events** | クラウドイベント通知でファイルを検出 | 低（イベントベース） | 推奨 |
| **Directory Listing** | ディレクトリスキャンでファイルを検出 | 高（スキャンコスト） | フォールバック |

### モード選定の指針

```
Q1: クラウドのイベント通知が利用可能か？
  Yes -> File Events モード（推奨）
  No  -> Directory Listing モード

Q2: File Events で取りこぼしの可能性があるか？
  Yes -> cloudFiles.backfillInterval を設定
  No  -> デフォルト設定で運用
```

---

## 2. 基本パターン

### パターン 1: JSON ファイルの取り込み

```python
# Auto Loader による JSON 取り込み（DLT 内）
import dlt
from pyspark.sql.functions import current_timestamp, input_file_name

@dlt.table(
    name="bronze_events",
    comment="イベントログの生データ取り込み",
    table_properties={"quality": "bronze"}
)
def bronze_events():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", "/mnt/schema/events/")
        .option("cloudFiles.inferColumnTypes", "false")
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .load("/mnt/landing/events/")
        .withColumn("_source_file", input_file_name())
        .withColumn("_ingested_at", current_timestamp())
    )
```

### パターン 2: CSV ファイルの取り込み

```python
@dlt.table(name="bronze_sales")
def bronze_sales():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.schemaLocation", "/mnt/schema/sales/")
        .option("header", "true")
        .option("cloudFiles.inferColumnTypes", "false")
        .option("multiLine", "true")
        .load("/mnt/landing/sales/")
        .withColumn("_source_file", input_file_name())
        .withColumn("_ingested_at", current_timestamp())
    )
```

### パターン 3: Parquet ファイルの取り込み

```python
@dlt.table(name="bronze_transactions")
def bronze_transactions():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "parquet")
        .option("cloudFiles.schemaLocation", "/mnt/schema/transactions/")
        .load("/mnt/landing/transactions/")
        .withColumn("_source_file", input_file_name())
        .withColumn("_ingested_at", current_timestamp())
    )
```

---

## 3. 高度なパターン

### パターン 4: スキーマ進化への対応

```python
@dlt.table(name="bronze_api_responses")
def bronze_api_responses():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", "/mnt/schema/api_responses/")
        .option("cloudFiles.inferColumnTypes", "false")
        # スキーマ進化: 新しいカラムが追加された場合に自動対応
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        # 予期しないスキーマ変更を _rescued_data カラムに退避
        .option("cloudFiles.rescuedDataColumn", "_rescued_data")
        .load("/mnt/landing/api_responses/")
        .withColumn("_source_file", input_file_name())
        .withColumn("_ingested_at", current_timestamp())
    )
```

### パターン 5: バックフィル付き File Events

```python
@dlt.table(name="bronze_logs")
def bronze_logs():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", "/mnt/schema/logs/")
        # File Events モード（デフォルト）
        .option("cloudFiles.useNotifications", "true")
        # 日次バックフィルで取りこぼし防止
        .option("cloudFiles.backfillInterval", "1 day")
        .load("/mnt/landing/logs/")
        .withColumn("_source_file", input_file_name())
        .withColumn("_ingested_at", current_timestamp())
    )
```

### パターン 6: ディレクトリリスティング + クリーンソース

```python
@dlt.table(name="bronze_uploads")
def bronze_uploads():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", "/mnt/schema/uploads/")
        # Directory Listing モード
        .option("cloudFiles.useNotifications", "false")
        # 処理済みファイルをアーカイブディレクトリに移動
        .option("cloudFiles.cleanSource", "archive")
        .option("cloudFiles.sourceArchiveDir", "/mnt/archive/uploads/")
        .load("/mnt/landing/uploads/")
        .withColumn("_source_file", input_file_name())
        .withColumn("_ingested_at", current_timestamp())
    )
```

---

## 4. DLT 以外での Auto Loader 利用

### Notebook でのスタンドアロン利用

```python
# チェックポイントベースのストリーミング取り込み
(spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", "/mnt/schema/orders/")
    .option("cloudFiles.inferColumnTypes", "true")
    .load("/mnt/landing/orders/")
    .writeStream
    .option("checkpointLocation", "/mnt/checkpoint/orders/")
    .trigger(availableNow=True)
    .toTable("catalog.schema.bronze_orders"))
```

### SQL での Auto Loader 利用（DLT 内）

```sql
CREATE OR REFRESH STREAMING TABLE bronze_orders
COMMENT "販売注文の生データ"
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  _metadata.file_modification_time AS _file_modified_at,
  current_timestamp() AS _ingested_at
FROM cloud_files(
  "/mnt/landing/orders/",
  "json",
  map(
    "cloudFiles.inferColumnTypes", "false",
    "cloudFiles.schemaEvolutionMode", "addNewColumns"
  )
);
```

---

## 5. トリガーモードの選定

| トリガーモード | 構文 | ユースケース | コスト特性 |
|:---|:---|:---|:---|
| **availableNow** | `.trigger(availableNow=True)` | 定時バッチ（推奨） | ジョブ終了で課金停止 |
| **once** | `.trigger(once=True)` | 一回限りの取り込み | 最小コスト |
| **processingTime** | `.trigger(processingTime="5 minutes")` | ニアリアルタイム | マイクロバッチ間で待機 |
| **continuous** | DLT continuous=true | リアルタイム | 常時起動 |

### 選定指針

```
Q1: レイテンシ要件は？
  秒単位       -> continuous (DLT) または processingTime("10 seconds")
  分単位       -> processingTime("1 minute") ~ processingTime("5 minutes")
  時間単位     -> availableNow（推奨）
  一回きり     -> once
```

---

## 6. ベストプラクティス

### 必須設定

| 設定 | 推奨値 | 理由 |
|:---|:---|:---|
| `cloudFiles.schemaLocation` | 固定パス | スキーマ推論結果の永続化 |
| `cloudFiles.format` | ソースに合わせて | 明示的に指定 |
| `checkpointLocation` | 固定パス（DLT 外） | 処理状態の永続化 |

### 推奨設定

| 設定 | 推奨値 | 理由 |
|:---|:---|:---|
| `cloudFiles.inferColumnTypes` | `"false"`（Bronze） | Bronze は STRING 保存を優先 |
| `cloudFiles.schemaEvolutionMode` | `"addNewColumns"` | スキーマ変更への自動対応 |
| `cloudFiles.rescuedDataColumn` | `"_rescued_data"` | パース失敗データの退避 |
| `cloudFiles.backfillInterval` | `"1 day"` | File Events の取りこぼし防止 |

### 運用上の注意事項

| 項目 | 注意点 |
|:---|:---|
| 7 日ルール | File Events モードでは 7 日以内にストリームを実行すること。超えるとフルスキャンが発生 |
| イミュータブルファイル | `cloudFiles.allowOverwrites = false`（デフォルト）を維持。ファイルの上書きは想定しない |
| チェックポイント | チェックポイントの場所を変更しない。変更すると全ファイルが再処理される |
| パーティション構造 | ソースディレクトリのパーティション構造（`year=2024/month=01/`）は自動検出される |
| ファイルサイズ | 小さすぎるファイル（< 1MB）が大量にある場合はパフォーマンスが低下する。ソース側での統合を検討 |

---

## 7. トラブルシューティング

| 問題 | 原因 | 対処法 |
|:---|:---|:---|
| ファイルが検出されない | File Events の通知設定ミス | Directory Listing にフォールバックし、原因を調査 |
| スキーマ推論エラー | 不正なファイルが混在 | `cloudFiles.rescuedDataColumn` を設定し、不正データを退避 |
| 処理が遅い | 小ファイルが大量 | ソース側でファイル統合、または `maxFilesPerTrigger` を調整 |
| 重複データ | `allowOverwrites = true` に設定 | デフォルトの `false` に戻し、ソースのイミュータビリティを確保 |
| メモリ不足 | 1 ファイルが巨大 | `maxBytesPerTrigger` で 1 トリガーあたりの処理量を制限 |
