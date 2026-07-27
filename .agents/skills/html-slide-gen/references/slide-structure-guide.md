# スライド用 HTML 構造ガイド

> 単一 HTML で複数スライドを表現し、**1 ページずつキー操作で切り替える**スライドショー形式を採用する。フォントサイズ・余白は **ui-design** スキルの [typography-guide.md](../../ui-design/references/typography-guide.md) および [spacing-and-layout.md](../../ui-design/references/spacing-and-layout.md) に準拠する。

## スライドショー基本構造

- 全 `<section>` を **1 つのラッパー**（`id="slide-container"`）で包む。
- 各 section に共通クラス **`slide`** を付与し、`position: absolute` で重ねて配置。表示中のみ **`slide-current`** クラスで前面に表示する。
- スライドショー用の **CSS** と **JS**（キー操作で次/前に切り替え）を HTML 内に 1 セット含める。
- **アスペクト比**: 一般的なプレゼン比率 **16:9** に統一。ビューポート内に収まる最大の 16:9 領域をスライド領域とする。
- **スライド内スクロール**: 行わない。各スライドのコンテンツは 16:9 の領域内に収まるように配置する（`overflow: hidden`）。収まらない場合はスライドを分割する。

### HTML テンプレート

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>スライドタイトル</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    #slide-container { position: relative; width: 100vw; height: 100vh; overflow: hidden; }
    .slide {
      position: absolute;
      left: 50%; top: 50%;
      transform: translate(-50%, -50%);
      width: min(100vw, 177.78vh);
      height: min(56.25vw, 100vh);
      display: flex; flex-direction: column; justify-content: center;
      padding: 1.5rem 2rem; box-sizing: border-box;
      overflow: hidden;
      visibility: hidden;
    }
    .slide.slide-current { visibility: visible; z-index: 1; }
    @media print {
      #slide-container { width: 100%; height: auto; overflow: visible; }
      .slide { position: static; transform: none; width: 100%; height: auto; min-height: 100vh; visibility: visible; page-break-after: always; }
      .slide:last-child { page-break-after: auto; }
    }
  </style>
</head>
<body class="bg-slate-50 text-slate-900">
  <div id="slide-container">
    <!-- スライド 1: タイトル -->
    <section class="slide flex flex-col justify-center px-8 py-6">
      <!-- snippets の Heading / Card 等をここに -->
    </section>
    <!-- スライド 2 -->
    <section class="slide flex flex-col justify-center px-8 py-6">
      ...
    </section>
  </div>
  <script>
    (function () {
      var slides = document.querySelectorAll('.slide');
      var idx = 0;
      function go(i) {
        if (i < 0 || i >= slides.length) return;
        slides[idx].classList.remove('slide-current');
        idx = i;
        slides[idx].classList.add('slide-current');
        if (window.location.hash !== undefined) { try { window.location.hash = idx; } catch (e) {} }
      }
      slides[idx].classList.add('slide-current');
      document.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); go(Math.min(idx + 1, slides.length - 1)); }
        else if (e.key === 'ArrowLeft') { e.preventDefault(); go(Math.max(idx - 1, 0)); }
        else if (e.key === 'Home') { e.preventDefault(); go(0); }
        else if (e.key === 'End') { e.preventDefault(); go(slides.length - 1); }
      });
    })();
  </script>
</body>
</html>
```

## キー操作の仕様

| キー | 動作 |
|:---|:---|
| **→** (ArrowRight) / **Space** | 次のスライド |
| **←** (ArrowLeft) | 前のスライド |
| **Home** | 先頭スライド |
| **End** | 最後のスライド |

- スクロールでは切り替えできない（常に 1 枚だけ表示）。フォーカスがページにある状態でキーが効く。

## フォントサイズ・余白（ui-design 準拠）

スライド内のタイポグラフィとスペーシングは **ui-design** の参照ドキュメントに合わせる。

### タイポグラフィ（Tailwind クラス）

| 用途 | クラス | 相当 | 備考 |
|:---|:---|:---|:---|
| スライドタイトル（h1） | `text-4xl` 〜 `text-5xl` | 36px〜48px | 大見出しは `tracking-tight` `leading-tight` |
| セクション見出し（h2） | `text-3xl` 〜 `text-4xl` | 30px〜36px | `font-bold` |
| カード・サブ見出し（h3） | `text-lg` 〜 `text-xl` | 18px〜20px | `font-semibold` |
| 本文 | `text-base` | 16px | line-height 1.5 以上（`leading-relaxed`） |
| セカンダリ・メタ | `text-sm` | 14px | `text-slate-500` 等 |
| キャプション・ラベル | `text-xs` | 12px | `uppercase` `tracking-wider` は控えめに |

### スペーシング（ui-design スケール 4–8–12–16–24–32）

| 用途 | Tailwind | 相当 |
|:---|:---|:---|
| スライド内パディング | `px-8 py-6` | 左右 32px・上下 24px（セクション間 24px に合わせる） |
| 要素間の密な間隔 | `gap-2` `mb-2` | 8px |
| 要素間の標準間隔 | `gap-4` `mb-4` | 16px |
| セクション内の区切り | `gap-6` `mb-6` `mt-6` | 24px |
| カード内パディング | `p-6` `px-6 py-4` | 24px〜（32px は `p-8`） |

CSS の `.slide` の padding は上記スケールに合わせる（例: `1.5rem 2rem` = 24px 32px）。

## 推奨クラス（section）

| 目的 | クラス例 |
|:---|:---|
| スライドショー用（必須） | `slide` — 全 section に付与。最初のスライドには JS で `slide-current` を付与 |
| アスペクト比 | CSS で 16:9 を指定。section に `min-h-screen` は付けない。スライド内はスクロールせず、コンテンツは 16:9 に収める（はみ出しは `overflow: hidden` で非表示） |
| 縦方向中央寄せ | `flex flex-col justify-center` |
| 余白 | `px-8 py-6`（スペーシングスケール 32px / 24px）。必要に応じて `px-6 py-5`（24px/20px）で詰める |

## 印刷・PDF 化

- `@media print` で `#slide-container` の `height` / `overflow` を解除し、`.slide` を `position: static` + `visibility: visible` にする。各 `.slide` に `page-break-after: always` を付与すると、印刷時に 1 スライド 1 ページになる（上記テンプレートの print ブロックを参照）。

## 表示確認

1. 生成した .html をブラウザで開く。
2. **キー操作**（→ / Space で次、← で前）で 1 枚ずつ切り替えられるか確認する。
3. Tailwind が効いているか（色・余白・フォント）を確認する。
4. フォントサイズ・余白が ui-design のタイポグラフィ・スペーシングスケールに沿っているか（本文 `text-base` 以上、見出しはスケールに従う）。

## オプション

- スライド番号表示（例: 「2 / 8」）や Next / Prev ボタンが必要な場合は、`#slide-container` の前後に UI を追加し、同じ `go(i)` を呼ぶようにする。
