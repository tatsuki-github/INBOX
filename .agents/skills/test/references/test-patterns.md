# テストパターン・コード例・リファクタリング手順

> 本ファイルは test スキルの詳細リファレンスである。
> 書籍『単体テストの考え方/使い方』(Vladimir Khorikov) の原則に基づく。

---

## 1. AAA パターンの実装例

### 1.1 出力値ベーステスト（最優先）

```python
# テスト対象: 純粋関数（副作用なし）
def calculate_discount(total: float, is_premium: bool) -> float:
    if is_premium and total >= 10000:
        return total * 0.15
    if total >= 10000:
        return total * 0.10
    return 0.0

# テスト: 戻り値のみを検証
def test_premium_customer_with_large_order_gets_15_percent_discount():
    # Arrange
    total = 10000
    is_premium = True

    # Act
    discount = calculate_discount(total, is_premium)

    # Assert
    assert discount == 1500.0

def test_regular_customer_with_large_order_gets_10_percent_discount():
    # Arrange
    total = 10000
    is_premium = False

    # Act
    discount = calculate_discount(total, is_premium)

    # Assert
    assert discount == 1000.0

def test_small_order_gets_no_discount():
    # Arrange
    total = 9999
    is_premium = True

    # Act
    discount = calculate_discount(total, is_premium)

    # Assert
    assert discount == 0.0
```

**ポイント**:
- 期待値はハードコード（計算ロジックをテストに書かない）
- テスト名は振る舞いを記述
- 各テストは独立して実行可能

### 1.2 状態ベーステスト

```python
# テスト対象: 状態変化を伴うドメインモデル
class ShoppingCart:
    def __init__(self):
        self._items = []

    def add_item(self, product: str, quantity: int) -> None:
        self._items.append({"product": product, "quantity": quantity})

    @property
    def item_count(self) -> int:
        return len(self._items)

# テスト: 操作後の状態を検証
def test_adding_item_increases_cart_count():
    # Arrange
    cart = ShoppingCart()

    # Act
    cart.add_item("Widget", 2)

    # Assert
    assert cart.item_count == 1
```

**ポイント**:
- 公開プロパティ経由で状態を検証（private状態を公開しない）
- オブジェクトの観察可能な振る舞いのみ検証

### 1.3 コミュニケーション・ベーステスト（モック使用）

```python
from unittest.mock import Mock

# テスト対象: 外部システムと通信するサービス
class OrderService:
    def __init__(self, email_gateway):
        self._email_gateway = email_gateway

    def place_order(self, order) -> None:
        # ビジネスロジック...
        self._email_gateway.send_confirmation(order.customer_email, order.id)

# テスト: 外部システムへのコマンド呼び出しを検証
def test_placing_order_sends_confirmation_email():
    # Arrange
    email_gateway = Mock()
    service = OrderService(email_gateway)
    order = Order(customer_email="user@example.com", id="ORD-001")

    # Act
    service.place_order(order)

    # Assert（コマンドの呼び出しを検証）
    email_gateway.send_confirmation.assert_called_once_with("user@example.com", "ORD-001")
```

**ポイント**:
- モックは**コマンド**（副作用を起こす操作）にのみ使用
- 呼び出し**回数**も検証する
- スタブ（クエリ）の呼び出し自体は検証しない

---

## 2. TDD サイクル（Vitest + TypeScript）

implementation-flow Phase 5 のドメイン層 TDD で使用する Red→Green→Refactor パターン。

### 2.1 Red — 失敗するテストを先に書く

```typescript
// calculateDiscount.ts — まだ存在しない（または空実装）

// calculateDiscount.test.ts
import { describe, it, expect } from 'vitest';
import { calculateDiscount } from './calculateDiscount';

describe('calculateDiscount', () => {
  it('premium_customer_with_large_order_gets_15_percent_discount', () => {
    const total = 10000;
    const isPremium = true;

    const discount = calculateDiscount(total, isPremium);

    expect(discount).toBe(1500);
  });
});
```

```bash
# Red 確認: テストが失敗することを確認してから Green へ
npx vitest run utils/calculateDiscount.test.ts
```

### 2.2 Green — テストを通す最小実装

```typescript
export function calculateDiscount(total: number, isPremium: boolean): number {
  if (isPremium && total >= 10000) {
    return total * 0.15;
  }
  if (total >= 10000) {
    return total * 0.10;
  }
  return 0;
}
```

### 2.3 Refactor — 構造改善（テストは Green 維持）

```typescript
const LARGE_ORDER_THRESHOLD = 10000;
const PREMIUM_DISCOUNT_RATE = 0.15;
const REGULAR_DISCOUNT_RATE = 0.10;

export function calculateDiscount(total: number, isPremium: boolean): number {
  if (total < LARGE_ORDER_THRESHOLD) {
    return 0;
  }
  const rate = isPremium ? PREMIUM_DISCOUNT_RATE : REGULAR_DISCOUNT_RATE;
  return total * rate;
}
```

### 2.4 コントローラ層 — 実装後の振る舞いテスト

hooks / components は TDD 対象外。実装完了後に追加する。

```typescript
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useProductFilters } from './useProductFilters';

describe('useProductFilters', () => {
  it('updating_price_range_reflects_in_filter_state', () => {
    const { result } = renderHook(() => useProductFilters());

    act(() => {
      result.current.setPriceRange({ min: 1000, max: 5000 });
    });

    expect(result.current.filters.priceRange).toEqual({ min: 1000, max: 5000 });
  });
});
```

**ポイント**:
- ドメイン層: Red ファースト必須
- コントローラ層: 実装後テスト、状態ベース or 出力値ベース
- モックは外部 API 境界のみ

---

## 3. モック vs スタブの判断フロー

```
依存オブジェクトのメソッドは？
  ├── 副作用がある（コマンド）
  │     ├── アプリケーション境界を超える？
  │     │     ├── YES → モックで検証 ✅
  │     │     └── NO  → モック不要（内部通信はテストしない）
  │     └── 管理下にある依存（DB等）？
  │           └── 実物 or インメモリ版を使用
  └── 値を返すだけ（クエリ）
        └── スタブで置換（呼び出しは検証しない）
```

### 悪い例：スタブの過剰検証

```python
# NG: クエリの呼び出しを検証している
def test_bad_stub_verification():
    repo = Mock()
    repo.get_user.return_value = User("Alice")  # スタブとして設定
    service = UserService(repo)

    service.greet_user(1)

    repo.get_user.assert_called_once_with(1)  # ← これは過剰検証！
```

### 良い例：スタブは設定のみ

```python
# OK: スタブは設定のみ、結果を検証
def test_greeting_includes_user_name():
    repo = Mock()
    repo.get_user.return_value = User("Alice")  # スタブとして設定
    service = UserService(repo)

    greeting = service.greet_user(1)

    assert greeting == "Hello, Alice!"  # 最終的な出力を検証
```

---

## 4. Humble Object パターン

過度に複雑なコード（ビジネスロジック + 多くの依存）を分離するパターン。

### Before（テスト困難）

```python
# 過度に複雑: ビジネスロジック + DB + メール送信が混在
class UserController:
    def change_email(self, user_id: int, new_email: str):
        user = self.db.get_user(user_id)
        company = self.db.get_company(user.company_id)

        # ビジネスロジック（テストしたい部分）
        if user.email == new_email:
            return
        if new_email.endswith("@company.com"):
            user.type = UserType.EMPLOYEE
            company.employee_count += 1
        else:
            user.type = UserType.CUSTOMER
            company.employee_count -= 1
        user.email = new_email

        self.db.save_user(user)
        self.db.save_company(company)
        self.email_gateway.send_change_notification(user_id, new_email)
```

### After（Humble Object 適用）

```python
# ドメインモデル: 純粋なビジネスロジック（テスト容易）
class User:
    def change_email(self, new_email: str, company: Company) -> None:
        if self.email == new_email:
            return
        if new_email.endswith("@company.com"):
            self.type = UserType.EMPLOYEE
            company.employee_count += 1
        else:
            self.type = UserType.CUSTOMER
            company.employee_count -= 1
        self.email = new_email
        self.domain_events.append(EmailChangedEvent(self.id, new_email))

# コントローラ: 薄い調整役（統合テストで検証）
class UserController:
    def change_email(self, user_id: int, new_email: str):
        user = self.db.get_user(user_id)
        company = self.db.get_company(user.company_id)

        user.change_email(new_email, company)  # ドメインロジック委譲

        self.db.save_user(user)
        self.db.save_company(company)
        for event in user.domain_events:
            self.event_dispatcher.dispatch(event)
```

**テスト戦略**:
- `User.change_email` → 出力値ベース or 状態ベースの**単体テスト**
- `UserController.change_email` → モックを使った**統合テスト**

---

## 5. テスト命名のリファクタリング例

### Before（メソッド名ベース）

```
test_IsDeliveryValid_InvalidDate_ReturnsFalse
test_Sum_TwoNumbers_ReturnsSum
test_GetUser_NonExistentId_ThrowsException
```

### After（振る舞いベース）

```
test_delivery_with_past_date_is_invalid
test_sum_of_two_positive_numbers_returns_correct_result
test_requesting_nonexistent_user_raises_not_found_error
```

**原則**:
- メソッド名を含めない（リファクタリングでメソッド名が変わっても影響なし）
- 「should」で始めない（事実を記述する）
- アンダースコアで単語を区切る（読みやすさ優先）

---

## 6. 境界値テストの設計パターン

重要なビジネスロジックには以下の境界値を網羅する。

### 数値の境界値

| 境界 | テストすべき値 |
|:---|:---|
| ゼロ | 0 |
| 負数 | -1 |
| 閾値の前後 | threshold - 1, threshold, threshold + 1 |
| 最大値 | MAX_INT, MAX_SAFE_INTEGER |
| 浮動小数点 | 0.1 + 0.2 の丸め誤差 |

### 文字列の境界値

| 境界 | テストすべき値 |
|:---|:---|
| 空文字列 | "" |
| null / None | None |
| 空白のみ | "   " |
| 最大長 | 制約の上限値 |
| 特殊文字 | 改行、タブ、Unicode |

### コレクションの境界値

| 境界 | テストすべき値 |
|:---|:---|
| 空 | [] |
| 1要素 | [x] |
| 多数要素 | 大量データ |
| 重複 | [x, x] |
| null要素 | [None] |

---

## 7. テストの価値判定マトリクス

テストを作成・レビューする際に、以下のマトリクスで価値を判定する。

### 高価値テスト（必ず書く）

- ドメインモデルのビジネスルール検証
- 重要なアルゴリズムの正確性検証
- 境界値での振る舞い検証
- 外部システムとの通信（コマンド）の検証

### 低価値テスト（書かない or 削除検討）

- 単純なgetter/setterのテスト
- コンストラクタの単純な代入のテスト
- フレームワークの機能自体のテスト
- 100%網羅率のためだけに存在するテスト
- 実装の詳細を検証するテスト

---

## 8. テストリファクタリング手順

既存テストの品質改善を行う際の手順。

### Step 1: アンチパターンの検出

- [ ] privateメソッドの直接テストがないか
- [ ] スタブの呼び出しを検証していないか
- [ ] テスト内に本番コードと同じ計算ロジックがないか
- [ ] テスト名がメソッド名に結合していないか
- [ ] 1つのテストに複数のActがないか
- [ ] テスト内にif文がないか

### Step 2: テストの分類

各テストを4本柱で評価し、A/B/C/Dにランク付け。

| ランク | 基準 | アクション |
|:---|:---|:---|
| A | 4本柱すべて高 | 維持 |
| B | 1-2本の柱が中程度 | 改善を検討 |
| C | 1本以上の柱が低い | リファクタリング必須 |
| D | 価値がない | 削除 |

### Step 3: リファクタリングの実施

優先順位: リファクタリング耐性の改善 > 退行保護の追加 > 保守性の向上 > フィードバック速度

理由: リファクタリング耐性は「あるか、ないか」の二択であり、中間が存在しないため、最初に対処すべき。

---

## 9. 言語別テストフレームワーク対応

| 言語 | フレームワーク | モックライブラリ |
|:---|:---|:---|
| Python | pytest | unittest.mock / pytest-mock |
| TypeScript | Jest / Vitest | 組み込みモック |
| Java | JUnit 5 | Mockito |
| C# | xUnit / NUnit | Moq / NSubstitute |
| Go | testing | testify/mock |
| Rust | cargo test | mockall |

テスト対象の言語に応じて、適切なフレームワークのイディオムに従うこと。
