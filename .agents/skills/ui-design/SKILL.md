---
name: ui-design
description: >
  UI デザインの設計・レビュー・改善を、書籍『Refactoring UI』の原則に基づいて支援する。
  視覚的階層、スペーシング、タイポグラフィ、カラー、コンポーネント設計のベストプラクティスを適用。
  Use when user says「UIを改善して」「デザインをレビューして」「配色を決めて」
  「レイアウトを設計して」「コンポーネントを設計して」「UIのベストプラクティスを教えて」
  「スペーシングを修正して」「タイポグラフィを改善して」「カラーパレットを作って」
  「ボタンのスタイルを決めて」「フォームを設計して」「カードデザインを作って」。
metadata:
  author: KC-Prop-Foundry
  version: 1.1.0
  category: development
  based-on: "Refactoring UI (Adam Wathan & Steve Schoger)"
---

# Skill: UI Design（UI 設計・レビュー・改善）

> **デザインは芸術ではなくエンジニアリング — 制約とシステムの中で最適解を見つけよ**

## Instructions

### ワークフロー内の位置

```
要件定義 → [ui-design] → 実装（effective-typescript）→ review
              ↓
         フロントエンド設計
         ・視覚的階層
         ・スペーシングシステム
         ・カラーパレット
         ・コンポーネント設計
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| UI コード（HTML/CSS/TSX） | 既存 UI の改善対象 | React コンポーネント、CSS ファイル |
| ワイヤーフレーム / 要件 | 新規 UI の設計指示 | 「ダッシュボードを設計して」 |
| デザイントークン | 既存のカラー/タイポグラフィ定義 | Tailwind config、CSS 変数 |
| スクリーンショット | UI の問題点の指摘元 | 「この画面を改善して」 |

### 出力

| 出力 | 形式 | 説明 |
|:---|:---|:---|
| 改善提案 | Markdown + コード | 問題点の指摘と具体的な修正案 |
| CSS / デザイントークン | CSS / JSON | カラーパレット、スペーシングスケール |
| コンポーネント設計 | HTML/CSS/TSX | コンポーネントの構造とスタイル |
| レビューレポート | Markdown | UI の品質評価と改善優先度 |

---

## Step 1: 現状分析

対象の UI を以下の 5 つの観点で分析する。

| 観点 | 確認項目 | 参照 |
|:---|:---|:---|
| **視覚的階層** | Primary / Secondary / Tertiary の 3 段階が存在するか | [visual-hierarchy.md](references/visual-hierarchy.md) |
| **スペーシング** | 一貫したスペーシングスケールに従っているか | [spacing-and-layout.md](references/spacing-and-layout.md) |
| **タイポグラフィ** | フォント種類・サイズ・行間が体系的か | [typography-guide.md](references/typography-guide.md) |
| **カラー** | パレットが 3 層（Primary/Neutrals/Supporting）で構成されているか | [color-system.md](references/color-system.md) |
| **コンポーネント** | ボタン・フォーム・カード等が一貫しているか | [component-patterns.md](references/component-patterns.md) |
| **深度・影** | 影のエレベーションシステムがあるか | [depth-images-finishing.md](references/depth-images-finishing.md) §1 |
| **画像・背景** | 画像上テキストのコントラスト、UGC 対応は適切か | [depth-images-finishing.md](references/depth-images-finishing.md) §2 |
| **仕上げ・装飾** | 空の状態、アクセントボーダー、デフォルト強化があるか | [depth-images-finishing.md](references/depth-images-finishing.md) §3 |

**チェックリスト**:
- [ ] ページ内に明確な視覚的階層（3 段階）が存在する
- [ ] スペーシングが制約ベースのスケールに従っている
- [ ] フォントが 2 種類以下に制限されている
- [ ] カラーパレットが体系的に定義されている
- [ ] コンポーネントのスタイルが統一されている
- [ ] 影のエレベーションシステムが一貫している
- [ ] 画像・背景の処理が適切である
- [ ] 仕上げ（空の状態、装飾）が考慮されている

---

## Step 2: 視覚的階層の設計

### 2a. テキスト階層の確立

3 つのレバー（サイズ・色・ウェイト）を組み合わせて階層を作る。

| レイヤー | サイズ | 色 | ウェイト | 用途 |
|:---|:---|:---|:---|:---|
| **Primary** | 大きめ | 濃い色（Neutral 50-200） | Bold / Semibold | 見出し、キー情報 |
| **Secondary** | 標準 | 中間色（Neutral 300-400） | Regular | 説明文、メタデータ |
| **Tertiary** | 小さめ | 薄い色（Neutral 500-600） | Regular / Light | 日付、注釈 |

### 2b. アクション階層の確立

```
Primary Action:   塗りつぶしボタン（1 画面 1-2 個）
Secondary Action: ボーダーボタン / 薄い背景ボタン
Tertiary Action:  テキストリンク
Danger Action:    Red 系カラーボタン（破壊的操作）
```

**チェックリスト**:
- [ ] サイズだけでなく色・ウェイトも活用して階層を作っている
- [ ] ラベルが値より目立っていない
- [ ] Primary Action は 1 画面に 1-2 個に制限されている

---

## Step 3: スペーシングシステムの適用

### 推奨スケール

```
4px — 8px — 12px — 16px — 24px — 32px — 48px — 64px — 96px — 128px
```

### 適用ルール

1. **関連要素は近く** — ラベルとフィールド: 8px
2. **グループ内**: 12-16px
3. **グループ間**: 24-32px
4. **セクション間**: 48-64px
5. **ページレベル**: 96-128px

### テキスト幅の制限

```css
/* 本文の最大幅 */
.prose { max-width: 65ch; }  /* 約 45-75 文字 */
```

**チェックリスト**:
- [ ] 任意のピクセル値ではなくスケールの値を使っている
- [ ] 関連要素間 < 非関連要素間 の距離関係が守られている
- [ ] テキスト行幅が 45-75 文字に収まっている

---

## Step 4: カラーシステムの設計

### 4a. 3 層パレットの構築

| 層 | 役割 | 段階数 |
|:---|:---|:---|
| **Primary** | ブランドカラー、主要アクション | 8-10 段階 |
| **Neutrals** | テキスト、背景、ボーダー | 8-10 段階 |
| **Supporting** | エラー・警告・成功・情報 | 各 8-10 段階 |

### 4b. HSL での定義

```css
:root {
  /* Primary — Blue 例 */
  --primary-900: hsl(205, 100%, 21%);  /* #003E6B — 最暗 */
  --primary-700: hsl(205, 82%, 33%);   /* #0F609B */
  --primary-500: hsl(205, 67%, 45%);   /* #2680C2 — Base */
  --primary-300: hsl(205, 84%, 74%);   /* #84C5F4 */
  --primary-100: hsl(205, 79%, 92%);   /* #DCEEFB — 最明 */

  /* Neutrals — Blue Grey */
  --neutral-900: hsl(209, 61%, 16%);   /* #102A43 — テキスト */
  --neutral-700: hsl(209, 34%, 30%);   /* #334E68 */
  --neutral-500: hsl(210, 22%, 49%);   /* #627D98 */
  --neutral-300: hsl(210, 31%, 80%);   /* #BCCCDC — ボーダー */
  --neutral-100: hsl(210, 36%, 96%);   /* #F0F4F8 — 背景 */
}
```

### 4c. アクセシビリティ確認

- テキストと背景: コントラスト比 **4.5:1 以上**（WCAG AA）
- 大きいテキスト（18px+ bold, 24px+）: **3:1 以上**
- 色だけで情報を伝えない

**チェックリスト**:
- [ ] 3 層パレットが定義されている
- [ ] 各色系統に 8-10 段階のバリエーションがある
- [ ] コントラスト比が WCAG AA を満たしている
- [ ] セマンティックカラー（Red/Yellow/Green/Blue）が用意されている

---

## Step 5: コンポーネントの設計・改善

### 対象コンポーネント

| コンポーネント | 主要な設計判断 | 参照 |
|:---|:---|:---|
| **ボタン** | 階層（Primary/Secondary/Tertiary）、サイズ、角丸 | [component-patterns.md](references/component-patterns.md) |
| **フォーム** | 入力スタイル、ラベル配置、バリデーション表示 | [component-patterns.md](references/component-patterns.md) |
| **カード** | 影 vs ボーダー、画像配置、情報構造 | [component-patterns.md](references/component-patterns.md) |
| **テーブル** | ストライプ、数値配置、ヘッダースタイル | [component-patterns.md](references/component-patterns.md) |
| **ナビゲーション** | 水平 vs 垂直、アクティブ表示 | [component-patterns.md](references/component-patterns.md) |
| **アラート** | スタイル、アクセントボーダー位置 | [component-patterns.md](references/component-patterns.md) |
| **ツールチップ** | モバイルではみ出し防止、長いラベル省略、スクロール時消去 | [component-patterns.md](references/component-patterns.md) §9 |
| **アイコン** | サイズ統一、色の一貫性、ラベル併用 | [icon-catalog.md](references/icon-catalog.md) |

**チェックリスト**:
- [ ] ボタンに Primary / Secondary / Tertiary の階層がある
- [ ] フォームフィールドのスタイルが統一されている
- [ ] テーブルの数値列が右揃え + 等幅数字になっている
- [ ] アイコンが統一サイズで、ラベルが併用されている

---

## Step 6: 深度と影（Depth & Shadow）

詳細は [depth-images-finishing.md](references/depth-images-finishing.md) §1 を参照。

### 光源の原則

「光は上から来る」を統一原則とする。

- **Raised 要素**: 上辺を明るく（`inset 0 1px 0` で明色）、下に影
- **Inset 要素**: 上辺に影（`inset 0 2px 2px` で暗色）、下辺を明るく
- 手動で色を選択する（半透明白は彩度を殺すため避ける）

### box-shadow の 5 段階エレベーション

```css
:root {
  --shadow-sm:  0 1px 3px hsla(0, 0%, 0%, 0.2);
  --shadow-md:  0 4px 6px hsla(0, 0%, 0%, 0.1),
                0 2px 4px hsla(0, 0%, 0%, 0.06);
  --shadow-lg:  0 5px 15px hsla(0, 0%, 0%, 0.1),
                0 4px 6px hsla(0, 0%, 0%, 0.07);
  --shadow-xl:  0 15px 35px hsla(0, 0%, 0%, 0.2);
  --shadow-2xl: 0 20px 25px hsla(0, 0%, 0%, 0.15),
                0 10px 10px hsla(0, 0%, 0%, 0.04);
}
```

| 影レベル | 用途 | インタラクション |
|:---|:---|:---|
| **sm** | ボタン、小さなインタラクティブ要素 | クリック時に除去 |
| **md** | カード、ドロップダウン | ホバーで lg へ |
| **lg** | ポップオーバー、ホバー時のカード | — |
| **xl** | モーダルダイアログ | — |
| **2xl** | 最前面の大きなモーダル | — |

### 二重シャドウ（質の高い影）

```css
/* 直接光（大きく柔らかい）+ 環境光（タイトで暗い）の 2 層構成 */
box-shadow:
  0 4px 6px rgba(0, 0, 0, 0.07),
  0 5px 15px rgba(0, 0, 0, 0.1);
```

エレベーションが高いほど、環境光（2 つ目）の影は薄くする。

### フラットデザインでの深度表現

- **色**: 背景より明るい → 手前、暗い → 奥
- **ソリッドシャドウ**: `box-shadow: 0 3px 0 hsl(220, 7%, 83%);`（blur なし）
- **重畳**: 要素を背景の境界をまたいで配置し、レイヤー感を演出

**チェックリスト**:
- [ ] 影が 5 段階のエレベーションシステムに従っている
- [ ] 光源の方向（上から）が統一されている
- [ ] インタラクション時に影が変化する（ホバー↑、クリック↓）
- [ ] 質の高い影に二重シャドウを使っている

---

## Step 7: 画像とコンテンツ

詳細は [depth-images-finishing.md](references/depth-images-finishing.md) §2 を参照。

### テキスト × 背景画像のコントラスト

背景画像上のテキストが読みにくい場合の対処法:

| 手法 | 実装 | 推奨場面 |
|:---|:---|:---|
| **半透明オーバーレイ** | `background-color: hsla(0,0%,0%,.55)` | ヒーローセクション |
| **画像コントラスト低減** | `brightness: +40%; contrast: -70%` | 写真の印象を保ちたい場合 |
| **画像カラー化** | desaturate + multiply ブレンド | ブランドカラー統一 |
| **テキストシャドウ** | `text-shadow: 0 0 50px hsla(0,0%,0%,.4)` | 部分的にコントラストを補強 |

### 意図されたサイズ

- アイコンを拡大しない（16-24px 用を 3-4 倍 → chunky）。大きく見せたい場合は背景付きで配置
- スクリーンショットを縮小しない（70% 縮小 → テキスト不可読）。部分 SS か簡略化イラストを使用

### UGC（ユーザーアップロードコンテンツ）

```css
.user-image {
  object-fit: cover;
  box-shadow: inset 0 0 0 1px hsla(0, 0%, 0%, 0.1); /* にじみ防止 */
}
```

**チェックリスト**:
- [ ] 背景画像上のテキストに十分なコントラストがある
- [ ] アイコンが意図されたサイズで使用されている
- [ ] UGC 画像が `object-fit: cover` で制御されている

---

## Step 8: 仕上げのテクニック

詳細は [depth-images-finishing.md](references/depth-images-finishing.md) §3 を参照。

### デフォルトの強化

既存要素のアップグレードだけで印象が変わる:
- 箇条書き → アイコン（チェックマーク、矢印、コンテンツ固有アイコン）
- チェックボックス / ラジオ → ブランドカラーのカスタムスタイル or 選択可能カード
- 引用 → 大きなクォーテーションマーク + ブランドカラー

### アクセントボーダー

```css
.card { border-top: 4px solid var(--primary-500); }
.alert-warning { border-left: 4px solid var(--yellow-500); }
```

カード上端、ナビアクティブ、アラート側面、見出し下、ページ上端に配置。

### 空の状態（Empty States）

コンテンツがない画面は**ユーザーの第一印象**。必ずデザインする:
1. イラスト / アイコン（注目を引く）
2. CTA ボタン（次のアクションを促す）
3. 補助 UI（タブ、フィルター）はコンテンツ作成後に表示

### ボーダーの代替

ボーダーの多用はデザインをビジーにする。代わりに:
- **box-shadow**: ボーダーより柔らかい区切り
- **背景色の違い**: 隣接要素を自然に区別
- **余白の追加**: UI 要素を追加せず分離

**チェックリスト**:
- [ ] デフォルト UI 要素が強化されている
- [ ] アクセントボーダーが効果的に配置されている
- [ ] 空の状態がデザインされている（イラスト + CTA）
- [ ] ボーダーの代わりに影・背景色・余白を検討した

---

## Step 9: 出力とレビュー

最終成果物を以下の形式で出力する。

### 改善提案の場合

```markdown
## UI 改善提案

### 問題点
1. [視覚的階層] テキストの階層が不明確（全要素が同じウェイト・色）
2. [スペーシング] margin/padding に一貫性がない（13px, 17px 等の任意値）
3. [カラー] ダークテキストのコントラスト比が不足

### 改善案
（具体的な CSS / コード変更を提示）

### 改善後の効果
- 視認性の向上
- 一貫性のある見た目
- アクセシビリティの改善
```

### デザインシステムの場合

```markdown
## デザイントークン

### Colors
（CSS カスタムプロパティで定義）

### Typography
（フォント・サイズ・行間のスケール）

### Spacing
（スペーシングスケール）

### Shadows
（box-shadow の段階定義）
```

**最終チェックリスト**:
- [ ] 8 つの観点（階層・スペーシング・タイポグラフィ・カラー・コンポーネント・深度・画像・仕上げ）すべてを検討した
- [ ] 具体的なコード / CSS で修正案を提示した
- [ ] アクセシビリティ（コントラスト比）を確認した
- [ ] 改善の優先度を明示した

---

## Examples

### Example 1: 既存 UI のレビューと改善

```
「このダッシュボードの UI をレビューして改善案を出して」

→ Step 1 で 5 観点の分析を実施
→ 問題点を優先度付きで列挙
→ 各問題に対する具体的な CSS 修正案を提示
```

### Example 2: カラーパレットの設計

```
「新規プロジェクトのカラーパレットを設計して。ブランドカラーは青系」

→ Step 4 で HSL ベースの 3 層パレットを生成
→ Primary（Blue 10段階）/ Neutrals（Blue Grey 10段階）/ Supporting（Red, Yellow, Green 各10段階）
→ CSS カスタムプロパティとして出力
→ コントラスト比の確認
```

### Example 3: コンポーネント設計

```
「ボタンとフォームのコンポーネントスタイルを設計して」

→ Step 2b でボタン階層を設計
→ Step 5 でフォームスタイルを選定
→ HTML/CSS のコード例を出力
→ レスポンシブ対応を含む
```

### Example 4: タイポグラフィスケールの設計

```
「アプリケーション用のタイポグラフィシステムを作って」

→ Step 3 でスペーシングスケールも同時に設計
→ フォント選定（システムフォント or カスタムフォント）
→ サイズスケール、行間、文字間の定義
→ CSS / Tailwind 設定として出力
```

### Example 5: ランディングページのヒーローセクション設計

```
「ヒーロー画像の上にテキストを載せたいが読みにくい。改善して」

→ Step 7 で背景画像のコントラスト対策を実施
→ 半透明オーバーレイ or テキストシャドウを適用
→ Step 2 でテキスト階層を設計
→ Step 8 でアクセントボーダー・背景装飾の仕上げ
```

### Example 6: 空の状態と仕上げの改善

```
「アプリの初回ログイン画面が殺風景。デザインを改善して」

→ Step 8 で空の状態をデザイン（イラスト + CTA）
→ デフォルト要素の強化（アイコン付き箇条書き、カスタムチェックボックス）
→ アクセントボーダーの配置
→ ボーダーの代替を検討（shadow / 背景色 / 余白）
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| すべてが同じに見える | 視覚的階層が不足 | Step 2 で 3 レイヤーの差を大きくする |
| 色の組み合わせが悪い | パレットが体系的でない | Step 4 で HSL ベースの 10 段階を再設計 |
| テキストが読みにくい | コントラスト比不足 or 行間不足 | コントラスト比 4.5:1 以上、line-height 1.5 以上 |
| 余白がバラバラに見える | 任意の数値を使っている | Step 3 のスペーシングスケールに統一 |
| ボタンが多すぎて迷う | アクション階層が不明確 | Primary は 1 画面 1-2 個に制限 |
| カードがのっぺりしている | 深度表現がない | Step 6 の shadow 段階を適用 |
| フォームが使いにくい | ラベル配置やバリデーション表示が不適切 | Step 5 のフォーム設計パターンを参照 |
| アイコンが浮いている | サイズ・色がテキストと不一致 | [icon-catalog.md](references/icon-catalog.md) のサイズ指針を適用 |
| 画像上のテキストが読めない | 背景画像の明暗が不均一 | Step 7 のオーバーレイ / テキストシャドウを適用 |
| 画面が殺風景に見える | 仕上げが不足 | Step 8 のアクセントボーダー / デフォルト強化を適用 |
| 空の状態が放置されている | 未デザイン | Step 8 でイラスト + CTA のデザインを追加 |
| 影がリアルに見えない | 単一シャドウのみ使用 | Step 6 の二重シャドウ（直接光 + 環境光）を適用 |

---

## References

| ファイル | 内容 |
|:---|:---|
| [visual-hierarchy.md](references/visual-hierarchy.md) | 視覚的階層の詳細パターン |
| [spacing-and-layout.md](references/spacing-and-layout.md) | スペーシングシステム + レイアウト原則 |
| [typography-guide.md](references/typography-guide.md) | タイポグラフィの選択基準 + スケール |
| [color-system.md](references/color-system.md) | HSL パレット設計 + アクセシビリティ |
| [component-patterns.md](references/component-patterns.md) | コンポーネント設計原則 + バリエーション |
| [icon-catalog.md](references/icon-catalog.md) | 200 SVG アイコン一覧 + CSS カラーサンプル |
| [depth-images-finishing.md](references/depth-images-finishing.md) | 深度・光源模倣・画像処理・仕上げテクニック |

---

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **effective-typescript** | 後続 | UI 設計に基づく React/TSX コンポーネントの実装 |
| **review** | 検証 | UI の品質レビュー、アクセシビリティ検証 |
| **diagram** | 補助 | ワイヤーフレームやフロー図の作成 |
