# 仕様書テンプレート集

> 8 仕様書の Markdown テンプレート。各テンプレートのプレースホルダーを埋めて使用する。

---

## 00: システム概要（00-system-overview.md）

```markdown
# システム概要

## プロジェクト情報

| 項目 | 内容 |
|:---|:---|
| プロジェクト名 | <PROJECT_NAME> |
| リポジトリ | <REPO_URL> |
| 技術スタック | <TECH_STACK> |
| 対象ブランチ | <BRANCH> |
| 仕様書生成日 | <DATE> |
| リポジトリ規模 | <SIZE>（ファイル数: <FILE_COUNT>, LOC: <LOC>） |

## プロジェクト概要

<README.md や既存ドキュメントから抽出したプロジェクトの目的・背景>

## 技術スタック

| カテゴリ | 技術 | バージョン | 用途 |
|:---|:---|:---|:---|
| フレームワーク | <FRAMEWORK> | <VERSION> | <PURPOSE> |
| ORM/DB | <ORM> | <VERSION> | <PURPOSE> |
| 認証 | <AUTH> | <VERSION> | <PURPOSE> |
| UI | <UI_LIB> | <VERSION> | <PURPOSE> |
| テスト | <TEST> | <VERSION> | <PURPOSE> |

## ディレクトリ構造

\```
<PROJECT_ROOT>/
├── <DIR_TREE>
\```

### 主要ディレクトリの役割

| ディレクトリ | 役割 |
|:---|:---|
| <DIR> | <ROLE> |

## 関連仕様書

- [アーキテクチャ](01-architecture.md)
- [API 仕様](02-api-spec.md)
- [データモデル](03-data-model.md)
- [ビジネスロジック](04-business-logic.md)
- [依存関係](05-dependencies.md)
- [設定](06-configuration.md)
- [デプロイメント](07-deployment.md)
```

---

## 01: アーキテクチャ（01-architecture.md）

```markdown
# アーキテクチャ仕様

## アーキテクチャパターン

| 項目 | 内容 |
|:---|:---|
| パターン | <PATTERN>（例: Layered, Clean Architecture, Feature-based） |
| 識別根拠 | <EVIDENCE> |

## Container 図

\```mermaid
graph TB
    <CONTAINER_DIAGRAM>
\```

## Component 図

\```mermaid
graph TB
    <COMPONENT_DIAGRAM>
\```

## レイヤー/モジュール構成

| レイヤー | ディレクトリ | 責務 | 依存先 |
|:---|:---|:---|:---|
| <LAYER> | <DIR> | <RESPONSIBILITY> | <DEPENDS_ON> |

## 主要データフロー

### フロー 1: <FLOW_NAME>

\```mermaid
sequenceDiagram
    <SEQUENCE_DIAGRAM>
\```

### フロー 2: <FLOW_NAME>

...

## 設計判断・特記事項

| 判断 | 内容 | 根拠 |
|:---|:---|:---|
| <DECISION> | <CONTENT> | <EVIDENCE_OR_推定> |
```

---

## 02: API 仕様（02-api-spec.md）

```markdown
# API 仕様

## 概要

| 項目 | 内容 |
|:---|:---|
| ベース URL | <BASE_URL> |
| 認証方式 | <AUTH_METHOD> |
| レスポンス形式 | <FORMAT>（JSON） |
| API バージョニング | <VERSIONING> |

## エンドポイント一覧

### <RESOURCE_GROUP>

| Method | Path | 認証 | 概要 |
|:---|:---|:---|:---|
| <METHOD> | <PATH> | <AUTH> | <DESCRIPTION> |

## エンドポイント詳細

### <METHOD> <PATH>

**概要**: <DESCRIPTION>

**認証**: <AUTH_REQUIRED>

**Request**:
| パラメータ | 位置 | 型 | 必須 | 説明 |
|:---|:---|:---|:---|:---|
| <PARAM> | <LOCATION> | <TYPE> | <REQUIRED> | <DESC> |

**Response（成功時）**:
\```json
<RESPONSE_EXAMPLE>
\```

**エラーレスポンス**:
| ステータス | コード | 説明 |
|:---|:---|:---|
| <STATUS> | <CODE> | <DESC> |

## ミドルウェアチェーン

| 順序 | ミドルウェア | 役割 |
|:---|:---|:---|
| <ORDER> | <MIDDLEWARE> | <ROLE> |

## 認証・認可フロー

\```mermaid
sequenceDiagram
    <AUTH_FLOW>
\```
```

---

## 03: データモデル（03-data-model.md）

```markdown
# データモデル仕様

## ER 図

\```mermaid
erDiagram
    <ER_DIAGRAM>
\```

## エンティティ定義

### <ENTITY_NAME>

| フィールド | 型 | NULL | デフォルト | 制約 | 説明 |
|:---|:---|:---|:---|:---|:---|
| <FIELD> | <TYPE> | <NULLABLE> | <DEFAULT> | <CONSTRAINT> | <DESC> |

**リレーション**:
| 対象 | 種別 | 外部キー | 説明 |
|:---|:---|:---|:---|
| <TARGET> | <RELATION_TYPE> | <FK> | <DESC> |

**インデックス**:
| 名前 | カラム | ユニーク | 説明 |
|:---|:---|:---|:---|
| <INDEX_NAME> | <COLUMNS> | <UNIQUE> | <DESC> |

## マイグレーション履歴

| 日時 | マイグレーション名 | 変更内容 |
|:---|:---|:---|
| <DATE> | <MIGRATION_NAME> | <CHANGES> |
```

---

## 04: ビジネスロジック（04-business-logic.md）

```markdown
# ビジネスロジック仕様

## ユースケース一覧

| # | ユースケース | ファイル | メソッド | 概要 |
|:---|:---|:---|:---|:---|
| <NUM> | <USE_CASE> | <FILE> | <METHOD> | <SUMMARY> |

## ユースケース詳細

### <USE_CASE_NAME>

**処理フロー**:
1. <STEP>
2. <STEP>

**ファイル参照**: `<FILE_PATH>:<LINE>`

## バリデーションルール

| エンティティ | フィールド | ルール | エラーメッセージ |
|:---|:---|:---|:---|
| <ENTITY> | <FIELD> | <RULE> | <ERROR_MSG> |

## 状態遷移

### <ENTITY_NAME> のステータス遷移

\```mermaid
stateDiagram-v2
    <STATE_DIAGRAM>
\```

| 遷移 | トリガー | 条件 | 副作用 |
|:---|:---|:---|:---|
| <FROM> → <TO> | <TRIGGER> | <CONDITION> | <SIDE_EFFECT> |

## 計算ロジック

### <CALCULATION_NAME>

**数式**: <FORMULA>
**実装**: `<FILE_PATH>:<LINE>`
**備考**: <NOTES>
```

---

## 05-07: 残りのテンプレート

### 05-dependencies.md

主要セクション:
- 直接依存一覧（カテゴリ別テーブル）
- 内部モジュール依存グラフ（Mermaid）
- バージョン管理方針
- セキュリティアドバイザリ

### 06-configuration.md

主要セクション:
- 環境変数一覧（必須/任意、カテゴリ別テーブル）
- 設定ファイル一覧
- シークレット管理方針
- 環境別設定差分（development/staging/production）

### 07-deployment.md

主要セクション:
- インフラ構成図（Mermaid）
- CI/CD パイプライン（ステージ別テーブル）
- Docker/コンテナ構成
- 環境分離（dev/staging/prod）
- 監視・ログ・アラート設定
- ローカル開発セットアップ手順
