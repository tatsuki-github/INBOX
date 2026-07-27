# コンピュートタイプ選定ガイド

> ワークロード特性に基づく最適なコンピュートタイプの選定マトリクス、サイジング指針、コスト比較をまとめたリファレンス。

---

## 1. コンピュートタイプ一覧

| タイプ | 正式名称 | 用途 | 管理モデル |
|:---|:---|:---|:---|
| **Serverless SQL WH** | Serverless SQL Warehouse | SQL 分析・BI・ダッシュボード | フルマネージド |
| **Serverless Jobs** | Serverless Compute for Jobs | ETL・バッチ処理 | フルマネージド |
| **Serverless Notebook** | Serverless Compute for Notebooks | 対話的開発 | フルマネージド |
| **Classic Job Cluster** | Job Cluster | ETL・バッチ処理 | セルフマネージド |
| **Classic All-Purpose** | All-Purpose Cluster | 対話的開発・デバッグ | セルフマネージド |
| **Classic SQL WH** | Pro/Classic SQL Warehouse | SQL 分析 | セミマネージド |

---

## 2. 選定マトリクス

### ワークロード別の推奨コンピュートタイプ

| ワークロード | 第一推奨 | 第二推奨 | 非推奨 |
|:---|:---|:---|:---|
| **定時バッチ ETL** | Serverless Jobs | Classic Job + Spot | All-Purpose |
| **ストリーミング ETL** | Classic Job (Continuous) | Serverless Jobs | All-Purpose |
| **DLT パイプライン** | Serverless (DLT) | Classic Job | All-Purpose |
| **アドホック SQL** | Serverless SQL WH | Classic Pro SQL WH | Job Cluster |
| **ダッシュボード** | Serverless SQL WH | Classic Pro SQL WH | All-Purpose |
| **Notebook 開発** | Serverless Notebook | Classic All-Purpose | Job Cluster |
| **ML 学習** | Classic Job + GPU | Serverless Jobs | SQL Warehouse |
| **ML サービング** | Model Serving (Serverless) | Classic Cluster | SQL Warehouse |
| **Feature Engineering** | Serverless Jobs | Classic Job + Photon | All-Purpose |

### 判断フローチャート

```
Q1: SQL のみか？
  Yes -> Serverless SQL Warehouse
  No  -> Q2 へ

Q2: バッチ処理か？
  Yes -> Q3 へ
  No  -> Q4 へ

Q3: 処理時間は 1 時間以上か？
  Yes -> Classic Job Cluster + Spot
  No  -> Serverless Jobs

Q4: 対話的開発か？
  Yes -> Serverless Notebook / Classic All-Purpose
  No  -> Q5 へ

Q5: ML ワークロードか？
  GPU 必要 -> Classic Job + GPU
  CPU のみ -> Serverless Jobs
```

---

## 3. Serverless vs Classic の比較

| 観点 | Serverless | Classic |
|:---|:---|:---|
| **起動時間** | 即座（秒単位） | 数分（Cold Start） |
| **料金体系** | DBU のみ（インフラ込み） | VM + DBU のデュアルコスト |
| **DBU 単価** | 高い | 低い |
| **TCO** | 短時間ジョブで有利 | 長時間連続ジョブで有利 |
| **Spot 対応** | 不可 | 可能（最大 90% 削減） |
| **インフラ管理** | 不要 | 必要（VM タイプ、ネットワーク等） |
| **カスタマイズ** | 制限あり | フル制御 |
| **Cluster Pools** | 不要 | 活用可能 |

### TCO 損益分岐点の目安

| シナリオ | Serverless が有利 | Classic が有利 |
|:---|:---|:---|
| ジョブ実行時間 | < 30 分 | > 2 時間 |
| 起動頻度 | 高頻度（日に数十回） | 低頻度（日に数回） |
| Spot 活用 | 不可 | 可能な場合 |
| クラスター再利用 | 不可 | Cluster Pools で可能 |

---

## 4. Photon Engine の適用ガイド

### 適用推奨マトリクス

| ワークロード | Photon 推奨度 | 期待効果 |
|:---|:---|:---|
| 大量データ集約（100GB+） | 強く推奨 | 3x-8x 高速化 |
| 複雑な結合クエリ | 強く推奨 | 3x-5x 高速化 |
| Delta Lake 読み書き | 推奨 | 2x-4x 高速化 |
| ディスクキャッシュ活用 | 推奨 | 繰り返しアクセスで効果大 |
| 時系列分析（IoT） | 推奨 | スキャン高速化 |
| Feature Engineering (SQL) | 推奨 | 集約処理の高速化 |
| UDF 多用 | 非推奨 | Photon 非対応 |
| RDD API | 非推奨 | Photon 非対応 |
| 2 秒以下の軽量クエリ | 効果薄 | オーバーヘッドが支配的 |

### Photon の有効化状況

| コンピュートタイプ | デフォルト状態 |
|:---|:---|
| SQL Warehouse（全種） | 有効 |
| Serverless Compute | 有効 |
| Classic Cluster（DBR 9.1+） | 有効 |
| ML Runtime（DBR 15.2+） | 手動で有効化可能 |

---

## 5. DBR バージョン選定ガイド

### バージョン比較（2025-2026 年）

| バージョン | Spark | Scala | LTS | 主な特徴 |
|:---|:---|:---|:---|:---|
| DBR 14.3 LTS | 3.5.0 | 2.12 | Yes | 安定版（サポート期限確認要） |
| DBR 15.4 LTS | 3.5.x | 2.12 | Yes | 広く利用されている |
| DBR 16.4 LTS | 3.5.x | 2.12/2.13 | Yes | 最新 LTS（推奨） |
| DBR 17.0+ | Spark 4 | 2.13 のみ | TBD | Scala 2.12 非サポート |

### 選定フローチャート

```
Q1: 本番環境か？
  Yes -> LTS バージョンを選択 -> Q2 へ
  No  -> 最新 GA でも可

Q2: ML ワークロードか？
  Yes -> DBR ML 版を選択（例: DBR 16.4 ML LTS）
  No  -> 標準 DBR を選択（例: DBR 16.4 LTS）

Q3: Scala 2.12 依存ライブラリがあるか？
  Yes -> DBR 16.4 LTS に留まる（17.0+ は 2.13 のみ）
  No  -> 最新 LTS を選択
```

---

## 6. SQL Warehouse サイジングガイド

### サイズ別の推奨ユースケース

| サイズ | クラスター数 | 推奨ユースケース | 同時実行の目安 |
|:---|:---|:---|:---|
| 2X-Small | 1 | 軽量ダッシュボード、個人分析 | 1-3 |
| X-Small | 1 | 小規模チームのアドホック分析 | 3-5 |
| Small | 1 | 標準ダッシュボード | 5-10 |
| Medium | 1 | 中規模の分析ワークロード | 10-20 |
| Large | 1 | 大量データの集約、複雑結合 | 20-50 |
| X-Large+ | 1 | 超大規模ワークロード | 50+ |

### マルチクラスター設定

| 設定 | 推奨値 | 説明 |
|:---|:---|:---|
| Min clusters | 1 | コスト抑制 |
| Max clusters | 同時実行ユーザー数 / 10 | スケールアウト |
| Auto Stop | 10-15 分 | アイドルコスト削減 |
| Scaling Policy | Enhanced (Serverless) | IWM による自動最適化 |

### Spill Rate の監視

Spill が発生している場合の判断基準:

| Spill 率 | 対応 |
|:---|:---|
| 0% | 問題なし |
| 1-10% | クエリの最適化で対応可能 |
| 10-30% | Warehouse サイズアップを検討 |
| 30%+ | 即座にサイズアップ、クエリ改善が必須 |

---

## 7. オートスケーリング設計パターン

### バッチ ETL パターン

```
min_workers: 2
max_workers: 10
autotermination_minutes: 30
spot_percentage: 80%
```

### 対話的開発パターン

```
min_workers: 1
max_workers: 4
autotermination_minutes: 60
spot_percentage: 0%  (開発では安定性優先)
```

### ストリーミングパターン

```
min_workers: 2
max_workers: 8
autotermination_minutes: 0  (常時起動)
spot_percentage: 50%  (Worker のみ Spot)
```

---

## 8. コスト概算の指標

### DBU レート目安（2025-2026 年概算）

| コンピュートタイプ | DBU レート目安 |
|:---|:---|
| Serverless SQL | ~$0.70/DBU-hour |
| Serverless Jobs | ~$0.50-0.75/DBU |
| Classic Jobs | ~$0.15-0.30/DBU + VM コスト |
| Classic All-Purpose | ~$0.40-0.55/DBU + VM コスト |
| Foundation Model Serving | ~$0.07/DBU |

**注意**: 実際の価格はクラウドプロバイダー、リージョン、契約形態（PAYG vs Committed）により異なる。正確な見積もりは Databricks 営業に確認すること。
