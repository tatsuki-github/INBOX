# 型設計パターン詳細リファレンス

> 『Effective TypeScript 第2版』の型設計に関する項目を実践コード例で解説する。

---

## 1. タグ付きユニオン（判別可能ユニオン）— 項目29, 34

### パターン: 状態マシンの型安全な表現

```typescript
// ====== NG: 不正な状態を許容する設計 ======
interface RequestState {
  isLoading: boolean;
  error: string | null;
  data: string[] | null;
}

// 以下の不正状態が型上は許される:
// { isLoading: true, error: "fail", data: ["x"] }

// ====== OK: タグ付きユニオンで有効な状態のみ表現 ======
type RequestState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "success"; data: string[] };

// 使用時: switch で網羅的に処理
function renderState(state: RequestState): string {
  switch (state.status) {
    case "idle":
      return "Ready";
    case "loading":
      return "Loading...";
    case "error":
      return `Error: ${state.error}`;
    case "success":
      return state.data.join(", ");
    default:
      // 新しいバリアント追加時にコンパイルエラーで検出
      const _exhaustive: never = state;
      throw new Error(`Unexpected state: ${JSON.stringify(_exhaustive)}`);
  }
}
```

### パターン: API レスポンスの型安全な設計

```typescript
// ====== NG: ユニオンを含むインターフェイス ======
interface ApiResponse {
  type: "user" | "post";
  // user の場合のみ使用
  username?: string;
  email?: string;
  // post の場合のみ使用
  title?: string;
  body?: string;
}

// ====== OK: インターフェイスのユニオン ======
type ApiResponse =
  | { type: "user"; username: string; email: string }
  | { type: "post"; title: string; body: string };

function handleResponse(res: ApiResponse) {
  if (res.type === "user") {
    // res.username, res.email が型安全にアクセス可能
    console.log(res.username);
  } else {
    // res.title, res.body が型安全にアクセス可能
    console.log(res.title);
  }
}
```

---

## 2. 入力には寛容に、出力には厳格に — 項目30

```typescript
// パラメーターは広い型を受け入れる
interface CameraOptions {
  center?: LngLat;          // オプション
  zoom?: number;
  bearing?: number;
  pitch?: number;
}

// LngLat は複数の形式を受け入れる
type LngLat =
  | { lng: number; lat: number }
  | { lon: number; lat: number }
  | [number, number];

// 戻り値は具体的な型を返す
interface Camera {
  center: { lng: number; lat: number };  // 正規化済み
  zoom: number;
  bearing: number;
  pitch: number;
}

// 入力は寛容、出力は厳格
function setCamera(options: CameraOptions): Camera {
  // 内部で正規化して返す
  // ...
}
```

---

## 3. null の扱い — 項目32, 33

### パターン: null を型の外側に押しやる

```typescript
// ====== NG: null が内部に散らばる ======
function getExtent(nums: number[]) {
  let min: number | undefined;
  let max: number | undefined;
  for (const num of nums) {
    if (min === undefined) {
      min = num;
      max = num;
    } else {
      min = Math.min(min, num);
      max = Math.max(max, num);
      //                ~~~ 'number | undefined' は 'number' に割り当てられない
    }
  }
  return [min, max]; // (number | undefined)[]
}

// ====== OK: null をまとめて外側に ======
function getExtent(nums: number[]): [number, number] | null {
  if (nums.length === 0) return null;
  let min = nums[0];
  let max = nums[0];
  for (const num of nums) {
    min = Math.min(min, num);
    max = Math.max(max, num);
  }
  return [min, max]; // [number, number] — null は外側で処理
}
```

### パターン: null を型エイリアスに含めない

```typescript
// ====== NG: null が型エイリアスに埋もれる ======
type UserName = string | null;
function greet(name: UserName) {
  return `Hello, ${name.toUpperCase()}`;
  //                ~~~ 'name' は 'null' の可能性があります
}

// ====== OK: null は使用箇所で明示 ======
type UserName = string;
function greet(name: UserName | null) {
  if (name === null) return "Hello, anonymous";
  return `Hello, ${name.toUpperCase()}`; // OK
}
```

---

## 4. 精度の高い型 — 項目35, 36

### パターン: string より精度の高い型

```typescript
// ====== NG: string で何でも通る ======
interface Album {
  artist: string;
  title: string;
  releaseDate: string;   // "YYYY-MM-DD" を期待しているが何でも入る
  recordingType: string;  // "live" | "studio" を期待
}

// ====== OK: リテラル型とテンプレートリテラル型 ======
type RecordingType = "live" | "studio";
type DateString = `${number}-${number}-${number}`;

interface Album {
  artist: string;
  title: string;
  releaseDate: DateString;
  recordingType: RecordingType;
}
```

### パターン: ブランド型で混同を防ぐ

```typescript
// 同じ number だが意味が異なる値を区別
type UserId = number & { readonly __brand: "UserId" };
type PostId = number & { readonly __brand: "PostId" };

function getUser(id: UserId): User { /* ... */ }
function getPost(id: PostId): Post { /* ... */ }

// 使用時
const userId = 42 as UserId;
const postId = 100 as PostId;

getUser(userId);  // OK
getUser(postId);  // コンパイルエラー！型が異なる
```

---

## 5. readonly の活用 — 項目14

```typescript
// ====== 配列の不変性 ======
function arraySum(arr: readonly number[]): number {
  // arr.push(1);  // コンパイルエラー！readonly
  return arr.reduce((a, b) => a + b, 0);
}

// ====== オブジェクトの不変性 ======
interface Config {
  readonly host: string;
  readonly port: number;
}

function startServer(config: Readonly<Config>) {
  // config.port = 3000;  // コンパイルエラー！
}

// ====== 関数の入力パラメーターは readonly を推奨 ======
// 変更しないことを型で保証する
function processItems(items: readonly Item[]): Result[] {
  return items.map(item => transform(item)); // map は新しい配列を返す
}
```

---

## 6. type vs interface の使い分け — 項目13

| 場面 | 推奨 | 理由 |
|:---|:---|:---|
| オブジェクト型の定義 | `interface` | 拡張性、宣言のマージ、エラーメッセージの明瞭さ |
| ユニオン型・交差型 | `type` | interface では表現不可 |
| タプル型 | `type` | interface では不自然 |
| マッピング型・条件型 | `type` | interface では不可 |
| ライブラリの公開 API | `interface` | 利用者が拡張可能 |
| プロジェクト内の統一 | どちらか一方に統一 | 一貫性が最重要 |

```typescript
// interface: オブジェクト型に適する
interface User {
  id: string;
  name: string;
  email: string;
}

// type: ユニオン・タプル・マッピングに適する
type Result = Success | Failure;
type Pair = [string, number];
type Partial<T> = { [K in keyof T]?: T[K] };
```

---

## 7. 余剰プロパティチェック — 項目11

```typescript
interface Options {
  title: string;
  darkMode?: boolean;
}

// オブジェクトリテラルでは余剰プロパティがチェックされる
const opts: Options = {
  title: "Dashboard",
  darkmode: true,
  // ~~~~~~~ 'darkmode' は型 'Options' に存在しません。'darkMode' ですか？
};

// 変数経由だとチェックされない（構造的型付け）
const intermediate = { title: "Dashboard", darkmode: true };
const opts2: Options = intermediate; // OK（darkmode は無視される）

// ポイント: オブジェクトリテラルに型アノテーションを付けて
//           余剰プロパティチェックを活用する
```
