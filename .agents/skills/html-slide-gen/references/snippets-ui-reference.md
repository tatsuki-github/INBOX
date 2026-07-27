# snippets/html/ui コンポーネント参照

> スライド生成時は、UI 部品をこのディレクトリの HTML ファイルからのみ流用する。

## パス

- リポジトリルート相対: `snippets/html/ui/`
- 各コンポーネントは単体の `.html` ファイル（例: `Heading.html`, `Card.html`）。

## 前提

- すべて **Tailwind CSS CDN** 使用（`<script src="https://cdn.tailwindcss.com"></script>`）。
- スライド用 HTML では上記スクリプトを **1 回だけ** 読み込む。snippets をコピーする際に重複させない。

## スライドでの推奨用途

| 用途 | コンポーネント | ファイル名 | 備考 |
|:---|:---|:---|:---|
| タイトル・見出し | Heading | Heading.html | h1〜h6、サブタイトル・meta 対応 |
| 本文カード・要点 | Card | Card.html | シャドウ/ボーダー/アクセント枠のバリアント |
| コードブロック | CodeBlock | CodeBlock.html | シンタックスハイライト風、コピーボタン付きも |
| 注意・補足・引用 | Callout | Callout.html | 情報/警告/成功などのバリアント |
| 一覧・データ | Table, DataList | Table.html, DataList.html | 比較表、箇条書きリスト |
| タブ切り替え | Tabs | Tabs.html | 複数トピックを 1 スライドに |
| 数値・KPI | Stat | Stat.html | 指標の強調表示 |
| タイムライン | Timeline | Timeline.html | 経緯・手順・履歴 |
| バナー・告知 | Banner | Banner.html | スライド上部の注意書き |
| 区切り線 | Divider | Divider.html | セクション区切り |
| ボタン・CTA | Button, ButtonGroup | Button.html, ButtonGroup.html | リンク風ボタン |
| プログレス | ProgressBar, Meter | ProgressBar.html, Meter.html | 進捗・割合の可視化 |
| 空状態 | EmptyState | EmptyState.html | 「データなし」等のプレースホルダー |

## その他のコンポーネント（必要に応じて）

| カテゴリ | 例 |
|:---|:---|
| フォーム系 | Input, Checkbox, RadioGroup, Select, Switch, Textarea |
| ナビ・レイアウト | Header, Footer, Navbar, Sidebar, Breadcrumb |
| フィードバック | Alert, Loading, Spinner, Skeleton |
| オーバーレイ | Modal, Dialog, Drawer, Sheet, Popover |
| メディア | Avatar, AspectRatio, GalleryGrid |
| チャート | BarChart, LineChart, PieChart, AreaChart |

## 流用時の手順

1. 割り当てたコンポーネントの `.html` を開く。
2. `<body>` 内の必要な部分（見出し・カード・コードブロック等）をコピーする。
3. スライド用の `<section>` 内に貼り付け、テキスト・クラスを内容に合わせて調整する。
4. 既に `<script src="https://cdn.tailwindcss.com"></script>` が document に含まれていれば、コピーしたブロックに script は含めない。

## 注意

- コンポーネント内の画像 URL（placeholder 等）は必要に応じて差し替える。
- スライドは縦長になるため、`min-h-screen` や `flex` で 1 スライド 1 画面になるよう section にクラスを付与することを推奨（詳細は slide-structure-guide.md）。
