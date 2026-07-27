# 設計パターン集（ロバスト Python 第II部・第III部 準拠）

本ファイルは SKILL.md の原則 3〜7 の詳細リファレンスである。

---

## 1. Enum パターン

### 1.1 基本: auto() で値を自動付番

```python
from enum import Enum, auto, Flag, unique

class MotherSauce(Enum):
    BECHAMEL = auto()
    VELOUTE = auto()
    ESPAGNOLE = auto()
    TOMATO = auto()
    HOLLANDAISE = auto()

def create_sauce(base: MotherSauce) -> Sauce:
    ...  # 無効な値は渡せない
```

### 1.2 Flag: ビット演算で組み合わせ

```python
class Allergen(Flag):
    FISH = auto()
    SHELLFISH = auto()
    TREE_NUTS = auto()
    PEANUTS = auto()
    SOY = auto()
    SEAFOOD = FISH | SHELLFISH  # エイリアス

# 複数のアレルゲンを OR で組み合わせ
dish_allergens = Allergen.FISH | Allergen.SOY
if dish_allergens & Allergen.FISH:
    print("魚を含みます")
```

### 1.3 @unique: 値の重複を禁止

```python
@unique
class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    # URGENT = 3  → ValueError: duplicate value 3
```

### 1.4 使うべきでない場面

| 状況 | 代替 |
|:---|:---|
| 選択肢が実行時に変わる | `dict` |
| 単純な値制限 | `Literal["a", "b", "c"]` |
| 整数との暗黙変換が必要 | `IntEnum`（レガシー互換のみ） |

CRITICAL: `IntEnum` / `IntFlag` は暗黙の int 変換がバグの温床。新規コードでは `Enum` + `auto()` を使う。

---

## 2. dataclass パターン

### 2.1 基本: frozen でイミュータブル

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Ingredient:
    name: str
    amount: float = 1.0
    units: str = "cup"

# frozen=True の効果:
# - 属性の変更が TypeError → スレッド安全
# - set の要素、dict のキーに使用可能（__hash__ が自動生成）
```

### 2.2 比較: eq と order

```python
@dataclass(eq=True, order=True)
class NutritionInfo:
    calories: int   # ← order の第1キー
    fat: int        # ← order の第2キー
    carbs: int

# 自動生成: ==, !=, <, <=, >, >=
info_a < info_b  # calories で比較、同値なら fat で比較
```

### 2.3 代替との比較

| 型 | 用途 | イミュータブル | メソッド | 実行時検証 |
|:---|:---|:---|:---|:---|
| `dict` | 同種 K→V マッピング | No | No | No |
| `TypedDict` | JSON/YAML パース結果 | No | No | No |
| `namedtuple` | レガシー（Python 3.7前） | Yes | No | No |
| `dataclass` | 構造化データ | `frozen=True` | Yes | No |
| `pydantic` | 外部入力検証 | 設定可 | Yes | **Yes** |

### 2.4 dataclass を避けるべき場面

フィールド間に**相互依存関係**がある場合はクラスを使う:

```python
# NG: dataclass ではフィールド間の制約を保護できない
@dataclass
class Pizza:
    radius: int
    toppings: list[str]
    # ← ソースは1種類だけ、という不変式を誰が守る？

# OK: クラスで不変式を保護
class Pizza:
    def __init__(self, radius: int, toppings: list[str]):
        if not (6 <= radius <= 12):
            raise ValueError("6〜12インチのみ")
        ...
```

---

## 3. クラスと不変式

### 3.1 不変式とは

オブジェクトの生涯にわたって**常に真でなければならない条件**。

例: ピザの不変式
- 生地サイズは 6〜12 インチ
- ソースは最大 1 種類
- トッピングは少なくとも 1 つ

### 3.2 不変式の保護パターン

```python
class PizzaSpec:
    def __init__(self, radius: int, toppings: list[str]):
        # 不変式の検証
        if not (6 <= radius <= 12):
            raise ValueError(f"radius must be 6-12, got {radius}")
        sauces = [t for t in toppings if is_sauce(t)]
        if len(sauces) > 1:
            raise ValueError("最大1種類のソース")
        if not toppings:
            raise ValueError("トッピングは1つ以上")

        # 内部状態をプライベートに
        self.__radius = radius
        self.__toppings = list(toppings)  # 防御的コピー

    @property
    def radius(self) -> int:
        return self.__radius

    @property
    def toppings(self) -> tuple[str, ...]:
        return tuple(self.__toppings)  # イミュータブルなコピーを返す

    def add_topping(self, topping: str) -> None:
        """不変式を維持しながらトッピングを追加"""
        if is_sauce(topping) and any(is_sauce(t) for t in self.__toppings):
            raise ValueError("ソースは1種類まで")
        self.__toppings.append(topping)
```

### 3.3 カプセル化の3層

| レベル | プレフィックス | 意味 |
|:---|:---|:---|
| パブリック | なし | 外部から自由にアクセス |
| プロテクト | `_` | 内部使用を示唆（強制なし） |
| プライベート | `__` | 名前マングリングで隠蔽 |

**ルール**: 不変式に関わる属性は `__` で保護し、メソッド経由でのみ変更を許可する。

---

## 4. Protocol パターン

### 4.1 基本: 構造的部分型

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Splittable(Protocol):
    cost: int
    name: str
    def split_in_half(self) -> tuple['Splittable', 'Splittable']: ...

# 継承不要！構造が一致すれば OK
class BLTSandwich:
    def __init__(self):
        self.cost = 695
        self.name = "BLT"

    def split_in_half(self) -> tuple['BLTSandwich', 'BLTSandwich']:
        ...

# 型チェッカが BLTSandwich を Splittable として受け入れる
def split_dish(dish: Splittable) -> tuple[Splittable, Splittable]:
    return dish.split_in_half()
```

### 4.2 複合 Protocol

```python
class Shareable(Protocol):
    def share_with(self, count: int) -> list['Shareable']: ...

class Substitutable(Protocol):
    def substitute(self, replacement: str) -> 'Substitutable': ...

# 複合: 複数の Protocol を同時に要求
class LunchEntry(Splittable, Shareable, Substitutable, Protocol):
    pass
```

### 4.3 実行時チェック

```python
@runtime_checkable
class Splittable(Protocol):
    ...

# isinstance で構造チェック可能
if isinstance(dish, Splittable):
    dish.split_in_half()
```

### 4.4 Protocol vs ABC vs 継承

| 手法 | 結合度 | 用途 |
|:---|:---|:---|
| Protocol | 最低 | 構造だけを要求（ダックタイピングの型安全版） |
| ABC | 中 | メソッド実装を強制 + デフォルト実装の提供 |
| 継承 | 最高 | 真の is-a 関係（LSP 遵守が前提） |

---

## 5. Pydantic パターン

### 5.1 実行時バリデーション

```python
from pydantic.dataclasses import dataclass
from pydantic import constr, PositiveInt, conlist, validator

@dataclass
class Restaurant:
    name: constr(pattern=r"^[a-zA-Z0-9 ]+$", min_length=1, max_length=16)
    owner: constr(min_length=1)
    employees: conlist(Employee, min_length=2)
    seats: PositiveInt
    delivery: bool

    @validator("employees")
    def check_staff(cls, employees):
        has_chef = any(e.position == "Chef" for e in employees)
        has_server = any(e.position == "Server" for e in employees)
        if not (has_chef and has_server):
            raise ValueError("Chef と Server が各1名以上必要")
        return employees
```

### 5.2 バリデーション vs パース

| 概念 | 動作 | 例 |
|:---|:---|:---|
| バリデーション | 型が一致しなければエラー | `int` に `"abc"` → エラー |
| パース | 型変換を試みる（pydantic デフォルト） | `int` に `"123"` → `123` |

**厳密にしたい場合**: `StrictInt`, `StrictStr`, `StrictBool` を使う。

```python
from pydantic import StrictInt

@dataclass
class StrictModel:
    value: StrictInt  # "123" → エラー（int のみ）
```

---

## 6. OCP（開放閉鎖の原則）パターン

### 6.1 OCP 違反の検出

**兆候チェックリスト**:
- 新機能追加に 5 ファイル以上の修正が必要
- 同じ `if/elif` チェーンが 3 箇所以上に散在
- `git diff` が常に大規模

### 6.2 対処: データ駆動設計

```python
# NG: ショットガン手術
def declare_special(dish, emails, texts, push_to_app):
    for email in emails:
        send_email(email, dish)
    for text in texts:
        send_text(text, dish)
    if push_to_app:
        push_notification(dish)

# OK: 通知方法をデータとして管理
@dataclass
class NewSpecial:
    dish: Dish
    start: datetime
    end: datetime

notify_config: dict[type, list[NotifyMethod]] = {
    NewSpecial: [Email("boss@co.jp"), API("supplier"), Push("app")],
    OutOfStock: [Email("boss@co.jp"), API("supplier")],
}

def send_notification(event: NotificationType) -> None:
    for method in notify_config[type(event)]:
        method.notify(event)
```

---

## 7. 依存関係パターン

### 7.1 3種類の依存関係

| 種類 | 定義 | 検出方法 |
|:---|:---|:---|
| 物理的 | import / 関数呼出 / 継承 | ツールで可視化 |
| 論理的 | HTTP / ダックタイピング / メッセージ | 実行時まで不明 |
| 時間的 | 処理の前後関係 | コメント / テスト |

### 7.2 依存可視化ツール

```bash
# パッケージ依存
$ pipdeptree

# モジュールインポート（ファンイン/ファンアウト分析）
$ pydeps your_package --max-bacon=2

# 静的コールグラフ
$ pyan3 your_module.py --dot | dot -Tpng -o callgraph.png

# 動的コールグラフ
$ python -m cProfile -o profile.out your_script.py
$ gprof2dot -f pstats profile.out | dot -Tpng -o dynamic.png
```

### 7.3 ファンイン/ファンアウト

- **ファンイン大**（多くが依存）: 安定させる。変更のコストが高い
- **ファンアウト大**（多くに依存）: 変更しやすい場所に配置。依存先の変更の影響を受ける

---

## 8. コンポーザビリティパターン

### 8.1 デコレータで横断的関心事を分離

```python
import backoff

# メカニズム（再試行）をデコレータで分離
@backoff.on_exception(backoff.expo, OperationError, max_tries=5)
@backoff.on_exception(backoff.expo, HTTPError, max_time=60)
def save_inventory(inventory: list[Item]) -> None:
    for item in inventory:
        db[item.name] = item.count
```

### 8.2 itertools で宣言的アルゴリズム

```python
import itertools

def recommend(policy: Policy) -> list[Meal]:
    sorted_meals = sorted(policy.meals, key=policy.sort_key, reverse=True)
    grouped = itertools.groupby(sorted_meals, key=policy.group_key)
    _, top_group = next(grouped)
    candidates = sorted(top_group, key=policy.secondary_key, reverse=True)
    selected = itertools.takewhile(policy.filter_fn, candidates)
    return list(selected)[:policy.max_results]
```

### 8.3 Template Method: ステップの差し替え

```python
@dataclass
class PizzaSteps:
    prepare: Callable
    pre_bake: Callable
    post_bake: Callable

def create_pizza(steps: PizzaSteps) -> Pizza:
    steps.prepare()
    roll_out_base()
    steps.pre_bake()
    bake()
    steps.post_bake()
```

### 8.4 Strategy: アルゴリズム全体の差し替え

```python
def prepare_dish(
    ingredients: list[Ingredient],
    recipe_maker: Callable[[list[Ingredient]], Dish],
) -> None:
    dish = recipe_maker(ingredients)
    serve(dish)

# 差し替え
prepare_dish(ingredients, make_taco)
prepare_dish(ingredients, make_burrito)
```

---

## 9. イベント駆動パターン

### 9.1 Observer パターン

```python
def complete_order(
    order: Order,
    observers: list[Callable[[Order], None]],
) -> None:
    package_order(order)
    for observe in observers:
        observe(order)

# 登録
complete_order(order, [
    notify_customer,
    schedule_pickup,
    update_analytics,
])
```

### 9.2 Pub/Sub（PyPubSub）

```python
from pubsub import pub

# コンシューマ登録
pub.subscribe(notify_customer, "meal-done")
pub.subscribe(schedule_pickup, "meal-done")

# プロデューサ
def complete_order(order: Order) -> None:
    package_order(order)
    pub.sendMessage("meal-done", order=order)
```

### 9.3 リアクティブ（RxPY）

```python
import rx
import rx.operators as ops

observable = rx.of(*sensor_data)

average_weight = observable.pipe(
    ops.filter(lambda d: isinstance(d, WeightData)),
    ops.map(lambda w: w.grams),
    ops.average(),
)
average_weight.subscribe(save_to_db)
```

---

## 10. プラグインアーキテクチャ（stevedore）

### 10.1 Protocol で契約を定義

```python
@runtime_checkable
class KitchenModule(Protocol):
    ingredients: list[Ingredient]
    def get_recipes(self) -> list[Recipe]: ...
    def prepare_dish(self, inventory: Inventory, recipe: Recipe) -> Dish: ...
```

### 10.2 エントリポイントで登録

```python
# setup.py
setup(
    entry_points={
        "kitchen.recipe_maker": [
            "pasta = kitchen.pasta:PastaModule",
            "tex_mex = kitchen.tex_mex:TexMexModule",
        ],
    },
)
```

### 10.3 動的ロード

```python
from stevedore import extension

mgr = extension.ExtensionManager(
    namespace="kitchen.recipe_maker",
    invoke_on_load=True,
)
all_recipes = list(itertools.chain.from_iterable(
    mgr.map(lambda ext: ext.obj.get_recipes())
))
```
