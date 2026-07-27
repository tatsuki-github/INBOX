# CSS スニペットカタログ

> コンセプト駆動で使える実践的 CSS スニペット集。全て `var(--color-xxx)` と連携。

---

## a) グラデーション背景

```css
/* 対角線リニア — 135deg/160deg で印象が変わる */
.hero-grad-linear { background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%); }
.hero-grad-linear-tri { background: linear-gradient(160deg, var(--color-primary-dark) 0%, var(--color-primary) 50%, var(--color-accent) 100%); }

/* メッシュグラデーション風 — 複数の楕円ラディアルを重ねる */
.hero-grad-mesh {
  background:
    radial-gradient(ellipse 80% 60% at 15% 40%, var(--color-primary) 0%, transparent 55%),
    radial-gradient(ellipse 60% 80% at 85% 25%, var(--color-accent) 0%, transparent 50%),
    radial-gradient(ellipse 70% 50% at 50% 90%, var(--color-primary-light) 0%, transparent 55%),
    var(--color-bg);
}

/* コニカル — 円錐状の光源効果 */
.hero-grad-conic {
  background: conic-gradient(from 220deg at 40% 60%, var(--color-primary-dark), var(--color-primary), var(--color-accent), var(--color-primary-dark));
}

/* グラデーション + SVGノイズテクスチャオーバーレイ */
.hero-grad-textured {
  background:
    url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.7' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.06'/%3E%3C/svg%3E"),
    linear-gradient(145deg, var(--color-primary-dark) 0%, var(--color-primary) 60%, var(--color-accent) 100%);
}

/* ソフトグロウ — ダーク系テーマ向きの淡い光球 */
.hero-grad-glow { background: var(--color-bg); position: relative; overflow: hidden; }
.hero-grad-glow::before {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background:
    radial-gradient(circle 500px at 20% 30%, color-mix(in srgb, var(--color-primary) 25%, transparent) 0%, transparent 100%),
    radial-gradient(circle 400px at 75% 70%, color-mix(in srgb, var(--color-accent) 20%, transparent) 0%, transparent 100%);
}
```

---

## b) テキストオーバーレイ

```css
/* 半透明暗幕 — 画像上のテキスト可読性確保 */
.overlay-solid { position: relative; }
.overlay-solid::after { content: ''; position: absolute; inset: 0; background: color-mix(in srgb, var(--color-bg) 65%, transparent); pointer-events: none; }
.overlay-solid > * { position: relative; z-index: 1; }

/* 下→上グラデーション — 画像下部にテキスト配置 */
.overlay-gradient { position: relative; }
.overlay-gradient::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(to top, color-mix(in srgb, var(--color-bg) 85%, transparent) 0%, color-mix(in srgb, var(--color-bg) 40%, transparent) 40%, transparent 70%);
}
.overlay-gradient > * { position: relative; z-index: 1; }

/* フロストガラス — backdrop-filter によるぼかし */
.overlay-frost {
  background: color-mix(in srgb, var(--color-surface) 40%, transparent);
  backdrop-filter: blur(16px) saturate(1.4);
  -webkit-backdrop-filter: blur(16px) saturate(1.4);
  border: 1px solid color-mix(in srgb, var(--color-text) 10%, transparent);
  border-radius: 12px;
  padding: clamp(1.5rem, 4vw, 3rem);
}
```

---

## c) CTA ボタン

全パターンに hover / active / focus-visible 状態を含む。

```css
/* ソリッド + ホバーリフト */
.cta-solid {
  display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.875rem 2rem;
  font-size: 1rem; font-weight: 600; color: var(--color-bg); background: var(--color-primary);
  border: 2px solid transparent; border-radius: 6px; cursor: pointer;
  transition: background 0.25s, transform 0.2s, box-shadow 0.25s;
}
.cta-solid:hover { background: var(--color-primary-dark); transform: translateY(-2px); box-shadow: 0 6px 20px color-mix(in srgb, var(--color-primary) 30%, transparent); }
.cta-solid:active { transform: translateY(0); box-shadow: none; }
.cta-solid:focus-visible { outline: 3px solid var(--color-accent); outline-offset: 3px; }

/* グラデーション + シャドウ */
.cta-gradient {
  display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.875rem 2rem;
  font-size: 1rem; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
  border: none; border-radius: 8px; cursor: pointer;
  box-shadow: 0 4px 16px color-mix(in srgb, var(--color-primary) 25%, transparent);
  transition: box-shadow 0.25s, transform 0.2s, filter 0.25s;
}
.cta-gradient:hover { box-shadow: 0 8px 28px color-mix(in srgb, var(--color-primary) 40%, transparent); transform: translateY(-2px); filter: brightness(1.08); }
.cta-gradient:active { transform: translateY(0); box-shadow: 0 2px 8px color-mix(in srgb, var(--color-primary) 20%, transparent); }
.cta-gradient:focus-visible { outline: 3px solid var(--color-accent); outline-offset: 3px; }

/* アウトライン → ソリッド変化 */
.cta-outline {
  display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.875rem 2rem;
  font-size: 1rem; font-weight: 600; color: var(--color-primary); background: transparent;
  border: 2px solid var(--color-primary); border-radius: 6px; cursor: pointer;
  transition: color 0.25s, background 0.25s, transform 0.2s;
}
.cta-outline:hover { color: var(--color-bg); background: var(--color-primary); transform: translateY(-1px); }
.cta-outline:active { transform: translateY(0); background: var(--color-primary-dark); }
.cta-outline:focus-visible { outline: 3px solid var(--color-accent); outline-offset: 3px; }

/* ピル型 + アイコン（.cta-icon にアイコンSVGを入れる） */
.cta-pill {
  display: inline-flex; align-items: center; gap: 0.625rem; padding: 0.875rem 2.25rem;
  font-size: 1rem; font-weight: 600; color: var(--color-bg); background: var(--color-primary);
  border: none; border-radius: 100px; cursor: pointer;
  transition: gap 0.3s, background 0.25s, transform 0.2s, box-shadow 0.25s;
}
.cta-pill .cta-icon { display: inline-flex; transition: transform 0.3s; }
.cta-pill:hover { background: var(--color-primary-dark); transform: translateY(-2px); gap: 0.875rem; box-shadow: 0 6px 20px color-mix(in srgb, var(--color-primary) 30%, transparent); }
.cta-pill:hover .cta-icon { transform: translateX(3px); }
.cta-pill:active { transform: translateY(0); box-shadow: none; }
.cta-pill:focus-visible { outline: 3px solid var(--color-accent); outline-offset: 3px; }
```

---

## d) アニメーション / マイクロインタラクション

```css
/* fadeInUp — テキスト登場 */
@keyframes fadeInUp { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: translateY(0); } }
.animate-fade-in-up { opacity: 0; animation: fadeInUp 0.7s cubic-bezier(0.22, 1, 0.36, 1) forwards; }
.animate-delay-1 { animation-delay: 0.15s; }
.animate-delay-2 { animation-delay: 0.3s; }
.animate-delay-3 { animation-delay: 0.45s; }

/* scaleIn — 画像/カード登場 */
@keyframes scaleIn { from { opacity: 0; transform: scale(0.92); } to { opacity: 1; transform: scale(1); } }
.animate-scale-in { opacity: 0; animation: scaleIn 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards; }

/* スクロールトリガー — JS側で .is-visible を付与（Intersection Observer） */
.scroll-reveal {
  opacity: 0; transform: translateY(32px);
  transition: opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1), transform 0.7s cubic-bezier(0.22, 1, 0.36, 1);
}
.scroll-reveal.is-visible { opacity: 1; transform: translateY(0); }
/* JS: const obs = new IntersectionObserver(es => es.forEach(e => { if(e.isIntersecting) e.target.classList.add('is-visible'); }), {threshold:.15}); document.querySelectorAll('.scroll-reveal').forEach(el => obs.observe(el)); */

/* パララックス風 — CSS-only の perspective ベース */
.parallax-container { height: 100vh; overflow-x: hidden; overflow-y: auto; perspective: 1px; }
.parallax-bg { position: absolute; inset: 0; transform: translateZ(-1px) scale(2); z-index: -1; background-size: cover; background-position: center; }
.parallax-content { position: relative; transform: translateZ(0); background: var(--color-bg); }

/* ホバーで画像ズーム */
.img-zoom { overflow: hidden; border-radius: 8px; }
.img-zoom img { display: block; width: 100%; height: auto; transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1); }
.img-zoom:hover img { transform: scale(1.06); }
```

---

## e) レスポンシブユーティリティ

```css
/* フルードタイポグラフィ & スペーシング — clamp() */
:root {
  --text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem);
  --text-sm: clamp(0.875rem, 0.8rem + 0.35vw, 1rem);
  --text-base: clamp(1rem, 0.9rem + 0.45vw, 1.125rem);
  --text-lg: clamp(1.125rem, 1rem + 0.6vw, 1.375rem);
  --text-xl: clamp(1.375rem, 1.1rem + 1.2vw, 2rem);
  --text-2xl: clamp(1.75rem, 1.3rem + 2vw, 3rem);
  --text-3xl: clamp(2.25rem, 1.5rem + 3.5vw, 4.5rem);
  --space-xs: clamp(0.5rem, 0.4rem + 0.5vw, 0.75rem);
  --space-sm: clamp(0.75rem, 0.6rem + 0.7vw, 1.25rem);
  --space-md: clamp(1.5rem, 1rem + 2vw, 3rem);
  --space-lg: clamp(2.5rem, 1.5rem + 4vw, 5rem);
  --space-xl: clamp(4rem, 2.5rem + 6vw, 8rem);
}

/* コンテナクエリ — 親幅ベースのレイアウト切替 */
.card-container { container-type: inline-size; container-name: card; }
@container card (min-width: 400px) { .card-layout { display: grid; grid-template-columns: 140px 1fr; gap: 1.5rem; align-items: start; } }
@container card (max-width: 399px) { .card-layout { display: flex; flex-direction: column; gap: 1rem; } }

/* モバイルファーストのブレークポイント戦略 */
.hero-layout { display: flex; flex-direction: column; gap: var(--space-md); padding: var(--space-md); text-align: center; }
@media (min-width: 640px) { .hero-layout { padding: var(--space-lg); max-width: 640px; margin: 0 auto; } }
@media (min-width: 768px) { .hero-layout { text-align: left; max-width: 768px; } }
@media (min-width: 1024px) { .hero-layout { display: grid; grid-template-columns: 1fr 1fr; align-items: center; gap: var(--space-lg); max-width: 1200px; } }
@media (min-width: 1280px) { .hero-layout { max-width: 1400px; gap: var(--space-xl); } }

/* アクセシビリティ — モーション抑制 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
}
```
