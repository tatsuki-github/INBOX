# 安全なリファクタリング手順ガイド

> リファクタリングは「振る舞いを変えない変更」だが、テストなしには証明できない。
> この文書は、特性化テスト・スモールステップ原則・git 戦略でリファクタリングを安全に行う手順を提供する。

---

## 1. 特性化テスト（Characterization Test）

### 概念

特性化テストとは「現在の振る舞いを記録するテスト」。バグかどうかは問わず、今の動作をそのまま固定する。

```
目的: リファクタリングで振る舞いが変わったことを検知できる状態を作る
注意: 「正しい振る舞い」を証明するテストではない（それはバグ修正の仕事）
```

### 書き方（ステップバイステップ）

```python
# Step 1: 対象コードを実行して、現在の出力を観察する
result = process_data(input_data)
print(result)  # → {"status": "ok", "count": 42}

# Step 2: その出力をそのまま期待値にしてテストを書く
def test_process_data_characterization():
    result = process_data({"type": "standard", "value": 100})
    # 現在の振る舞いを固定（正しさは問わない）
    assert result == {"status": "ok", "count": 42}

# Step 3: エッジケースも同様に記録する
def test_process_data_with_empty_input():
    result = process_data({})
    assert result == {"status": "error", "message": "invalid input"}
```

### TypeScript 版

```typescript
describe('processData - characterization tests', () => {
  it('現在の振る舞い: 標準入力 → ステータスOKと件数を返す', () => {
    const result = processData({ type: 'standard', value: 100 });
    expect(result).toEqual({ status: 'ok', count: 42 });
  });

  it('現在の振る舞い: 空入力 → エラーを返す', () => {
    const result = processData({});
    expect(result).toEqual({ status: 'error', message: 'invalid input' });
  });
});
```

### 特性化テストが必要なカバレッジ基準

| カバレッジ状況 | アクション |
|:---|:---|
| 80% 以上 | 追加不要。既存テストが安全網として機能 |
| 40-80% | リファクタリング対象コードのパスにテストを追加 |
| 40% 未満 | 主要フロー全ての特性化テストを作成してから開始 |
| テストなし | 全フロー（正常系・エッジケース）の特性化テストが必須 |

---

## 2. スモールステップ原則

### サイクルの定義

```
1 サイクル = 1 リファクタリングパターンの完全な適用

サイクル内:
  Before: テストが Green
  変更: 1 パターンのみ適用
  After: テストが Green → コミット
```

### コミットメッセージの規則

```
形式: refactor: <パターン名> - <対象の説明>

例:
  refactor: Extract Function - extractUserValidation from UserService
  refactor: Move Method - moveAddressUpdate to AddressService
  refactor: Rename - getUserById to findUserById for clarity
  refactor: Extract Class - AddressService from UserService
  refactor: Remove Dead Code - remove unused processLegacyOrder function
```

### Red になったときの対処

```
Red → 即ロールバック。推測で続けない。

ロールバック手順:
1. git stash  （変更を退避）
2. テストが Green であることを確認
3. git stash pop  （変更を戻す）
4. 変更を小さく分割し直して再試行

または:
1. git checkout <filename>  （ファイルを元に戻す）
2. 変更の原因を特定
3. 1 つずつ変更して Green を確認しながら再実施
```

---

## 3. Git 戦略

### ブランチ戦略

```bash
# リファクタリング開始前
git status  # クリーンな状態であることを確認
git checkout -b refactor/<scope>

# 例:
git checkout -b refactor/user-service-split
git checkout -b refactor/dry-validation-utils
git checkout -b refactor/payment-strategy-pattern
```

### チェックポイントの作成

```bash
# リファクタリング開始時の状態を保存
git add -p  # 対象ファイルのみ選択的に追加
git commit -m "refactor: checkpoint before Extract Class on UserService"

# 各パターン適用後
git add src/UserService.ts src/AddressService.ts
git commit -m "refactor: Extract Class - AddressService from UserService"
```

### ロールバック手順

```bash
# 直前のコミットに戻る（変更を捨てる）
git reset --hard HEAD

# 特定のコミットまで戻る
git log --oneline  # コミットハッシュを確認
git reset --hard <hash>

# 特定ファイルだけ戻す
git checkout HEAD -- src/UserService.ts

# stash で一時退避
git stash
git stash pop  # 戻す
git stash drop  # 破棄
```

---

## 4. 変更禁止リストの管理

リファクタリング前に「変えてはいけない振る舞い」を明示的に記録する。

### 記録テンプレート

```markdown
## 変更禁止リスト（<スキャン対象>）

### 外部 API（シグネチャ変更禁止）
- `getUserById(id: string): Promise<User | null>`
- `createUser(data: CreateUserInput): Promise<User>`

### エラー動作（変えてはいけない例外・エラーコード）
- 存在しない ID を渡すと `404` エラーを返す
- バリデーションエラーは `ValidationError` をスロー

### 副作用（順序・タイミング変更禁止）
- ユーザー作成時に `user.created` イベントを発行する
- ログは `INFO` レベルで `userId` を含む

### 戻り値の形式
- User オブジェクトは `{ id, name, email, createdAt }` の形式
```

---

## 5. テストがないコードへのアプローチ（段階的安全化）

### アプローチ選択肢

| 状況 | 推奨アプローチ |
|:---|:---|
| テストが書きやすいコード | 特性化テストを先に書いてからリファクタリング |
| 依存が多くテストが書きにくい | マイクロステップで変更（1 Rename ずつ）+ 手動確認 |
| 削除予定コード | テストを書かずに Rename で「_deprecated_」を付けてから削除 |
| 重要な本番コード | **test スキルに委譲** してテスト設計から始める |

### マイクロステップ戦略（テストなしの場合）

```
テストなしでも安全に変更できる最小単位:

✅ 安全なマイクロ変更:
  - Rename（変数名・関数名の改名）— IDE の安全なリネームを使う
  - Extract Variable（インライン式を変数に抽出）
  - Inline Variable（変数をインライン化）
  - Remove Dead Code（参照がないことをgrepで確認後）

⚠️ 要注意（手動確認必須）:
  - Extract Function（スコープのミスが起きやすい）
  - Move Method（参照の更新漏れが起きやすい）

❌ テストなしでは危険:
  - Replace Conditional with Polymorphism（振る舞いの変更リスクが高い）
  - Extract Class（循環依存のリスク）
```
