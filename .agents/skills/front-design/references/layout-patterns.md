# ヒーローセクション レイアウトパターン集

> LP・コーポレートサイトのファーストビューを決定づける8つのレイアウトパターン。各パターンに適合業種・CSSコード例・レスポンシブ方針を付記。

---

## パターン一覧

| # | パターン名 | 適合トーン | 適合業種例 |
|:---|:---|:---|:---|
| 1 | フルスクリーンビジュアル + テキストオーバーレイ | 感情的・没入 | ホテル / 旅行 / ブランド |
| 2 | スプリットレイアウト（左テキスト・右画像） | バランス・実用 | SaaS / コーポレート |
| 3 | センター配置CTA + グラデーション背景 | 先進的・テック | スタートアップ / AI |
| 4 | 動画/スライダー背景 | ダイナミック・臨場感 | エンタメ / 飲食 / イベント |
| 5 | 非対称グリッド | 個性的・クリエイティブ | デザイン / ポートフォリオ |
| 6 | テキスト主体ミニマル | 知的・権威 | コンサル / 士業 / メディア |
| 7 | カード/フィーチャーグリッド | 情報整理・多機能 | EC / ダッシュボード / 比較 |
| 8 | スクロールアニメーション連動 | 先進的・体験重視 | テック / プロダクト紹介 |

---

## 1. フルスクリーンビジュアル + テキストオーバーレイ

全画面に背景画像を敷き、暗いオーバーレイの上にテキストを配置。ビジュアルで引き込む。

```css
.hero-fullscreen {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: url('/images/hero.jpg') center/cover no-repeat;
}

.hero-fullscreen::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.5),
    rgba(0, 0, 0, 0.7)
  );
}

.hero-fullscreen__content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: #fff;
  max-width: 48rem;
  padding: 2rem;
}
```

**レスポンシブ**: 構造変更不要。画像の `object-position` を調整して被写体を見せる。

---

## 2. スプリットレイアウト（左テキスト・右画像）

画面を左右に二分割。左にテキスト + CTA、右にイメージやイラスト。最も汎用的。

```css
.hero-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 80vh;
  align-items: center;
}

.hero-split__text {
  padding: clamp(2rem, 5vw, 6rem);
}

.hero-split__visual {
  height: 100%;
}

.hero-split__visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* モバイル: 縦に積む（画像を上に） */
@media (max-width: 768px) {
  .hero-split {
    grid-template-columns: 1fr;
    min-height: auto;
  }
  .hero-split__visual {
    order: -1;        /* 画像を先に表示 */
    max-height: 50vh;
  }
}
```

**レスポンシブ**: 768px以下で1カラムに変更。画像を上に移動して視覚的な掴みを維持。

---

## 3. センター配置CTA + グラデーション背景

テキストとボタンを画面中央に配置。背景にグラデーションやメッシュを使い、画像なしで華やかに。

```css
.hero-center {
  min-height: 90vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.hero-center__heading {
  font-size: var(--text-4xl);
  max-width: 40rem;
  margin-bottom: 1.5rem;
}

.hero-center__cta {
  display: inline-flex;
  gap: 1rem;
  flex-wrap: wrap;
  justify-content: center;
}

.hero-center__btn {
  padding: 0.875rem 2rem;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: var(--text-base);
  border: 2px solid transparent;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.hero-center__btn--primary {
  background: #fff;
  color: #4338ca;
}

.hero-center__btn--secondary {
  background: transparent;
  color: #fff;
  border-color: rgba(255, 255, 255, 0.5);
}
```

**レスポンシブ**: 構造変更不要。フォントサイズは `clamp()` で自動縮小。

---

## 4. 動画/スライダー背景

背景に自動再生動画やカルーセルを敷く。飲食・イベントなど動きが映える業種向け。

```css
.hero-video {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.hero-video__bg {
  position: absolute;
  inset: 0;
  z-index: -1;
}

.hero-video__bg video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-video__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
}

.hero-video__content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: #fff;
  padding: 2rem;
}
```

```html
<section class="hero-video">
  <div class="hero-video__bg">
    <video autoplay muted loop playsinline
           poster="/images/hero-poster.jpg">
      <source src="/video/hero.mp4" type="video/mp4">
    </video>
    <div class="hero-video__overlay"></div>
  </div>
  <div class="hero-video__content">
    <!-- 見出し・CTAを配置 -->
  </div>
</section>
```

**レスポンシブ**: モバイルでは `poster` 画像だけ表示し動画を無効化してパフォーマンスを確保する方針もある。

---

## 5. 非対称グリッド

意図的にカラム幅を偏らせ、画像やテキストブロックを変則的に配置。クリエイティブ感を演出。

```css
.hero-asymmetric {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  grid-template-rows: auto auto;
  gap: 1.5rem;
  padding: clamp(2rem, 5vw, 6rem);
  min-height: 80vh;
  align-items: center;
}

.hero-asymmetric__heading {
  grid-column: 1 / -1;
  font-size: var(--text-4xl);
}

.hero-asymmetric__body {
  padding-right: 2rem;
}

.hero-asymmetric__visual {
  border-radius: 1rem;
  overflow: hidden;
}

.hero-asymmetric__visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

@media (max-width: 768px) {
  .hero-asymmetric {
    grid-template-columns: 1fr;
  }
  .hero-asymmetric__body {
    padding-right: 0;
  }
}
```

**レスポンシブ**: 768px以下で1カラムに。非対称感はフォントサイズの強弱で維持。

---

## 6. テキスト主体ミニマル

画像を使わず、大きなタイポグラフィだけで構成。コンテンツの力で勝負する。

```css
.hero-minimal {
  min-height: 70vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: clamp(3rem, 8vw, 10rem) clamp(2rem, 5vw, 6rem);
  max-width: 64rem;
  margin: 0 auto;
}

.hero-minimal__heading {
  font-size: var(--text-4xl);
  line-height: 1.1;
  margin-bottom: 1.5rem;
}

.hero-minimal__sub {
  font-size: var(--text-lg);
  color: var(--color-gray-600);
  max-width: 36rem;
  margin-bottom: 2rem;
}

.hero-minimal__link {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-primary-600);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.hero-minimal__link:hover {
  text-decoration: underline;
  text-underline-offset: 4px;
}
```

**レスポンシブ**: 構造変更不要。`clamp()` でパディングとフォントが自動調整。

---

## 7. カード/フィーチャーグリッド

ヒーロー下部に3-4枚のカードを並べ、主要機能や特徴を一覧表示。情報量が多いサービス向け。

```css
.hero-cards {
  text-align: center;
  padding: clamp(3rem, 6vw, 8rem) clamp(1rem, 3vw, 4rem);
}

.hero-cards__heading {
  font-size: var(--text-3xl);
  margin-bottom: 1rem;
}

.hero-cards__sub {
  color: var(--color-gray-600);
  max-width: 36rem;
  margin: 0 auto 3rem;
}

.hero-cards__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 1.5rem;
  max-width: 64rem;
  margin: 0 auto;
}

.hero-cards__card {
  background: #fff;
  border: 1px solid var(--color-gray-200);
  border-radius: 0.75rem;
  padding: 2rem;
  text-align: left;
  transition: box-shadow 0.2s, transform 0.2s;
}

.hero-cards__card:hover {
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}
```

**レスポンシブ**: `auto-fit + minmax` により自動的にカラム数が調整される。追加のブレークポイント不要。

---

## 8. スクロールアニメーション連動

スクロールに応じて要素がフェードイン・パララックスするインタラクティブなヒーロー。

```css
.hero-scroll {
  min-height: 100vh;
  display: grid;
  place-items: center;
  position: relative;
  overflow: hidden;
}

.hero-scroll__content {
  text-align: center;
  padding: 2rem;
}

/* アニメーション対象要素の初期状態 */
.hero-scroll [data-animate] {
  opacity: 0;
  transform: translateY(2rem);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.hero-scroll [data-animate].is-visible {
  opacity: 1;
  transform: translateY(0);
}

/* 要素ごとに遅延を付けてカスケード表示 */
.hero-scroll [data-animate]:nth-child(2) { transition-delay: 0.15s; }
.hero-scroll [data-animate]:nth-child(3) { transition-delay: 0.3s; }
.hero-scroll [data-animate]:nth-child(4) { transition-delay: 0.45s; }
```

```javascript
// Intersection Observer でスクロール検知（軽量）
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);  // 1回だけ発火
      }
    });
  },
  { threshold: 0.2 }
);

document.querySelectorAll('[data-animate]').forEach((el) => {
  observer.observe(el);
});
```

**レスポンシブ**: アニメーションのロジックはそのまま動作する。`prefers-reduced-motion` への配慮を追加する。

```css
@media (prefers-reduced-motion: reduce) {
  .hero-scroll [data-animate] {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
```

---

## パターン選定フローチャート

プロジェクトの業種・トーンに応じて、最適なパターンを選ぶ指針。

```
Q1: ビジュアル素材（写真・動画）はあるか？
├── YES → Q2へ
└── NO  → Q5へ

Q2: 動画素材があるか？
├── YES → 【4. 動画/スライダー背景】
└── NO  → Q3へ

Q3: 画像で没入感を出したいか？
├── YES → 【1. フルスクリーンビジュアル】
└── NO  → Q4へ

Q4: テキストと画像を同等に見せたいか？
├── YES（バランス重視） → 【2. スプリットレイアウト】
└── NO（変則的に見せたい） → 【5. 非対称グリッド】

Q5: 訴求したい情報量は？
├── 多い（機能・特徴が3つ以上） → 【7. カード/フィーチャーグリッド】
└── 少ない → Q6へ

Q6: 先進性・テック感を出したいか？
├── YES → 【3. センター配置CTA + グラデーション】or【8. スクロールアニメーション連動】
└── NO  → 【6. テキスト主体ミニマル】
```

### 業種×トーン 推奨パターン早見表

| | 信頼・安定 | 先進・テック | エレガント | カジュアル |
|:---|:---|:---|:---|:---|
| **SaaS** | 2 スプリット | 3 センターCTA | - | - |
| **EC** | 7 カードグリッド | - | - | 2 スプリット |
| **ホテル/旅行** | - | - | 1 フルスクリーン | - |
| **飲食** | - | - | - | 4 動画背景 |
| **コンサル/士業** | 6 テキストミニマル | - | 6 テキストミニマル | - |
| **デザイン** | - | 8 スクロール連動 | 5 非対称グリッド | 5 非対称グリッド |
| **メディア** | 6 テキストミニマル | 8 スクロール連動 | - | 7 カードグリッド |
