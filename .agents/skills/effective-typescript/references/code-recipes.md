# TypeScript 実践レシピ集

> 『Effective TypeScript 第2版』の実践パターンを即座に適用できるレシピとして整理。

---

## 1. 網羅性チェック（Exhaustiveness Check）— 項目59

### レシピ A: assertUnreachable 関数

```typescript
function assertUnreachable(x: never): never {
  throw new Error(`Unexpected value: ${x}`);
}

type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "square"; side: number }
  | { kind: "triangle"; base: number; height: number };

function area(shape: Shape): number {
  switch (shape.kind) {
    case "circle":
      return Math.PI * shape.radius ** 2;
    case "square":
      return shape.side ** 2;
    case "triangle":
      return (shape.base * shape.height) / 2;
    default:
      return assertUnreachable(shape);
  }
}
// Shape に新しいバリアントを追加すると、
// default の assertUnreachable でコンパイルエラーが発生する
```

### レシピ B: ペアパターン（型と値の同期）

```typescript
type Color = "red" | "green" | "blue";

// Record で全キーの網羅を強制
const colorHex: Record<Color, string> = {
  red: "#ff0000",
  green: "#00ff00",
  blue: "#0000ff",
  // "yellow" を追加し忘れると Color に追加した時点でエラー
};
```

---

## 2. 型ガード（Type Guard）— 項目22

### レシピ A: typeof / instanceof / in

```typescript
function processValue(value: string | number | Date) {
  if (typeof value === "string") {
    // value: string
    return value.toUpperCase();
  }
  if (value instanceof Date) {
    // value: Date
    return value.toISOString();
  }
  // value: number
  return value.toFixed(2);
}
```

### レシピ B: カスタム型ガード（is キーワード）

```typescript
interface Fish {
  swim(): void;
}
interface Bird {
  fly(): void;
}

function isFish(pet: Fish | Bird): pet is Fish {
  return "swim" in pet;
}

function move(pet: Fish | Bird) {
  if (isFish(pet)) {
    pet.swim(); // pet: Fish
  } else {
    pet.fly();  // pet: Bird
  }
}
```

### レシピ C: Array.isArray による絞り込み

```typescript
function flatten(input: string | string[]): string[] {
  if (Array.isArray(input)) {
    return input;       // input: string[]
  }
  return [input];       // input: string
}
```

---

## 3. オブジェクトの安全な反復 — 項目60

### レシピ A: Object.entries（推奨）

```typescript
interface Point {
  x: number;
  y: number;
}

const point: Point = { x: 1, y: 2 };

// OK: Object.entries で安全に反復
for (const [key, value] of Object.entries(point)) {
  console.log(`${key}: ${value}`);
  // key: string, value: number
}
```

### レシピ B: キーの明示的列挙

```typescript
const keys = ["x", "y"] as const;
for (const key of keys) {
  console.log(`${key}: ${point[key]}`);
  // key: "x" | "y" — 型安全
}
```

### NG: for-in ループの危険性

```typescript
// NG: k は string 型（プロトタイプチェーンのプロパティも含むため）
for (const k in point) {
  console.log(point[k]);
  //          ~~~~~~~~ Element implicitly has an 'any' type
}
```

---

## 4. async/await と型の流れ — 項目27

### レシピ: コールバックを async に変換

```typescript
// ====== NG: コールバックスタイル ======
function fetchData(
  url: string,
  callback: (error: Error | null, data?: string) => void
): void {
  // 型が複雑で、エラーハンドリングが漏れやすい
}

// ====== OK: async/await ======
async function fetchData(url: string): Promise<string> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.text();
}

// 並列実行
async function fetchMultiple(urls: string[]): Promise<string[]> {
  return Promise.all(urls.map(url => fetchData(url)));
  // 戻り値型は自動的に Promise<string[]> に推論される
}
```

---

## 5. unknown の活用 — 項目46

### レシピ: 外部入力の安全な処理

```typescript
// ====== NG: any で受ける ======
function parseJSON(json: string): any {
  return JSON.parse(json);
}
const data = parseJSON('{"name": "Alice"}');
data.nonExistentMethod(); // 実行時エラー、型チェックなし

// ====== OK: unknown で受けて絞り込む ======
function parseJSON(json: string): unknown {
  return JSON.parse(json);
}

// 型ガードで安全に使用
function isUser(obj: unknown): obj is { name: string; age: number } {
  return (
    typeof obj === "object" &&
    obj !== null &&
    "name" in obj &&
    typeof (obj as { name: unknown }).name === "string" &&
    "age" in obj &&
    typeof (obj as { age: unknown }).age === "number"
  );
}

const data = parseJSON('{"name": "Alice", "age": 30}');
if (isUser(data)) {
  console.log(data.name); // data: { name: string; age: number }
}
```

### レシピ: ライブラリとの連携（Zod）

```typescript
import { z } from "zod";

const UserSchema = z.object({
  name: z.string(),
  age: z.number(),
});

type User = z.infer<typeof UserSchema>;

function parseUser(input: unknown): User {
  return UserSchema.parse(input);
  // バリデーション失敗時は ZodError をスロー
}
```

---

## 6. ジェネリックの実践パターン — 項目50-53

### レシピ A: 型安全なイベントエミッター

```typescript
type EventMap = {
  click: { x: number; y: number };
  focus: undefined;
  input: { value: string };
};

class TypedEmitter<T extends Record<string, unknown>> {
  private listeners = new Map<keyof T, Set<Function>>();

  on<K extends keyof T>(
    event: K,
    listener: T[K] extends undefined ? () => void : (payload: T[K]) => void
  ): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(listener);
  }

  emit<K extends keyof T>(
    event: K,
    ...args: T[K] extends undefined ? [] : [T[K]]
  ): void {
    this.listeners.get(event)?.forEach(fn => fn(...args));
  }
}

const emitter = new TypedEmitter<EventMap>();
emitter.on("click", (payload) => {
  console.log(payload.x, payload.y); // 型安全
});
emitter.emit("click", { x: 10, y: 20 }); // OK
emitter.emit("focus"); // OK（引数なし）
```

### レシピ B: 条件型でオーバーロードを置き換え

```typescript
// ====== NG: オーバーロード ======
function wrap(value: string): string[];
function wrap(value: number): number[];
function wrap(value: string | number): (string | number)[] {
  return [value];
}

// ====== OK: 条件型 ======
function wrap<T extends string | number>(value: T): T[] {
  return [value];
}

const a = wrap("hello"); // string[]
const b = wrap(42);       // number[]
```

---

## 7. 移行パターン — 項目79-83

### レシピ: 段階的な strict 化

```jsonc
// Step 1: 最小限の tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ES2020",
    "moduleResolution": "node",
    "allowJs": true,        // JS と TS の共存
    "checkJs": false,       // JS の型チェックは後で
    "outDir": "./dist",
    "strict": false          // まだ strict にしない
  }
}

// Step 2: noImplicitAny を有効化
{
  "compilerOptions": {
    "noImplicitAny": true   // ← まずこれだけ
  }
}

// Step 3: strictNullChecks を有効化
{
  "compilerOptions": {
    "noImplicitAny": true,
    "strictNullChecks": true // ← 次にこれ
  }
}

// Step 4: strict を有効化（最終目標）
{
  "compilerOptions": {
    "strict": true           // すべての厳格チェック
  }
}
```

### レシピ: ファイル単位の移行（@ts-check）

```javascript
// @ts-check
// ↑ この1行で JavaScript ファイルに型チェックを適用

/** @type {string} */
let name = "Alice";

/** @param {number} a @param {number} b @returns {number} */
function add(a, b) {
  return a + b;
}

add("hello", "world");
// ~~~ Argument of type 'string' is not assignable to parameter of type 'number'
```

---

## 8. tsconfig.json 推奨設定 — 項目2, 付録B

```jsonc
{
  "compilerOptions": {
    // === 厳格性 ===
    "strict": true,
    "noUncheckedIndexedAccess": true,      // 配列・オブジェクトアクセスの安全性
    "noImplicitOverride": true,            // override キーワード必須
    "noPropertyAccessFromIndexSignature": true,

    // === モジュール ===
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "esModuleInterop": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,

    // === 出力 ===
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",

    // === パス ===
    "rootDir": "./src",
    "baseUrl": ".",

    // === チェック ===
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

---

## 9. enum の代替パターン — 項目72

```typescript
// ====== 文字列リテラルのユニオン ======
type Direction = "north" | "south" | "east" | "west";

// ====== as const オブジェクト（値が必要な場合） ======
const Direction = {
  North: "north",
  South: "south",
  East: "east",
  West: "west",
} as const;

type Direction = (typeof Direction)[keyof typeof Direction];
// "north" | "south" | "east" | "west"

// 使用例
function move(dir: Direction) {
  console.log(`Moving ${dir}`);
}
move(Direction.North); // OK
move("north");          // OK
```

---

## 10. 型の重複を避けるユーティリティ型 — 項目15

```typescript
interface State {
  userId: string;
  pageTitle: string;
  recentFiles: string[];
  pageContents: string;
}

// 一部のプロパティだけの型
type TopNavState = Pick<State, "userId" | "pageTitle" | "recentFiles">;

// すべてオプショナル
type PartialState = Partial<State>;

// すべて必須
type RequiredState = Required<State>;

// 特定キーを除外
type StateWithoutContents = Omit<State, "pageContents">;

// 戻り値型を取得
type ReturnOfFetch = ReturnType<typeof fetch>;

// パラメーター型を取得
type ParamsOfFetch = Parameters<typeof fetch>;
```
