---
name: repo-spec
description: >
  既存リポジトリのコードベースを体系的に読解・分析し、
  システム概要・アーキテクチャ・API仕様・データモデル・ビジネスロジック・
  依存関係・設定・デプロイメント構成を網羅する仕様書をMarkdownで逆生成する。
  仕様書が存在しないレガシーコード、ドキュメントが陳腐化したリポジトリ、
  新メンバーオンボーディング用の技術文書が必要な場面で、
  コードからの仕様リバースエンジニアリングを一気通貫で実行する。
  ディレクトリ構造→エントリーポイント→依存関係→データフロー→API境界→
  ビジネスルールの順で段階的に解析し、各フェーズで品質確認を行う。
  Use when user says「このリポジトリの仕様書を作って」「コードから仕様を起こして」
  「リポジトリのドキュメントを生成して」「既存コードの仕様書がほしい」
  「このプロジェクトのアーキテクチャを文書化して」「API仕様をコードから抽出して」
  「データモデルのドキュメントを作って」「新メンバー向けの技術概要書を作って」
  「レガシーコードの仕様を把握したい」「repo-specで仕様書を生成して」。
  Do NOT use for: 新規プロジェクトの仕様設計（→ software-architecture / flow-architecture）、
  APIドキュメント自動生成ツールの設定（→ OpenAPI/Swagger 設定タスク）、
  コードの改善・リファクタリング（→ improve-finder / improve-flow）。
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: documentation
  pattern: "sequential"
  secondary-pattern: "domain-specific"
  based-on: "リバースエンジニアリング実践知 + arc42/C4 Model ドキュメンテーション手法"
---

# Skill: Repo Spec（既存リポジトリからの仕様書リバースエンジニアリング）

> **コードは動く仕様書だ — 読み解き、言語化し、残せ**

## Instructions

### ワークフロー内の位置

```
既存リポジトリ（コードベース）
  ↓
[repo-spec]
  ├─ Step 1: リポジトリ概況スキャン
  ├─ Step 2: エントリーポイント・依存関係の解析
  ├─ Step 3: アーキテクチャ構造の分析と文書化
  ├─ Step 4: API 境界・インターフェース仕様の抽出
  ├─ Step 5: データモデル・永続化層の分析
  ├─ Step 6: ビジネスロジック・ドメインルールの抽出
  ├─ Step 7: 設定・環境・デプロイメント構成の文書化
  └─ Step 8: 仕様書の統合・品質検証・引き渡し
  ↓
仕様書群（Markdown 8 ドキュメント）
  ↓
improve-finder / review / 新メンバーオンボーディング
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| リポジトリパス | 仕様書を生成する対象のリポジトリルート | `./my-project/`, `/path/to/repo` |
| フォーカス領域（任意） | 特定の仕様領域を優先 | `api`, `data-model`, `architecture` |
| 出力先ディレクトリ（任意） | 仕様書の出力先 | デフォルト: `<リポジトリルート>/specs/` |
| 対象ブランチ（任意） | 分析対象のブランチ | `main`, `develop` |
| 既存ドキュメント（任意） | 参照すべき既存のドキュメント | `README.md`, `docs/` |

### 出力

| 出力 | 形式 | 説明 |
|:---|:---|:---|
| 00-system-overview.md | Markdown | プロジェクト概要・技術スタック・ディレクトリ構造 |
| 01-architecture.md | Markdown + Mermaid | レイヤー構成・コンポーネント関係・データフロー |
| 02-api-spec.md | Markdown | エンドポイント一覧・型定義・認証・エラー |
| 03-data-model.md | Markdown + Mermaid | エンティティ・リレーション・制約・ER 図 |
| 04-business-logic.md | Markdown | ドメインルール・状態遷移・バリデーション |
| 05-dependencies.md | Markdown | 外部/内部依存・バージョン管理方針 |
| 06-configuration.md | Markdown | 環境変数・設定ファイル・シークレット管理 |
| 07-deployment.md | Markdown | インフラ構成・CI/CD・環境分離・監視 |

---

## Step 1: リポジトリ概況スキャン

全体像を 30 分で掴める「地図」を作る。この段階で技術スタック・規模・構造を把握し、後続ステップの解析戦略を決定する。

### 1a. ディレクトリ構造の取得

対象リポジトリのルートから 3 階層のツリーを取得する。`.gitignore` に従い `node_modules/`, `dist/`, `__pycache__/` 等のビルド成果物・依存キャッシュは除外する。`tree` や `find` コマンドでディレクトリ構造を取得する。

### 1b. 技術スタック検出

以下のファイル存在チェックで技術スタックを自動判定する:

| 検出ファイル | 技術スタック | 解析戦略参照 |
|:---|:---|:---|
| `package.json` + `next.config.*` | Next.js | [analysis-strategies.md](references/analysis-strategies.md)#nextjs |
| `package.json` + `vite.config.*` | Vite + React/Vue | 同上#vite |
| `requirements.txt` / `pyproject.toml` + `manage.py` | Django | 同上#django |
| `requirements.txt` / `pyproject.toml` + `main.py` (FastAPI import) | FastAPI | 同上#fastapi |
| `go.mod` | Go | 同上#go |
| `Gemfile` + `config/routes.rb` | Rails | 同上#rails |
| `pom.xml` / `build.gradle` | Java/Spring | 同上#spring |
| `Cargo.toml` | Rust | 同上#rust |

### 1c. リポジトリ規模の把握

| メトリクス | 取得方法 | 判定基準 |
|:---|:---|:---|
| ソースファイル数 | `find . -name '*.ts' -o -name '*.py' ...` + `wc -l` | S: <50, M: 50-200, L: 200+ |
| 総行数（LOC） | `cloc` or `wc -l` | S: <5K, M: 5K-50K, L: 50K+ |
| パッケージ依存数 | `package.json` / `requirements.txt` の行数 | — |
| Git コミット数 | `git log --oneline | wc -l` | プロジェクト成熟度の推定 |

### 1d. 既存ドキュメントの読解

README.md、CONTRIBUTING.md、docs/ 配下の既存ドキュメントを全て読み、以下を抽出する:
- プロジェクトの目的・背景
- セットアップ手順（依存する外部サービスの特定）
- 既知の設計判断・ADR

### 1e. モノレポ判定

`workspaces` (npm/yarn), `packages/` ディレクトリ, `turbo.json`, `nx.json`, `lerna.json` の存在で判定する。モノレポの場合は各パッケージを個別のサブリポジトリとして扱い、Step 2 以降をパッケージ単位で実行する。

**チェックリスト**:
- [ ] ディレクトリ構造を 3 階層まで取得した
- [ ] 技術スタックを特定し、解析戦略を決定した
- [ ] リポジトリ規模（S/M/L）を判定した
- [ ] README.md 等の既存ドキュメントを読解した
- [ ] モノレポかシングルレポかを判定した
- [ ] 出力先ディレクトリを決定した（デフォルト: `<リポジトリルート>/specs/`）

---

## Step 2: エントリーポイント・依存関係の解析

アプリケーションの「入口」と「部品同士のつながり」を特定する。ここがリバースエンジニアリングの起点になる。

### 2a. エントリーポイントの特定

| フレームワーク | エントリーポイント | 確認ファイル |
|:---|:---|:---|
| Next.js | `app/layout.tsx` / `pages/_app.tsx` | `next.config.*` のリダイレクト・ミドルウェア |
| React SPA | `src/main.tsx` / `src/index.tsx` | ルーター定義（`createBrowserRouter` 等） |
| FastAPI | `main.py` の `app = FastAPI()` | `router.include_router()` のチェーン |
| Django | `urls.py` + `settings.py` | `INSTALLED_APPS`, `MIDDLEWARE` |
| Go (Gin) | `main.go` の `gin.Default()` | `r.Group()` / `r.GET()` 等のルーティング |
| Rails | `config/routes.rb` | `config/application.rb` |
| Spring | `@SpringBootApplication` クラス | `@RestController` / `@Service` アノテーション |

### 2b. パッケージ依存の解析

パッケージマネージャの定義ファイル（`package.json`, `requirements.txt`, `go.mod`, `Gemfile`, `pom.xml` 等）とロックファイルを解析し、直接依存と主要ライブラリの役割を特定する。各依存を以下のカテゴリに分類する:
- **フレームワーク**: アプリの骨格（Next.js, FastAPI 等）
- **ORM/DB**: データ永続化（Prisma, SQLAlchemy, GORM 等）
- **認証**: 認証・認可（NextAuth, JWT, OAuth 等）
- **UI**: UIライブラリ（Tailwind, MUI, shadcn 等）
- **テスト**: テストフレームワーク（Jest, pytest, testing-library 等）
- **ユーティリティ**: その他（zod, lodash, date-fns 等）

### 2c. 内部モジュール依存グラフ

主要ディレクトリ間の import/require 関係を追跡し、依存の方向と強さを把握する。

**チェックリスト**:
- [ ] エントリーポイントを特定した
- [ ] 直接依存を全て解析しカテゴリ分類した（フレームワーク/ORM/認証/UI/テスト/ユーティリティ）
- [ ] 内部モジュール間の依存方向を把握した（循環依存の有無を含む）

---

## Step 3: アーキテクチャ構造の分析と文書化

コードの「骨格」を読み取り、C4 モデルの Container/Component レベルで文書化する。推測ではなくディレクトリ構造・import パターン・命名規則から客観的に判定する。

### 3a. アーキテクチャパターンの識別

コードの構造から該当するパターンを推定する:

| パターン | 識別手がかり | 典型的なディレクトリ構造 |
|:---|:---|:---|
| **MVC** | `controllers/`, `models/`, `views/` | Rails, Django デフォルト |
| **Layered** | `presentation/`, `application/`, `domain/`, `infrastructure/` | Spring, Clean Architecture |
| **Hexagonal** | `ports/`, `adapters/`, `domain/` | DDD 志向のプロジェクト |
| **Feature-based** | `features/<name>/` に model/controller/view が同居 | Next.js App Router, モダン React |
| **Serverless** | `functions/`, `handlers/`, `serverless.yml` | AWS Lambda, Vercel Functions |
| **Microservices** | `services/<name>/` が独立した package.json/go.mod を持つ | モノレポ内の複数サービス |

### 3b. コンポーネント境界の識別

各レイヤー/モジュールの責務を、ファイル名・export・import パターンから推定する。

### 3c. データフローの追跡

エントリーポイント（API リクエスト / ページレンダリング）から永続化層までの主要なデータフローを 3-5 パス追跡し、文書化する。

### 3d. C4 モデル図の生成

Mermaid 記法で以下を生成する（テンプレートは [spec-templates.md](references/spec-templates.md) 参照）:
- **Container 図**: システムを構成する主要コンテナ（Web App, API, DB, Queue 等）
- **Component 図**: 各コンテナ内の主要コンポーネントとその関係

**チェックリスト**:
- [ ] アーキテクチャパターンを識別し、根拠を記録した
- [ ] 各レイヤー/モジュールの責務を定義した
- [ ] 主要データフローを 3-5 パス追跡した
- [ ] Container 図を Mermaid で生成した
- [ ] Component 図を Mermaid で生成した
- [ ] 推測箇所には「推定」と明記した（幻覚防止）

---

## Step 4: API 境界・インターフェース仕様の抽出

外部に公開される API のコントラクト（契約）を正確に文書化する。ルーティング定義→ミドルウェア→ハンドラ→レスポンス型の順で解析する。

### 4a. ルーティング定義の全量抽出

フレームワーク固有のルーティング定義から全エンドポイントを抽出する。各フレームワークの解析対象ファイルは [analysis-strategies.md](references/analysis-strategies.md) を参照。ルーティング定義（ファイルベース / デコレータ / DSL）に応じた抽出方法を選択する。

### 4b. エンドポイント仕様テーブル

各エンドポイントを以下の形式で文書化:

| Method | Path | 認証 | Request Body | Response | 説明 |
|:---|:---|:---|:---|:---|:---|
| GET | `/api/users` | Bearer | — | `User[]` | ユーザー一覧取得 |
| POST | `/api/users` | Bearer + Admin | `CreateUserDto` | `User` | ユーザー作成 |

### 4c. ミドルウェア・認証フローの文書化

リクエスト処理チェーン（認証→バリデーション→ハンドラ→レスポンス）を文書化する。

### 4d. エラーハンドリングの文書化

グローバルエラーハンドラ、カスタムエラークラス、HTTPステータスコードの使い分けを記録する。

**チェックリスト**:
- [ ] 全エンドポイントを抽出し一覧化した
- [ ] 各エンドポイントの Method / Path / 認証 / 型を記録した
- [ ] ミドルウェアチェーンと認証・認可フローを文書化した
- [ ] エラーハンドリング戦略を記録した
- [ ] 型定義（Request/Response）をコードから正確に抽出した

---

## Step 5: データモデル・永続化層の分析

データの「形」と「関係」を正確に文書化する。ORM 定義やマイグレーションファイルが最も信頼できるソース。

### 5a. スキーマ定義の解析

Step 1b で検出した ORM/ツールに対応するスキーマ定義ファイルを解析する。各 ORM の定義ファイルと解析対象は [analysis-strategies.md](references/analysis-strategies.md) を参照。モデル定義・リレーション・インデックス・制約を抽出する。

### 5b. エンティティ定義テーブル

各エンティティを以下の形式で文書化:

| フィールド | 型 | NULL | デフォルト | 制約 | 説明 |
|:---|:---|:---|:---|:---|:---|
| id | UUID | No | `gen_random_uuid()` | PK | 一意識別子 |
| email | VARCHAR(255) | No | — | UNIQUE | メールアドレス |

### 5c. リレーション図（ER 図）の生成

Mermaid の `erDiagram` 記法でエンティティ間のリレーションを図示する。

### 5d. マイグレーション履歴の文書化

マイグレーションファイルのタイムスタンプと内容から、スキーマの変遷を記録する。

**チェックリスト**:
- [ ] 全エンティティの定義（フィールド・型・制約・デフォルト値）を正確に記録した
- [ ] リレーション（1:N, N:M, 1:1）を全て特定した
- [ ] ER 図を Mermaid で生成した
- [ ] インデックス定義とマイグレーション履歴を記録した

---

## Step 6: ビジネスロジック・ドメインルールの抽出

コードに埋め込まれた「なぜそう動くのか」を言語化する。最も難度が高いステップ — 推測と事実を厳密に分離すること。

### 6a. サービス層/ユースケース層の分析

ビジネスロジックが集中するレイヤーを特定し、主要なユースケースを列挙する:

| ユースケース | ファイル | メソッド | 概要 |
|:---|:---|:---|:---|
| ユーザー登録 | `src/services/user.ts` | `createUser()` | メール重複チェック → ハッシュ化 → DB 保存 → 確認メール送信 |

### 6b. バリデーションルールの一覧化

入力バリデーション（zod, class-validator, Pydantic 等）を全て抽出する:

| フィールド | ルール | エラーメッセージ |
|:---|:---|:---|
| email | `z.string().email()` | 「有効なメールアドレスを入力してください」 |
| password | `z.string().min(8).regex(/[A-Z]/)` | 「8文字以上、大文字を1文字以上含む」 |

### 6c. 状態遷移の文書化

ステータスフィールドを持つエンティティの状態遷移を Mermaid `stateDiagram` で図示する。

### 6d. 計算・集計ロジックの文書化

金額計算、スコア算出、集計処理等の重要な計算ロジックを数式とコード参照で記録する。

### 6e. 推測と事実の分離

ビジネスロジックの文書化では以下のルールを厳守する:
- **事実**: コードから直接読み取れるもの → 「〜である」と断定
- **推測**: コードの意図を推定するもの → 「【推定】〜と考えられる」と明記
- **不明**: コードからは読み取れないもの → 「【要確認】〜」と明記

**チェックリスト**:
- [ ] 主要ユースケースを列挙し処理フローを文書化した
- [ ] バリデーションルールを全て抽出した
- [ ] 状態遷移を持つエンティティを特定し図示した
- [ ] 重要な計算ロジックを記録した
- [ ] 推測箇所に「【推定】」、不明箇所に「【要確認】」を明記した
- [ ] ビジネスルールの根拠となるコード参照（ファイル:行番号）を記載した

---

## Step 7: 設定・環境・デプロイメント構成の文書化

「どう動かすか」「どこで動くか」を文書化する。環境依存の情報は特に新メンバーのオンボーディングで重要。

### 7a. 環境変数の一覧化

`.env.example`, `.env.sample`, `docker-compose.yml`, デプロイ設定から全環境変数を抽出する:

| 変数名 | 必須 | デフォルト | 説明 | カテゴリ |
|:---|:---|:---|:---|:---|
| `DATABASE_URL` | Yes | — | DB 接続文字列 | データベース |
| `JWT_SECRET` | Yes | — | JWT 署名キー | 認証 |
| `NODE_ENV` | No | `development` | 実行環境 | アプリ設定 |

### 7b. CI/CD パイプラインの文書化

`.github/workflows/`, `Jenkinsfile`, `.gitlab-ci.yml`, `Makefile` 等からビルド・テスト・デプロイのパイプラインを文書化する。

### 7c. コンテナ・インフラ構成の文書化

`Dockerfile`, `docker-compose.yml`, `k8s/`, `terraform/` 等からインフラ構成を文書化する。

**チェックリスト**:
- [ ] 全環境変数を抽出し一覧化した
- [ ] シークレット（API キー、DB パスワード等）は値ではなく説明のみ記載した
- [ ] CI/CD パイプラインを文書化した
- [ ] Docker/K8s 構成を文書化した（存在する場合）
- [ ] ローカル開発セットアップ手順を記録した

---

## Step 8: 仕様書の統合・品質検証・引き渡し

全仕様書を統合し、品質を保証し、利用者に引き渡す。review スキルに品質検証を委譲する。

### 8a. 仕様書インデックスの生成

全仕様書への目次と相互参照リンクを持つインデックスファイルを生成する:

```markdown
# リポジトリ仕様書

## 概要
- リポジトリ: <repository-name>
- 技術スタック: <tech-stack>
- 生成日: <date>
- 対象ブランチ: <branch>

## 仕様書一覧
1. [システム概要](00-system-overview.md)
2. [アーキテクチャ](01-architecture.md)
3. [API 仕様](02-api-spec.md)
4. [データモデル](03-data-model.md)
5. [ビジネスロジック](04-business-logic.md)
6. [依存関係](05-dependencies.md)
7. [設定](06-configuration.md)
8. [デプロイメント](07-deployment.md)
```

### 8b. 整合性チェック

| チェック対象 | 確認内容 |
|:---|:---|
| エンティティ名 | data-model と business-logic で同一エンティティ名が使われているか |
| API パス | api-spec のエンドポイントと architecture のデータフローが一致するか |
| 環境変数 | configuration の変数が deployment で参照されているか |
| 用語 | 全仕様書で用語が統一されているか |

### 8c. review スキルへの品質検証委譲

review スキルの **Part A: ドキュメントレビュー基準** を適用する:
- A-1: 要件カバレッジ（リポジトリの全主要コンポーネントが文書化されているか）
- A-2: 章間整合性（仕様書間で矛盾がないか）
- A-4: 可読性と説得力（新メンバーが理解できる構成か）

### 8d. 引き渡しサマリー

```markdown
## 仕様書生成完了

### 対象リポジトリ
- パス: <path>
- 技術スタック: <stack>
- 規模: <size> (ファイル数 / LOC)

### 生成ファイル
- 00-system-overview.md — システム概要（N 行）
- 01-architecture.md — アーキテクチャ（N 行、Mermaid 図 N 枚）
- 02-api-spec.md — API 仕様（N エンドポイント）
- 03-data-model.md — データモデル（N エンティティ、ER 図付き）
- 04-business-logic.md — ビジネスロジック（N ユースケース）
- 05-dependencies.md — 依存関係（N パッケージ）
- 06-configuration.md — 設定（N 環境変数）
- 07-deployment.md — デプロイメント

### 品質メトリクス
- 【推定】マーク: N 箇所
- 【要確認】マーク: N 箇所
- Mermaid 図: N 枚
```

**チェックリスト**:
- [ ] 仕様書インデックスを生成した
- [ ] エンティティ名・API パス・用語が仕様書間で統一されている
- [ ] review スキルの A-1, A-2, A-4 チェックを通過した
- [ ] 引き渡しサマリーを生成した（【推定】【要確認】マークの数を含む）

---

## Examples

### Example 1: Next.js + Prisma のフルスタックアプリの仕様書生成

```
「このNext.jsプロジェクトの仕様書を作って」

→ Step 1: next.config.ts + prisma/schema.prisma 検出 → Next.js + Prisma と判定、規模 M
→ Step 2: app/layout.tsx がエントリーポイント、25 の依存パッケージを分類
→ Step 3: App Router + Server Actions + Prisma の Feature-based 構成と判定
→ Step 4: app/api/ 配下の route.ts から 18 エンドポイントを抽出
→ Step 5: prisma/schema.prisma から 12 モデルの ER 図を生成
→ Step 6: lib/actions/ からバリデーション 30 ルール + 状態遷移 3 パターンを抽出
→ Step 7: .env.example から 15 環境変数、Vercel デプロイ構成を文書化
→ Step 8: 全 8 ドキュメントを統合、相互参照リンクを設定して引き渡し
```

### Example 2: FastAPI + SQLAlchemy の REST API の仕様書生成

```
「このPython APIの仕様書がほしい」

→ Step 1: pyproject.toml + main.py (FastAPI) 検出、規模 S
→ Step 2: main.py の app = FastAPI() + include_router チェーンを追跡
→ Step 3: Clean Architecture 構成（routers/services/repositories/models）と判定
→ Step 4: @router.get/post デコレータから 12 エンドポイントを抽出
→ Step 5: SQLAlchemy models + Alembic マイグレーションから 8 エンティティを解析
→ Step 6: Pydantic スキーマから 20 バリデーションルールを抽出
→ Step 7: docker-compose.yml + .env から DB/Redis 構成を文書化
→ Step 8: 統合 + 品質検証
```

### Example 3: Go + Gin のマイクロサービスの仕様書生成

```
「このGoサービスのアーキテクチャを文書化して」

→ Step 1: go.mod + main.go (gin.Default()) 検出、規模 M
→ Step 2: cmd/main.go → internal/ の Layered 構造を追跡
→ Step 3: handler/service/repository の 3 レイヤー + middleware チェーンを識別
→ Step 4: r.Group("/api/v1") 配下の 22 エンドポイントを抽出
→ Step 5: GORM struct タグから 15 エンティティ + DB インデックスを解析
→ Step 6: service 層のビジネスルール + error handling パターンを文書化
→ Step 7: Dockerfile + k8s/ マニフェストから本番デプロイ構成を文書化
→ Step 8: 統合 + review 委譲
```

### Example 4: Rails モノリスのレガシーアプリの仕様書生成

```
「レガシーRailsアプリの仕様を把握したい」

→ Step 1: Gemfile + config/routes.rb 検出、規模 L（300+ ファイル）
→ Step 2: routes.rb から 80+ ルーティング、config/initializers/ を全読解
→ Step 3: 標準 MVC + concerns/ によるモジュール共有パターンと判定
→ Step 4: routes.rb の resources/namespace から 45 エンドポイントを体系化
→ Step 5: db/schema.rb から 35 テーブル + マイグレーション 120 件の変遷を記録
→ Step 6: models/ の validates + callbacks + scope を全抽出、状態遷移 5 パターン
→ Step 7: .env + Capistrano/Docker デプロイ構成を文書化
→ Step 8: L 規模のため特に整合性チェックを重点実施
```

### Example 5: モノレポ（Turborepo）の仕様書生成

```
「このモノレポ全体の仕様書を生成して」

→ Step 1: turbo.json + packages/ 検出 → モノレポ判定、5 パッケージ
→ Step 2-7: パッケージ単位（web/api/shared/ui/config）で各ステップを実行
→ Step 8: パッケージ間依存図 + 統合インデックスを生成
```

### Example 6: React SPA（フロントエンドのみ）の仕様書生成

```
「このReactアプリのドキュメントを作って」

→ Step 1: vite.config.ts + React 検出、バックエンド API は外部
→ Step 2: src/main.tsx → React Router → 各ページコンポーネントを追跡
→ Step 3: Atomic Design パターン（atoms/molecules/organisms）を識別
→ Step 4: API クライアント（axios/fetch）の呼び出し先を全て抽出 → 外部 API 仕様として文書化
→ Step 5: データモデルは型定義（types/）から推定、DB 直接なし
→ Step 6: カスタムフック・Context によるステート管理ロジックを文書化
→ Step 7: Vite ビルド設定 + 環境変数を文書化
→ Step 8: フロントエンド固有の構成で統合（API 仕様は「外部 API 連携」として記載）
```

### Example 7: API 仕様のみにフォーカスした部分仕様書生成

```
「API仕様だけコードから抽出して」

→ Step 1: フォーカス領域 = api → Step 1-2 は簡易実行
→ Step 4: 全エンドポイントを詳細に文書化（型定義・認証・エラーコード・レート制限）
→ Step 8: 02-api-spec.md のみを出力
```

### Example 8: ドキュメントゼロのレガシー Python スクリプト群の仕様書生成

```
「ドキュメントが何もないPythonスクリプト群の仕様を起こして」

→ Step 1: フレームワーク未検出 → スクリプト群と判定、各 .py の main/if __name__ を走査
→ Step 2: import 文から内部/外部依存を手動追跡（パッケージマネージャ定義なしの場合あり）
→ Step 3: スクリプト間の呼び出し関係からパイプライン構造を推定
→ Step 4: API なし → スキップ（CLI 引数があれば CLI インターフェースとして文書化）
→ Step 5: DB 接続があれば直 SQL を解析、なければスキップ
→ Step 6: 各スクリプトの処理フローを関数単位で文書化、【推定】マーク多用
→ Step 7: 実行方法（cron/手動）を推定して文書化
→ Step 8: 【要確認】マーク多数 → 確認依頼リストを別途出力
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| フレームワークを特定できない | 独自構成 or 複数フレームワーク混在 | エントリーポイント（main/index）から手動追跡。[analysis-strategies.md](references/analysis-strategies.md) の汎用戦略を適用 |
| ORM 定義がなく SQL が直書きされている | レガシーコード or 軽量フレームワーク | SQL ファイル / クエリ文字列を grep で全量抽出し、テーブル定義を逆算。`CREATE TABLE` / `ALTER TABLE` も検索 |
| ルーティングが動的に生成される | メタプログラミング / デコレータの自動登録 | 実行時ログ or テストコードからエンドポイントを推定。【推定】マークを付与 |
| ビジネスロジックがコントローラに散在している | Fat Controller パターン（責務分離不足） | コントローラを全読解し、ロジック部分を抽出。構造の問題は仕様書の「改善提案」セクションに記載 |
| テストコードが存在しない | テスト未整備 | コードの分岐条件から仕様を推定するが、【推定】マークを必ず付与。確認依頼リストに追加 |
| モノレポでパッケージ間の依存が複雑 | 内部パッケージの相互参照 | パッケージ依存図を先に作成し、依存の下流（shared/core）から順に解析 |
| 環境変数の用途が不明 | 変数名が曖昧 or ドキュメントなし | コード内での参照箇所を全て検索し、使用コンテキストから用途を推定。【推定】マークを付与 |
| ファイル数が多すぎて解析が終わらない | L 規模のリポジトリ | Step 1 で主要ディレクトリを特定し、優先度をつけて解析。テスト・設定ファイルは後回し |
| 認証フローが複雑で追いきれない | OAuth + JWT + セッション等の複合 | 認証ミドルウェアのエントリーポイントから追跡。シーケンス図で文書化 |
| 古い依存が大量にあり把握しきれない | 依存のアップデート未実施 | 直接依存のみに集中。間接依存は `outdated` コマンドで概要把握に留める |
| コメントが嘘をついている（実装と乖離） | コメントの更新漏れ | コメントは参考程度に留め、コードの実際の振る舞いを優先して文書化する |

---

## References

| ファイル | 内容 |
|:---|:---|
| [analysis-strategies.md](references/analysis-strategies.md) | フレームワーク別（Next.js/Rails/Django/FastAPI/Go/Spring/Rust）の解析戦略・注目ファイル・パターン |
| [spec-templates.md](references/spec-templates.md) | 8 仕様書の Markdown テンプレート集（プレースホルダー付き） |
| [framework-patterns.md](references/framework-patterns.md) | 主要フレームワークのディレクトリ規約・命名規則・アーキテクチャパターン対応表 |
| [reverse-engineering-checklist.md](references/reverse-engineering-checklist.md) | リバースエンジニアリング時の見落としポイント・確認チェックリスト |

---

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **deep-research** | 補助（Step 1） | Step 1 でフレームワーク固有のディレクトリ規約やベストプラクティスを調査する際に委譲。特に馴染みの薄いフレームワークの解析戦略策定に活用 |
| **software-architecture** | 補助（Step 3） | Step 3 のアーキテクチャ分析で C4 モデルの Container/Component 図の生成パターンと設計判断の評価観点を参照。Clean Architecture / Hexagonal の識別基準を提供 |
| **diagram** | 補助（Step 3/5/6） | Step 3 のアーキテクチャ図、Step 5 の ER 図、Step 6 の状態遷移図の Mermaid 記法生成を委譲 |
| **review** | 品質検証（Step 8） | Step 8 で仕様書全体に Part A ドキュメントレビュー基準（A-1 要件カバレッジ、A-2 章間整合性、A-4 可読性）を適用して品質検証 |
| **data-arch** | 参照（Step 5） | Step 5 のデータモデル分析でデータアーキテクチャの評価フレームワーク（6 種アーキテクチャ比較、データモデリング手法）を参照 |
| **improve-finder** | 後工程 | repo-spec で現状を文書化した後、improve-finder で改善機会を体系的にスキャンする。仕様書が improve-finder の入力コンテキストとなる |
| **distill** | 並行スキル | repo-spec は「コード → 仕様書」の逆方向ドキュメント生成、distill は「知識ソース → 蒸留メモ」の要約生成。目的と入力が異なる |
