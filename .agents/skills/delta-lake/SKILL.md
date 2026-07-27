---
name: delta-lake
description: >
  Delta Lake テーブルの設計・最適化・運用を支援するスキル。
  テーブル設計（Liquid Clustering、パーティション、Deletion Vectors）、
  データ操作（MERGE最適化、CDF、Streaming）、
  パフォーマンス（OPTIMIZE、VACUUM、Data Skipping）、
  Medallion Architecture実装、運用メンテナンスを一貫してガイドする。
  Use when user says「Delta Lakeのテーブルを設計して」「Deltaテーブルを最適化して」
  「MERGEのパフォーマンスを改善して」「Medallion Architectureを設計して」
  「OPTIMIZE/VACUUMのスケジュールを設計して」「Liquid Clusteringを設定して」
  「CDFを設計して」「パーティション戦略を決めて」「Small File Problemを解決して」。
  Do NOT use for: クラウドインフラ設計（→ databricks-cloud-arch）、
  Unity Catalogのカタログ/権限設計（→ unity-catalog）。
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: data-platform
---

# Skill: Delta Lake（テーブル設計・最適化・運用）

> **データレイクに ACID の堅牢性を — Delta Lake の設計から運用まで一気通貫で支援する**

## Instructions

### ワークフロー内の位置

```
data-arch（上流）→ [delta-lake] → diagram（構成図）→ review（検証）
                       ↓
                  テーブル設計書・DDL・メンテナンス計画
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| ワークロード要件 | データ量・更新頻度・SLA | 「日次 10GB、5分以内にクエリ可能」 |
| クエリパターン | 主要なフィルタ・JOIN 条件 | 「日付と顧客IDでフィルタが多い」 |
| Medallion 層 | 対象テーブルが属する層 | 「Silver 層の顧客マスタ」 |
| 既存テーブル定義 | 既存の DDL やプロパティ | CREATE TABLE 文、SHOW TBLPROPERTIES 出力 |
| パフォーマンス課題 | 具体的なボトルネック | 「MERGE が 3 時間かかる」「小ファイルが大量にある」 |

### 出力

| 出力 | 形式 | 説明 |
|:---|:---|:---|
| テーブル設計書 | Markdown | DDL・プロパティ・クラスタリング戦略を含む設計ドキュメント |
| DDL スクリプト | SQL | CREATE TABLE / ALTER TABLE の実行可能な SQL |
| メンテナンス計画 | Markdown テーブル | OPTIMIZE / VACUUM / ANALYZE のスケジュールと設定 |
| パフォーマンス改善案 | Markdown | ボトルネック分析と改善策のリスト |

---

## Step 1: 要件分析

ワークロード特性とデータ要件を把握し、設計の方向性を決定する。

### 1a. ワークロード特性の把握

| 観点 | 確認事項 | 設計への影響 |
|:---|:---|:---|
| **処理パターン** | バッチ / ストリーミング / 混合 | Streaming 設計・チェックポイント戦略 |
| **書き込み頻度** | 日次 / 時次 / リアルタイム | Auto Compaction・OPTIMIZE 頻度 |
| **データ量** | 日次増分量・テーブル総量 | パーティション vs Liquid Clustering の選択 |
| **更新パターン** | Append Only / Upsert / Delete あり | Deletion Vectors・MERGE 戦略 |
| **同時実行** | 並行書き込みの有無 | Coordinated Commits の要否 |

### 1b. クエリパターンの分析

主要なクエリの WHERE 句・JOIN 条件を収集し、Data Skipping の効果を最大化するためのキー列を特定する。

### 1c. Medallion Architecture 層の特定

| 層 | 特徴 | 主な設計関心事 |
|:---|:---|:---|
| **Bronze** | 生データ取り込み、Append Only | スキーマ進化、Auto Loader 設計 |
| **Silver** | クレンジング・正規化 | MERGE 最適化、CDF 設計 |
| **Gold** | 集計・BI モデル | 読み取り最適化、マテリアライズドビュー |

### 1d. SLA・非機能要件の確認

- データ鮮度要件（取り込みからクエリ可能になるまでの許容時間）
- タイムトラベル保持期間の要件
- ストレージコスト制約
- 既存システムとの互換性要件（Iceberg / Hudi クライアントからの読み取り需要）

**チェックリスト**:
- [ ] ワークロードパターン（バッチ/ストリーミング/混合）を特定した
- [ ] 日次データ増分量とテーブル総量を把握した
- [ ] 主要クエリのフィルタ条件・JOIN 条件を 3 つ以上収集した
- [ ] Medallion Architecture での対象層を特定した
- [ ] データ鮮度 SLA とタイムトラベル保持期間を確認した
- [ ] 同時書き込みの有無と互換性要件を確認した

---

## Step 2: テーブル設計

要件に基づき、テーブルのデータレイアウトとプロパティを設計する。
詳細な選定フローは [table-design-guide.md](references/table-design-guide.md) を参照。

### 2a. クラスタリング戦略の選定

**判断フロー:**

```
テーブルサイズ < 1TB?
├── Yes → Liquid Clustering を推奨（パーティション不要）
└── No → テーブルサイズ >= 1TB
         ├── 新規テーブル → Liquid Clustering を推奨
         └── 既存パーティションテーブル
              ├── 問題なし → 現行維持
              └── 問題あり → Liquid Clustering への移行を検討
```

**Liquid Clustering のキー選定ガイドライン:**
- キー数は **1-4 列**に制限する
- WHERE 句・JOIN 条件で頻繁に使われる列を選択する
- カーディナリティが中〜高程度の列が最適
- キーの変更はメタデータ操作のみ（`ALTER TABLE ... CLUSTER BY`）

### 2b. スキーマ設計

- 頻繁にフィルタされる列をスキーマの先頭 32 列以内に配置する（Data Skipping の対象）
- Column Mapping の必要性を評価する（カラム名変更・削除の要件がある場合）
- Type Widening の対象カラムを事前に特定する

### 2c. Deletion Vectors の有効化判断

| 条件 | 推奨 |
|:---|:---|
| UPDATE / DELETE が頻繁に発生する | 有効化を推奨 |
| Append Only のテーブル | 不要（有効化しても害はない） |
| Databricks Runtime 12.1+ を使用 | デフォルトで有効 |

### 2d. テーブルプロパティの設定

主要プロパティの設定を検討する。
完全なプロパティ一覧は [property-reference.md](references/property-reference.md) を参照。

```sql
-- 推奨プロパティの設定例
CREATE TABLE my_table (...)
USING DELTA
CLUSTER BY (col1, col2)
TBLPROPERTIES (
  'delta.enableDeletionVectors' = 'true',
  'delta.enableChangeDataFeed' = 'true',
  'delta.logRetentionDuration' = 'interval 30 days',
  'delta.deletedFileRetentionDuration' = 'interval 7 days',
  'delta.dataSkippingNumIndexedCols' = 32,
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true'
);
```

**チェックリスト**:
- [ ] Liquid Clustering vs パーティショニングの選択根拠を明記した
- [ ] クラスタリングキー / パーティション列をクエリパターンに基づいて選定した
- [ ] Data Skipping に有効な列をスキーマの先頭に配置した
- [ ] Deletion Vectors の有効化を判断した
- [ ] テーブルプロパティを要件に合わせて設定した
- [ ] DDL スクリプト（CREATE TABLE 文）を作成した

---

## Step 3: データ操作パターンの設計

テーブルへの読み書きパターンを設計する。
MERGE の詳細な最適化手法は [merge-optimization.md](references/merge-optimization.md) を参照。

### 3a. 操作パターンの選定

| 要件 | 推奨操作 | 理由 |
|:---|:---|:---|
| 新規データの追加のみ | `INSERT` / `APPEND` | 最も高速。ファイル追加のみ |
| パーティション単位の置換 | `INSERT OVERWRITE` | 対象パーティション内のファイルを全置換 |
| 単純な条件付き更新 | `UPDATE` | MERGE より高速 |
| 単純な条件付き削除 | `DELETE` | MERGE より高速 |
| 複合 Upsert ロジック | `MERGE` | 最も柔軟だがコスト最大 |

**設計原則:** MERGE は最後の手段。単純な操作で代替できないかを常に検討する。

### 3b. MERGE 最適化（必要な場合）

**7 つの最適化原則:**

1. **検索空間の削減** — マッチ条件にクラスタリングキー / パーティション列を含める
2. **ソースデータの事前フィルタリング** — 不要な行を MERGE に送らない
3. **ファイルのコンパクション** — MERGE 前に OPTIMIZE を実行する
4. **Low Shuffle Merge の活用** — DBR 10.4+ でデフォルト有効
5. **Optimized Writes の有効化** — 小ファイルの大量生成を防止
6. **Liquid Clustering の採用** — MERGE 後の再最適化コストが低い
7. **MERGE 頻度の最小化** — CDF で代替できないか検討する

```sql
-- 最適化された MERGE の例
MERGE INTO silver_customers t
USING (
  SELECT * FROM bronze_changes
  WHERE change_date = current_date()  -- 原則2: 事前フィルタリング
) s
ON t.customer_id = s.customer_id
   AND t.region = s.region           -- 原則1: 検索空間の削減
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;
```

### 3c. Change Data Feed（CDF）の設計

**有効化を推奨するケース:**
- Medallion Architecture で Silver → Gold のインクリメンタル更新がある場合
- 下流パイプラインが変更データのみを処理したい場合
- 監査証跡が必要な場合

**設計上の注意:**
- CDF は Delta ログに依存するため、`delta.logRetentionDuration` を十分に設定する（30 日推奨）
- 恒久的な変更履歴が必要な場合は CDF の内容を別テーブルに書き出す
- VACUUM による ログ消失で CDF クエリが失敗するリスクに注意する

### 3d. Streaming パイプラインの設計

Streaming を使用する場合、以下を設計する:

- **チェックポイントの配置**: ライフサイクルポリシーが適用されない安全なストレージ
- **トリガー設定**: `maxFilesPerTrigger` / `maxBytesPerTrigger` でスループットを制御
- **Exactly-Once 保証**: Delta Lake のトランザクションログにより自動で担保される
- **Auto Loader（Bronze 層）**: ファイル検出モードの選定（Directory Listing vs File Notification）

**チェックリスト**:
- [ ] 操作パターン（INSERT / UPDATE / DELETE / MERGE）の使い分けを定義した
- [ ] MERGE を使用する場合、7 つの最適化原則に基づいて設計した
- [ ] CDF の有効化と保持期間を判断した
- [ ] Streaming の場合、チェックポイント配置とトリガー設定を設計した
- [ ] 各操作のスキーマ進化ポリシーを決定した

---

## Step 4: Medallion Architecture 実装設計

Bronze / Silver / Gold 各層の具体的な実装パターンを設計する。
各層の詳細なコード例は [medallion-patterns.md](references/medallion-patterns.md) を参照。

### 4a. Bronze 層の設計

**設計原則:** 全てを保存し、何も変換しない（Preserve Everything, Transform Nothing）

| 項目 | 推奨設定 |
|:---|:---|
| 取り込み方法 | Auto Loader（cloudFiles）または Kafka |
| スキーマ管理 | `mergeSchema = true` でスキーマ変更に柔軟対応 |
| メタデータ付与 | `_ingestion_timestamp`, `_source_file` カラムを追加 |
| クラスタリング | 取り込み日時での Liquid Clustering、または取り込み日付パーティション |
| 品質チェック | 最小限（スキーマ適用のみ）。検証は Silver 層で実施 |

### 4b. Silver 層の設計

**設計原則:** 検証済み・クレンジング済み・正規化済みデータの提供

| 項目 | 推奨設定 |
|:---|:---|
| 更新方法 | MERGE（Upsert）+ CDF 有効化 |
| 品質チェック | DLT Expectations（`expect_or_drop` / `expect_or_fail`） |
| クラスタリング | ビジネスキーでの Liquid Clustering |
| Deletion Vectors | 有効化推奨（更新・削除が頻繁） |
| 出力 | CDF を有効にし、Gold 層へのインクリメンタル更新に活用 |

### 4c. Gold 層の設計

**設計原則:** ビジネス消費に最適化された非正規化モデル

| 項目 | 推奨設定 |
|:---|:---|
| 更新方法 | Silver 層の CDF を活用したインクリメンタル集計 |
| データモデル | スター/スノーフレークスキーマ（JOIN を最小化） |
| クラスタリング | 分析で頻繁に使うディメンションキーでの Liquid Clustering |
| ファイルサイズ | 大きめ（512MB - 1GB）に最適化 |
| マテリアライズドビュー | Databricks 環境では積極的に活用 |

### 4d. DLT Expectations による品質チェック

| Expectations モード | 不正データの扱い | ユースケース |
|:---|:---|:---|
| `@dlt.expect` | 保持してメトリクスを記録 | 品質監視、許容範囲の逸脱 |
| `@dlt.expect_or_drop` | 不正行をドロップ | データクレンジング |
| `@dlt.expect_or_fail` | パイプラインを停止 | クリティカルな品質制約 |

**チェックリスト**:
- [ ] Bronze 層の取り込みパターン（Auto Loader / Kafka / バッチ）を選定した
- [ ] Silver 層の MERGE パターンと CDF 設計を完了した
- [ ] Gold 層のデータモデルと更新戦略を設計した
- [ ] DLT Expectations の品質ルールを層ごとに定義した
- [ ] 層間のデータフロー（バッチ / ストリーミング）を明確にした

---

## Step 5: パフォーマンス最適化

テーブルの読み書きパフォーマンスを最適化する。
メンテナンスの詳細は [maintenance-runbook.md](references/maintenance-runbook.md) を参照。

### 5a. OPTIMIZE の設計

```sql
-- Liquid Clustering テーブルの最適化
OPTIMIZE my_table;

-- パーティションテーブルの最適化（Z-Ordering 付き）
OPTIMIZE my_table WHERE date >= '2025-01-01' ZORDER BY (customer_id);
```

| 設定項目 | 推奨値 | 説明 |
|:---|:---|:---|
| 実行頻度 | 日次〜週次 | 書き込み頻度に応じて調整 |
| 対象範囲 | 最新パーティションのみ | 全テーブル OPTIMIZE は不要な場合が多い |
| 理想ファイルサイズ | 256MB - 1GB | 小さすぎるとスキャンが遅く、大きすぎると並列性が低下 |

### 5b. VACUUM の設計

```sql
-- 保持期間を指定して VACUUM
VACUUM my_table RETAIN 168 HOURS;

-- ドライランで削除対象を事前確認
VACUUM my_table DRY RUN;
```

**重要:** 実行順序は必ず **OPTIMIZE → VACUUM** の順にする。OPTIMIZE が新しい統合ファイルを作成し、古い小ファイルが不要になるため。

### 5c. Auto Compaction / Optimized Writes

| 機能 | 設定 | 効果 |
|:---|:---|:---|
| **Auto Compaction** | `delta.autoOptimize.autoCompact = true` | 書き込み後に自動で小ファイルを結合 |
| **Optimized Writes** | `delta.autoOptimize.optimizeWrite = true` | 書き込み時にファイルサイズを最適化 |

多くのワークロードでは Auto Compaction で十分。レイテンシ要件が厳しい場合のみ、別の Spark プールでスケジュールされた OPTIMIZE を実行する。

### 5d. Data Skipping の最適化

- フィルタで頻繁に使われる列をスキーマの先頭 32 列以内に配置する
- `delta.dataSkippingNumIndexedCols` でインデックス対象カラム数を調整する
- Liquid Clustering / Z-Ordering と組み合わせて効果を最大化する

### 5e. Bloom Filter Index の適用判断

| 条件 | Bloom Filter の適合度 |
|:---|:---|
| 高カーディナリティ列（user_id, ip_address） | 最適 |
| 等値条件（`=`）でのフィルタ | 最適 |
| 範囲条件（`<`, `>`, `BETWEEN`） | 不適（等値検索専用） |

```sql
-- Bloom Filter Index の作成例
CREATE BLOOMFILTER INDEX ON TABLE my_table
FOR COLUMNS (user_id OPTIONS (fpp = 0.1, numItems = 50000000));
```

**チェックリスト**:
- [ ] OPTIMIZE のスケジュールと対象範囲を設計した
- [ ] VACUUM の保持期間をタイムトラベル要件に合わせて設定した
- [ ] 実行順序を OPTIMIZE → VACUUM に設定した
- [ ] Auto Compaction / Optimized Writes の有効化を判断した
- [ ] Data Skipping に有効なカラム配置を確認した
- [ ] Bloom Filter Index の適用候補カラムを評価した

---

## Step 6: 運用・メンテナンス設計

テーブルの長期的な健全性を維持するための運用計画を策定する。

### 6a. メンテナンススケジュール

| タスク | 頻度 | 実行順序 | 備考 |
|:---|:---|:---|:---|
| **OPTIMIZE** | 日次〜週次 | 1番目 | 書き込み頻度に応じて調整 |
| **VACUUM** | 日次〜週次 | 2番目（OPTIMIZE の後） | 保持期間はタイムトラベル要件に合わせる |
| **ANALYZE TABLE** | 週次、または大量ロード後 | 3番目 | 統計情報の更新 |
| **REORG TABLE APPLY (PURGE)** | 月次 | 適宜 | Deletion Vectors のソフトデリートを物理適用 |

### 6b. Predictive Optimization（Databricks 環境）

Databricks 環境では Predictive Optimization が利用可能。機械学習でメンテナンスタイミングを自動予測し、OPTIMIZE / VACUUM / ANALYZE を自動スケジュールする。

### 6c. モニタリング

定期的に以下を確認し、問題を早期に検知する:

| 監視項目 | 確認コマンド | アラート条件 |
|:---|:---|:---|
| ファイル数・サイズ | `DESCRIBE DETAIL my_table` | ファイル数が急増、平均サイズが 10MB 以下 |
| テーブル履歴 | `DESCRIBE HISTORY my_table` | 想定外の操作、長時間実行 |
| テーブルプロパティ | `SHOW TBLPROPERTIES my_table` | 設定値の意図しない変更 |
| Deletion Vectors 蓄積 | `DESCRIBE DETAIL` の numDeletionVectors | 蓄積が閾値を超えた場合 REORG を検討 |

### 6d. Small File Problem の予防と対処

**予防策（書き込み時）:**
- `optimizeWrite.enabled = true` を有効にする
- Auto Compaction を有効にする
- Streaming の `maxFilesPerTrigger` / `maxBytesPerTrigger` を適切に設定する

**対処策（事後）:**
- `OPTIMIZE` でファイルを統合する
- `VACUUM` で不要ファイルを削除する
- Liquid Clustering の採用でパーティション細分化を回避する

### 6e. 移行・クローン

| 移行パターン | コマンド | ユースケース |
|:---|:---|:---|
| Parquet → Delta | `CONVERT TO DELTA` | 既存 Parquet テーブルの Delta 化 |
| Shallow Clone | `CREATE TABLE ... SHALLOW CLONE` | テスト環境の構築（メタデータのみコピー） |
| Deep Clone | `CREATE TABLE ... DEEP CLONE` | バックアップ・完全コピー |
| インクリメンタル Clone | `CREATE OR REPLACE TABLE ... DEEP CLONE` | 定期的な差分コピー |

**チェックリスト**:
- [ ] OPTIMIZE / VACUUM / ANALYZE のスケジュールを策定した
- [ ] Predictive Optimization の利用可否を確認した
- [ ] モニタリング対象と確認手順を定義した
- [ ] Small File Problem の予防策を設定した
- [ ] 移行・クローンが必要な場合、手順を設計した

---

## Step 7: 互換性・相互運用設計

他フォーマットやプラットフォームとの相互運用が必要な場合に設計する。
バージョンごとの機能対応は [version-features.md](references/version-features.md) を参照。

### 7a. UniForm（Iceberg / Hudi 互換）

- Snowflake / Trino / Presto など非 Spark エンジンからの読み取りが必要な場合に有効化する
- 読み取り専用互換性の提供であり、書き込みは Delta 経由のみ
- Delta 3.3+ では既存テーブルへのデータ書き換えなしで有効化可能

### 7b. Delta Sharing

組織間・プラットフォーム間でデータ共有が必要な場合、共有範囲（テーブル / パーティション単位）、アクセス制御（トークン認証、IP リスト）、消費者側エンジンを設計する。

### 7c. OSS vs Databricks の差異

Databricks 専用機能（Auto Loader、DLT Expectations、Photon、Predictive Optimization、Low Shuffle Merge、VACUUM LITE）を把握し、OSS 環境では代替手段を設計する。

**チェックリスト**:
- [ ] UniForm の必要性を評価し、対象フォーマットを決定した
- [ ] Delta Sharing の要件がある場合、共有範囲とアクセス制御を設計した
- [ ] 使用環境（Databricks / OSS）に応じた機能制約を確認した

---

## Step 8: レビューチェックリスト

設計全体を横断的に検証する。

**チェックリスト**:
- [ ] クラスタリング戦略がクエリパターンと整合している
- [ ] テーブルプロパティがワークロード要件に合致している
- [ ] MERGE の使用が必要最小限に抑えられ、マッチ条件にキー列を含んでいる
- [ ] CDF の有効化と保持期間が下流パイプラインの要件を満たしている
- [ ] OPTIMIZE → VACUUM の順序でスケジュールが策定されている
- [ ] モニタリング項目と Small File Problem の予防策が定義されている
- [ ] UniForm / Delta Sharing / 環境固有の制約を確認した
- [ ] 設計書・DDL・メンテナンス計画の 3 点セットが揃っている

---

## Examples

### Example 1: 新規 Silver テーブルの設計

```
「顧客マスタの Silver テーブルを設計して。日次バッチで MERGE、約500GB」

→ Step 1: 日次バッチ、MERGE、500GB、Silver 層
→ Step 2: Liquid Clustering（customer_id, region）、Deletion Vectors 有効化
→ Step 3: MERGE 最適化（region をマッチ条件に追加）、CDF 有効化
→ Step 5: OPTIMIZE 日次、VACUUM 週次（RETAIN 168 HOURS）
→ Step 8: レビューチェックリストで検証

出力: CREATE TABLE DDL + メンテナンス計画
```

### Example 2: MERGE パフォーマンス改善

```
「MERGE が 3 時間かかっている。改善したい」

→ Step 1: 現在の MERGE SQL とテーブル定義を確認
→ Step 3b: 7 つの最適化原則に照らして診断
  - マッチ条件にクラスタリングキーがない → 追加
  - ソースデータの事前フィルタリングがない → WHERE 句追加
  - 小ファイルが多い → OPTIMIZE を事前実行
→ Step 5: OPTIMIZE 後に MERGE を再実行

出力: 最適化された MERGE SQL + 事前 OPTIMIZE スケジュール
```

### Example 3: Medallion Architecture 全体設計

```
「EC サイトのデータパイプラインを Medallion Architecture で設計して」

→ Step 1: ストリーミング（注文）+ バッチ（商品マスタ）の混合ワークロード
→ Step 4a: Bronze — Auto Loader で JSON 取り込み、Liquid Clustering（_ingestion_date）
→ Step 4b: Silver — 注文テーブルに MERGE、CDF 有効、DLT Expectations で品質チェック
→ Step 4c: Gold — 日次売上集計、CDF ベースのインクリメンタル更新
→ Step 6: 層ごとのメンテナンススケジュール策定

出力: 3 層の設計書 + DDL + DLT パイプライン定義
```

### Example 4: Small File Problem の解決

```
「テーブルに 10 万個の小ファイルがある。解決して」

→ Step 1: 原因分析（Streaming のマイクロバッチ + 頻繁な MERGE）
→ Step 5a: OPTIMIZE でファイルを統合
→ Step 5b: VACUUM で古いファイルを削除
→ Step 5c: Auto Compaction + Optimized Writes を有効化（予防策）
→ Step 6d: Streaming の maxFilesPerTrigger を調整

出力: 即時対処の SQL + 予防設定の ALTER TABLE 文
```

### Example 5: Liquid Clustering への移行

```
「既存のパーティションテーブルを Liquid Clustering に移行したい」

→ Step 1: 現在のパーティション設計と問題点を確認
→ Step 2a: Liquid Clustering のキーをクエリパターンから選定
→ Step 6e: 移行手順の設計（新テーブル作成 → データコピー → 切り替え）
→ Step 5: 移行後の OPTIMIZE 実行でクラスタリングを適用
→ Step 8: 移行前後のクエリパフォーマンスを比較

出力: 移行スクリプト + 検証クエリ
```

### Example 6: CDF を活用したインクリメンタルパイプライン

```
「Silver → Gold のインクリメンタル更新を CDF で実装して」

→ Step 1: Silver テーブルの変更パターンと Gold テーブルの集計要件を確認
→ Step 3c: CDF の有効化、logRetentionDuration の設定
→ Step 4b: Silver テーブルに CDF を有効化
→ Step 4c: Gold テーブルで table_changes() を使ったインクリメンタル集計
→ Step 6: CDF ベースパイプラインのモニタリング設計

出力: CDF 有効化 SQL + インクリメンタル集計のコード
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| MERGE が非常に遅い | 検索空間が広い / 小ファイルが多い | マッチ条件にクラスタリングキーを追加、事前に OPTIMIZE を実行。[merge-optimization.md](references/merge-optimization.md) の 7 原則を確認 |
| 小ファイルが大量に蓄積する | Streaming マイクロバッチ / 頻繁な MERGE | Auto Compaction と Optimized Writes を有効化。OPTIMIZE を定期実行 |
| タイムトラベルが失敗する | VACUUM が保持期間外のファイルを削除 | `delta.deletedFileRetentionDuration` を延長し、VACUUM 頻度を調整 |
| CDF クエリが失敗する | ログが VACUUM で消失 | `delta.logRetentionDuration` を 30 日以上に設定 |
| スキーマ進化で下流が失敗する | 予期しないカラム追加・型変更 | スキーマ進化前に下流パイプラインへの影響を確認。`mergeSchema` はグローバルでなく個別指定 |
| Liquid Clustering の効果が薄い | キー選定がクエリパターンと不一致 | WHERE 句・JOIN 条件の分析に基づいてキーを再選定（`ALTER TABLE ... CLUSTER BY`） |
| OPTIMIZE が長時間かかる | テーブル全体を処理している | WHERE 句で最新データのみに絞り込む。Liquid Clustering はインクリメンタルで効率的 |
| Streaming のチェックポイント破損 | ストレージのライフサイクルポリシー | チェックポイントをライフサイクルポリシー対象外のストレージに移動 |
| Deletion Vectors が蓄積し読み取りが遅い | REORG TABLE が未実行 | `REORG TABLE ... APPLY (PURGE)` でソフトデリートを物理適用し、その後 VACUUM を実行 |
| Shallow Clone で FileNotFoundException | ソーステーブルの VACUUM | `CREATE OR REPLACE TABLE ... SHALLOW CLONE` で修復、または Deep Clone に切替 |
| UniForm 有効化後の書き込み遅延 | Iceberg メタデータの並行生成 | 書き込み頻度が高い場合は影響を計測し、許容範囲か確認 |
| VACUUM DRY RUN で大量のファイルが表示される | 長期間 VACUUM 未実行 | 段階的に VACUUM を実行（保持期間を徐々に短縮） |

---

## References

| ファイル | 内容 |
|:---|:---|
| [table-design-guide.md](references/table-design-guide.md) | パーティション / Liquid Clustering / Deletion Vectors の選定フローと設計ガイドライン |
| [merge-optimization.md](references/merge-optimization.md) | MERGE パフォーマンスチューニング 7 原則と SQL パターン |
| [medallion-patterns.md](references/medallion-patterns.md) | Bronze / Silver / Gold 各層の設計パターンとコード例 |
| [maintenance-runbook.md](references/maintenance-runbook.md) | OPTIMIZE / VACUUM / ANALYZE スケジューリングガイドとトラブルシューティング |
| [property-reference.md](references/property-reference.md) | テーブルプロパティのリファレンス（設定値・デフォルト・影響範囲） |
| [version-features.md](references/version-features.md) | Delta Lake 3.x / 4.x 新機能サマリーと互換性情報 |

---

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **data-arch** | 上流 | データアーキテクチャ選定後、ストレージレイヤーの具体設計として delta-lake スキルを発動 |
| **diagram** | 後続 | Delta Lake のデータフロー図（Medallion Architecture 構成図）を draw.io で生成 |
| **review** | 検証 | テーブル設計書・DDL・メンテナンス計画のクリティカルレビュー |
| **data-validation** | 補完 | DLT Expectations の設計支援、データ品質チェック戦略の策定 |
| **test** | 補完 | Delta Lake パイプラインの単体テスト・統合テスト設計 |
