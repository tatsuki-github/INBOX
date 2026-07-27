# フレームワークパターン対応表

> 主要フレームワークのディレクトリ規約・命名規則・アーキテクチャパターンを対応させた早見表。Step 3 のアーキテクチャ識別で参照する。

---

## フレームワーク × アーキテクチャパターン

| フレームワーク | デフォルトパターン | 発展パターン | 識別の手がかり |
|:---|:---|:---|:---|
| **Next.js (App Router)** | Feature-based | Layered (Server/Client 分離) | `app/<feature>/` に page + route + component が同居 |
| **Next.js (Pages Router)** | Pages-based (MVC 的) | Feature-based | `pages/` + `components/` + `lib/` の 3 分離 |
| **React SPA** | Component-based | Atomic Design / Feature-based | `components/atoms/molecules/` or `features/<name>/` |
| **Vue (Nuxt)** | Feature-based | Layered | `pages/` + `composables/` + `server/` |
| **FastAPI** | Layered (Router/Service/Repo) | Clean Architecture | `routers/` + `services/` + `repositories/` の 3 層 |
| **Django** | MVC (MTV) | DDD 風 apps 分割 | `models.py` + `views.py` + `templates/` per app |
| **Rails** | MVC | Concerns + Service Objects | `app/models/` + `app/controllers/` + `app/views/` |
| **Go (Gin/Echo)** | Standard Layout | Clean Architecture | `cmd/` + `internal/` + `pkg/` |
| **Spring Boot** | Layered (Annotation-driven) | Hexagonal / DDD | `@Controller` + `@Service` + `@Repository` |
| **Express/Fastify** | 自由形式 | MVC / Layered | `routes/` + `controllers/` + `models/` (あれば) |
| **NestJS** | Module-based (DI) | Hexagonal / CQRS | `@Module()` + `@Controller()` + `@Injectable()` |
| **Rust (Actix/Axum)** | Layered | Clean Architecture | `handlers/` + `services/` + `models/` |

---

## ディレクトリ名 → 責務マッピング

### よくあるディレクトリ名とその責務

| ディレクトリ名 | 責務 | レイヤー | 代替名 |
|:---|:---|:---|:---|
| `controllers/` | HTTP リクエスト処理 | Presentation | `handlers/`, `routes/`, `api/` |
| `services/` | ビジネスロジック | Application/Domain | `usecases/`, `interactors/` |
| `repositories/` | データアクセス抽象化 | Infrastructure | `dao/`, `stores/`, `gateways/` |
| `models/` | データ構造定義 | Domain | `entities/`, `schemas/`, `types/` |
| `middleware/` | 横断的関心事 | Cross-cutting | `interceptors/`, `guards/` |
| `utils/` | 汎用ユーティリティ | Shared | `helpers/`, `lib/`, `common/` |
| `config/` | 設定管理 | Infrastructure | `settings/`, `env/` |
| `migrations/` | DB スキーマ変更履歴 | Infrastructure | `db/migrate/`, `alembic/` |
| `tests/` | テストコード | — | `__tests__/`, `spec/`, `test/` |
| `types/` | 型定義 | Shared | `interfaces/`, `dtos/` |
| `hooks/` | React カスタムフック | Presentation | `composables/` (Vue) |
| `store/` | 状態管理 | Application | `state/`, `atoms/` |
| `assets/` | 静的ファイル | — | `public/`, `static/` |
| `components/` | UI コンポーネント | Presentation | `ui/`, `views/` |

---

## 命名規則パターン

| フレームワーク | ファイル命名 | クラス/関数命名 | 例 |
|:---|:---|:---|:---|
| Next.js | kebab-case / PascalCase (コンポーネント) | PascalCase (コンポーネント) | `user-profile.tsx` → `UserProfile` |
| React | PascalCase (コンポーネント) | PascalCase | `UserProfile.tsx` → `UserProfile` |
| FastAPI | snake_case | snake_case (関数) / PascalCase (モデル) | `user_router.py` → `get_users()` |
| Django | snake_case | snake_case / PascalCase (モデル) | `user_views.py` → `class User(Model)` |
| Rails | snake_case | PascalCase (クラス) / snake_case (メソッド) | `user.rb` → `class User < ApplicationRecord` |
| Go | snake_case (パッケージ) / camelCase (内部) | PascalCase (公開) / camelCase (非公開) | `user_handler.go` → `func GetUser()` |
| Spring | PascalCase | PascalCase (クラス) / camelCase (メソッド) | `UserController.java` → `getUser()` |
| NestJS | kebab-case | PascalCase (クラス) / camelCase (メソッド) | `user.controller.ts` → `class UserController` |

---

## アーキテクチャパターン判定フロー

```
ディレクトリ構造を確認
  │
  ├─ controllers/ + models/ + views/ → MVC
  │
  ├─ domain/ + application/ + infrastructure/ → Clean Architecture / Hexagonal
  │     └─ ports/ + adapters/ があれば → Hexagonal 確定
  │
  ├─ features/<name>/ に複数層が同居 → Feature-based
  │
  ├─ functions/ or handlers/ + serverless.yml → Serverless
  │
  ├─ services/<name>/ が独立パッケージ → Microservices
  │
  ├─ @Module() + @Controller() + @Injectable() → Module-based (NestJS)
  │
  └─ 上記に該当しない → 自由形式 / カスタム構成
      └─ import パターンから依存方向を分析して推定
```
