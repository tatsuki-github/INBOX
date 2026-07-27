# フレームワーク別解析戦略

> 各フレームワーク固有のディレクトリ構造・注目ファイル・解析順序を定義する。Step 1b の技術スタック判定後に該当セクションを参照する。

---

## Next.js {#nextjs}

### 注目ファイル（優先順）

| 優先度 | ファイル/ディレクトリ | 解析内容 |
|:---|:---|:---|
| 1 | `next.config.ts` / `next.config.mjs` | リダイレクト、リライト、環境変数、プラグイン |
| 2 | `app/layout.tsx` / `pages/_app.tsx` | ルートレイアウト、グローバル Provider |
| 3 | `app/**/page.tsx` / `pages/**/*.tsx` | ページ一覧（= ルーティング） |
| 4 | `app/**/route.ts` / `pages/api/**/*.ts` | API エンドポイント |
| 5 | `middleware.ts` | リクエスト前処理（認証、リダイレクト） |
| 6 | `prisma/schema.prisma` / `drizzle/schema.ts` | データモデル |
| 7 | `lib/` / `utils/` / `actions/` | ビジネスロジック、Server Actions |
| 8 | `components/` | UI コンポーネント体系 |
| 9 | `tailwind.config.ts` | デザインシステム（カラー、フォント、間隔） |

### App Router vs Pages Router の判定

| 判定基準 | App Router | Pages Router |
|:---|:---|:---|
| `app/` ディレクトリ存在 | ✅ | ❌ |
| `pages/` ディレクトリ存在 | ❌ (or 共存) | ✅ |
| `layout.tsx` 存在 | ✅ | ❌ |
| `_app.tsx` 存在 | ❌ | ✅ |
| Server Components 使用 | ✅ | ❌ |

### 解析パターン

1. **ルーティング**: ファイルベースルーティングをツリー構造で全列挙
2. **データフェッチ**: `fetch` / `prisma` / Server Actions の使い分けを分類
3. **認証**: NextAuth / Clerk / カスタム認証の判定
4. **ミドルウェア**: `middleware.ts` のマッチャーパターンを解析

---

## Vite + React/Vue {#vite}

### 注目ファイル

| 優先度 | ファイル/ディレクトリ | 解析内容 |
|:---|:---|:---|
| 1 | `vite.config.ts` | プラグイン、プロキシ、ビルド設定 |
| 2 | `src/main.tsx` / `src/main.ts` | エントリーポイント、Provider 設定 |
| 3 | `src/App.tsx` | ルーティング定義（React Router 等） |
| 4 | `src/routes/` / `src/pages/` | ページコンポーネント一覧 |
| 5 | `src/api/` / `src/services/` | API クライアント・通信層 |
| 6 | `src/store/` / `src/hooks/` | 状態管理（Zustand/Redux/Jotai） |
| 7 | `src/components/` | UI コンポーネント |
| 8 | `src/types/` | 型定義（API レスポンス型、ドメインモデル） |

---

## FastAPI {#fastapi}

### 注目ファイル

| 優先度 | ファイル/ディレクトリ | 解析内容 |
|:---|:---|:---|
| 1 | `main.py` / `app/main.py` | FastAPI インスタンス、include_router |
| 2 | `routers/` / `api/` | エンドポイント定義 |
| 3 | `models/` / `schemas/` | SQLAlchemy モデル / Pydantic スキーマ |
| 4 | `services/` / `crud/` | ビジネスロジック |
| 5 | `core/config.py` | 設定・環境変数 |
| 6 | `deps.py` / `dependencies/` | DI（依存性注入） |
| 7 | `alembic/` | マイグレーション履歴 |
| 8 | `tests/` | テスト（API テストからエンドポイント仕様を逆算可能） |

### 解析パターン

1. **Pydantic スキーマ**: Request/Response の型を Pydantic モデルから完全抽出
2. **依存性注入**: `Depends()` チェーンを追跡し、認証・DB セッション管理を把握
3. **バックグラウンドタスク**: `BackgroundTasks` の使用パターンを確認

---

## Django {#django}

### 注目ファイル

| 優先度 | ファイル/ディレクトリ | 解析内容 |
|:---|:---|:---|
| 1 | `settings.py` / `settings/` | INSTALLED_APPS, MIDDLEWARE, DB 設定 |
| 2 | `urls.py`（各アプリ + プロジェクト） | ルーティング定義 |
| 3 | `models.py`（各アプリ） | データモデル |
| 4 | `views.py` / `viewsets.py` | ビュー / API ビューセット |
| 5 | `serializers.py` | DRF シリアライザ（API の型定義） |
| 6 | `admin.py` | 管理画面の構成 |
| 7 | `forms.py` | フォームバリデーション |
| 8 | `signals.py` | シグナル（イベント駆動ロジック） |
| 9 | `migrations/` | マイグレーション履歴 |

---

## Go (Gin/Echo/Chi) {#go}

### 注目ファイル

| 優先度 | ファイル/ディレクトリ | 解析内容 |
|:---|:---|:---|
| 1 | `go.mod` | 依存パッケージ、Go バージョン |
| 2 | `cmd/` / `main.go` | エントリーポイント |
| 3 | `internal/handler/` / `internal/controller/` | HTTP ハンドラ |
| 4 | `internal/service/` | ビジネスロジック |
| 5 | `internal/repository/` | データアクセス層 |
| 6 | `internal/model/` / `internal/entity/` | データモデル（GORM struct） |
| 7 | `internal/middleware/` | ミドルウェア（認証、ログ、CORS） |
| 8 | `pkg/` | 共有ユーティリティ |
| 9 | `Makefile` | ビルド・テスト・デプロイコマンド |

### 解析パターン

1. **Standard Layout**: `cmd/`, `internal/`, `pkg/` の Go 標準プロジェクト構成
2. **Wire/fx**: DI フレームワーク使用時のプロバイダ定義を追跡
3. **struct タグ**: `json:"..."`, `gorm:"..."`, `validate:"..."` からフィールド仕様を抽出

---

## Rails {#rails}

### 注目ファイル

| 優先度 | ファイル/ディレクトリ | 解析内容 |
|:---|:---|:---|
| 1 | `config/routes.rb` | ルーティング定義 |
| 2 | `db/schema.rb` | 現在のスキーマ（最も信頼できるソース） |
| 3 | `app/models/` | モデル定義（バリデーション、アソシエーション） |
| 4 | `app/controllers/` | コントローラ（API エンドポイント） |
| 5 | `config/application.rb` | アプリ全体設定 |
| 6 | `config/initializers/` | 初期化設定（認証、メール、キャッシュ等） |
| 7 | `app/services/` / `app/jobs/` | サービスオブジェクト、バックグラウンドジョブ |
| 8 | `db/migrate/` | マイグレーション履歴（スキーマ変遷） |
| 9 | `app/views/` / `app/serializers/` | ビュー / API レスポンス形式 |

### 解析パターン

1. **Concerns**: `app/models/concerns/`, `app/controllers/concerns/` でモジュール共有パターンを確認
2. **Callbacks**: `before_save`, `after_create` 等のモデルコールバックを全列挙
3. **Scope**: 名前付きスコープからクエリパターンを抽出

---

## Spring Boot (Java/Kotlin) {#spring}

### 注目ファイル

| 優先度 | ファイル/ディレクトリ | 解析内容 |
|:---|:---|:---|
| 1 | `pom.xml` / `build.gradle` | 依存パッケージ |
| 2 | `@SpringBootApplication` クラス | エントリーポイント |
| 3 | `@RestController` / `@Controller` | API エンドポイント |
| 4 | `@Service` | ビジネスロジック |
| 5 | `@Repository` / `@Entity` | データアクセス・モデル |
| 6 | `application.yml` / `application.properties` | 設定 |
| 7 | `@Configuration` | Bean 設定、セキュリティ設定 |
| 8 | `@Aspect` | AOP（横断的関心事） |

---

## Rust {#rust}

### 注目ファイル

| 優先度 | ファイル/ディレクトリ | 解析内容 |
|:---|:---|:---|
| 1 | `Cargo.toml` | 依存パッケージ、ワークスペース構成 |
| 2 | `src/main.rs` / `src/lib.rs` | エントリーポイント |
| 3 | `src/routes/` / `src/handlers/` | HTTP ハンドラ（Actix/Axum） |
| 4 | `src/models/` | データモデル（Diesel/SeaORM struct） |
| 5 | `src/services/` | ビジネスロジック |
| 6 | `migrations/` | マイグレーション |

---

## 汎用戦略（フレームワーク特定不能時）

フレームワークを特定できない場合の解析アプローチ:

1. **エントリーポイント探索**: `main`, `index`, `app`, `server` を含むファイルを検索
2. **import/require 追跡**: エントリーポイントから import チェーンを再帰的に追跡
3. **HTTP サーバー検出**: `listen`, `serve`, `createServer` 等のキーワードで HTTP サーバーを検索
4. **DB 接続検出**: `connect`, `createConnection`, `Database`, `Pool` 等で DB 接続を検索
5. **設定ファイル検出**: `.env`, `config.*`, `settings.*` で設定を検索
6. **テストファイル解析**: テストコードからインターフェースの期待動作を逆算
