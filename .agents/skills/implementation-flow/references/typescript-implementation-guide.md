# TypeScript 実装ガイド（Phase 5 詳細リファレンス）

implementation-flow Phase 5 で適用する TypeScript コーディング規約と型設計パターンの詳細。
Effective TypeScript 83 項目のうち、implementation-flow で特に重要なものを抽出。

---

## 型設計パターン

### タグ付きユニオン（Discriminated Union）

不正な状態を型レベルで排除する最重要パターン。

**❌ Bad — boolean フラグで状態管理**

```typescript
interface ApiState {
  isLoading: boolean;
  error: Error | null;
  data: User[] | null;
}
// isLoading=true かつ data=User[] が表現可能 → 不正状態
```

**✅ Good — タグ付きユニオンで有効な状態のみ表現**

```typescript
type ApiState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: User[] };
```

### ブランド型（Branded Types）

プリミティブ型の意味を区別し、誤った代入を型レベルで防止する。

```typescript
type UserId = string & { readonly __brand: unique symbol };
type OrderId = string & { readonly __brand: unique symbol };

function createUserId(raw: string): UserId {
  // バリデーション
  return raw as UserId;
}

// UserId を OrderId に渡すとコンパイルエラー
function getOrder(orderId: OrderId): Order { ... }
getOrder(createUserId("u-123")); // ← 型エラー ✅
```

### never 型による網羅性チェック

switch 文で全ケースを処理していることをコンパイル時に保証する。

```typescript
function assertNever(x: never): never {
  throw new Error(`Unexpected value: ${x}`);
}

function handleState(state: ApiState): string {
  switch (state.status) {
    case 'idle': return '待機中';
    case 'loading': return '読み込み中';
    case 'error': return `エラー: ${state.error.message}`;
    case 'success': return `${state.data.length} 件`;
    default: return assertNever(state);
    // ↑ 新しい status を追加したのに case を書き忘れるとコンパイルエラー
  }
}
```

---

## コーディング規約

| ルール | 理由 | 代替 |
|:-------|:-----|:-----|
| `any` 禁止 | 型安全性の喪失 | `unknown` + 型ガード |
| `enum` 禁止 | Tree-shaking 不可、型推論が弱い | 文字列リテラルユニオン |
| `as` 型アサーション最小化 | 型安全性をバイパスする | 型ガード関数で絞り込み |
| パブリック API に戻り値型明示 | 意図しない型変更を防止 | 関数シグネチャに `: ReturnType` |
| `interface` vs `type` | `interface` は拡張用、`type` はユニオン用 | 用途で使い分け |
| `readonly` 活用 | 不変性保証 | オブジェクト・配列に `readonly` / `ReadonlyArray` |
| `null` vs `undefined` | API 境界は `null`、内部は `undefined` | 一貫した使い分け |

### enum の代替パターン

```typescript
// ❌ Bad
enum Status { Active = 'active', Inactive = 'inactive' }

// ✅ Good
const STATUS = {
  Active: 'active',
  Inactive: 'inactive',
} as const;
type Status = typeof STATUS[keyof typeof STATUS];
// → type Status = 'active' | 'inactive'
```

---

## 実装順序の詳細（TDD 統合版）

以下の順序で実装することで、依存関係エラーを最小化し、型推論とテストで品質を担保する。

### ステップ 1-2: 型・定数（TDD 対象外）

```
1. types/         — 全ドメイン型、タグ付きユニオン、ブランド型
2. constants/     — マジックナンバー排除、設定値
```

コンパイル時検証で十分。テストは書かない。

### ステップ 3-4: ドメイン層 TDD サイクル

各モジュールごとに **Red → Green → Refactor** を反復する。

```
3. utils/         — 純粋関数（型ガード、変換関数）+ *.test.ts
4. services/      — ビジネスロジック、DTO 変換 + *.test.ts
```

| フェーズ | スキル | 作業 |
|:---------|:-------|:-----|
| **Red** | test Step 1-4 | 失敗するテストを書き、`vitest` で失敗を確認 |
| **Green** | effective-typescript | テストを通す最小実装 |
| **Refactor** | refactor + test | 構造改善。テストは Green を維持 |

**TDD 中断条件**: test Step 1 で「取るに足らない」と判定されたコードには Red を書かない。

### ステップ 5-9: UI 層（実装ファースト → 振る舞いテスト）

```
5. hooks/         — カスタムフック（状態管理、副作用）
6. components/    — Presentational → Container
7. pages/         — ページコンポーネント（ルーティング）
8. styles/        — CSS → CSS Modules / Tailwind 統合
9. index.ts       — Public API の Re-export（バレルファイル）
10. *.test.ts(x)  — hooks / components / API route の振る舞いテスト（実装後）
```

**注意**: バレルファイル（index.ts）は公開 API のみ Re-export する。内部実装はエクスポートしない。

---

## Vitest 規約

### 実行コマンド

| 対象 | コマンド | 用途 |
|:-----|:---------|:-----|
| Backend | `cd backend && npm test` | 単発実行 |
| Backend | `cd backend && npm run test:watch` | TDD サイクル中のウォッチ |
| Frontend | `cd frontend && npm test` | 単発実行 |

### テストファイル命名・配置

| 規約 | 例 |
|:-----|:---|
| 本番コードと同階層 | `utils/calculateDiscount.ts` → `utils/calculateDiscount.test.ts` |
| Backend 単体テスト | `backend/tests/unit/[module].test.ts` |
| 拡張子 | `.test.ts` または `.test.tsx`（プロジェクト慣習に従う） |

### TDD サイクル中の確認手順

1. **Red**: テストファイル作成 → `vitest [test-file]` で **失敗** を確認
2. **Green**: 本番コード実装 → 同コマンドで **成功** を確認
3. **Refactor**: 構造改善 → 再度 **成功** を確認（振る舞い不変）
4. モジュール完了後: `npm test` で関連スイート全体を実行

---

## 検証実行（verify）規約

QE5 / QE6 の品質ゲートで、**シェル上で実際にコマンドを実行し、全て成功すること**を必須とする。口頭での「通ったはず」は不可。

### 実行コマンド

| 対象 | コマンド | 用途 |
|:-----|:---------|:-----|
| Backend | `cd backend && npm test` | vitest 全件実行 |
| Backend | `cd backend && npm run build` | TypeScript コンパイル（`tsc`） |
| Frontend | `cd frontend && npm test` | vitest 全件実行 |
| Frontend | `cd frontend && npm run lint` | ESLint |
| Frontend | `cd frontend && npm run build` | 型チェック + Vite バンドル（`tsc -b && vite build`） |

**frontend の実行順序**: `npm test` → `npm run lint` → `npm run build`（lint が軽いため build の前に実行）

**both（本リポジトリのデフォルト）の例**:

```bash
cd backend && npm test && npm run build
cd frontend && npm test && npm run lint && npm run build
```

### 対象パッケージの判定

Phase 0 で `backend` / `frontend` / `both` を記録する。実行時は `git diff` で最終確定する。

| 記録値 | 実行する検証 |
|:---|:---|
| `backend` | backend: test + build |
| `frontend` | frontend: test + lint + build |
| `both` | 上記両方 |

**スキップルール**:

- 該当パッケージに本番ソース（`src/` 等）の変更が無い場合、そのパッケージの build / lint はスキップ可
- テストファイルのみ変更した場合でも、同一パッケージの `npm test` は実行する
- Phase 0 で `backend` のみと記録したが frontend を変更した場合は `both` として再実行する

### 実行タイミング（必須 3 回）

| タイミング | 実施箇所 | 内容 |
|:---|:---|:---|
| Phase 5 実装直後 | QE5-0 | 検証実行（初回） |
| refactor 完了後 | QE5-4 完了条件 | 検証実行（退行検証・R5 直前） |
| 最終統合レビュー前 | QE6-0 | 検証実行（最終） |

bug-triage-fix や QE5-6 でコードを修正した場合も、修正後に対象パッケージの検証実行を再実行する。

### 永続ドキュメント（Docs Sync）と verify の関係

- `specs/` / `docs/` の Markdown は **npm test / build / lint の対象外**
- **QE5-7 Docs Sync** は QE5-4 退行検証の後・R5 の直前に実施する（コード確定後）
- doc と実装の整合は **R5** および Phase 6 **A-5** でレビュー担保する
- 詳細は [docs-sync-guide.md](docs-sync-guide.md) を参照

---

## CSS 実装ルール

### デザイントークンの CSS 変数化

```css
:root {
  /* Phase 4 のデザイン仕様から転写 */
  --color-primary-500: #3b82f6;
  --color-neutral-100: #f3f4f6;
  --color-neutral-900: #111827;
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --font-size-body: clamp(0.875rem, 0.8rem + 0.25vw, 1rem);
}
```

### フルード設計

```css
.container {
  width: clamp(320px, 90vw, 1200px);
  padding: clamp(var(--spacing-sm), 3vw, var(--spacing-xl));
  font-size: clamp(0.875rem, 0.8rem + 0.25vw, 1rem);
}
```

### アクセシビリティ対応

```css
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-neutral-100: #1f2937;
    --color-neutral-900: #f9fafb;
  }
}
```

---

## コンポーネント実装パターン

### Presentational コンポーネント

```typescript
type ButtonVariant = 'primary' | 'secondary' | 'ghost';

interface ButtonProps {
  readonly variant: ButtonVariant;
  readonly label: string;
  readonly onClick: () => void;
  readonly disabled?: boolean;
}

export function Button({ variant, label, onClick, disabled = false }: ButtonProps): JSX.Element {
  return (
    <button
      className={`btn btn--${variant}`}
      onClick={onClick}
      disabled={disabled}
      type="button"
    >
      {label}
    </button>
  );
}
```

### Container コンポーネント

```typescript
export function ProfileFormContainer(): JSX.Element {
  const { state, actions } = useProfileForm();

  switch (state.status) {
    case 'idle':
    case 'editing':
      return <ProfileForm data={state.data} onSubmit={actions.submit} />;
    case 'submitting':
      return <ProfileForm data={state.data} onSubmit={actions.submit} disabled />;
    case 'success':
      return <SuccessMessage message="保存しました" />;
    case 'error':
      return <ProfileForm data={state.data} onSubmit={actions.submit} error={state.error} />;
    default:
      return assertNever(state);
  }
}
```
