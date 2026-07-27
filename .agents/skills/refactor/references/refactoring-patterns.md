# リファクタリングパターン集

> Fowler『Refactoring 2nd Ed.』の 66 パターンから厳選した、頻出パターンの実施ガイド。
> コードスメル → パターン選定 → 実施手順 の順で引けるリファレンス。

---

## パターン選定マトリクス

| コードスメル | 第一候補 | 代替 |
|:---|:---|:---|
| Long Method | **Extract Function** | Replace Temp with Query, Decompose Conditional |
| Duplicate Code | **Extract Function** → Pull Up Method | Form Template Method |
| Large Class | **Extract Class** | Move Method, Move Field |
| Long Parameter List | **Introduce Parameter Object** | Preserve Whole Object |
| Feature Envy | **Move Method** | Extract Function + Move |
| Data Clumps | **Introduce Parameter Object** | Extract Class |
| Dead Code | **Remove Dead Code** | — |
| Divergent Change | **Extract Class** | — |
| Speculative Generality | **Inline Class** | Collapse Hierarchy |
| Refused Bequest | **Replace Inheritance with Delegation** | — |
| Conditional Complexity | **Replace Conditional with Polymorphism** | Introduce Special Case |
| Primitive Obsession | **Replace Primitive with Object** | Introduce Parameter Object |

---

## Extract Function（関数の抽出）

**コンテキスト**: コードの意図が分かりにくい、または同じコードが繰り返し使われている。

### 実施手順

```
1. 抽出するコードブロックを特定する
2. 新関数を作成し、意図を表す名前を付ける
   （What ではなく Why を名前に込める。例: getTotalCost() より calculateInvoiceTotal()）
3. 元のコードのローカル変数をすべてパラメータとして渡す
4. 元のコードで変更される変数があれば戻り値として返す
5. 元のコードを新関数の呼び出しに置き換える
6. テストを実行して Green を確認する
```

### Before / After

```typescript
// Before
function printOwing(invoice: Invoice) {
  printBanner();
  let outstanding = 0;
  for (const o of invoice.orders) {
    outstanding += o.amount;
  }
  // print details
  console.log(`name: ${invoice.customer}`);
  console.log(`amount: ${outstanding}`);
}

// After
function printOwing(invoice: Invoice) {
  printBanner();
  const outstanding = calculateOutstanding(invoice);
  printDetails(invoice, outstanding);
}

function calculateOutstanding(invoice: Invoice): number {
  return invoice.orders.reduce((acc, o) => acc + o.amount, 0);
}

function printDetails(invoice: Invoice, outstanding: number) {
  console.log(`name: ${invoice.customer}`);
  console.log(`amount: ${outstanding}`);
}
```

### よくある失敗と対処

| 失敗 | 原因 | 対処 |
|:---|:---|:---|
| 変数参照エラー | ローカル変数を引数に渡し忘れ | 抽出前にブロック内で使われている外部変数をすべてリスト化する |
| 戻り値が複数必要 | 複数の変数を変更している | オブジェクトで返す or 副作用を意図的に利用する |
| 命名が曖昧 | `process()`, `handle()` のような汎用名 | 「このコードが何をするか」ではなく「なぜするか」で名付ける |

---

## Extract Class（クラスの抽出）

**コンテキスト**: 1 つのクラスが複数の責務を持っている（Large Class / God Class）。

### 実施手順

```
1. 新クラスを作成する（名前は責務を表す明確な名前）
2. 移動すべきフィールドを新クラスに移動する（Move Field）
3. フィールドを移動したメソッドを新クラスに移動する（Move Method）
4. 元クラスから新クラスへの参照を追加する
5. 各ステップ後にテストを実行して Green を確認する
6. 元クラスのインターフェース（外部公開メソッド）が維持されているか確認する
```

### 責務の見極め方

```
質問: 「このメソッドが変わる理由は何か？」

UserService の例:
- validateEmail() → メールバリデーションルールが変わったとき
- hashPassword() → 暗号化アルゴリズムが変わったとき
- updateAddress() → 住所の形式（郵便番号の桁数等）が変わったとき

→ 変わる理由が3つ → 3クラスに分離する
  ValidationService, AuthService, AddressService
```

### よくある失敗と対処

| 失敗 | 原因 | 対処 |
|:---|:---|:---|
| 循環依存が生じた | 双方向参照を作ってしまった | 一方向に依存の向きを整理する。どちらが主体か決める |
| 新クラスが薄すぎる | 1-2 メソッドしか移動しなかった | 責務ごとに移動を徹底する。薄すぎる場合は元クラスに残す |

---

## Move Method（メソッドの移動）

**コンテキスト**: Feature Envy — メソッドが自クラスより他クラスのデータを多用している。

### 実施手順

```
1. 移動先クラスに同じシグネチャのメソッドを作成する
2. 元のメソッドの本体を新メソッドにコピーする
3. コピーしたコードを新クラスのコンテキストで動作するよう調整する
4. 元クラスのメソッドを新メソッドへの委譲に変える
5. テストを実行して Green を確認する
6. 元クラスのメソッドへの外部参照がなくなったら元のメソッドを削除する
```

---

## Introduce Parameter Object（パラメータオブジェクトの導入）

**コンテキスト**: Long Parameter List / Data Clumps — 常に一緒に渡される引数群。

### Before / After

```typescript
// Before
function amountInvoiced(startDate: Date, endDate: Date, customer: Customer) { ... }
function amountReceived(startDate: Date, endDate: Date, customer: Customer) { ... }
function amountOverdue(startDate: Date, endDate: Date, customer: Customer) { ... }

// After
class DateRange {
  constructor(readonly start: Date, readonly end: Date) {}
  includes(aDate: Date): boolean {
    return aDate >= this.start && aDate <= this.end;
  }
}

function amountInvoiced(range: DateRange, customer: Customer) { ... }
function amountReceived(range: DateRange, customer: Customer) { ... }
function amountOverdue(range: DateRange, customer: Customer) { ... }
```

> **ポイント**: Parameter Object をただの Data Class にしない。関連するロジック（includes 等）を持たせることで Value Object に育てる。

---

## Replace Conditional with Polymorphism（条件分岐をポリモーフィズムに置き換える）

**コンテキスト**: 同じ型チェックを繰り返す switch/if 文がある。

### 実施手順

```
1. 各ケースに対応するサブクラス or Strategy クラスを作成する
2. 条件分岐を各クラスのメソッドに移動する
3. 元の条件分岐をポリモーフィックな呼び出しに置き換える
4. Factory 関数でオブジェクトを生成する
```

### Before / After

```typescript
// Before
function calculatePayment(payment: Payment): number {
  switch (payment.type) {
    case 'credit': return payment.amount * 1.03;
    case 'bank': return payment.amount;
    case 'crypto': return payment.amount * getCryptoRate();
  }
}

// After
interface PaymentStrategy {
  calculate(amount: number): number;
}
class CreditPayment implements PaymentStrategy {
  calculate(amount: number) { return amount * 1.03; }
}
class BankPayment implements PaymentStrategy {
  calculate(amount: number) { return amount; }
}
// Factory で生成
function createPaymentStrategy(type: string): PaymentStrategy { ... }
```

---

## Rename（改名系パターン）

**コンテキスト**: 名前が意図を表していない、または誤解を招く。

### 原則

```
良い命名の原則:
- What（何をするか）より Why（なぜするか）を名前に
- 省略形を避ける（usr → user, calc → calculate）
- 動詞で始める関数名（getUserById, validateEmail, calculateTotal）
- 名詞のクラス名（UserRepository, PaymentService）
- bool 変数は is/has/can プレフィックス（isActive, hasPermission）
```

### IDE リネームの活用

```
TypeScript: VS Code / JetBrains の「Rename Symbol」（F2 / Shift+F6）
Python: PyCharm の「Rename」または「rope」ライブラリ
Go: gopls の「Rename」
※ 文字列テンプレート内の参照は自動更新されないため手動確認が必要
```

---

## Remove Dead Code（デッドコードの削除）

**コンテキスト**: 使われていないコードが残っている。

### 検出方法

```bash
# TypeScript: 未使用変数・関数の検出
npx ts-prune  # または tsc --noUnusedLocals

# Python
pylint --disable=all --enable=unused-variable src/

# 一般的な grep での確認
grep -rn "functionName" src/ --include="*.ts"  # 定義以外の参照があるか確認
```

### 注意点

```
削除前に確認すること:
- 外部ライブラリから参照されていないか（エクスポートされている場合）
- リフレクションや動的呼び出しで参照されていないか
- テストコードからのみ参照されているケース（テストごと削除か検討）
```

---

## Inline Function / Inline Variable（インライン化）

**コンテキスト**: 関数の本体が名前と同じくらい自明なとき。または Extract Function の逆操作が必要なとき。

```typescript
// Before（インライン化が適切なケース）
function moreThanFiveLateDeliveries(driver: Driver): boolean {
  return driver.numberOfLateDeliveries > 5;
}
if (moreThanFiveLateDeliveries(driver)) { ... }

// After（関数を呼び出し箇所に展開）
if (driver.numberOfLateDeliveries > 5) { ... }
```

> **逆方向も重要**: リファクタリングは一方向ではない。Extract と Inline を状況に応じて使い分ける。

---

## パターン適用の黄金律

| 原則 | 説明 |
|:---|:---|
| **KISS（最小変更）** | リファクタリングは動作を変えない最小限の構造変更 |
| **Green → Refactor → Green** | テストが通る状態でのみリファクタリングし、必ず Green に戻る |
| **1 パターン = 1 コミット** | 複数パターンを同時に適用しない。ロールバック可能に |
| **名前は最初から正しく** | 仮の名前でコミットしない。リネームは後ほど困難になる |
| **Scout Rule（限定版）** | 「通りすがりに小さく直す」はOK だが、スコープ外の大きな変更は次回に |
