# Bug Patterns Catalog（バグカテゴリ別検出シグネチャ集）

> Step 3〜5 の実行リファレンス。各カテゴリの「検出シグネチャ」と「発現条件の確認方法」を集約する。

---

## カテゴリ 1: Null / Undefined 参照

### 検出シグネチャ

| シグネチャ | 言語 | 重大度 |
|:---|:---|:---|
| `obj.prop` の前に null チェックなし | 全言語 | High |
| `arr.find(...).value` — find() の結果を直接使用 | JS/TS/Python | High |
| `dict.get('key').method()` — get() 結果の直接使用 | Python | High |
| `document.getElementById('id').click()` — DOM 要素未チェック | JS/TS | Medium |
| `result, _ := query()` — エラー無視 | Go | High |

### 発現条件の確認方法

```
1. 対象コードで「null/None/undefined を返す可能性のある関数」を列挙する
2. その戻り値に null チェックなしでアクセスしているコードパスを追う
3. 「どの入力値または状態のときに null が返るか」を特定する
4. 特定できた場合のみバグ候補として記録する（推測での記録は不可）
```

---

## カテゴリ 2: 型変換・型強制エラー

### 検出シグネチャ

| シグネチャ | 言語 | 重大度 |
|:---|:---|:---|
| `parseInt(val)` — 基数未指定 | JS/TS | Medium |
| `"3" + 5` — 文字列と数値の演算 | JS | Medium |
| `0.1 + 0.2` — 浮動小数点で金額計算 | 全言語 | High（金融系） |
| `if value == None` — is の代わりに == | Python | Low |
| `"10" > "9"` — 文字列として比較 | JS/TS | Medium |

---

## カテゴリ 3: ロジック・制御フロー

### 検出シグネチャ

| シグネチャ | 説明 | 重大度 |
|:---|:---|:---|
| `for (i = 0; i <= arr.length; i++)` | オフバイワン（`<=` が `<` の誤り） | High |
| `switch` に `default` がない | サイレント失敗 | Medium |
| `catch(e) {}` — 空の catch | エラーの握りつぶし | High |
| `forEach(async item => await ...)` | forEach は await を待たない | High |
| `const data = fetchData()` — await 欠落 | Promise オブジェクトが返る | High |

### 発現条件の確認方法

```
オフバイワン:
- ループの終了条件が < か <= かを精査する
- 配列の最後の要素にアクセスするユースケースを考える

サイレント失敗:
- switch に渡される値の取りうる範囲を列挙する
- default がない場合に何も実行されないコードパスを確認する
```

---

## カテゴリ 4: 競合状態（Race Condition）

### 検出シグネチャ

| パターン名 | コード例 | 重大度 |
|:---|:---|:---|
| Check-Then-Act | `if (exists(path)) { read(path) }` | Critical |
| Read-Modify-Write | `count = count + 1`（非アトミック） | Critical |
| DB 更新の競合 | SELECT → UPDATE をトランザクション外で実行 | Critical |
| DOM 競合（JS） | async 処理中に要素を参照・削除 | Medium |

### 発現条件の確認方法

```
「複数の実行コンテキスト（スレッド/リクエスト/タスク）が同じリソースにアクセスするか」を確認する。
以下がすべて当てはまる場合は競合状態の候補:
1. 複数の実行コンテキストが存在する（非同期処理/マルチスレッド/複数リクエスト）
2. 共有リソース（変数/ファイル/DBレコード）へのアクセスがある
3. アクセスがアトミックでない（ロック/トランザクションがない）
```

---

## カテゴリ 5: リソースリーク

### 検出シグネチャ

| リソース | リーク条件 | 言語 | 重大度 |
|:---|:---|:---|:---|
| DB コネクション | finally / with なしで取得 | 全言語 | High |
| ファイルハンドル | `open()` が `with` の外 | Python | High |
| HTTP クライアント | session / client が close されない | 全言語 | Medium |
| setInterval | clearInterval がペアにない | JS/TS | Medium |
| addEventListener | removeEventListener がない | JS/TS | Medium |
| goroutine | キャンセル条件なしに起動 | Go | High |

---

## カテゴリ 6: 外部依存の誤用

### 検出シグネチャ

| シグネチャ | 問題 | 重大度 |
|:---|:---|:---|
| タイムアウト未設定の外部 API 呼び出し | 無限待機でスレッドを消費 | High |
| レスポンスのステータスコード未チェック | エラーを正常として処理 | Medium |
| リトライロジックなしの冪等でない操作 | 一時障害時にデータ不整合 | Medium |
| 依存サービスのダウンを想定しない | 連鎖障害（Cascade Failure） | High |
