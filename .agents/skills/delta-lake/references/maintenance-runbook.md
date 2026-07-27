# メンテナンス運用ガイド

> OPTIMIZE / VACUUM / ANALYZE スケジューリングガイドとトラブルシューティング

---

## 1. メンテナンスタスク一覧

| タスク | 目的 | 頻度 | 実行順序 |
|:---|:---|:---|:---|
| **OPTIMIZE** | 小ファイルの統合（bin-compaction） | 日次〜週次 | 1番目 |
| **VACUUM** | 不要ファイルの物理削除 | 日次〜週次 | 2番目（OPTIMIZE の後） |
| **ANALYZE TABLE** | 統計情報の更新 | 週次 / 大量ロード後 | 3番目 |
| **REORG TABLE APPLY (PURGE)** | Deletion Vectors の物理適用 | 月次 | 適宜 |

**重要:** 実行順序は必ず **OPTIMIZE → VACUUM → ANALYZE** の順にする。

---

## 2. OPTIMIZE の運用

### 2.1 基本コマンド

```sql
-- テーブル全体の最適化
OPTIMIZE catalog.silver.events;

-- 最新データのみ最適化（推奨）
OPTIMIZE catalog.silver.events
WHERE event_date >= date_sub(current_date(), 7);

-- Z-Ordering 付き最適化（Liquid Clustering 非使用時のみ）
OPTIMIZE catalog.silver.events
WHERE event_date >= date_sub(current_date(), 7)
ZORDER BY (customer_id);
```

### 2.2 スケジューリングガイドライン

| ワークロードタイプ | 推奨頻度 | 対象範囲 |
|:---|:---|:---|
| 高頻度書き込み（ストリーミング） | 日次 | 直近 1-7 日分 |
| 中頻度書き込み（日次バッチ） | 日次〜週次 | 直近バッチの対象範囲 |
| 低頻度書き込み（週次以下） | 週次 | テーブル全体（小規模の場合） |

### 2.3 Auto Compaction vs スケジュール OPTIMIZE

| 項目 | Auto Compaction | スケジュール OPTIMIZE |
|:---|:---|:---|
| トリガー | 書き込み完了後に自動実行 | ジョブスケジューラで定期実行 |
| 対象 | 書き込みがあったファイルのみ | 指定範囲全体 |
| リソース消費 | 書き込みジョブと同じクラスタ | 別のクラスタで実行可能 |
| レイテンシへの影響 | 書き込み完了時間が延びる | 書き込みジョブに影響なし |
| 推奨 | ほとんどのワークロードで十分 | レイテンシ要件が厳しい場合 |

**判断基準:** まず Auto Compaction を有効にし、レイテンシ要件を満たせない場合にスケジュール OPTIMIZE に切り替える。

---

## 3. VACUUM の運用

### 3.1 基本コマンド

```sql
-- デフォルト保持期間（7日）での VACUUM
VACUUM catalog.silver.events;

-- 保持期間を指定
VACUUM catalog.silver.events RETAIN 168 HOURS;  -- 7日

-- ドライラン（削除対象ファイルの確認のみ）
VACUUM catalog.silver.events DRY RUN;
```

### 3.2 保持期間の設計

| 要件 | 推奨保持期間 | 設定 |
|:---|:---|:---|
| 標準（タイムトラベル不要） | 7 日（デフォルト） | `RETAIN 168 HOURS` |
| タイムトラベル 30 日 | 30 日 | `RETAIN 720 HOURS` |
| CDF 利用あり | 30 日以上 | `delta.logRetentionDuration = 'interval 30 days'` も合わせて設定 |
| ストレージコスト重視 | 最短 7 日 | デフォルトを維持 |
| 監査要件あり | 90 日以上 | 要件に合わせて設定 |

**重要:** 実効的なタイムトラベル可能期間 = `min(ファイル保持期間, 最後の VACUUM 以降の期間)`

### 3.3 VACUUM LITE（Delta 3.3+）

定期的に VACUUM を実行しているテーブルで 5-10 倍高速:
- トランザクションログを使用して不要ファイルを特定（ディレクトリリスティング不要）
- 初回実行時は通常の VACUUM と同じ速度
- 2 回目以降で高速化の効果が発揮される

### 3.4 VACUUM 実行時の注意事項

- VACUUM 中も他の読み書きは通常どおり可能
- VACUUM は不可逆操作 — 削除されたファイルは復元できない
- 保持期間を 7 日未満に設定すると、同時実行中のクエリが失敗する可能性がある
- ドライラン（`DRY RUN`）で事前に削除対象を確認することを推奨

---

## 4. ANALYZE TABLE の運用

### 4.1 基本コマンド

```sql
-- Delta 統計情報の更新（Data Skipping 用）
ANALYZE TABLE catalog.silver.events COMPUTE DELTA STATISTICS;

-- クエリオプティマイザ統計情報の更新
ANALYZE TABLE catalog.silver.events COMPUTE STATISTICS;

-- 全カラムの統計情報
ANALYZE TABLE catalog.silver.events COMPUTE STATISTICS FOR ALL COLUMNS;

-- 特定カラムの統計情報
ANALYZE TABLE catalog.silver.events
COMPUTE STATISTICS FOR COLUMNS event_date, customer_id;
```

### 4.2 使い分け

| コマンド | 目的 | 推奨タイミング |
|:---|:---|:---|
| `COMPUTE DELTA STATISTICS` | Data Skipping の統計更新（min/max/null count） | 大量データロード後 |
| `COMPUTE STATISTICS` | クエリオプティマイザの統計更新 | 週次 |
| `FOR ALL COLUMNS` | 全カラムの詳細統計 | 初期設定時 |
| `FOR COLUMNS col1, col2` | 特定カラムの統計 | フィルタ/JOIN で使う列に対して |

---

## 5. REORG TABLE の運用

### 5.1 基本コマンド

```sql
-- Deletion Vectors のソフトデリートを物理適用
REORG TABLE catalog.silver.events APPLY (PURGE);

-- 特定範囲のみ物理適用
REORG TABLE catalog.silver.events
WHERE event_date >= '2025-01-01'
APPLY (PURGE);
```

### 5.2 実行タイミング

- Deletion Vectors が大量に蓄積し、読み取りパフォーマンスが低下した場合
- データの物理的な削除が規制要件で必要な場合（GDPR 等）
- 月次のメンテナンスサイクルで定期実行

**注意:** REORG TABLE 後も古いファイルはディスク上に残る。完全な物理削除には VACUUM が必要。

---

## 6. メンテナンスジョブのテンプレート

### 6.1 日次メンテナンスジョブ（SQL）

```sql
-- 1. OPTIMIZE（直近データのみ）
OPTIMIZE catalog.silver.events
WHERE event_date >= date_sub(current_date(), 1);

-- 2. VACUUM
VACUUM catalog.silver.events RETAIN 168 HOURS;
```

### 6.2 週次メンテナンスジョブ（SQL）

```sql
-- 1. OPTIMIZE（直近 1 週間）
OPTIMIZE catalog.silver.events
WHERE event_date >= date_sub(current_date(), 7);

-- 2. VACUUM
VACUUM catalog.silver.events RETAIN 168 HOURS;

-- 3. ANALYZE TABLE
ANALYZE TABLE catalog.silver.events COMPUTE DELTA STATISTICS;
ANALYZE TABLE catalog.silver.events COMPUTE STATISTICS FOR COLUMNS event_date, customer_id;
```

### 6.3 月次メンテナンスジョブ（SQL）

```sql
-- 1. REORG TABLE（Deletion Vectors の物理適用）
REORG TABLE catalog.silver.events APPLY (PURGE);

-- 2. OPTIMIZE（REORG 後にファイルを再統合）
OPTIMIZE catalog.silver.events;

-- 3. VACUUM
VACUUM catalog.silver.events RETAIN 168 HOURS;

-- 4. ANALYZE TABLE（全カラム）
ANALYZE TABLE catalog.silver.events COMPUTE STATISTICS FOR ALL COLUMNS;
```

---

## 7. Predictive Optimization（Databricks 環境）

Databricks を使用している場合、手動メンテナンスの代替として Predictive Optimization を検討する。

| 項目 | 説明 |
|:---|:---|
| **対象操作** | OPTIMIZE, VACUUM, ANALYZE |
| **仕組み** | 機械学習でテーブルの書き込みパターンを分析し、最適なタイミングを予測 |
| **メリット** | 手動スケジューリングの負担削減、過不足ないメンテナンス |
| **制約** | Databricks プロプライエタリ機能 |

**有効化:**
```sql
ALTER TABLE catalog.silver.events
SET TBLPROPERTIES ('delta.enablePredictiveOptimization' = 'true');
```

---

## 8. モニタリングとアラート

### 8.1 テーブル状態の確認コマンド

```sql
-- テーブルの詳細情報（ファイル数、サイズ、最終更新等）
DESCRIBE DETAIL catalog.silver.events;

-- テーブル履歴（操作ログ）
DESCRIBE HISTORY catalog.silver.events LIMIT 10;

-- テーブルプロパティ
SHOW TBLPROPERTIES catalog.silver.events;
```

### 8.2 アラート条件の設計

| 監視項目 | 確認コマンド | アラート条件 |
|:---|:---|:---|
| ファイル数 | `DESCRIBE DETAIL` → `numFiles` | 想定値の 3 倍を超えた場合 |
| 平均ファイルサイズ | `sizeInBytes / numFiles` | 10MB 未満になった場合 |
| 最終 OPTIMIZE | `DESCRIBE HISTORY` | 7 日以上未実行の場合 |
| 最終 VACUUM | `DESCRIBE HISTORY` | 14 日以上未実行の場合 |
| Deletion Vectors 数 | `DESCRIBE DETAIL` | 閾値（テーブルサイズ依存）を超えた場合 |

---

## 9. トラブルシューティング

| 問題 | 確認コマンド | 対処法 |
|:---|:---|:---|
| OPTIMIZE が長時間かかる | `DESCRIBE DETAIL`でファイル数を確認 | WHERE 句で範囲を絞る。初回は時間がかかるが、以降はインクリメンタル |
| VACUUM 後のタイムトラベル失敗 | `SHOW TBLPROPERTIES` で保持期間を確認 | `delta.deletedFileRetentionDuration` を延長 |
| VACUUM DRY RUN で大量ファイル | 長期間 VACUUM 未実行 | 段階的に実行（まず長い保持期間 → 徐々に短縮） |
| ANALYZE TABLE が遅い | カラム数が多い | `FOR COLUMNS` で必要なカラムのみに絞る |
| Auto Compaction で書き込みが遅い | コンパクション処理が書き込みジョブに影響 | Auto Compaction を無効化し、別クラスタでスケジュール OPTIMIZE に切り替え |
