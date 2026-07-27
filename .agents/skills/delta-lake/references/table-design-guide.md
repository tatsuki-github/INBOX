# テーブル設計ガイド

> パーティション / Liquid Clustering / Deletion Vectors の選定フローと設計ガイドライン

---

## 1. クラスタリング戦略の選定フロー

```
テーブルサイズは?
│
├── < 1TB
│   ├── 新規テーブル → Liquid Clustering（推奨）
│   └── 既存テーブル → パーティションなしで運用、必要なら Liquid Clustering を追加
│
└── >= 1TB
    ├── 新規テーブル → Liquid Clustering（推奨）
    └── 既存パーティションテーブル
         ├── パーティション設計に問題がない → 現行維持
         ├── Small File Problem がある → Liquid Clustering への移行を検討
         └── パーティション列を変更したい → Liquid Clustering への移行（キー変更がメタデータのみ）
```

**結論:** Databricks は新規テーブル（Streaming テーブルやマテリアライズドビューを含む）すべてに Liquid Clustering を推奨している。

---

## 2. Liquid Clustering 設計ガイドライン

### 2.1 キー選定の原則

| 原則 | 説明 | 例 |
|:---|:---|:---|
| **クエリパターンに基づく** | WHERE 句・JOIN 条件で頻繁に使われる列を選択 | `customer_id`, `event_date` |
| **キー数は 1-4 列** | 多すぎると Data Skipping の効果が薄れる | 2-3 列が最適 |
| **中〜高カーディナリティ** | 低すぎると効果が薄く、極端に高いとコストが増す | 日付列、リージョン列 |
| **更新パターンを考慮** | MERGE のマッチ条件に含まれる列を優先 | ビジネスキー |

### 2.2 Liquid Clustering の SQL パターン

```sql
-- テーブル作成時に指定
CREATE TABLE events (
  event_id BIGINT,
  event_date DATE,
  customer_id STRING,
  event_type STRING,
  payload STRING
)
USING DELTA
CLUSTER BY (event_date, customer_id);

-- クラスタリングキーの変更（データ書き換え不要）
ALTER TABLE events CLUSTER BY (customer_id, event_type);

-- クラスタリングの解除
ALTER TABLE events CLUSTER BY NONE;
```

### 2.3 既存パーティションテーブルからの移行

1. 新しい Liquid Clustering テーブルを作成する
2. `INSERT INTO ... SELECT * FROM` でデータをコピーする
3. `OPTIMIZE` を実行してクラスタリングを適用する
4. 旧テーブルからの参照を切り替える
5. 旧テーブルを DROP する

**注意:** Liquid Clustering はパーティショニング・Z-Ordering と非互換。同一テーブルでの併用は不可。

---

## 3. パーティショニング設計ガイドライン（既存テーブル向け）

### 3.1 パーティション列の選定基準

| 基準 | 推奨 | 非推奨 |
|:---|:---|:---|
| カーディナリティ | 低〜中（日付、リージョン） | 高（user_id, transaction_id） |
| パーティションサイズ | 各パーティション 1GB 以上 | 1GB 未満（Small File Problem） |
| クエリでのフィルタ頻度 | 頻繁にフィルタされる列 | ほとんどフィルタされない列 |
| 列数 | 1-2 列 | 3 列以上 |

### 3.2 パーティショニングの注意点

- パーティション列の選択を後から変更するにはテーブル全体の書き換えが必要
- 高カーディナリティ列でパーティションすると Small File Problem を引き起こす
- パーティション列をまたぐクエリのパフォーマンスが悪化する

---

## 4. Z-Ordering vs Liquid Clustering 比較

| 比較項目 | Z-Ordering | Liquid Clustering |
|:---|:---|:---|
| **最適化方法** | テーブル/パーティション全体を書き換え | 未クラスタリングの ZCube のみ処理（インクリメンタル） |
| **コスト** | 大規模テーブルでは非常に高い | インクリメンタルで低コスト |
| **キー変更** | OPTIMIZE コマンドで都度指定 | ALTER TABLE で永続的に変更可能 |
| **パーティショニングとの関係** | 併用可能 | 非互換 |
| **障害耐性** | 途中失敗で最初からやり直し | ZCube 単位で部分的進行が可能 |
| **MERGE 後のレイアウト** | データレイアウトが崩れる | Low Shuffle Merge でレイアウト維持 |
| **推奨ワークロード** | 読み取り専用に近いテーブル | 更新が頻繁なテーブル |

---

## 5. Deletion Vectors 設計ガイドライン

### 5.1 有効化判断フロー

```
UPDATE / DELETE 操作がある?
├── Yes → Deletion Vectors を有効化
│   ├── 頻繁な更新/削除 → 有効化必須 + REORG TABLE の定期実行を計画
│   └── 稀な更新/削除 → 有効化推奨（オーバーヘッドは最小限）
└── No（Append Only） → 有効化不要（害はないが恩恵もない）
```

### 5.2 Deletion Vectors の動作

1. DELETE / UPDATE 実行時、Parquet ファイルは書き換えず、削除行の RoaringBitmap を記録
2. 読み取り時、Deletion Vector で該当行をフィルタアウト（Merge-on-Read）
3. 物理的な削除は OPTIMIZE / REORG TABLE で実行

### 5.3 メンテナンス

```sql
-- Deletion Vectors の有効化
ALTER TABLE my_table SET TBLPROPERTIES ('delta.enableDeletionVectors' = true);

-- ソフトデリートの物理適用
REORG TABLE my_table APPLY (PURGE);

-- 特定パーティションのみ物理適用
REORG TABLE events WHERE date >= '2025-01-01' APPLY (PURGE);
```

**重要:** REORG TABLE 後も古いファイルはディスク上に残る。物理削除には VACUUM が必要。

---

## 6. スキーマ設計のベストプラクティス

### 6.1 列の配置順序

Data Skipping はデフォルトで**最初の 32 カラム**の統計情報を収集する。フィルタや JOIN で頻繁に使われるカラムを先頭に配置する。

```sql
CREATE TABLE optimized_table (
  -- 頻繁にフィルタされる列を先頭に（Data Skipping 対象）
  event_date DATE,
  customer_id STRING,
  region STRING,
  event_type STRING,
  -- 以降は分析で使う列
  amount DECIMAL(18,2),
  quantity INT,
  -- 大きなカラムやフィルタで使わない列は後方
  metadata STRING,
  raw_payload STRING
)
USING DELTA
CLUSTER BY (event_date, customer_id);
```

### 6.2 Column Mapping

カラムの名前変更や削除が予想される場合、Column Mapping を有効化しておく:

```sql
ALTER TABLE my_table SET TBLPROPERTIES (
  'delta.minReaderVersion' = '2',
  'delta.minWriterVersion' = '5',
  'delta.columnMapping.mode' = 'name'
);
```

### 6.3 スキーマ進化のポリシー

| 方針 | 設定 | ユースケース |
|:---|:---|:---|
| 厳格（デフォルト） | スキーマ適用のみ | 本番テーブル |
| 柔軟 | `mergeSchema = true`（書き込み時） | Bronze 層、進化が頻繁なテーブル |
| 置換 | `overwriteSchema = true` | 完全にスキーマを変更する場合 |
| 明示的 | `ALTER TABLE ADD COLUMN` | ガバナンスが必要な場合 |

---

## 7. テーブルプロパティ設定チェックリスト

新規テーブル作成時に検討すべきプロパティ:

- [ ] `CLUSTER BY` — クラスタリングキーの設定
- [ ] `delta.enableDeletionVectors` — UPDATE / DELETE がある場合 `true`
- [ ] `delta.enableChangeDataFeed` — 下流パイプラインが変更データを使う場合 `true`
- [ ] `delta.logRetentionDuration` — CDF 利用時は `interval 30 days` 以上
- [ ] `delta.deletedFileRetentionDuration` — タイムトラベル要件に合わせて設定
- [ ] `delta.dataSkippingNumIndexedCols` — 32 列以上にフィルタ対象列がある場合に調整
- [ ] `delta.autoOptimize.optimizeWrite` — 書き込みファイルサイズの最適化
- [ ] `delta.autoOptimize.autoCompact` — 書き込み後の自動コンパクション
- [ ] `delta.columnMapping.mode` — カラム名変更 / 削除が必要な場合 `name`
- [ ] `delta.universalFormat.enabledFormats` — Iceberg 互換が必要な場合 `iceberg`
