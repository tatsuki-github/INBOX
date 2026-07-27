# セーフティネットガイド（ロバスト Python 第IV部 準拠）

本ファイルは SKILL.md の原則 8 の詳細リファレンスである。

---

## 1. 静的解析スタック

### 1.1 mypy 推奨設定

```ini
# mypy.ini
[mypy]
python_version = 3.11
strict = true
warn_return_any = true
warn_unused_ignores = true
show_error_codes = true

# レガシーモジュールは段階的に厳格化
[mypy-legacy_module.*]
disallow_untyped_defs = false
ignore_missing_imports = true
```

**主要オプション解説**:

| オプション | 効果 | 推奨 |
|:---|:---|:---|
| `strict` | 全 strict オプションを一括有効化 | 新規プロジェクト |
| `strict_optional` | None チェックを強制 | **常時有効** |
| `no_implicit_optional` | `Optional` の明示を強制 | **常時有効** |
| `disallow_any_generics` | 裸 `list`, `dict` を禁止 | 推奨 |
| `disallow_untyped_defs` | 全関数にアノテーション要求 | 新規コード |
| `warn_return_any` | `Any` 戻り値を警告 | 推奨 |
| `warn_unused_ignores` | 不要な `# type: ignore` を検出 | 推奨 |

**mypy デーモンモード**（大規模プロジェクト向け）:
```bash
$ dmypy run -- your_package/  # 初回: フル解析
$ dmypy run -- your_package/  # 2回目以降: 差分解析（高速）
```

### 1.2 Pylint

```bash
$ pip install pylint
$ pylint your_package/
```

**検出する主な問題**:
- ミュータブルデフォルト引数（`W0102: dangerous-default-value`）
- 不整合な return 文（`R1710: inconsistent-return-statements`）
- `return` 後のデッドコード（`W0101: unreachable`）
- 未使用変数/インポート
- 保護属性への外部アクセス

### 1.3 カスタム Pylint プラグイン

ドメイン固有のルールを自動強制する。

```python
# カスタムチェッカー例: NewType の生成箇所を制限
import astroid
from pylint.checkers import BaseChecker

class NewTypeCreationChecker(BaseChecker):
    name = "newtype-creation"
    msgs = {
        "C9001": (
            "NewType '%s' は '%s' 関数内でのみ生成可能",
            "invalid-newtype-creation",
            "NewType の生成箇所が不正です",
        ),
    }

    def visit_call(self, node: astroid.Call) -> None:
        # ReadyToServeHotDog の生成を hotdog.prepare_for_serving に限定
        ...

def register(linter):
    linter.register_checker(NewTypeCreationChecker(linter))
```

### 1.4 Bandit（セキュリティ解析）

```bash
$ pip install bandit
$ bandit -r your_package/ -f json -o security_report.json
```

**検出する主な脆弱性**:
- Flask `debug=True`（リモートコード実行）
- `verify=False`（HTTPS 証明書検証スキップ）
- 生 SQL 文字列（SQL インジェクション）
- 弱い暗号鍵（RSA 1024bit 等）
- `yaml.load()` の unsafe 使用

### 1.5 複雑度チェッカ（mccabe）

```bash
$ pip install mccabe
$ python -m mccabe --min 5 your_module.py
```

**循環的複雑度の目安**:
- 1-4: 低（良好）
- 5-10: 中（許容）
- 11-20: 高（要リファクタリング）
- 21+: 非常に高（バグの温床）

### 1.6 スイスチーズモデル

```
                    バグ →
┌──────────────────────────────────────────┐
│  mypy / Pyright     ○   ○        ○      │ ← 型エラーを検出
├──────────────────────────────────────────┤
│  Pylint + カスタム      ○    ○   ○      │ ← プログラミングミスを検出
├──────────────────────────────────────────┤
│  Bandit              ○      ○           │ ← セキュリティ脆弱性を検出
├──────────────────────────────────────────┤
│  pytest              ○          ○       │ ← 振る舞いの誤りを検出
├──────────────────────────────────────────┤
│  Hypothesis                   ○         │ ← 境界値・エッジケースを検出
├──────────────────────────────────────────┤
│  mutmut                           ○     │ ← テスト品質の穴を検出
└──────────────────────────────────────────┘
                    → 検出！
```

各ツールには穴（○）があるが、層を重ねることで全体の検出率を最大化する。

---

## 2. テスト戦略

### 2.1 テストピラミッド

```
        /  \         ← UI / E2E テスト（少、高コスト）
       /    \
      /      \       ← 統合テスト（中）
     /        \
    /          \     ← 単体テスト（多、低コスト）
   /____________\
```

**重要**: ラベル（unit / integration / E2E）よりも**価値 / コスト比**で判断する。

### 2.2 AAA パターン（Arrange-Act-Assert）

```python
def test_calorie_calculation():
    # Arrange: 前提条件のセットアップ（小さく保つ）
    db = create_test_database()
    add_ingredient(db, "bacon", calories_per_pound=2400)
    setup_recipe(db, "bacon_burger", ["bacon", "beef", "bun"])

    # Act: テスト対象の実行（1-2行）
    calories = get_calories(db, "bacon_burger")

    # Assert: 結果の検証（1つの論理的アサーション）
    assert calories == 1200, f"Expected 1200, got {calories}"
```

### 2.3 pytest フィクスチャ

```python
import pytest

@pytest.fixture
def test_db():
    """テストデータベースの作成とクリーンアップ"""
    db = create_database()
    add_base_ingredients(db)
    try:
        yield db  # テスト実行
    finally:
        db.cleanup()  # 必ずクリーンアップ

def test_with_fixture(test_db):
    # test_db は自動的にセットアップ＆クリーンアップ
    calories = get_calories(test_db, "burger")
    assert calories == 900
```

### 2.4 パラメータ化テスト

```python
@pytest.mark.parametrize(
    "dish_name, expected_calories",
    [
        ("bacon_burger", 900),
        ("cobb_salad", 1000),
        ("chicken_wings", 800),
    ],
)
def test_calorie_calculation(dish_name, expected_calories, test_db):
    calories = get_calories(test_db, dish_name)
    assert calories == expected_calories
```

### 2.5 モック戦略

**原則**: モックは外部サービス（DB, API, ファイルシステム）にのみ使う。
モックが多すぎる場合は**設計の問題**。

```python
# NG: 内部関数をモンキーパッチ → 設計の密結合
def test_order(monkeypatch):
    monkeypatch.setattr("module.calculate_tax", lambda x: 0)
    monkeypatch.setattr("module.check_inventory", lambda: True)
    monkeypatch.setattr("module.send_email", lambda *a: None)
    ...  # モックだらけ = 設計を見直すべき

# OK: 依存注入で外部サービスのみモック
def test_order(mock_payment_gateway):
    order_service = OrderService(payment=mock_payment_gateway)
    result = order_service.process(order)
    assert result.status == "completed"
```

### 2.6 Hamcrest マッチャー

```python
from hamcrest import assert_that, is_, has_property, has_length

assert_that(dish, is_(vegan()))
assert_that(menu, has_length(5))
assert_that(order, has_property("status", "confirmed"))
# エラーメッセージが分かりやすい:
# Expected: a vegan dish
# But: non-vegan ingredients: beef
```

---

## 3. 受入テスト（BDD）

### 3.1 Gherkin 記法

```gherkin
Feature: ビーガンメニュー

  Scenario: ビーガン代替品の提供
    Given チーズバーガー付きフライドポテトの注文
    When ビーガン代替が要求された
    Then 料理に動物性食品が含まれていない

  Scenario: ビーガン代替不可
    Given ミートローフの注文
    When ビーガン代替が要求された
    Then エラー「ビーガン代替なし」が表示される
```

### 3.2 behave でのステップ定義

```python
from behave import given, when, then

@given("チーズバーガー付きフライドポテトの注文")
def setup_order(ctx):
    ctx.dish = CheeseburgerWithFries()

@when("ビーガン代替が要求された")
def substitute_vegan(ctx):
    try:
        ctx.dish.substitute_vegan()
        ctx.error = None
    except VeganSubstitutionError as e:
        ctx.error = str(e)

@then("料理に動物性食品が含まれていない")
def check_vegan(ctx):
    assert all(is_vegan(ing) for ing in ctx.dish.ingredients())

@then('エラー「{message}」が表示される')
def check_error(ctx, message):
    assert ctx.error == message
```

### 3.3 Scenario Outline（テーブル駆動）

```gherkin
Scenario Outline: ビーガン代替
  Given <dish> の注文
  When ビーガン代替が要求された
  Then <result>

  Examples: 代替可能
    | dish           | result         |
    | チーズバーガー   | 動物性食品なし   |
    | コブサラダ       | 動物性食品なし   |

  Examples: 代替不可
    | dish      | result              |
    | ミートローフ | エラー: 代替不可     |
```

---

## 4. プロパティベーステスト（Hypothesis）

### 4.1 基本: 不変式をテスト

```python
from hypothesis import given
from hypothesis.strategies import integers

@given(calories=integers(min_value=900))
def test_meal_recommendation(calories):
    meals = recommend(Recommendation.BY_CALORIES, calories)

    # 不変式の検証（特定の値ではなく性質）
    assert len(meals) == 3
    assert is_appetizer(meals[0])
    assert is_salad(meals[1])
    assert is_main(meals[2])
    assert sum(m.calories for m in meals) <= calories
```

### 4.2 カスタム Strategy

```python
from hypothesis import given
from hypothesis.strategies import composite, integers

@composite
def three_course_meals(draw):
    appetizer = draw(integers(min_value=100, max_value=900))
    main = draw(integers(min_value=550, max_value=1800))
    dessert = draw(integers(min_value=500, max_value=1000))
    return (
        Dish("appetizer", appetizer),
        Dish("main", main),
        Dish("dessert", dessert),
    )

@given(meal=three_course_meals())
def test_substitutions(meal):
    ...  # 生成されたデータでテスト
```

### 4.3 ステートフルテスト（RuleBasedStateMachine）

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

class RecommenderChecker(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.engine = RecommendationEngine()

    @rule(limit=integers(min_value=6, max_value=200))
    def filter_by_price(self, limit):
        self.engine.apply_price_filter(limit)

    @rule(cuisine=sampled_from(["和食", "洋食", "中華"]))
    def filter_by_cuisine(self, cuisine):
        self.engine.apply_cuisine_filter(cuisine)

    @invariant()
    def always_three_unique_meals(self):
        meals = self.engine.get_meals()
        assert len(meals) == 3
        assert len(set(meals)) == 3

TestRecommender = RecommenderChecker.TestCase
```

### 4.4 データベースの共有

```python
# settings.py: チーム内で失敗事例を共有
from hypothesis import settings
from hypothesis.database import MultiplexedDatabase, DirectoryBasedExampleDatabase

settings.register_profile("ci", database=MultiplexedDatabase(
    DirectoryBasedExampleDatabase(".hypothesis/examples"),
    DirectoryBasedExampleDatabase("//shared/hypothesis-db"),
))
```

---

## 5. ミューテーションテスト（mutmut）

### 5.1 基本的な使い方

```bash
$ pip install mutmut
$ mutmut run --paths-to-mutate your_package/
$ mutmut results         # 結果サマリー
$ mutmut show <id>       # 特定ミュータントの差分
$ mutmut apply <id>      # ミュータントをソースに適用（デバッグ用）
```

### 5.2 ミュータントの種類

| 変異 | 例 | 検出対象 |
|:---|:---|:---|
| 整数リテラル +1 | `0` → `1` | オフバイワンエラー |
| 文字列挿入 | `""` → `"XX"` | 文字列処理の穴 |
| break ↔ continue | `break` → `continue` | ループ制御の穴 |
| True ↔ False | `True` → `False` | ブール論理の穴 |
| 演算子変更 | `<` → `<=`, `/` → `//` | 境界条件の穴 |
| None チェック反転 | `is None` → `is not None` | null チェックの穴 |

### 5.3 生存ミュータントへの対処

```
生存ミュータント発見
      │
      ├── そのコード行は不要？ → 削除
      ├── テスト不要（ロギング等）？ → スキップ
      └── テストの穴？ → テスト追加
            │
            ├── mutmut apply <id>
            ├── 失敗するテストを書く
            ├── mutmut undo (ミュータント除去)
            └── テストがパスすることを確認
```

### 5.4 カバレッジとの併用

```bash
# カバレッジでテスト済みコードのみをミューテーション対象に
$ coverage run -m pytest your_package/
$ mutmut run --paths-to-mutate your_package/ --use-coverage
```

CRITICAL: カバレッジ率は品質を保証しない。以下のテストはカバレッジ 100% だが品質ゼロ:

```python
# NG: アサーションが無意味
def test_foo():
    result = calculate_something()
    assert result is not None  # 存在チェックだけ、値の検証なし
```

ミューテーションテストはこの種の「見せかけのテスト」を検出する。
