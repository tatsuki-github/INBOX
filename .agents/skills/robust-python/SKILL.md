---
name: robust-python
description: >
  Python コードの設計・実装・レビューを、書籍『ロバスト Python』
  （Patrick Viafore 著、全24章・4部構成）の原則に基づいて支援する。
  型アノテーションによる意図の伝達、ユーザー定義型の適切な選択（Enum/dataclass/class/Protocol）、
  不変式の保護、拡張性設計（OCP/コンポーザビリティ）、
  多層セーフティネット（静的解析・テスト戦略）を適用し、
  将来のメンテナが安心してコードを変更できるロバストな Python コードを実現する。
  Use when user says「Pythonを書いて」「Pythonのコードをレビューして」
  「型アノテーションを付けて」「型を設計して」「dataclassを使うべきか」
  「クラス設計をレビューして」「Protocolを使うべきか」「拡張性を改善して」
  「依存関係を整理して」「Pythonのベストプラクティスを教えて」
  「ロバストなコードにして」「保守性を高めて」。
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: development
  based-on: "Robust Python (Patrick Viafore, 24 Chapters / 4 Parts)"
---

# Skill: Robust Python（ロバスト Python ベストプラクティス）

> **「コードは未来の開発者との非同期コミュニケーションである」**

## Instructions

本スキルは Python コードの新規作成・リファクタリング・コードレビュー時に発動する。
書籍『ロバスト Python』の 4 部構成に対応する 9 原則を適用し、
将来のメンテナが安心して変更できるコードを実現する。

```
ワークフロー位置:
  設計/実装 ─→ ★ robust-python ─→ review（レビュー）
                     ↕                    ↑
                test（テスト品質）   data-validation
```

**入力**: Python ソースコード、設計相談、コードレビュー依頼
**出力**: ロバストなコード、改善提案、レビューコメント

**コアフレームワーク — 4部構成**:

| 部 | テーマ | 対応原則 |
|:---|:---|:---|
| 第I部 | 型アノテーション — 意図を伝える | 原則 1, 2 |
| 第II部 | ユーザー定義型 — ドメインを表現する | 原則 3, 4, 5 |
| 第III部 | 拡張性 — 変更に備える | 原則 6, 7 |
| 第IV部 | セーフティネット — エラーを検出する | 原則 8 |

---

## 原則 1: 型アノテーションでコミュニケーションする

型アノテーションは将来の開発者への手紙である。実行時には無視されるが、
型チェッカと人間の両方にとって最も効率的なドキュメントとなる。

**必須ルール**:
- 関数の引数と戻り値には**常に型を付ける**
- ローカル変数は**型推論に任せる**（自明な場合はアノテーション不要）
- 空のコレクションには型を明示する（`items: list[str] = []`）
- `Any` は**原則禁止** — 使う場合はコメントで理由を書く

```python
# NG: 戻り値不明、呼び出し元は実装を読む必要がある
def find_workers(open_time):
    ...

# OK: 関数シグネチャだけで契約が分かる
def find_workers(open_time: datetime.datetime) -> list[str]:
    ...
```

**型チェッカ設定（mypy 推奨）**:

| 設定 | 効果 |
|:---|:---|
| `--strict-optional` | None チェックを強制（**最重要**） |
| `--no-implicit-optional` | `Optional` の明示を強制 |
| `--disallow-any-generics` | 裸の `list`, `dict` を禁止 |
| `--disallow-untyped-defs` | 未アノテーション関数を禁止 |
| `--warn-return-any` | `Any` 戻り値を警告 |

CRITICAL: 新規コードに `# type: ignore` を使ってはならない。レガシーコード専用。

---

## 原則 2: Optional/Union で無効な状態を排除する

`None` は「10億ドルの過ち」。`Optional` を明示し、Union で有効な状態のみを表現する。

**必須ルール**:
- `None` を返しうる関数は**必ず** `Optional[T]` と宣言する
- 複数型を返す関数は `Union` で全候補を列挙する
- Product 型（全フィールド1クラス）より **Sum 型**（Union of 特化クラス）を優先する

```python
# NG: Product型 — 無効な組み合わせが表現可能
@dataclass
class Snack:
    name: str
    error_code: int       # エラー時のみ有効
    disposed_of: bool     # error_code != 0 の時のみ有効

# OK: Sum型 — 有効な状態のみ表現可能
@dataclass
class SnackOK:
    name: str
    condiments: set[str]

@dataclass
class SnackError:
    error_code: Literal[1, 2, 3, 4, 5]
    disposed_of: bool

Result = Union[SnackOK, SnackError]
```

**意味的型安全の強化**:
- `NewType` で同じ基底型の混同を防ぐ（`SanitizedString` vs `str`）
- `Literal` で許容値を制限する（`Literal["red", "green", "blue"]`）
- `Final` でモジュール定数の再代入を防ぐ

詳細パターンは `references/type-system-patterns.md` を参照。

---

## 原則 3: ユーザー定義型を正しく選択する

データの性質に応じて最適な型を選ぶ。選択を間違えると不変式が壊れるか、過剰な複雑さを招く。

**選択フローチャート**:
```
データの性質は？
  ├── キー → 値のマッピング？ ──────────→ dict
  ├── 静的な選択肢の集合？ ──────────────→ Enum
  ├── フィールド間が独立？ ──────────────→ dataclass
  │     └── 外部データのバリデーション？ → pydantic dataclass
  ├── フィールド間に不変式がある？ ──────→ class
  └── 構造だけを要求？（ダックタイピング）→ Protocol
```

**各型の使い分け**:

| 型 | 用途 | 注意点 |
|:---|:---|:---|
| `Enum` | 静的な選択肢（`auto()` / `Flag`） | 実行時に変わるなら dict |
| `dataclass` | 独立フィールドの集約（`frozen=True` 推奨） | 不変式があるなら class |
| `class` | 不変式の保護が必要 | 不変式がなければ過剰 |
| `TypedDict` | JSON/YAML パース結果の型付け | 実行時検証なし |
| `Protocol` | 継承なしの構造的部分型 | 振る舞いの契約が必要なら ABC |
| `pydantic` | 外部入力の実行時バリデーション | パース（型変換）に注意 |

```python
# NG: 不変式のないデータにクラスを使う（過剰設計）
class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

# OK: dataclass で十分
@dataclass(frozen=True)
class Point:
    x: float
    y: float
```

詳細パターンは `references/design-patterns.md` を参照。

---

## 原則 4: 不変式を保護するクラス設計

クラスの存在意義は**不変式の保護**にある。不変式がなければ dataclass を使う。

**必須ルール**:
- `__init__` で不変式を検証する（`assert` または `raise ValueError`）
- 内部状態は `__` プレフィックスで隠蔽し、メソッド経由でのみ変更を許可
- 全公開メソッドで不変式の事後条件を維持する

```python
class PizzaSpec:
    def __init__(self, radius: int, toppings: list[str]):
        if not (6 <= radius <= 12):
            raise ValueError("生地は6〜12インチ")
        sauces = [t for t in toppings if is_sauce(t)]
        if len(sauces) > 1:
            raise ValueError("ソースは1種類まで")
        self.__radius = radius
        self.__toppings = list(toppings)

    def add_topping(self, topping: str) -> None:
        if is_sauce(topping) and any(is_sauce(t) for t in self.__toppings):
            raise ValueError("ソースは1種類まで")
        self.__toppings.append(topping)
```

**不変式を伝える手段**: `__init__` のアサーション、docstring、ユニットテスト

---

## 原則 5: Protocol で構造的部分型を活用する

Protocol はダックタイピングに型安全性を与える。継承なしで「必要な振る舞い」を型として宣言できる。

**使い分け**:
- **Protocol**: 構造（メソッド/属性の存在）だけを要求する場合
- **ABC**: サブクラスにメソッド実装を強制し、振る舞いの契約（不変式）を定義する場合
- **継承**: 真の is-a 関係でリスコフの置換原則（LSP）を保証できる場合のみ

```python
# NG: Union で列挙 → 新クラス追加のたびに修正
def split(dish: Union[BLT, Chili, Salad]):
    ...

# OK: Protocol で構造要求 → 新クラスは Protocol を満たすだけでよい
from typing import Protocol, runtime_checkable

@runtime_checkable
class Splittable(Protocol):
    cost: int
    def split_in_half(self) -> tuple['Splittable', 'Splittable']: ...

def split(dish: Splittable) -> tuple[Splittable, Splittable]:
    return dish.split_in_half()
```

**LSP 違反の危険信号**:
- オーバーライドで追加の引数チェック（事前条件の厳格化）
- `super()` を呼ばないオーバーライド
- 基底クラスにない例外の送出
- 早期リターンによる事後条件の省略

CRITICAL: 継承は is-a 関係でのみ使う。コード再利用が目的ならコンポジションを使う。

---

## 原則 6: 拡張に対して開き、変更に対して閉じる（OCP）

新機能の追加で既存コードの修正を最小化する設計を目指す。

**OCP 違反の兆候**:
- 簡単な変更に多数のファイル修正が必要（ショットガン手術）
- 同じ `if/elif` チェーンが複数箇所に散在
- 新機能の見積もりが常に大きい

**対処パターン**:
1. **データ型の分離**: 通知内容・通知手段・通知先をそれぞれ独立した型にする
2. **イベント駆動**: プロデューサとコンシューマを分離（Observer / Pub-Sub）
3. **プラグイン**: Protocol + エントリポイントで動的拡張

```python
# NG: 通知先追加のたびに全関数に引数追加
def declare_special(dish, emails, texts, send_to_customer):
    ...

# OK: 通知手段をデータとして管理
notify_map: dict[type, list[NotifyMethod]] = {
    NewSpecial: [Email("boss@co.jp"), API("supplier")],
}

def declare_special(dish: Dish, start: datetime, end: datetime):
    send_notification(NewSpecial(dish, start, end))
```

**注意**: OCP の過剰適用は可読性を損なう。変更頻度が高い箇所に限定して適用する。

詳細パターンは `references/design-patterns.md` を参照。

---

## 原則 7: ポリシーとメカニズムを分離する

ポリシー（何をするか）とメカニズム（どうやるか）を分けると、
メカニズムを自由に組み合わせて新しい振る舞いを構築できる。

```python
# NG: 再試行ロジックがビジネスロジックに埋め込まれている
def save_inventory(inventory):
    retry_counter = 0
    while retry_counter < 5:
        try:
            for item in inventory:
                db[item.name] = item.count
            break
        except OperationError:
            retry_counter += 1
            time.sleep(2 ** retry_counter)

# OK: メカニズム（再試行）をデコレータで分離
@backoff.on_exception(backoff.expo, OperationError, max_tries=5)
def save_inventory(inventory):
    for item in inventory:
        db[item.name] = item.count
```

**実践パターン**:
- **デコレータ**: 横断的関心事（ロギング、再試行、キャッシュ）の分離
- **itertools**: アルゴリズムを宣言的に組み合わせる
- **Template Method**: アルゴリズムの骨格を固定、ステップを差し替え可能に
- **Strategy**: アルゴリズム全体を差し替え可能に

---

## 原則 8: セーフティネットを多層化する（スイスチーズモデル）

単一のツールですべてのバグは防げない。複数のツールを**層状に重ねる**ことで、
1 層で漏れたバグを次の層で捕捉する。

**セーフティネットスタック**:

| 層 | ツール | 検出対象 | コスト | 頻度 |
|:---|:---|:---|:---|:---|
| 型チェック | mypy / Pyright | 型エラー, None 誤用 | 極低 | 保存/コミット毎 |
| リンター | Pylint + カスタム | ミュータブルデフォルト, デッドコード | 極低 | コミット毎 |
| 複雑度 | mccabe | バグの温床となる複雑なコード | 極低 | 定期的 |
| セキュリティ | Bandit | SQL注入, 弱い暗号, デバッグモード | 低 | コミット毎 |
| 単体テスト | pytest + AAA | 関数/クラスの振る舞い | 低-中 | コミット毎 |
| 受入テスト | behave + Gherkin | 顧客の期待 | 中 | 日次/週次 |
| プロパティテスト | Hypothesis | 境界値, 不変式違反 | 中 | コミット毎 |
| ミューテーションテスト | mutmut | テスト品質の穴 | 高 | 定期的/対象限定 |

CRITICAL: カバレッジ率は品質を保証しない。ミューテーションテストでテストの実効性を検証せよ。

**AAA パターン（テスト構造の基本）**:
1. **Arrange**: 前提条件のセットアップ（小さく保つ、共通部分はフィクスチャに）
2. **Act**: テスト対象の実行（1-2 行に抑える）
3. **Assert**: 結果の検証（1 つの論理的アサーション）
4. **Annihilate**: リソースのクリーンアップ（`yield` フィクスチャで保証）

詳細は `references/safety-net-guide.md` を参照。

---

## コードレビュー時のチェックリスト

**型アノテーション**:
- 関数の引数と戻り値にすべて型が付いているか
- `None` を返しうる関数は `Optional[T]` で宣言しているか
- 裸の `list`, `dict`, `set` を使っていないか（要素型を明示しているか）
- `Any` を使っている箇所にコメントで理由が書かれているか

**ユーザー定義型**:
- データの性質に合った型を選んでいるか（Enum/dataclass/class/Protocol）
- 不変式のないデータにクラスを使っていないか（dataclass で十分ではないか）
- 不変式を持つクラスが `__init__` で検証しているか
- 継承は LSP を満たしているか（コンポジションで代替できないか）

**拡張性**:
- 同じ `if/elif` チェーンが複数箇所に散在していないか（OCP 違反）
- ポリシー（ビジネスロジック）とメカニズム（インフラ）が分離されているか
- 依存関係の向きが適切か（ファンインの大きいモジュールは安定しているか）

**セーフティネット**:
- テストが AAA パターンに従っているか
- 外部サービスのモックが過剰になっていないか（設計の問題の兆候）
- ミュータブルデフォルト引数を使っていないか

---

## アンチパターン一覧

| アンチパターン | 問題 | 対処 |
|:---|:---|:---|
| 裸のコレクション型 | 要素の型が不明で型チェッカが無力 | `list[str]`, `dict[str, int]` と明示 |
| 暗黙の Optional | `def f(x: int = None)` は意図が不明 | `Optional[int]` を明示 |
| 組み込み dict/list の継承 | `__getitem__` のオーバーライドが `.get()` に反映されない | `UserDict`, `UserList` を使う |
| Product 型の乱用 | 無効な状態の組み合わせが表現可能 | Union で Sum 型に分割 |
| 不変式のないクラス | 過剰設計、dataclass で十分 | `@dataclass(frozen=True)` に変更 |
| IntEnum の使用 | 暗黙の int 変換がバグの温床 | `Enum` + `auto()` を使う |
| DRY の過剰適用 | 変更理由が異なるコードを統合 | 似ているだけのコードは重複を許容 |
| ミュータブルデフォルト引数 | `def f(items=[])` は呼び出し間で共有 | `None` デフォルト + 関数内で新規作成 |
| カバレッジ至上主義 | 高カバレッジでもアサーションが無意味なら品質は低い | ミューテーションテストで実効性を検証 |

---

## Examples

### Example 1: 新規 Python コードの設計

```
「robust-python スキルで、注文管理システムの Python コードを設計して」
```

→ ドメインモデルを Enum/dataclass/class で設計し、型アノテーション完備のコードを生成。
不変式のあるエンティティは class、独立データは dataclass、ステータスは Enum で表現。
mypy `--strict` で型安全性を確保。

### Example 2: 既存コードのレビュー

```
「robust-python スキルで、この Python コードをレビューして」
```

→ 8 原則に基づきレビュー。型アノテーション漏れ、Product 型の乱用、
不変式の未検証、OCP 違反、テスト品質の問題点を指摘。
改善案をコード例付きで提示。

### Example 3: 型設計の相談

```
「robust-python スキルで、この辞書を適切な型に変換して」
```

→ 選択フローチャートに基づき、dataclass / TypedDict / class のいずれが最適かを判定。
フィールド間の依存関係を分析し、不変式があれば class、なければ dataclass を提案。
pydantic の必要性（外部入力バリデーション）も併せて判断。

### Example 4: 拡張性の改善

```
「robust-python スキルで、この通知システムの拡張性を改善して」
```

→ OCP 違反を検出し、通知内容・手段・宛先をデータとして分離。
Observer パターンまたは Protocol ベースのプラグイン設計を提案。
依存グラフの可視化ツール（pydeps, pyan3）の活用も案内。

---

## Troubleshooting

| 問題 | 原因 | 対処 |
|:---|:---|:---|
| mypy エラーが大量に出て対処不能 | レガシーコードへの一括適用 | モジュール単位で段階導入。`--per-module` 設定で重要モジュールから |
| `Optional` チェックが煩雑 | None ハンドリングの連鎖 | 早期リターンパターン、またはモナド的な合成で簡潔に |
| dataclass と class の使い分けが不明 | 不変式の有無の判断ミス | 「フィールド A を変えたとき B も変えなければならないか？」で判定 |
| Protocol が過剰に感じる | 小規模コードでは冗長 | 2箇所以上で同じダックタイピングが使われた時点で Protocol を導入 |
| テストでモックが多すぎる | 物理的依存関係の密結合 | 設計を見直す。依存注入（DI）やイベント駆動で結合度を下げる |
| ミューテーションテストが遅い | 全コードベースに実行 | `--use-coverage` でテスト済みコードに限定。重要モジュールのみ対象 |

---

## References

| ファイル | 用途 |
|:---|:---|
| [type-system-patterns.md](references/type-system-patterns.md) | Optional/Union/Literal/NewType/Final/TypedDict/Generics の詳細パターン集 |
| [design-patterns.md](references/design-patterns.md) | Enum/dataclass/class/Protocol/Pydantic + OCP/依存関係/コンポーザビリティの設計パターン集 |
| [safety-net-guide.md](references/safety-net-guide.md) | mypy設定/Pylint/Bandit + AAA/BDD/Hypothesis/mutmut のテスト戦略ガイド |

---

## Related Skills

| スキル | 関係 | 連携内容 |
|:---|:---|:---|
| **test** | 補完 | robust-python の原則 8（セーフティネット）を test スキルの 4 本柱で深化。AAA パターンとモック戦略を共有 |
| **review** | 後工程 | robust-python でコードを実装した後、review スキルでクリティカルレビューを実施 |
| **effective-typescript** | 相互 | 型システム活用の思想を共有。Python の Protocol は TypeScript の構造的部分型に対応 |
