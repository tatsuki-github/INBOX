---
name: html-slide-gen
description: >
  プレゼン用の HTML スライドを 1 本の HTML ファイルとして生成する。
  テーマ・対象者・枚数目安を確認したうえで構成案を作成し、
  リポジトリ内の snippets/html/ui にあるコンポーネント（Heading, Card, Callout, CodeBlock, Tabs 等）を
  必ず参照して流用し、Tailwind CDN 利用の単一 HTML にまとめる。
  各スライドは section 単位で区切り、ブラウザでそのまま表示・発表できる形式で出力する。
  Use when user says「HTMLスライドを作って」「プレゼン用のスライドを生成して」
  「snippets のコンポーネントでスライドを作って」「技術発表用のHTMLスライドがほしい」
  「勉強会のスライドをHTMLで」「採用説明のスライドをHTMLで」「html-slide-gen でスライドを」。
  Do NOT use for: 記事・ブログの執筆（→ article-craft）、
  LP・ウェブサイトのデザイン（→ front-design）、PPTX/PDF の生成（→ 別ツール）、
  draw.io 等の図の作成（→ diagram）。
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: design
  pattern: "sequential"
  based-on: "プレゼン設計の実践知 + リポジトリ snippets/html/ui"
---

# Skill: HTML Slide Gen（HTML スライド生成）

> **snippets を組み合わせ、1 本の HTML でスライドを仕上げよ**

## Instructions

### ワークフロー内の位置

```
テーマ・対象者・枚数
  ↓
[html-slide-gen]
  ├─ Step 1: テーマ・対象者・枚数の確認
  ├─ Step 2: スライド構成案の作成
  ├─ Step 3: スライドごとの内容と使用コンポーネントの割当
  ├─ Step 4: snippets/html/ui の参照（該当ファイルを読んで流用箇所を特定）
  ├─ Step 5: 単一 HTML ファイルの生成（Tailwind CDN、section 単位でスライド）
  ├─ Step 6: 表示確認・微調整の指示
  └─ Step 7: 出力ファイルの配置・引き渡し
  ↓
単一 HTML ファイル（スライド）
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| テーマ | スライドの主題 | 「新APIの紹介」「採用方針」「アーキテクチャ概要」 |
| 対象者（任意） | 想定聴衆 | 「エンジニア」「経営層」「新卒」 |
| 枚数目安（任意） | スライド枚数 | 「5枚」「10枚程度」 |
| スタイル希望（任意） | トーン・レイアウト | 「簡潔に」「図多め」 |
| リポジトリパス（任意） | snippets の場所 | 未指定時はワークスペースの `snippets/html/ui` |

### 出力

| 出力 | 形式 | 説明 |
|:---|:---|:---|
| スライド HTML | 単一 .html ファイル | Tailwind CDN 利用、`<section>` 単位でスライド、snippets 由来のマークアップを含む |

---

## Step 1: テーマ・対象者・枚数の確認

ユーザーからスライドのテーマ・対象者・枚数目安を聞き取り、不足があれば質問する。snippets のパスを確認する。

### 1a. 聞き取り項目

| 項目 | 必須 | 質問例 |
|:---|:---:|:---|
| テーマ | 必須 | 「どのような内容のスライドにしますか？」 |
| 対象者 | 任意 | 「聴衆は誰を想定していますか？（エンジニア・経営層・新卒等）」 |
| 枚数目安 | 任意 | 「何枚程度を想定していますか？」 |
| スタイル | 任意 | 「簡潔に・図多め・コード多めなど希望はありますか？」 |

### 1b. snippets パスの確認

- ワークスペース（リポジトリ）内の `snippets/html/ui` が存在するか確認する。
- ユーザーが別パスを指定していればそのパスを用いる。未指定の場合はリポジトリルート相対で `snippets/html/ui` を使用する。

**チェックリスト**:
- [ ] テーマが明確に言語化されている
- [ ] 対象者・枚数・スタイルの希望を確認した（任意項目は省略可）
- [ ] `snippets/html/ui` のパスを特定した

---

## Step 2: スライド構成案の作成

タイトル・目次・本編・まとめの流れで構成案を出し、ユーザーに確認する。

### 2a. 構成の型

| 型 | 内容 | 例 |
|:---|:---|:---|
| タイトル | 1 枚目。タイトル・サブタイトル・発表者等 | Heading + Card または Banner |
| 目次（任意） | 2 枚目。本編の見出し一覧 | Heading + DataList または Table |
| 本編 | 3〜N 枚。テーマに沿った見出し・本文・コード・図 | Heading, Card, Callout, CodeBlock, Tabs 等を組み合わせ |
| まとめ | 最後の 1 枚。要点の再掲・次のアクション | Heading + Card または Callout |

### 2b. 構成案の出力形式

各スライドを「スライド番号・見出し・概要（1 行）」でリスト化する。ユーザーに「この流れで進めてよいか」確認する。

**チェックリスト**:
- [ ] タイトル・本編・まとめが含まれている
- [ ] 枚数目安に収まる本編の数を決めた
- [ ] ユーザーに構成案を提示し、了承を得た

---

## Step 3: スライドごとの内容と使用コンポーネントの割当

各スライドの見出し・本文・コードの有無・一覧の有無を決め、どのスライドで `snippets/html/ui` のどのコンポーネントを使うか割り当てる。

### 3a. コンポーネント割当のルール

[snippets-ui-reference.md](references/snippets-ui-reference.md) の「スライドでの推奨用途」に従い、各スライドに 1 つ以上のコンポーネントを割り当てる。

| スライドの内容 | 推奨コンポーネント |
|:---|:---|
| タイトル・見出しのみ | Heading |
| 要点・説明文 | Card, Callout |
| コード例 | CodeBlock |
| 比較表・一覧 | Table, DataList |
| 複数トピックを 1 枚に | Tabs |
| 数値・KPI | Stat |
| 経緯・手順 | Timeline |
| 注意・告知 | Banner, Alert |

### 3b. 割当表の作成

スライド番号・見出し・本文の要約・使用するコンポーネント名（ファイル名ベース）を表にまとめる。これにより Step 4 で参照するファイルが一意に決まる。

**チェックリスト**:
- [ ] 全スライドに少なくとも 1 つの snippets コンポーネントを割り当てた
- [ ] 割当表を用意し、Step 4 で参照するファイル名が明確になった
- [ ] 本文の要約またはキーワードをメモし、Step 5 で文言を書く際のたたきにした

---

## Step 4: snippets/html/ui の参照

割り当てたコンポーネントに対応するファイルを開き、必要な部分の HTML を確認する。コピーしてスライド用に調整する際の注意を明記する。

### 4a. 参照手順

1. [snippets-ui-reference.md](references/snippets-ui-reference.md) で用途→ファイル名を確認する。
2. `snippets/html/ui/<ComponentName>.html` を開く（例: `Heading.html`, `Card.html`, `CodeBlock.html`）。
3. `<body>` 内の、スライドに流用するブロック（見出し・カード・コードブロック等）を特定する。
4. そのブロックの HTML をコピーする際、以下の点を守る:
   - `<script src="https://cdn.tailwindcss.com"></script>` は document に 1 回だけ含めるため、コピーするブロックには含めない。
   - 親要素の `class` が必要なコンポーネントは、親ごとコピーする。

### 4b. 流用時の調整

- プレースホルダーのテキスト（「見出し」「説明文」等）を、Step 2・3 で決めた実際の内容に置き換える。
- 画像 URL が placeholder の場合は、必要に応じて差し替えるか削除する。
- スライド用の section には [slide-structure-guide.md](references/slide-structure-guide.md) の推奨に従い、**16:9 アスペクト比**のスライド領域と推奨クラスを付与する。**フォントサイズ・余白**は **ui-design** スキルの typography-guide および spacing-and-layout に準拠する（slide-structure-guide に Tailwind クラス対応表あり）。アスペクト比は CSS で指定するため section に `min-h-screen` は付けない。

**チェックリスト**:
- [ ] 割り当てた全コンポーネントの .html ファイルを参照した
- [ ] コピーするブロックを特定し、Tailwind の二重読み込みを避けることを確認した
- [ ] 各ブロックをどのスライドのどの位置に置くか整理した

---

## Step 5: 単一 HTML ファイルの生成

`<!DOCTYPE html>` から書き、Tailwind CDN を 1 回だけ含め、**スライドショー用のラッパー・CSS・JS** と各スライドを `<section class="slide ...">` で区切って出力する。1 ページずつキー操作（→ / Space で次、← で前）で切り替えられる形式にする。

### 5a. ファイル構造

[slide-structure-guide.md](references/slide-structure-guide.md) に従う。

- `<head>`: charset, viewport, title, `<script src="https://cdn.tailwindcss.com"></script>`、スライドショー用の `<style>`（`#slide-container` / `.slide` の **16:9 アスペクト比** / `.slide-current` / `@media print`）
- `<body>`: 共通クラス（例: `bg-slate-50 text-slate-900`）
- **ラッパー**: `<div id="slide-container">` で全スライドを包む。
- 各スライド: `<section class="slide flex flex-col justify-center px-8 py-6">` で囲み、その中に Step 4 で準備した snippets 由来のマークアップを配置する。スライド領域は CSS で 16:9 に固定し、**スライド内ではスクロールさせない**（`overflow: hidden`）。**余白・フォント**は ui-design のスペーシングスケール・タイポグラフィに合わせる（slide-structure-guide の「フォントサイズ・余白」参照）。1 枚のコンテンツは 16:9 に収まる量に抑え、収まらない場合はスライドを分割する。最初のスライドには JS で `slide-current` を付与するため、section には class `slide` を必ず含める。
- **キー操作用 script**: `</body>` 直前に `<script>...</script>` で、[slide-structure-guide.md](references/slide-structure-guide.md) のキー操作（ArrowRight / Space = 次、ArrowLeft = 前、任意で Home / End）で `slide-current` を付け替えるロジックを 1 セット含める。

### 5b. コンテンツの反映

Step 3 の割当表と Step 2 の構成に基づき、各 section 内の見出し・本文・コードを実際のテキストで埋める。snippets のコメントやサンプル文言は削除し、発表用の内容に置き換える。

### 5c. 出力

Write ツールで単一の .html ファイルを出力する。出力先はユーザー指定があればそれに従い、なければ `slides.html` や `projects/<案件名>/slides.html` 等を提案する。

**チェックリスト**:
- [ ] Tailwind CDN を 1 回だけ読み込んでいる
- [ ] 全スライドが `<div id="slide-container">` で包まれ、各スライドが `<section class="slide ...">` で区切られている
- [ ] スライドショー用の CSS（`#slide-container` / `.slide` / `.slide-current`）とキー操作用の script を 1 セット含めている
- [ ] 全スライドで snippets 由来のマークアップを用いている（自作の div だけのスライドにしない）
- [ ] 見出し・本文が発表内容に沿って記入されている
- [ ] ファイルを指定パスに書き出した

---

## Step 6: 表示確認・微調整の指示

生成した HTML をブラウザで確認する手順と、よくある微調整を説明する。

### 6a. 確認手順の伝達

- 出力した .html をブラウザで開く（ダブルクリックまたはドラッグ＆ドロップ）。
- **キー操作**（→ / Space で次、← で前）で 1 枚ずつ切り替えられるか確認する。常に 1 枚だけ表示され、スクロールでは切り替わらない想定。
- 文字サイズ・余白・色が読みやすいか確認する。

### 6b. よくある微調整

| 要望 | 対処例 |
|:---|:---|
| 文字を大きくしたい | 該当 section の見出しに `text-3xl`〜`text-4xl`、本文に `text-base`〜`text-lg` を付与（ui-design タイポスケールに従う） |
| 余白を広げたい | section の `px-8 py-6` を `px-10 py-8` 等に変更（スペーシングスケール 16–24–32 に合わせる） |
| 色を変えたい | Tailwind の色クラス（`text-slate-900` → `text-slate-800` 等）を差し替え |

ユーザーから微調整の依頼があった場合は、該当 section のクラスやテキストを修正し、再度ファイルを保存する。

**チェックリスト**:
- [ ] ブラウザで開いて表示を確認する手順をユーザーに伝えた
- [ ] 微調整の希望があれば Step 5 のファイルを修正した

---

## Step 7: 出力ファイルの配置・引き渡し

出力先パスに保存済みであることを確認し、使い方を簡潔に伝える。

### 7a. 保存先の確認

- ファイルが指定したパスに存在することを確認する。
- 上書きした場合は、その旨を伝える。

### 7b. 引き渡しメッセージ

- 「〇〇 にスライドを保存しました。ブラウザで開いてご確認ください。」
- 必要なら「印刷→PDF に保存で配布用 PDF にできます」等の一言を添える。

**チェックリスト**:
- [ ] 出力ファイルが指定パスに存在する
- [ ] ユーザーに保存先と確認方法を伝えた

---

## Examples

### Example 1: 新 API 紹介スライド 5 枚

```
「新しくリリースした REST API の紹介スライドを HTML で 5 枚作って。対象は社内エンジニア」

→ Step 1: テーマ=新API紹介、対象者=社内エンジニア、枚数=5
→ Step 2: 構成案＝タイトル・概要・エンドポイント一覧・コード例・まとめ
→ Step 3: 各スライドに Heading, Card, CodeBlock, Callout を割当
→ Step 4: snippets/html/ui の Heading.html, Card.html, CodeBlock.html, Callout.html を参照
→ Step 5: slides.html を生成
→ 成果物: 単一 HTML、ブラウザで発表可能
```

### Example 2: 採用説明スライド 10 枚

```
「採用説明会用のスライドを HTML で 10 枚程度。会社紹介・技術スタック・キャリア・応募方法を含めて」

→ Step 1: テーマ=採用説明、対象者=応募者、枚数目安=10
→ Step 2: タイトル・目次・会社紹介・技術スタック・キャリアパス・福利厚生・応募方法・まとめ・Q&A
→ Step 3: Heading, Card, Callout, Tabs, Banner を割当
→ Step 4〜5: 上記コンポーネントを参照して 1 本の HTML にまとめる
→ 成果物: 採用説明用 slides.html
```

### Example 3: 技術勉強会スライド 8 枚

```
「来週の勉強会で使うスライドを HTML で。テーマは『マイグレーション戦略』で 8 枚」

→ Step 1: テーマ=マイグレーション戦略、枚数=8
→ Step 2: 課題・現状アーキテクチャ・目標・戦略案・フェーズ分け・デモ・注意点・まとめ
→ Step 3: Heading, Card, CodeBlock, Callout, Table, Timeline を割当
→ Step 4〜5: snippets を参照して HTML 生成
→ 成果物: 勉強会用 slides.html
```

### Example 4: 四半期レビュー 6 枚

```
「四半期の振り返りスライドを HTML で 6 枚。実績・課題・次期方針を入れて」

→ Step 1: テーマ=四半期レビュー、枚数=6
→ Step 2: タイトル・実績サマリ・課題・次期目標・スケジュール・まとめ
→ Step 3: Heading, Stat, Card, Callout を割当
→ Step 4〜5: 生成・保存
→ 成果物: 四半期レビュー用 slides.html
```

### Example 5: 障害報告 4 枚

```
「先週の障害の報告スライドを HTML で 4 枚。概要・原因・対応・再発防止」

→ Step 1: テーマ=障害報告、枚数=4
→ Step 2: タイトル・概要・原因・対応内容・再発防止策
→ Step 3: Heading, Callout, Timeline, Card を割当
→ Step 4〜5: 生成・保存
→ 成果物: 障害報告用 slides.html
```

### Example 6: チーム方針共有 7 枚

```
「チームの年間方針を共有するスライドを HTML で 7 枚。ビジョン・目標・役割・スケジュール」

→ Step 1: テーマ=チーム方針、枚数=7
→ Step 2: タイトル・ビジョン・目標・役割分担・KPI・スケジュール・まとめ
→ Step 3: Heading, Card, Banner, Table を割当
→ Step 4〜5: 生成・保存
→ 成果物: チーム方針共有用 slides.html
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| snippets ディレクトリが見つからない | パスが違う、ワークスペース外 | リポジトリルートの `snippets/html/ui` を絶対パスまたは相対パスで指定。ユーザーに「snippets はこのリポジトリの snippets/html/ui でよいか」確認する。[troubleshooting.md](references/troubleshooting.md) 参照 |
| コピーした部分だけスタイルが崩れる | Tailwind が 2 回読み込まれている | `<script src="https://cdn.tailwindcss.com"></script>` は document に 1 回だけ。snippets をコピーする際に script タグを含めない |
| スライドが 1 画面に収まらない | 16:9 領域に対して内容が多すぎる | スライド内スクロールは行わない。内容が多いスライドは 2 枚に分割するか、フォント・余白を調整して 16:9 に収めるよう提案する |
| フォントが小さくて読めない | 本文に text-sm や text-xs のまま | スライド用に `text-base` 以上に変更。見出しは `text-2xl` 以上を推奨 |
| どのコンポーネントを使えばよいかわからない | 一覧を参照していない | [snippets-ui-reference.md](references/snippets-ui-reference.md) の「スライドでの推奨用途」で用途→コンポーネントを確認する |
| 枚数が多すぎて 1 ファイルが重い | テーマが広い、希望枚数が多い | 10〜15 枚を超える場合は「2 本に分ける」「概要版と詳細版に分ける」を提案する |
| 構成案で止まって進まない | ユーザーが内容を決めきれていない | デフォルトの構成案（タイトル・概要・本編 3〜5 点・まとめ）を提示し、「この流れでよいか」で合意してから Step 4 に進む |
| レイアウトが幅で崩れる | 長いコードや URL が折り返されない | 該当要素に `break-words` や `overflow-x-auto` を付与。CodeBlock は snippet のクラスを維持する |
| 出力先が不明 | ユーザーがパスを指定していない | `slides.html` や `projects/<案件名>/slides.html` を提案し、確認してから保存する |
| 既存ファイルを上書きしてよいか不安 | 同名ファイルが既にある | 保存前に「〇〇 に保存してよいか」とユーザーに確認する |
| コンポーネント内の画像が表示されない | placeholder の URL のまま | 必要に応じて画像 URL を差し替えるか、画像ブロックを削除する |
| 印刷で 1 スライド 1 ページにしたい | 標準では改ページされない | `@media print` で各 section に `page-break-after: always` を付与する CSS を追加する。[slide-structure-guide.md](references/slide-structure-guide.md) の印刷の項を参照。スライドショー用テンプレートには印刷用ブロックが含まれており、印刷時は従来どおり 1 section 1 ページになる |
| キー操作で切り替わらない | フォーカスがページにない（別要素にフォーカスがある） | ページ内の余白をクリックしてから、→ / ← / Space を押す。キーイベントは document で捕捉しているため、フォーカスが body 上にあれば動作する |

---

## References

| ファイル | 内容 |
|:---|:---|
| [snippets-ui-reference.md](references/snippets-ui-reference.md) | snippets/html/ui のパス、代表コンポーネント一覧、スライドでの推奨用途、Tailwind CDN 前提 |
| [slide-structure-guide.md](references/slide-structure-guide.md) | スライドショー用の基本構造（ラッパー・slide クラス・CSS/JS）、キー操作仕様、印刷・表示の注意 |
| [troubleshooting.md](references/troubleshooting.md) | よくある問題（snippets が見つからない、レイアウト崩れ、枚数過多）と対処 |

---

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **article-craft** | 境界 | 記事・ブログの執筆は article-craft。スライド生成は本スキル |
| **front-design** | 境界 | LP・ウェブサイトのデザインは front-design。スライドは本スキル |
| **diagram** | 補助 | 図・アーキテクチャ図は diagram。スライド内に図を埋め込む場合は diagram の出力を参照可能 |
| **ui-design** | 参照 | フォントサイズ・余白は ui-design の typography-guide と spacing-and-layout に準拠。スライドのタイポグラフィ・スペーシングスケールは slide-structure-guide 経由で参照 |
