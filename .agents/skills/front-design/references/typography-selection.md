# フォント選定・ペアリングガイド

> サイトのトーンに合ったフォント選び、日本語対応、レスポンシブなタイプスケールの設計指針。

---

## トーン別フォント推薦（欧文）

| トーン | 見出し向き | 本文向き | 特徴 |
|:---|:---|:---|:---|
| 先進的・テック | Outfit / Space Grotesk | Inter / DM Sans | 幾何学的で端正。SaaS・スタートアップに最適 |
| エレガント・高級 | Playfair Display / Cormorant | Lora / Source Serif 4 | セリフ体の繊細さが高級感を演出 |
| 親しみやすい・カジュアル | Nunito / Quicksand | Mulish / Rubik | 丸みのあるジオメトリックサンセリフ |
| 力強い・大胆 | Bebas Neue / Oswald | Roboto / Barlow | コンデンス体でインパクトを出す |
| クリーン・ニュートラル | Plus Jakarta Sans / Figtree | Inter / Noto Sans | 癖がなく汎用性が高い |
| レトロ・個性的 | Fraunces / Syne | Literata / Atkinson Hyperlegible | 独自の字形で差別化 |

## 日本語フォント推薦

| フォント名 | 分類 | 特徴 | 推奨用途 |
|:---|:---|:---|:---|
| **Noto Sans JP** | ゴシック | Google 提供。ウェイト7種。最も汎用的 | 本文・見出し両方 |
| **Zen Kaku Gothic New** | ゴシック | 柔らかく温かみのある字形 | コーポレート・教育系 |
| **BIZ UDGothic** | UDゴシック | ユニバーサルデザイン。可読性最高 | 官公庁・アクセシビリティ重視 |
| **M PLUS 1p** | ゴシック | 丸みが強く親しみやすい | カジュアル・EC |
| **Shippori Mincho** | 明朝 | 端正で伝統的な明朝体 | 和食・旅館・ブランド |
| **Zen Old Mincho** | 明朝 | クラシカルで品格がある | 出版・高級ブランド |
| **Zen Maru Gothic** | 丸ゴシック | 丸みが強く柔和な印象 | 子供向け・福祉 |
| **Kiwi Maru** | 丸ゴシック | 手書き感のある柔らかさ | カフェ・ハンドメイド |

## 見出し×本文 ペアリング例

| # | 見出し | 本文 | トーン | 適合業種 |
|:---|:---|:---|:---|:---|
| 1 | **Space Grotesk** | Inter | 先進的・クリーン | SaaS / テック |
| 2 | **Playfair Display** | Source Serif 4 | エレガント・格調 | ホテル / ジュエリー |
| 3 | **Bebas Neue** | Barlow | 大胆・力強い | スポーツ / メディア |
| 4 | **Outfit** | DM Sans | モダン・洗練 | デザインスタジオ |
| 5 | **Nunito** | Mulish | 親しみやすい | 教育 / 子供向け |
| 6 | **Plus Jakarta Sans** | Noto Sans JP | ニュートラル | コーポレート全般 |
| 7 | **Fraunces** | Literata | 個性的・レトロ | カフェ / クラフト |
| 8 | **Cormorant** | Lora | 文学的・品格 | 出版 / 文化施設 |

## タイプスケール（Modular Scale）

`clamp()` を使ったフルードタイポグラフィで、ビューポートに応じて滑らかにサイズを変化させる。

```css
:root {
  /* ベース: 16px (320px) → 18px (1280px) */
  --text-base: clamp(1rem, 0.95rem + 0.25vw, 1.125rem);

  /* スケール比: Major Third (1.25) */
  --text-sm:   clamp(0.8rem,   0.76rem + 0.2vw,  0.889rem);
  --text-base: clamp(1rem,     0.95rem + 0.25vw,  1.125rem);
  --text-lg:   clamp(1.25rem,  1.15rem + 0.5vw,   1.406rem);
  --text-xl:   clamp(1.563rem, 1.38rem + 0.9vw,   1.758rem);
  --text-2xl:  clamp(1.953rem, 1.65rem + 1.5vw,   2.197rem);
  --text-3xl:  clamp(2.441rem, 1.95rem + 2.4vw,   2.747rem);
  --text-4xl:  clamp(3.052rem, 2.3rem  + 3.7vw,   3.433rem);
}

body {
  font-size: var(--text-base);
}

h1 { font-size: var(--text-4xl); }
h2 { font-size: var(--text-3xl); }
h3 { font-size: var(--text-2xl); }
h4 { font-size: var(--text-xl); }
h5 { font-size: var(--text-lg); }
h6 { font-size: var(--text-base); font-weight: 600; }
```

## line-height / letter-spacing ベストプラクティス

| 要素 | line-height | letter-spacing | 備考 |
|:---|:---|:---|:---|
| 本文（欧文） | `1.5` 〜 `1.7` | `normal` | WCAGでは1.5以上を推奨 |
| 本文（日本語） | `1.7` 〜 `2.0` | `0.04em` 〜 `0.08em` | 日本語は行間を広めに取る |
| 見出し（大） | `1.1` 〜 `1.2` | `-0.02em` 〜 `-0.01em` | 大きい文字はタイトに詰める |
| 見出し（中） | `1.2` 〜 `1.3` | `0` 〜 `0.01em` | |
| キャプション・注釈 | `1.4` 〜 `1.5` | `0.02em` | 小さい文字はやや広げる |
| 大文字ラベル | `1.0` | `0.05em` 〜 `0.1em` | オールキャップスは必ず広げる |

```css
body {
  line-height: 1.7;                 /* 日本語対応 */
  letter-spacing: 0.04em;          /* 日本語の読みやすさ向上 */
  font-feature-settings: "palt";   /* プロポーショナル詰め */
}

h1, h2, h3 {
  line-height: 1.2;
  letter-spacing: -0.01em;
}

.label-caps {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: var(--text-sm);
}
```

## @font-face / @import の最適化

### 推奨: preconnect + link で読み込み

```html
<!-- Google Fonts の場合 -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
```

### セルフホスティングの場合

```css
@font-face {
  font-family: 'Inter';
  src: url('/fonts/Inter-Variable.woff2') format('woff2');
  font-weight: 100 900;           /* 可変フォント */
  font-display: swap;             /* FOUT を許容し表示を速く */
  unicode-range: U+0000-00FF;     /* ラテン文字のみ先行ロード */
}
```

### @import は避ける

```css
/* 非推奨: レンダリングブロッキングの原因になる */
@import url('https://fonts.googleapis.com/css2?family=Inter&display=swap');

/* 推奨: HTML の <link> で読み込む（上記参照） */
```

## 日本語Webフォントの注意点

### ファイルサイズ

| フォント | 1ウェイト | 全ウェイト（7種） |
|:---|:---|:---|
| Inter（欧文） | 約 100KB | 約 300KB（可変） |
| Noto Sans JP | 約 1.5MB | 約 6MB+ |

**対策**: Google Fonts は自動でサブセット化（unicode-range 分割）する。セルフホスティングの場合は `pyftsubset` 等でサブセット化が必須。

### font-feature-settings

```css
/* 日本語フォントで有効な OpenType 機能 */
.japanese-text {
  font-feature-settings:
    "palt" 1,  /* プロポーショナル詰め（約物の半角化） */
    "kern" 1;  /* カーニング */
}

/* 縦組みの場合 */
.vertical-text {
  writing-mode: vertical-rl;
  text-orientation: mixed;
  font-feature-settings:
    "vpal" 1,  /* 縦組みプロポーショナル */
    "vkrn" 1;  /* 縦組みカーニング */
}
```

### ウェイトの選定

日本語フォントはファイルが大きいため、必要なウェイトを絞る。

```
推奨: Regular (400) + Bold (700) の2ウェイト
余裕があれば: Medium (500) を追加（UIラベル用）
避ける: Thin (100) / Light (300) は本文では可読性が低い
```

### フォールバックの設定

```css
body {
  font-family:
    'Noto Sans JP',          /* Webフォント */
    'Hiragino Kaku Gothic ProN',  /* macOS */
    'Yu Gothic',             /* Windows */
    'Meiryo',                /* Windows旧版 */
    sans-serif;
}
```

> **ポイント**: `Yu Gothic` は Windows 10+ で標準搭載だが、細いウェイトはアンチエイリアスが弱い。`font-weight: 500` 以上を推奨。
