---
name: effective-typescript
description: >
  TypeScript コードの設計・実装・レビューを、書籍『Effective TypeScript 第2版』
  （Dan Vanderkam 著、83項目）の原則に基づいて支援する。
  型設計、型推論の活用、ジェネリック、タグ付きユニオン、any の排除、
  コード移行など、実践的なTypeScriptのベストプラクティスを適用する。
  Use when user says「TypeScriptを書いて」「型を設計して」「TSのコードをレビューして」
  「型エラーを修正して」「TypeScriptのベストプラクティスを教えて」
  「JavaScriptをTypeScriptに移行して」「型を改善して」「ジェネリックを書いて」
  「enumを使うべきか」「any を減らしたい」「型安全にしたい」。
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: development
  based-on: "Effective TypeScript 2nd Edition (Dan Vanderkam, 83 Items)"
---

# Skill: Effective TypeScript

> **構文を知っていることと、いつ使うべきかを知っていることは別のことである**

## Instructions

TypeScript コードの作成・レビュー時は、以下の原則を適用すること。
本スキルの根拠はすべて書籍『Effective TypeScript 第2版』の83項目に基づく。

---

## 原則 1: 型システムの正しいメンタルモデル

### TypeScript と JavaScript の関係（項目1-5）

- TypeScript は JavaScript の**構文的スーパーセット**。型は実行時に**消去**される
- コード生成（JavaScript 出力）は型チェックとは**完全に独立**している
- TypeScript の型システムは JavaScript の実行時の動作を**モデリング**する（健全性は保証しない）
- 構造的型付け: 型は「シール」されない。宣言以外のプロパティを持つ値も適合する

**実装ルール**:
- 実行時に型を判定する必要がある場合は**タグ付きユニオン**か**プロパティチェック**を使う
- `instanceof` で interface / type を判定しない（実行時に存在しない）
- `--strict` を常に有効にする（`noImplicitAny` + `strictNullChecks` + その他）

---

## 原則 2: 型推論を最大限に活用する

### 不要な型アノテーションを書かない（項目18-28）

TypeScript の型推論は非常に強力。冗長な型アノテーションはコードのノイズになる。

**書くべき場所**:
- 関数のパラメーター（推論できない）
- パブリック API の戻り値（意図を明示・エラーの局所化）
- オブジェクトリテラル（余剰プロパティチェックの活用）

**書かないべき場所**:
- 初期値から型が明らかなローカル変数
- 関数の戻り値（型が自明な場合）
- 式から推論可能な中間変数

```typescript
// NG: 冗長な型アノテーション
const person: { name: string; age: number } = { name: "Alice", age: 30 };

// OK: 推論に任せる
const person = { name: "Alice", age: 30 };

// OK: パブリック API には型を明示
function getUser(id: string): Promise<User> { /* ... */ }
```

### 制御フロー解析の活用（項目22）

- TypeScript は `if`、`switch`、`instanceof`、`in` 演算子等で型を**自動的に絞り込む**
- 型ガード関数（`is` キーワード）でカスタムの絞り込みを定義できる
- エイリアスを作ったら一貫してそれを使う（項目23）

---

## 原則 3: 有効な状態のみ表現する型を設計する

### 型設計の核心（項目29-42）

CRITICAL: これは本書で最も重要な章の1つ。

**タグ付きユニオン（判別可能ユニオン）を使う**（項目29, 34）:

```typescript
// NG: 不正な状態を許容する設計
interface State {
  isLoading: boolean;
  error: string | null;
  data: string | null;
}
// isLoading=true かつ error="fail" という矛盾した状態を許してしまう

// OK: 有効な状態のみ表現
type State =
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "success"; data: string };
```

**Postel の法則: 入力には寛容に、出力には厳格に**（項目30）:
- 関数のパラメーターは広い型（ユニオン、`readonly`）を受け入れる
- 関数の戻り値は具体的な型を返す

**string / number を直接使わず、より精度の高い型を選択する**（項目35-36）:

```typescript
// NG
function play(artist: string, title: string): void {}
play("Led Zeppelin", "Stairway to Heaven"); // OK
play("Stairway to Heaven", "Led Zeppelin"); // 引数が逆でもエラーにならない！

// OK: ブランド型や専用型を使う
type ArtistName = string & { readonly __brand: "ArtistName" };
type SongTitle = string & { readonly __brand: "SongTitle" };
```

**オプションプロパティは限定的に使用する**（項目37）:
- `?` プロパティは「未設定」と「未定義」を混同させる
- 明示的に `| undefined` をユニオンに含めるか、必須プロパティにすることを検討

**null / undefined を型エイリアスに含めない**（項目32）:
```typescript
// NG
type UserOrNull = User | null;
function getUser(): UserOrNull {}  // null がどこに伝播するか追跡困難

// OK: null は使用箇所で明示
function getUser(): User | null {}
```

---

## 原則 4: any 型を排除する

### 不健全性と any の制限（項目5, 43-49）

**any は型安全性を破壊する。以下のルールを厳守する**:

1. **any よりも `unknown` を使う**（項目46）
   - `unknown` は型安全な「何でも入る」型。使用前に型の絞り込みが必須
   - `any` はすべての型チェックを無効化する
2. **any を使う場合はスコープを最小限に**（項目43）
   ```typescript
   // NG: 変数全体を any にする
   const config: any = loadConfig();

   // OK: 必要な箇所のみ
   const config = loadConfig();
   (config as any).experimentalFeature;
   ```
3. **any をそのまま使わず、より具体的な形式で使う**（項目44）
   - `any` → `any[]`、`{[key: string]: any}`、`(...args: any[]) => any` 等
4. **安全でない型アサーションは関数内部に隠す**（項目45）
   ```typescript
   // 内部で any を使うが、外部には型安全な API を公開
   function cacheLast<T extends Function>(fn: T): T {
     let lastArgs: any[] | null = null;
     let lastResult: any;
     return function (...args: any[]) {
       if (lastArgs && shallowEqual(lastArgs, args)) return lastResult;
       lastResult = fn(...args);
       lastArgs = args;
       return lastResult;
     } as unknown as T;
   }
   ```
5. **型カバレッジを監視する**（項目49）
   - `type-coverage` ツールで any の割合を計測

---

## 原則 5: ジェネリックを適切に使う

### ジェネリックと型レベルプログラミング（項目50-58）

**ジェネリックを「型に対する関数」と考える**（項目50）:
- 型パラメーター `T` は関数の引数に相当
- `extends` で制約を加え、安全性を確保

**不必要な型パラメーターを避ける**（項目51）:
```typescript
// NG: T が1回しか使われていない → ジェネリック不要
function identity<T>(arg: T): T { return arg; }
// これは有用だが、以下は不要
function printLength<T extends { length: number }>(arg: T): void {
  console.log(arg.length);
}
// OK: ジェネリックなしで十分
function printLength(arg: { length: number }): void {
  console.log(arg.length);
}
```

**条件型をオーバーロードより優先する**（項目52）:
```typescript
// NG: オーバーロード
function double(x: number): number;
function double(x: string): string;
function double(x: number | string) { /* ... */ }

// OK: 条件型
function double<T extends number | string>(
  x: T
): T extends string ? string : number {
  // ...
}
```

**コード生成を複雑な型の代替手段として検討する**（項目58）:
- 型が複雑すぎる場合、スキーマや DB 定義からコードを自動生成することを検討
- pgTyped、Prisma、GraphQL Code Generator 等

---

## 原則 6: TypeScript レシピ

### 実践パターン（項目59-64）

**never 型で網羅性チェック**（項目59）:
```typescript
type Shape = { kind: "circle"; r: number } | { kind: "square"; s: number };

function area(shape: Shape): number {
  switch (shape.kind) {
    case "circle": return Math.PI * shape.r ** 2;
    case "square": return shape.s ** 2;
    default:
      // 新しいバリアントを追加し忘れるとコンパイルエラー
      const _exhaustive: never = shape;
      throw new Error(`Unexpected shape: ${_exhaustive}`);
  }
}
```

**Record 型で値の同期を保つ**（項目61）:
```typescript
type PageKey = "home" | "about" | "contact";
// すべてのキーに対応する値が必須
const pageUrls: Record<PageKey, string> = {
  home: "/",
  about: "/about",
  contact: "/contact",
};
```

**ブランド型で名目的型付け**（項目64）:
```typescript
type Meters = number & { readonly __brand: "Meters" };
type Kilometers = number & { readonly __brand: "Kilometers" };

function metersToKm(m: Meters): Kilometers {
  return (m / 1000) as Kilometers;
}
```

---

## 原則 7: TypeScript 独自機能を避ける

### ECMAScript の機能を優先（項目72）

以下の TypeScript 独自機能は**避ける**:

| 避けるべき機能 | 代替手段 | 理由 |
|:---|:---|:---|
| `enum`（特に数値） | 文字列リテラルのユニオン型 | 名目的型付けが構造的型付けと矛盾。JS ユーザーが使えない |
| `namespace` | ES モジュール (`import`/`export`) | 標準の模倣で十分 |
| パラメータープロパティ | 通常のプロパティ宣言 | 可読性が低い |
| トリプルスラッシュ (`///`) | `import` | 非標準 |
| デコレーター（実験的） | 高階関数 | 仕様未確定のリスク |

```typescript
// NG: enum
enum Flavor { Vanilla = "vanilla", Chocolate = "chocolate" }

// OK: ユニオン型
type Flavor = "vanilla" | "chocolate" | "strawberry";
```

---

## 原則 8: 型宣言のベストプラクティス

### 型宣言と @types（項目65-71）

- TypeScript と `@types` は `devDependencies` に追加する（項目65）
- パブリック API で使われるすべての型をエクスポートする（項目67）
- API コメントに TSDoc を使う（項目68）
- モジュールオーグメンテーションで既存の型を改善できる（項目71）

---

## 原則 9: JavaScript からの移行

### 段階的な移行戦略（項目79-83）

1. **モダン JavaScript を書く**（項目79）: ES2015+ の機能を採用
2. **`@ts-check` と JSDoc で試す**（項目80）: ファイル単位で型チェック
3. **`allowJs` で共存**（項目81）: JS と TS を混在させる
4. **依存関係グラフの下から上へ移行**（項目82）: import される側から変換
5. **`noImplicitAny` を有効にして完了**（項目83）: これがオンになるまで移行は未完了

---

## コードレビュー時のチェックリスト

TypeScript コードをレビューする際は以下を確認:

**型設計**:
- [ ] 不正な状態を表現できる型がないか（タグ付きユニオンにすべき）
- [ ] `string` や `number` を直接使っている箇所に、より精度の高い型を適用できないか
- [ ] オプションプロパティが本当に必要か（必須にできないか）
- [ ] null/undefined が型エイリアスに埋もれていないか

**型安全性**:
- [ ] `any` が使われていないか（`unknown` に置き換え可能か）
- [ ] `as` 型アサーションが適切か（型ガードに置き換え可能か）
- [ ] `enum` が使われていないか（ユニオン型に置き換え可能か）

**型推論**:
- [ ] 冗長な型アノテーションがないか（推論に任せるべき箇所）
- [ ] パブリック API に戻り値型が明示されているか
- [ ] 型の絞り込みが適切に行われているか

**パターン**:
- [ ] switch 文に網羅性チェック（never 型）があるか
- [ ] ジェネリックの型パラメーターが本当に必要か（1回しか使われていないものはないか）
- [ ] `Record` で値の同期が保たれているか

---

## Examples

### Example 1: 型設計の改善

```
「effective-typescript スキルで、この State 型をタグ付きユニオンにリファクタリングして」
```

→ 不正な状態を排除するタグ付きユニオンに変換し、switch 文に網羅性チェックを追加。

### Example 2: コードレビュー

```
「effective-typescript スキルで、この TypeScript コードをレビューして」
```

→ 上記チェックリストに沿って型設計・型安全性・パターンの観点からレビュー。

### Example 3: JavaScript からの移行

```
「effective-typescript スキルで、この JS ファイルを TypeScript に移行して」
```

→ 段階的移行戦略に沿い、型アノテーション追加・any の排除・strict 有効化を実施。

### Example 4: ジェネリック関数の設計

```
「effective-typescript スキルで、このユーティリティ関数にジェネリックを適用して」
```

→ 型パラメーターの必要性を判断し、制約付きジェネリックを設計。

---

## Troubleshooting

| 問題 | 原因 | 対処 |
|:---|:---|:---|
| 型エラーが多すぎる | `strict` を一度に有効化 | 段階的に有効化（noImplicitAny → strictNullChecks → strict） |
| any が蔓延 | 移行時の妥協が残存 | `type-coverage` で計測し、段階的に unknown / 具体型に置換 |
| 型が複雑すぎて読めない | 過度な型レベルプログラミング | コード生成を検討（項目58）。型の表示に配慮（項目56） |
| enum のインポートエラー | JS プロジェクトとの相互運用 | 文字列リテラルのユニオン型に置き換え |
| 型の絞り込みが効かない | エイリアスの再代入 | エイリアスを一貫して使う（項目23） |
| 構造的型付けで予期しない型が通る | 余剰プロパティの存在 | 項目11 の余剰プロパティチェックを活用 |

---

## References

| ファイル | 用途 |
|:---|:---|
| [type-design-patterns.md](references/type-design-patterns.md) | 型設計パターンの詳細コード例 |
| [code-recipes.md](references/code-recipes.md) | 実践的 TypeScript レシピ集 |

## Related Skills

| スキル | 関係 | 連携内容 |
|:---|:---|:---|
| **test** | 補助 | TypeScript コードの単体テスト設計・生成 |
| **review** | 統合 | コードレビュー基準との連携 |
