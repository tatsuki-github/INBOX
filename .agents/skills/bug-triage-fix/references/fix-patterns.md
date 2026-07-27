# Fix Patterns — バグ種別別修正パターン集

> バグの根本原因カテゴリに対応する、実装レベルの修正パターン。コピーして適用する。

---

## 1. Null / Undefined 参照エラー

**症状**: `TypeError: Cannot read properties of null`, `AttributeError: 'NoneType' object has no attribute`

| パターン | Before | After |
|:---|:---|:---|
| オプショナルチェーン | `user.profile.name` | `user?.profile?.name` |
| Nullish Coalescing | `user.name \|\| 'default'` | `user?.name ?? 'default'` |
| 早期リターン | ネストした if | `if (!user) return null` |
| デフォルト値 | `list.length > 0` | `(list ?? []).length > 0` |

```typescript
// Before: Null 未考慮
function getAvatarUrl(user: User): string {
  return user.profile.avatar.url; // null で例外
}

// After: Null ガード付き
function getAvatarUrl(user: User): string {
  return user?.profile?.avatar?.url ?? '/default-avatar.png';
}
```

---

## 2. 競合状態（Race Condition）

**症状**: 間欠的なエラー、タイミング依存の失敗

| パターン | 問題 | 解決 |
|:---|:---|:---|
| 二重送信 | ボタンを複数回クリックで重複リクエスト | 送信中フラグで無効化 |
| TOCTOU | 確認→実行間に状態が変わる | アトミックな更新（CAS / SELECT FOR UPDATE） |
| 非同期レース | 複数の async が同一リソースを変更 | Promise.all → 直列化、または mutex |

```typescript
// Before: 二重送信の危険
async function submitOrder() {
  const result = await api.createOrder(cart);
  router.push('/complete');
}

// After: 送信中フラグで防御
async function submitOrder() {
  if (isSubmitting) return;
  setIsSubmitting(true);
  try {
    const result = await api.createOrder(cart);
    router.push('/complete');
  } finally {
    setIsSubmitting(false);
  }
}
```

---

## 3. サイレント失敗（Silent Failure）

**症状**: エラーなしでデータが保存されない / 処理が完了しない

| パターン | 問題 | 解決 |
|:---|:---|:---|
| 空 catch ブロック | 例外を握りつぶす | ログ出力 + 適切な例外再スロー |
| 戻り値の無視 | 失敗を検知しない | 戻り値を確認、エラーをスロー |
| 非同期の await 忘れ | Promise が未解決のまま | async/await を正しく使用 |

```typescript
// Before: エラーを握りつぶす
try {
  await saveProfile(data);
} catch (e) {
  // 何もしない ← サイレント失敗の原因
}

// After: ログ + 適切なエラーハンドリング
try {
  await saveProfile(data);
} catch (e) {
  logger.error('Profile save failed', { userId, error: e });
  throw new AppError('プロフィールの保存に失敗しました', { cause: e });
}
```

---

## 4. データ型・変換エラー

**症状**: 計算結果がおかしい、型変換で `NaN` や意図しない値

| パターン | Before | After |
|:---|:---|:---|
| 整数変換 | `parseInt(val)` | `parseInt(val, 10)` + NaN チェック |
| 浮動小数点 | `0.1 + 0.2 === 0.3` | `Math.round((0.1 + 0.2) * 10) / 10` |
| 文字列⇔数値 | 暗黙の型強制 | 明示的な変換 + バリデーション |
| 日付のタイムゾーン | `new Date(str)` | `new Date(str + 'Z')` または dayjs/date-fns |

```typescript
// Before: 基数なし parseInt (タコマ橋崩壊の原因と同種)
const quantity = parseInt(req.body.quantity);

// After: 基数明示 + NaN ガード
const raw = parseInt(req.body.quantity, 10);
if (Number.isNaN(raw) || raw < 0) {
  throw new ValidationError('数量は0以上の整数で指定してください');
}
const quantity = raw;
```

---

## 5. 認証・認可エラー

**症状**: `401 Unauthorized`, `403 Forbidden`, 他ユーザーのデータが見える

| パターン | 問題 | 解決 |
|:---|:---|:---|
| 認可チェック漏れ | リソース所有者を検証しない | `WHERE id = :id AND user_id = :userId` |
| トークン検証の不備 | 期限切れトークンを通す | `jwt.verify()` のエラーを適切にハンドル |
| エラーレスポンスの情報漏洩 | 「ユーザーが存在しない」を返す | 「メールアドレスまたはパスワードが違います」に統一 |

```typescript
// Before: 認可チェックなし（IDOR 脆弱性）
async function getDocument(id: string) {
  return db.documents.findById(id); // 誰でも取得可能
}

// After: 所有者確認付き
async function getDocument(id: string, currentUserId: string) {
  const doc = await db.documents.findOne({ id, ownerId: currentUserId });
  if (!doc) throw new NotFoundError('Document not found');
  return doc;
}
```

---

## 6. DB 制約・クエリエラー

**症状**: `UNIQUE constraint failed`, `FK constraint`, デッドロック

| パターン | 問題 | 解決 |
|:---|:---|:---|
| 重複挿入 | UNIQUE 制約違反 | UPSERT または挿入前に存在チェック |
| デッドロック | ロック取得順序が不一致 | テーブルのロック取得順序を統一 |
| N+1 クエリ | ループ内で DB アクセス | JOIN または一括取得に変更 |

```sql
-- Before: デッドロックが起きやすい
-- Transaction A: orders → inventory の順でロック
-- Transaction B: inventory → orders の順でロック（デッドロック）

-- After: 全トランザクションで同じ順序でロック
BEGIN;
SELECT * FROM inventory WHERE product_id = ? FOR UPDATE;  -- 先にinventory
SELECT * FROM orders WHERE id = ? FOR UPDATE;              -- 次にorders
COMMIT;
```

---

## 7. メモリ・パフォーマンス問題

**症状**: メモリリーク、タイムアウト、大量データで失敗

| パターン | 問題 | 解決 |
|:---|:---|:---|
| イベントリスナーの解除忘れ | メモリリーク | `useEffect` の cleanup 関数で解除 |
| 大量データの一括処理 | タイムアウト / OOM | バッチ処理・ページネーション |
| キャッシュ未使用 | 毎回 DB アクセス | Redis キャッシュを追加 |

```typescript
// Before: メモリリーク
useEffect(() => {
  window.addEventListener('resize', handleResize);
  // cleanup なし → コンポーネントアンマウント後もリスナーが残る
}, []);

// After: cleanup で解除
useEffect(() => {
  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize); // cleanup
}, []);
```
