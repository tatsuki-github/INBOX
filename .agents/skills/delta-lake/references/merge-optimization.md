# MERGE パフォーマンスチューニング

> MERGE パフォーマンスチューニング 7 原則と SQL パターン

---

## 1. MERGE の基本構文

```sql
MERGE INTO target_table t
USING source_table s
ON t.id = s.id
WHEN MATCHED AND s.op = 'DELETE' THEN DELETE
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
```

MERGE は最も柔軟だが、最もコストが高い操作。**単純な INSERT / UPDATE / DELETE で代替できないか**を常に検討すること。

---

## 2. 7 つの最適化原則

### 原則 1: 検索空間の削減（最重要）

マッチ条件にクラスタリングキー / パーティション列を含め、スキャン対象を最小化する。

```sql
-- 悪い例: id だけでマッチ（全ファイルスキャン）
MERGE INTO target t
USING source s
ON t.id = s.id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

-- 良い例: クラスタリングキーを追加
MERGE INTO target t
USING source s
ON t.id = s.id AND t.event_date = s.event_date
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
```

**効果:** 関連するパーティション / ファイルのみがスキャンされ、I/O が大幅に削減される。

### 原則 2: ソースデータの事前フィルタリング

不要な行を MERGE に送らず、ソーステーブルを事前に絞り込む。

```sql
-- 悪い例: ソース全体を MERGE に渡す
MERGE INTO target t
USING source s
ON t.id = s.id ...

-- 良い例: サブクエリで事前フィルタリング
MERGE INTO target t
USING (
  SELECT * FROM source
  WHERE change_date = current_date()
  AND is_valid = true
) s
ON t.id = s.id ...
```

**効果:** ソース側の行数が減り、マッチング処理のコストが低減する。

### 原則 3: ファイルのコンパクション

小さなファイルが多いとマッチ検索が遅くなる。MERGE 前に OPTIMIZE を実行する。

```sql
-- MERGE 前に OPTIMIZE を実行
OPTIMIZE target_table WHERE event_date >= date_sub(current_date(), 7);

-- その後に MERGE
MERGE INTO target_table t
USING source s
ON ...
```

**目標:** 各ファイルサイズを 256MB - 1GB に統合する。

### 原則 4: Low Shuffle Merge の活用

Databricks Runtime 10.4+ でデフォルト有効。未変更行を軽量パスで処理し、シャッフルを大幅に削減する。

| 条件 | Low Shuffle Merge の効果 |
|:---|:---|
| 更新行が少なく、コピー行が多い | 非常に高い |
| 更新行がテーブルの大半 | 限定的 |
| MERGE 後のデータレイアウト維持 | Liquid Clustering との組み合わせで効果的 |

**確認方法:**
```python
# Low Shuffle Merge が有効か確認
spark.conf.get("spark.databricks.delta.merge.lowShuffle.enabled")
```

### 原則 5: Optimized Writes の有効化

パーティションテーブルでの MERGE 時、小ファイルの大量生成を防止する。

```python
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
```

特に**パーティション列をまたぐ MERGE** で効果が大きい。

### 原則 6: Liquid Clustering の採用

Z-Ordering と異なり、Liquid Clustering はインクリメンタルで、MERGE 後の再最適化コストが低い。

| 観点 | Z-Ordering | Liquid Clustering |
|:---|:---|:---|
| MERGE 後の再最適化 | テーブル全体を書き換え | 未クラスタリング部分のみ処理 |
| コスト | 高い | 低い |
| レイアウト維持 | 崩れる | Low Shuffle Merge と組み合わせで維持 |

### 原則 7: MERGE 頻度の最小化

MERGE は可能な限り遅く・少なく実行する。

**代替パターン:**
- **Append + CDF**: データを Append で追加し、CDF で変更をキャプチャ
- **INSERT OVERWRITE**: パーティション単位での置換で MERGE を回避
- **バッチ集約**: 小さな MERGE を集約して 1 回の大きな MERGE にする

---

## 3. MERGE の典型パターン

### 3.1 SCD Type 1（最新値のみ保持）

```sql
MERGE INTO dim_customer t
USING staging_customer s
ON t.customer_id = s.customer_id
WHEN MATCHED THEN
  UPDATE SET
    t.name = s.name,
    t.email = s.email,
    t.updated_at = current_timestamp()
WHEN NOT MATCHED THEN
  INSERT (customer_id, name, email, created_at, updated_at)
  VALUES (s.customer_id, s.name, s.email, current_timestamp(), current_timestamp());
```

### 3.2 SCD Type 2（履歴保持）

```sql
-- Step 1: 既存レコードのクローズ
MERGE INTO dim_customer t
USING (
  SELECT s.*, t.surrogate_key
  FROM staging_customer s
  JOIN dim_customer t ON s.customer_id = t.customer_id
  WHERE t.is_current = true
    AND (t.name != s.name OR t.email != s.email)
) changes
ON t.surrogate_key = changes.surrogate_key
WHEN MATCHED THEN
  UPDATE SET
    t.is_current = false,
    t.end_date = current_date();

-- Step 2: 新しいバージョンの挿入
INSERT INTO dim_customer
SELECT
  uuid() as surrogate_key,
  customer_id, name, email,
  current_date() as start_date,
  null as end_date,
  true as is_current
FROM staging_customer s
WHERE EXISTS (
  SELECT 1 FROM dim_customer t
  WHERE t.customer_id = s.customer_id
    AND t.is_current = false
    AND t.end_date = current_date()
)
OR NOT EXISTS (
  SELECT 1 FROM dim_customer t
  WHERE t.customer_id = s.customer_id
);
```

### 3.3 Delete + Upsert パターン

```sql
MERGE INTO target t
USING source s
ON t.id = s.id AND t.region = s.region
WHEN MATCHED AND s.operation = 'DELETE' THEN DELETE
WHEN MATCHED AND s.operation = 'UPDATE' THEN UPDATE SET *
WHEN NOT MATCHED AND s.operation != 'DELETE' THEN INSERT *;
```

---

## 4. MERGE パフォーマンス診断チェックリスト

MERGE が遅い場合、以下を順に確認する:

| 順序 | 確認項目 | 対処法 |
|:---|:---|:---|
| 1 | マッチ条件にクラスタリングキー / パーティション列があるか | 追加する |
| 2 | ソースデータが事前にフィルタリングされているか | サブクエリで絞り込む |
| 3 | ターゲットテーブルに小ファイルが多くないか | OPTIMIZE を事前実行 |
| 4 | Low Shuffle Merge が有効か | Spark 設定を確認 |
| 5 | Optimized Writes が有効か | テーブルプロパティを確認 |
| 6 | MERGE の頻度は最小限か | バッチ集約や CDF での代替を検討 |
| 7 | Liquid Clustering を使用しているか | 移行を検討 |

---

## 5. パフォーマンス計測

MERGE のパフォーマンスを計測し、改善効果を確認する:

```sql
-- MERGE 実行前のテーブル状態
DESCRIBE DETAIL target_table;
-- → numFiles, sizeInBytes を記録

-- MERGE 実行
MERGE INTO target_table t ...

-- 直近の操作のメトリクスを確認
DESCRIBE HISTORY target_table LIMIT 1;
-- → operationMetrics に numTargetRowsInserted, numTargetRowsUpdated,
--   numTargetRowsDeleted, numTargetFilesAdded, numTargetFilesRemoved が含まれる
```

**注目すべきメトリクス:**
- `numTargetFilesAdded` / `numTargetFilesRemoved`: ファイル書き換え量
- `executionTimeMs`: 実行時間
- `scanTimeMs` / `rewriteTimeMs`: スキャンと書き換えの内訳
