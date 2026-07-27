# 型システムパターン集（ロバスト Python 第I部 準拠）

本ファイルは SKILL.md の原則 1・原則 2 の詳細リファレンスである。

---

## 1. 型アノテーション基本ルール

### 1.1 関数シグネチャ — 常にアノテーションする

```python
# NG: 呼び出し元は実装を読まないと戻り値が分からない
def find_workers_available_for_time(open_time):
    ...

# OK: シグネチャだけで契約が完結
def find_workers_available_for_time(
    open_time: datetime.datetime,
) -> list[str]:
    ...
```

### 1.2 変数アノテーション — 自明なら省略

```python
# NG: 冗長（型推論で十分）
number: int = 0
text: str = "hello"
worker: Worker = Worker()

# OK: 型が自明でない場合のみ明示
config: dict[str, Union[str, int]] = load_config()
items: list[str] = []  # 空コレクションは型推論が効かない
```

### 1.3 コレクション型 — 要素型を常に明示

```python
# NG: 要素の型が不明
def create_mapping(cookbooks: list) -> dict:
    ...

# OK: 要素型付き + 型エイリアスで可読性向上
AuthorCount = dict[str, int]
def create_mapping(cookbooks: list[Cookbook]) -> AuthorCount:
    ...
```

---

## 2. Optional 型パターン

### 2.1 None を返す関数は必ず Optional

```python
# NG: str と宣言しながら None を返す
def get_name(city: str) -> str:
    if city in US_CITIES:
        return "Pat's Place"
    return None  # 型違反！

# OK: Optional で明示
def get_name(city: str) -> Optional[str]:
    if city in US_CITIES:
        return "Pat's Place"
    return None
```

### 2.2 空 vs 不在の区別

| 戻り値 | 意味 |
|:---|:---|
| `[]`（空リスト） | データはあるが結果が0件 |
| `None` | データ取得に失敗、または該当なし |

```python
# OK: 空と不在を区別
def search_recipes(query: str) -> Optional[list[Recipe]]:
    if not connected_to_db():
        return None  # 不在（エラー）
    results = db.query(query)
    return results  # 空リスト = 0件だが正常
```

### 2.3 --strict-optional の効果

```python
# mypy --strict-optional 有効時:
name: Optional[str] = get_name("Tokyo")
print(name.upper())  # ERROR: name が None の可能性

# 正しいハンドリング
if name is not None:
    print(name.upper())
```

### 2.4 --no-implicit-optional

```python
# NG: 暗黙の Optional（意図が不明瞭）
def foo(x: int = None) -> None:
    ...

# OK: 明示的な Optional
def foo(x: Optional[int] = None) -> None:
    ...
```

---

## 3. Union 型パターン

### 3.1 複数型を返す関数

```python
# OK: 呼び出し元は全ケースのハンドリングを強制される
def dispense(user_input: str) -> Union[HotDog, Pretzel]:
    if user_input == "hotdog":
        return HotDog()
    elif user_input == "pretzel":
        return Pretzel()
    raise ValueError(f"Unknown: {user_input}")
```

### 3.2 Sum 型 vs Product 型

**Product 型**（直積）: 全フィールドの組み合わせが可能 → 無効な状態を含む

```python
# Product型: 3 × 4 × 2 = 24通りだが有効は一部
@dataclass
class Snack:
    name: str           # 3種
    condiments: set[str] # 4通り
    error_code: int      # 0 or 非0
```

**Sum 型**（直和）: Union で有効な組み合わせだけを定義

```python
# Sum型: 有効状態のみ
@dataclass
class SnackOK:
    name: Literal["pretzel", "hotdog", "veggie"]
    condiments: set[Literal["mustard", "ketchup"]]

@dataclass
class SnackError:
    error_code: Literal[1, 2, 3, 4, 5]
    disposed_of: bool

Result = Union[SnackOK, SnackError]  # 無効な組み合わせは不可能
```

---

## 4. Literal 型

値の範囲を静的に制限する。

```python
# NG: 任意の int が渡せる
def set_error(code: int): ...

# OK: 許容値のみ
def set_error(code: Literal[1, 2, 3, 4, 5]): ...
```

---

## 5. NewType — 意味的型安全

同じ基底型で意味が異なる値を型レベルで区別する。

```python
from typing import NewType

# 「洗浄済み」と「未洗浄」の文字列を区別
SanitizedString = NewType("SanitizedString", str)

def execute_query(query: SanitizedString) -> list[Row]:
    ...  # 安全な文字列のみ受け付ける

def sanitize(raw: str) -> SanitizedString:
    validated = validate_and_escape(raw)
    return SanitizedString(validated)

# NG: 生の文字列を直接渡す → 型エラー
execute_query("DROP TABLE users")

# OK: sanitize 経由でのみ生成
safe = sanitize(user_input)
execute_query(safe)
```

**NewType のユースケース例**:
- `SanitizedString` — SQL インジェクション防止
- `ValidUserId` — 検証済みユーザー ID
- `ReadyToServeHotDog` — 調理完了済みのホットドッグ

**特性**: 一方向変換。`HotDog` → `ReadyToServeHotDog` は不可、逆は可。

---

## 6. Final — 定数の保護

```python
from typing import Final

VENDOR_NAME: Final = "Auto-Dog"
# VENDOR_NAME = "Other"  → mypy エラー: Cannot assign to final name

# 注意: Final は再代入を防ぐが、オブジェクト内部の変更は防がない
ITEMS: Final = [1, 2, 3]
ITEMS.append(4)  # これは防げない！
```

---

## 7. Annotated — メタデータ付き型

型チェッカでは検証されないが、ドキュメントとして機能する。

```python
from typing import Annotated

x: Annotated[int, "3以上5以下の値"]
y: Annotated[str, "YYYY形式の年"]
```

pydantic と組み合わせると実行時検証が可能:

```python
from pydantic import Field

class Config(BaseModel):
    port: Annotated[int, Field(ge=1, le=65535)]
```

---

## 8. TypedDict — 異種辞書の型付け

JSON / YAML / API レスポンスなど、キーが固定された辞書に使う。

```python
from typing import TypedDict

class NutritionInfo(TypedDict):
    calories: int
    fat: float
    unit: str
    confidence: float

# 型チェッカがキーの存在と値の型を検証
info: NutritionInfo = {
    "calories": 250,
    "fat": 12.5,
    "unit": "kcal",
    "confidence": 0.95,
}
```

**制限**: TypedDict は型チェッカのみ。実行時の型は `dict`。
実行時検証が必要なら pydantic を使う。

**TypedDict vs dataclass**:
- TypedDict: JSON パース結果をそのまま使う場合（メソッド不要）
- dataclass: メソッド定義、`frozen`、`order` 等が必要な場合

---

## 9. Generics（ジェネリクス）

入出力の型を関連付ける。

```python
from typing import TypeVar

T = TypeVar("T")

def reverse(coll: list[T]) -> list[T]:
    return coll[::-1]

# API エラーハンドリングパターン
APIResponse = Union[T, APIError]

def get_info(recipe: str) -> APIResponse[NutritionInfo]: ...
def get_items(recipe: str) -> APIResponse[list[Ingredient]]: ...
```

---

## 10. コレクション型のカスタマイズ

### 10.1 組み込み型の継承は禁止

```python
# NG: __getitem__ のオーバーライドが .get() に反映されない
class MyDict(dict):
    def __getitem__(self, key):
        ...  # .get() はこれを使わない！

# OK: UserDict を使う
from collections import UserDict

class MyDict(UserDict):
    def __getitem__(self, key):
        return self.data[key]  # .get() もこれを使う
```

### 10.2 抽象基底クラスでインタフェース型を使う

```python
from collections.abc import Iterable, Mapping, Sequence

# OK: 具象型ではなく抽象型でアノテーション
def process(items: Iterable[str]) -> None:
    for item in items:
        ...  # list, tuple, set, generator すべて受け付ける
```

---

## 11. 型チェック導入戦略

### 優先順位の決め方

| 戦略 | 対象 | 効果 |
|:---|:---|:---|
| 新規コードのみ | 新規/修正ファイル | ゼロコストで開始 |
| ボトムアップ | 共有ユーティリティ | 効果が全呼び出し元に波及 |
| 収益コード優先 | ビジネスロジック | 最も長寿命・高価値 |
| 高頻度変更 | git log で最多コミットのファイル | 最も恩恵が大きい |
| 複雑コード | 理解困難なモジュール | ドキュメント効果が最大 |

### MonkeyType — 実行時からアノテーション生成

```bash
$ pip install monkeytype
$ monkeytype run your_script.py
$ monkeytype stub your_module  # 推論結果を確認
$ monkeytype apply your_module  # ソースに適用
```

生成された `Union` は要注意 — 複数型を受ける関数は設計の問題かもしれない。

### Pytype — 静的推論（Google製）

```bash
$ pip install pytype
$ pytype your_module.py  # アノテーションなしでも型エラーを検出
```
