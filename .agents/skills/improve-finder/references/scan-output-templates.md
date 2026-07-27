# scan-output-templates.md

> improve-finder Phase 6 の出力テンプレート集。
> 「改善機会レポート」と「improve-flow 引き継ぎパック」の 2 種類のフォーマットを提供する。

---

## テンプレート 1: 改善機会レポート（全体版）

```markdown
## 改善機会レポート
- **対象**: `<パス>`
- **言語 / スタック**: <言語 + フレームワーク>
- **スキャン日時**: YYYY-MM-DD
- **スキャン次元**: <全7次元 / フォーカス: architecture, type-safety 等>

---

### スキャンサマリー

| 優先度 | 件数 | 代表的な改善機会 |
|:---|:---|:---|
| P1（今すぐ） | N | N+1 クエリ解消、WCAG AA 修正 |
| P2（次に） | N | any 除去、責務分離 |
| P3（余力で） | N | 命名改善、コメント追加 |
| P4（保留） | N | 全体アーキリファクタリング |

---

### P1 改善機会（今すぐ対応）

#### IMP-001: <タイトル>
- **ファイル**: `src/xxx.ts:42`
- **次元**: パフォーマンス（N+1 問題）
- **現状**: `for (const user of users) { await db.orders.findMany({ where: { userId: user.id } }) }` — ループ内クエリ
- **改善方向**: `db.orders.findMany({ where: { userId: { in: users.map(u => u.id) } } })` でバッチ取得
- **期待効果**: クエリ数が users.length → 1 に削減。100 ユーザー時に 100 クエリ → 1 クエリ
- **引き継ぎ**: improve-flow Phase 5 のコード改善実装で対応

#### IMP-002: <タイトル>
- **ファイル**: `src/components/Button.tsx:15`
- **次元**: UX/UI（WCAG AA コントラスト比）
- **現状**: `color: #999999` on `background: #ffffff` — コントラスト比 2.8:1（AA 基準 4.5:1 未達）
- **改善方向**: `color: #595959` に変更（コントラスト比 7.0:1 — AA 達成）
- **期待効果**: WCAG AA 準拠、視覚的弱者へのアクセシビリティ確保
- **引き継ぎ**: improve-flow Phase 4 の UI/ビジュアル改善実装で対応

---

### P2 改善機会（次のサイクルで計画的に対応）

#### IMP-003: <タイトル>
- **ファイル**: `src/features/order/orderService.ts`
- **次元**: 型安全性（boolean フラグ地獄）
- **現状**: `isLoading: boolean; isError: boolean; isSuccess: boolean` の 3 フラグが共存
- **改善方向**: `type OrderState = { status: 'idle' } | { status: 'loading' } | { status: 'error'; error: Error } | { status: 'success'; data: Order }` タグ付きユニオンに移行
- **期待効果**: 無効な状態（`isLoading: true` かつ `isSuccess: true` 等）が型レベルで不可能に
- **引き継ぎ**: improve-flow Phase 5 のコード改善実装で対応

---

### P3 改善機会（余力があれば対応）

- `src/utils/helpers.ts:L8` — `tmp` 変数を `temporaryBuffer` に改名（可読性）
- `src/components/Modal.tsx:L33` — `// TODO: handle edge case` を実装またはトラッキング（観測可能性）

---

### P4 保留（このサイクルでは対応しない）

- 全体的な状態管理ライブラリの Zustand → Jotai 移行（High Effort、Medium Impact）— 将来のアーキ検討課題として記録

---

### 既知の改善課題（TODO / FIXME 集計）

| ファイル | 行 | コメント |
|:---|:---|:---|
| `src/auth/token.ts` | L45 | `// TODO: JWT expiry validation` |
| `src/api/client.ts` | L89 | `// FIXME: retry logic missing` |

```

---

## テンプレート 2: improve-flow 引き継ぎパック

improve-finder の最終出力として improve-flow Phase 0 に渡す引き継ぎ情報。

```markdown
## improve-flow 引き継ぎパック

> improve-finder スキャン結果を improve-flow Phase 0 の入力として使用する

### 改善対象
- **ファイル / 機能**: `src/features/order/` ディレクトリ
- **改善ドメイン**: コード品質（型安全性）+ パフォーマンス

### 成功基準（Before/After 比較用）

| 基準 | Before | After 目標 |
|:---|:---|:---|
| N+1 クエリ数 | 3 箇所 | 0 箇所 |
| `any` 使用数 | 12 件 | 0 件 |
| WCAG AA 違反数 | 8 箇所 | 0 箇所 |
| テストなしのサービス関数 | 5 件 | 0 件 |

### P1 課題リスト（improve-flow で最優先対応）

1. **IMP-001**: N+1 クエリ — `src/api/userOrders.ts:42`
2. **IMP-002**: WCAG コントラスト比 — `src/components/Button.tsx:15`, `Card.tsx:8`（2 箇所）
3. **IMP-004**: 未テストのビジネスロジック — `src/services/paymentService.ts`

### P2 課題リスト（improve-flow 次サイクル以降）

1. **IMP-003**: boolean フラグ → タグ付きユニオン — `src/features/order/orderService.ts`
2. **IMP-005**: 責務過多コンポーネント分割 — `src/pages/Dashboard.tsx`（850 行）

### フェーズスキップ判定（improve-flow Phase 0 用）

| Phase | スキップ判定 | 理由 |
|:---|:---|:---|
| Phase 1（現状診断）| スキップ可能 | improve-finder の診断結果をそのまま使用 |
| Phase 4（UI/ビジュアル実装）| 簡略化 | IMP-002 のみ（全体的な UI 刷新ではない）|
| Phase 5（コード改善）| 必須 | IMP-001・IMP-003 のコード変更が必要 |

```

---

## テンプレート 3: フォーカス次元スキャン結果（軽量版）

特定次元のみをスキャンした場合の簡略レポート。

```markdown
## 改善機会スキャン結果（フォーカス: <次元名>）
- **対象**: `<パス>`
- **スキャン次元**: <次元名>
- **スキャン日時**: YYYY-MM-DD

### 発見サマリー

- P1（今すぐ）: N 件
- P2（次に）: N 件
- P3（余力で）: N 件

### 改善機会一覧

| ID | ファイル:行 | 改善パターン | 優先度 | 期待効果 |
|:---|:---|:---|:---|:---|
| IMP-001 | `src/xxx.ts:42` | N+1 クエリ | P1 | クエリ数 10 → 1 |
| IMP-002 | `src/yyy.ts:15` | メモ化欠如 | P1 | 不要な再レンダリング削減 |
| IMP-003 | `src/zzz.ts:88` | 命名不明確 (`tmp`) | P3 | 可読性向上 |

### improve-flow 引き継ぎ推奨
- P1 の <N> 件を improve-flow Phase 5（コード改善実装）に引き継ぐ
- 成功基準: <具体的なBefore/After基準>
```

---

## 同一パターングルーピングの例

同じ改善パターンが複数箇所で発見された場合の記録方法:

```markdown
#### `any` 使用（12 箇所）— IMP-010 グループ
- `src/api/client.ts:L15, L32, L89`
- `src/features/auth/authSlice.ts:L44, L78`
- `src/components/Table.tsx:L12, L23, L45, L67, L89, L102, L134`

**共通の改善方向**: 各 `any` を具体型または `unknown` + 型ガードに置換
**推奨アプローチ**: effective-typescript スキルで一括対応
**優先度**: P2（High Impact, High Effort — 12 件の一括置換）
```
