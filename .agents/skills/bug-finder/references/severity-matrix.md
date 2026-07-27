# Severity Matrix（重大度判定マトリクスとレポートテンプレート）

> Step 7 の実行リファレンス。Review Gate 7 の通過基準として、各バグの重大度判定にこのマトリクスを適用する。

---

## 重大度判定マトリクス（影響範囲 × 発現確率）

|  | 発現確率: 高（常に/高頻度） | 発現確率: 中（特定条件） | 発現確率: 低（まれ/複雑な条件） |
|:---|:---:|:---:|:---:|
| **影響: 致命的**（データ損失/認証突破/本番停止） | 🔴 Critical | 🔴 Critical | 🟠 High |
| **影響: 重大**（主要機能破綻/データ汚染/セキュリティリスク） | 🔴 Critical | 🟠 High | 🟡 Medium |
| **影響: 中**（部分機能障害/エラーの握りつぶし） | 🟠 High | 🟡 Medium | 🟡 Medium |
| **影響: 軽微**（表示崩れ/パフォーマンス劣化） | 🟡 Medium | 🔵 Low | 🔵 Low |

---

## カテゴリ別デフォルト重大度

| カテゴリ | 典型例 | デフォルト重大度 |
|:---|:---|:---:|
| SQL インジェクション | ユーザー入力をクエリに直接結合 | 🔴 Critical |
| コマンドインジェクション | shell=True + ユーザー入力 | 🔴 Critical |
| 認証バイパス | 認証ミドルウェアの適用漏れ | 🔴 Critical |
| 弱いパスワードハッシュ | MD5/SHA1 でパスワードを保存 | 🔴 Critical |
| JWT 署名未検証 | alg=none 受け入れ | 🔴 Critical |
| ハードコードシークレット | API キーのリテラル埋め込み | 🔴 Critical |
| mutex のロック解放漏れ | Lock() without defer Unlock() | 🔴 Critical |
| XSS | innerHTML へのユーザー入力 | 🟠 High |
| Null 参照（主要機能） | メインフローでの NullPointerException | 🟠 High |
| DB コネクションリーク | finally で close されない | 🟠 High |
| エラーの握りつぶし（主要処理） | 決済・保存処理で空の catch | 🟠 High |
| N+1 問題 | ループ内で個別 DB クエリ | 🟠 High |
| forEach + async/await | Promise を待機しない | 🟠 High |
| タイムゾーン非対応 | timezone-naive な datetime | 🟡 Medium |
| switch default 欠如 | サイレント失敗 | 🟡 Medium |
| デッドコード | 到達不能コードパス | 🔵 Low |
| 未使用変数 | 宣言後に一度も参照しない変数 | 🔵 Low |

---

## バグ発見レポートテンプレート

### スキャンサマリーセクション

```markdown
## バグ発見レポート

| 項目 | 詳細 |
|:---|:---|
| **スキャン対象** | `./src/` |
| **スキャン日時** | YYYY-MM-DD |
| **言語** | TypeScript |
| **スキャンファイル数** | 38 ファイル |

| 重大度 | 件数 | 推奨対応期限 |
|:---|:---:|:---|
| 🔴 Critical | 2 | 当日中 |
| 🟠 High | 3 | 今スプリント |
| 🟡 Medium | 5 | 次スプリント |
| 🔵 Low | 8 | バックログ |
| **合計** | **18** | — |
```

### 個別バグエントリーテンプレート（Critical/High）

```markdown
#### BUG-001: <バグタイトル>
- **重大度**: 🔴 Critical
- **ファイル**: `src/api/users.ts:87`
- **カテゴリ**: SQL インジェクション（OWASP A03）
- **発現条件**: `/api/users?id=` パラメータに任意文字列を渡したとき
- **証拠**:
  ```ts
  const q = `SELECT * FROM users WHERE id=${req.query.id}`;
  ```
- **修正方向**: Prepared Statement（`db.query('SELECT * FROM users WHERE id=?', [req.query.id])`）に変更
- **引き継ぎ**: bug-triage-fix で根本調査・修正を実施
```

### 推奨アクションセクション

```markdown
### 推奨アクション
1. 🔴 Critical バグを即座に bug-triage-fix で対応（当日中）
2. 🟠 High バグを今スプリントのバックログに追加
3. 🟡 Medium バグをリファクタリングチケットとして起票
4. 🔵 Low バグをバックログの最下位に登録

### bug-triage-fix への引き継ぎ情報
- BUG-001（SQL インジェクション）: Step 3（仮説ツリー）から開始。仮説 A: ユーザー入力のサニタイズなし
- BUG-002（JWT 未検証）: Step 3 から開始。仮説 A: jwt.verify() の呼び出しなし
```
