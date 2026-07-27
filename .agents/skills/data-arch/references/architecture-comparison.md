# Architecture Comparison Reference

> 6種のデータアーキテクチャの詳細比較リファレンス

## 1. アーキテクチャの進化の系譜

```
1984  RDW（Relational Data Warehouse）
       │  Bill Inmon 提唱。構造化データの集約・分析
       ↓
2010  Data Lake
       │  James Dixon（Pentaho）提唱。全データ種別を raw 保存
       ↓
2011  MDW（Modern Data Warehouse）
       │  RDW + Data Lake のハイブリッド
       ├──────────────────────────┐
       ↓                          ↓
2016  Data Fabric              2019  Data Mesh
       │  Gartner 提唱              │  Zhamak Dehghani 提唱
       │  メタデータ駆動の統合        │  ドメインオーナーシップ
       ↓
2020  Data Lakehouse
       Databricks 提唱。DL + DW の融合
```

## 2. 詳細比較表

### 2a. 基本特性

| 項目 | RDW | Data Lake | MDW | Data Fabric | Data Mesh | Data Lakehouse |
|:---|:---|:---|:---|:---|:---|:---|
| 登場年 | 1984 | 2010 | 2011 | 2016 | 2019 | 2020 |
| 集中/分散 | 集中 | 集中 | 集中 | 集中 | 分散 | 集中 |
| ストレージ | リレーショナル | ファイル | 両方 | 両方 | 両方 | ファイル+トランザクション |
| データ種別 | 構造化のみ | 全種別 | 全種別 | 全種別 | 全種別 | 全種別 |
| スキーマ | オンライト | オンリード | 両方 | 両方 | 両方 | 両方 |

### 2b. 非機能要件

| 項目 | RDW | Data Lake | MDW | Data Fabric | Data Mesh | Data Lakehouse |
|:---|:---|:---|:---|:---|:---|:---|
| セキュリティ | 高 | 低〜中 | 高 | 高 | 中 | 中〜高 |
| レイテンシ | バッチ | バッチ | バッチ+RT | バッチ+RT | バッチ+RT | バッチ+RT |
| コスト | 中〜高 | 低 | 中〜高 | 中〜高 | 高 | 低〜中 |
| 難易度 | 中 | 低〜中 | 中〜高 | 高 | 非常に高 | 中 |
| スケーラビリティ | 垂直 | 水平 | 水平 | 水平 | 水平 | 水平 |

### 2c. 組織・プロセス

| 項目 | RDW | Data Lake | MDW | Data Fabric | Data Mesh | Data Lakehouse |
|:---|:---|:---|:---|:---|:---|:---|
| チーム構造 | 中央集権 | 中央集権 | 中央集権 | 中央集権 | ドメイン分散 | 中央集権 |
| ガバナンス | 集中 | 集中 | 集中 | 集中（自動化） | 連合的 | 集中 |
| 最適規模 | 小〜中 | 中〜大 | 中〜大 | 大 | 大（分散組織） | 中〜大 |
| 成熟度 | 非常に高い | 高い | 高い | 中 | 低（新しい） | 中 |

## 3. 各アーキテクチャの詳細

### RDW（Relational Data Warehouse）

**定義**: 構造化データを中央のリレーショナルデータベースに集約し、BI・レポーティングに最適化されたアーキテクチャ。

**特徴**:
- スキーマオンライト（データ投入前にスキーマ定義が必要）
- SQL ベースのアクセス
- 高いデータ品質（ETL で変換・クレンジング済み）
- ACID トランザクション

**利点**: 実績豊富、高いデータ品質、SQLの親和性
**欠点**: 構造化データのみ、スケーラビリティの限界、高コスト

### Data Lake

**定義**: あらゆる種類のデータをそのまま（raw format）で保存する大容量ストレージ。

**5層構造**:
1. Raw Layer（ブロンズ）: データをそのまま保存
2. Conformed Layer: 基本的なクレンジング・標準化
3. Cleansed Layer: 品質チェック・重複排除
4. Presentation Layer（キュレーション）: BI・分析用に最適化
5. Sandbox: データサイエンス用の実験領域

**利点**: 低コスト、全データ種別対応、スケーラブル
**欠点**: データスワンプ化リスク、セキュリティ弱、クエリ性能

### MDW（Modern Data Warehouse）

**定義**: RDW と Data Lake を組み合わせたハイブリッドアーキテクチャ。

**5ステージ**:
1. Ingestion（取り込み）: バッチ + リアルタイム
2. Storage（保存）: Data Lake + リレーショナル
3. Transformation（変換）: ELT/ETL パイプライン
4. Modeling（モデリング）: ディメンショナルモデル
5. Visualization（可視化）: BI ツール

**段階的移行パス**:
- EDW Augmentation: 既存 EDW に Data Lake を追加
- Temporary Data Lake + EDW: 並行運用
- All-in-One: 完全な MDW 統合

### Data Fabric

**定義**: MDW の進化形。メタデータ駆動のインテリジェントデータ統合レイヤー。

**8つの主要コンポーネント**:
1. データアクセスポリシー
2. メタデータカタログ
3. MDM（マスターデータ管理）
4. データ仮想化
5. リアルタイム処理
6. API
7. サービス
8. データプロダクト

**利点**: メタデータ駆動の自動化、データ仮想化、セルフサービス
**欠点**: 高い初期投資、スキル要件、ベンダーロックインリスク

### Data Mesh

**定義**: ドメインオーナーシップに基づく分散型データアーキテクチャ。

**4原則**:
1. Domain Ownership（ドメインオーナーシップ）
2. Data as a Product（データ・アズ・ア・プロダクト）
3. Self-Serve Data Infrastructure as a Platform
4. Federated Computational Governance

**ドメインの種類**:
- Source-aligned: ソースシステムに近い
- Aggregated: 複数ソースの集約
- Consumer-aligned: 消費者ニーズに特化

**トポロジー**:
- Type 1: P2P 直接通信
- Type 2: 中央プラットフォーム経由
- Type 3: ハイブリッド

### Data Lakehouse

**定義**: Data Lake + Data Warehouse の融合。Delta Lake ベースのトランザクショナルストレージ。

**Delta Lake の特徴**:
- DML 操作（INSERT, UPDATE, DELETE, MERGE）
- ACID トランザクション
- タイムトラベル（過去データへのアクセス）
- スキーマ強制
- コンパクション（小ファイル統合）

**パフォーマンス最適化技術**:
- Data Skipping, Caching, Fast Indexing
- Predicate Pushdown, Column Pruning
- Vectorized Execution, Z-order

**解決する6つの問題**: 信頼性、データ鮮度、分析サポート、TCO、ガバナンス、複雑性

## 4. Data Mesh vs Data Fabric

| 項目 | Data Mesh | Data Fabric |
|:---|:---|:---|
| 哲学 | 組織構造の変革（分散化） | 技術的統合（メタデータ駆動） |
| 所有権 | ドメインチーム | 中央データチーム |
| フォーカス | 人・プロセス | テクノロジー |
| プラットフォーム | ドメインごとに自律 | 統一プラットフォーム |
| 併用 | 可能（補完的） | 可能（補完的） |

両者は排他的ではなく、補完的に併用可能。Data Fabric の技術基盤上で Data Mesh のドメインオーナーシップを実現するアプローチが有効。
