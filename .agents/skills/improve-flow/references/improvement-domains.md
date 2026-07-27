# 改善ドメイン別 診断観点・改善パターン

> improve-flow の Phase 1 診断と Phase 3 設計で参照する、ドメイン別の診断チェックリストと改善パターン集

---

## UX 改善ドメイン

### 診断観点（Phase 1: ux-psychology 診断モード）

| Laws of UX | 診断する症状 | 検出方法 |
|:---|:---|:---|
| **Miller's Law** | 1 画面に情報が多すぎる（7±2 を超えるアイテム数） | 画面内の独立要素を数える |
| **Hick's Law** | 選択肢が多すぎて決断できない | ナビゲーション・フィルタの選択肢数を確認 |
| **Jakob's Law** | 他サービスと操作が異なって混乱する | 業界標準 UI パターンとの比較 |
| **Fitts's Law** | ボタン・リンクが小さすぎてタップできない | タッチターゲットサイズを計測（44px 基準） |
| **Postel's Law** | バリデーションが厳格すぎてユーザーが弾かれる | フォームエラーの発生パターンを観察 |
| **Peak-End Rule** | 完了・エラー時の体験が平坦（感情設計なし） | フロー終端の演出を確認 |
| **Von Restorff Effect** | 重要な情報が埋もれて気づかれない | 重要要素の視覚的強調度を確認 |
| **Doherty Threshold** | クリック後の反応が遅い（400ms 超） | 応答時間を計測 |
| **Tesler's Law** | ユーザーに複雑さを押しつけている | 操作ステップ数を数える |
| **Aesthetic-Usability Effect** | 見た目が古くて「使えない」と思わせている | 視覚的完成度を評価 |

### 改善パターン（Phase 3: ux-psychology 設計モード）

| 問題 | 改善パターン | 実装方針 |
|:---|:---|:---|
| 情報過多 | チャンキング + 段階的開示 | アコーディオン・タブ・ページネーションで分割 |
| 選択肢過多 | デフォルト値設定 + フィルタ | 推奨を1つ強調表示、残りを折りたたむ |
| タッチ困難 | タッチターゲット拡大 | padding 拡大（最小 44×44px）、Icon ボタンに label 追加 |
| 厳格バリデーション | リアルタイム許容バリデーション | 入力中は寛容→サブミット時に正確、エラーメッセージを具体的に |
| 完了体験なし | ポジティブピーク設計 | 完了アニメーション・成功メッセージ・次アクション提示 |
| 重要情報の埋没 | 視覚的強調 | カラー・サイズ・位置で差別化（Von Restorff 適用） |

---

## UI/ビジュアル改善ドメイン

### 診断観点（Phase 1: ui-design 診断）

| 観点 | 問題パターン | 検出方法 |
|:---|:---|:---|
| **視覚的階層** | 全テキストが同じサイズ・色で階層なし | フォントサイズ・ウェイト・カラーの種類数を確認 |
| **カラーシステム** | ハードコード色値（`#3B82F6` 等）が散在 | コード検索で hex/rgb 値を探す |
| **コントラスト** | 文字色と背景色のコントラスト比が 4.5:1 未満 | DevTools の contrast checker で確認 |
| **スペーシング** | margin/padding がバラバラ（8, 10, 13, 15px 等） | 使用している spacing 値を列挙 |
| **コンポーネント統一性** | 同じ役割のボタンが複数スタイルで存在 | 同機能コンポーネントを比較 |
| **影のエレベーション** | 影が一種類のみ or 使われていない | z-index 階層と shadow 値を確認 |
| **空の状態** | リストが空の時に何も表示されない | 空データ時の表示を確認 |
| **レスポンシブ** | 固定幅（`width: 800px`）でモバイルで崩れる | モバイル表示を確認 |

### 改善パターン（Phase 4: front-design + ui-design）

| 問題 | 改善パターン | CSS 実装 |
|:---|:---|:---|
| ハードコード色 | CSS 変数化 | `color: var(--color-primary-500)` に置換 |
| コントラスト不足 | カラー値の調整 | WCAG AA 基準（4.5:1）を満たす値に変更 |
| スペーシング不統一 | 4px ベーススケール導入 | `margin: var(--space-4)` に統一 |
| 視覚的階層なし | 3段階ヒエラルキー設計 | `font-size: var(--text-xl)` / `text-base` / `text-sm` で差別化 |
| 空の状態なし | EmptyState コンポーネント | `<EmptyState message="..." action="..." />` を実装 |

---

## コード品質改善ドメイン

### 診断観点（Phase 1: bug-finder）

| 問題カテゴリ | 診断指標 | 優先度 |
|:---|:---|:---|
| **型安全性** | `any` 使用箇所数、`enum` 使用箇所数、型アサーション（as）数 | High |
| **状態管理** | boolean フラグの複数組み合わせ（isLoading + isError + data） | High |
| **Null 安全性** | オプショナルチェーン未使用、null チェック漏れ | High |
| **エラーハンドリング** | try/catch の空 catch、エラーの握りつぶし | High |
| **パブリック API** | 戻り値型の省略、引数型の any | Medium |
| **循環依存** | A→B→A の依存関係 | Medium |
| **デッドコード** | 未使用関数・変数・型 | Low |
| **マジックナンバー** | 意味不明の数値リテラル（`if (status === 3)` 等） | Low |

### 改善パターン（Phase 5: effective-typescript）

| 問題 | Before（問題コード） | After（改善コード） |
|:---|:---|:---|
| boolean フラグ状態 | `{ isLoading: boolean; error: Error \| null; data: T \| null }` | `type State<T> = \| { status: 'loading' } \| { status: 'error'; error: Error } \| { status: 'success'; data: T }` |
| enum 使用 | `enum Status { Active, Inactive, Pending }` | `type Status = 'active' \| 'inactive' \| 'pending'` |
| any 使用 | `function parse(data: any): Result` | `function parse(data: unknown): Result { if (!isResult(data)) throw new Error(...); return data; }` |
| 型アサーション乱用 | `const user = response as User` | `function isUser(v: unknown): v is User { return ... }; if (isUser(response)) { ... }` |
| never 網羅性なし | `switch (status) { case 'a': ... case 'b': ... }` | `switch (status) { case 'a': ... case 'b': ... default: const _: never = status; }` |

---

## パフォーマンス改善ドメイン

### 診断観点（Phase 1: bug-finder パフォーマンスモード）

| 問題 | 症状 | 診断方法 |
|:---|:---|:---|
| **N+1 レンダリング** | 親コンポーネント変化で子が全再レンダリング | React DevTools Profiler |
| **不要な再レンダリング** | props が変わっていないのにレンダリング発生 | `why-did-you-render` |
| **メモ化漏れ** | 重い計算が毎レンダリング実行 | `console.time` で計測 |
| **大量データの一括表示** | 1000+ アイテムを一度に DOM に出力 | DOM ノード数を確認 |
| **バンドルサイズ** | 初期ロードで全コードを読み込む | `next/bundle-analyzer` で確認 |

### 改善パターン（Phase 5: effective-typescript + コード改善）

| 問題 | 改善手法 | 実装 |
|:---|:---|:---|
| 親コンポーネント変化で子再レンダリング | React.memo | `export const Child = React.memo(({ prop }) => ...)` |
| 重い計算の毎回実行 | useMemo | `const result = useMemo(() => heavyCalc(data), [data])` |
| コールバック再生成 | useCallback | `const handler = useCallback(() => ..., [dep])` |
| 大量データ表示 | 仮想スクロール | `react-virtual` または `react-window` を使用 |
| バンドルサイズ肥大 | Dynamic import | `const Chart = dynamic(() => import('./Chart'), { ssr: false })` |

---

## アクセシビリティ改善ドメイン

### 診断観点（Phase 1: UI/ビジュアル診断）

| WCAG 項目 | 問題パターン | 基準 |
|:---|:---|:---|
| **1.4.3 コントラスト** | テキスト色と背景色のコントラスト不足 | 4.5:1 以上（通常テキスト）|
| **1.4.11 非テキストのコントラスト** | UI コンポーネントのコントラスト不足 | 3:1 以上 |
| **2.1.1 キーボード** | キーボードのみで操作できない | Tab + Enter/Space で全機能操作可能 |
| **2.4.7 フォーカス可視** | フォーカスが見えない（outline: none） | focus-visible スタイルあり |
| **4.1.2 名前・役割・値** | ボタン・リンクに aria-label なし | `<button aria-label="閉じる">` 等 |
| **1.3.1 情報と関係性** | セマンティック HTML 未使用 | `<div>` → `<nav>`, `<main>`, `<button>` 等 |
| **2.3.3 モーション** | prefers-reduced-motion 未対応 | `@media (prefers-reduced-motion: reduce)` |

### 改善パターン（Phase 4-5: 実装）

```css
/* コントラスト改善 */
:root {
  --color-text-primary: #111827;     /* 背景白に対して 16:1 */
  --color-text-secondary: #4B5563;   /* 背景白に対して 7:1 */
  --color-text-disabled: #9CA3AF;    /* AA準拠の最低限 */
}

/* フォーカス表示 */
:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

/* モーション対応 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```
