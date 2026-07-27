---
name: diagram
description: >
  テキスト、画像、Excelから編集可能なdraw.io図面（.drawio, .drawio.svg）を生成するスキル。
  アーキテクチャ図、フローチャート、シーケンス図、ER図、ネットワーク構成図、状態遷移図に対応。
  Azure2/AWSクラウドアイコン対応。VS Code Draw.io Integration互換のXML検証。
  Use when user says「図を作成して」「アーキテクチャ図を描いて」「フローチャートを作って」
  「シーケンス図を生成して」「draw.ioで図を作成して」「Azure構成図を描いて」
  「AWS構成図を作って」「ER図を作って」「ネットワーク図を作成して」
  「クラス図を生成して」「状態遷移図を描いて」「システム構成図を作って」。
allowed-tools: "Write"
metadata:
  author: KC-Prop-Foundry
  version: 2.0.0
  category: document-creation
---

# Skill: Diagram (作図 & 図解生成)

VS Code + Draw.io Integration 環境向けに、編集可能な `.drawio` ファイルを生成するスキル。

## Instructions

### Step 1: 入力解析

ユーザーの指示から以下を特定する。

| 解析項目 | 確認内容 | デフォルト値 |
|:---|:---|:---|
| **図の対象** | 何を図にするか（システム構成、業務フロー等） | — (必須) |
| **出力形式** | `.drawio` or `.drawio.svg` | `.drawio` |
| **出力先** | ファイルパス | `outputs/` またはカレントディレクトリ |
| **クラウドアイコン** | Azure / AWS アイコンが必要か | 不要 |
| **入力ソース** | テキスト指示 / 既存ファイル参照 / 画像 | テキスト指示 |

「図の対象」が不明な場合は必ずユーザーに質問する。

### Step 2: 図の種別判定とリファレンス読み込み

対象に応じて図の種別を判定し、必要なリファレンスを読み込む。

| 図の種別 | 例 | 読み込むリファレンス |
|:---|:---|:---|
| アーキテクチャ図 | システム構成、Azure/AWS 構成 | `references/cloud-icons.md` + `references/style-guide.md` |
| フローチャート | 業務フロー、ログインフロー | `references/style-guide.md` |
| シーケンス図 | API 呼び出し、処理順序 | `references/mxcell-structure.md` + `references/style-guide.md` |
| ER図 / クラス図 | データモデル、クラス設計 | `references/mxcell-structure.md` + `references/style-guide.md` |
| ネットワーク図 | VNet、サブネット構成 | `references/cloud-icons.md` + `references/style-guide.md` |
| その他 | 状態遷移図、データフロー図等 | `references/mxcell-structure.md` + `references/style-guide.md` |

CRITICAL: Azure / AWS アイコンを使う場合は、XML 生成前に `references/cloud-icons.md` を必ず読み込むこと。

### Step 3: XML 生成

`references/mxcell-structure.md` の構造定義に従い、draw.io 互換の XML を生成する。

**生成ルール**:
1. 各ノードの `id` は一意にする（`node-1`, `node-2`, ... 等の連番を推奨）
2. エッジの `source` / `target` は既存ノードの `id` を正確に参照する
3. `value` 属性内の HTML 特殊文字は必ずエスケープする（`&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`）
4. Azure アイコンは `img/lib/azure2/...` 形式のみ使用する（`mxgraph.azure.*` 形式は使用禁止）
5. スタイルは `references/style-guide.md` の配色・レイアウト指針に従う
6. Write ツールで `.drawio` または `.drawio.svg` ファイルを出力する

```xml
<!-- OK: Azure2 形式 -->
<mxCell style="aspect=fixed;image=img/lib/azure2/networking/Front_Doors.svg;..." />

<!-- NG: 古い形式 (VS Code で青い四角形になる) -->
<mxCell style="shape=mxgraph.azure.front_door;..." />
```

### Step 4: 検証

生成した XML を以下の観点でセルフチェックする。1つでも NG があれば Step 3 に戻って修正。

- XML が well-formed である（タグの開閉が正しい）
- 全ノードの `id` が一意である
- 全エッジの `source` / `target` が実在するノード `id` を参照している
- `value` 属性内の HTML 特殊文字がエスケープされている
- Azure アイコン使用時、全て `img/lib/azure2/` パスである
- ファイル拡張子が `.drawio` または `.drawio.svg` である

---

## Output Format

| 拡張子 | 説明 | 推奨用途 |
|:---|:---|:---|
| `*.drawio` | 標準形式 | 編集・保守用（推奨）。編集安定性が高い |
| `*.drawio.svg` | SVG + メタデータ | ドキュメント埋め込み用。Markdown で画像表示可能かつ編集可 |

## VS Code 設定 (初回のみ)

1. `.drawio` ファイルを VS Code で開く
2. 左下の「+ その他の図形」をクリック
3. Azure および AWS にチェックを入れて「適用」

---

## Examples

### Example 1: 基本的なフローチャート

```
「ログインフローの図を作成して」
```

### Example 2: Azure アーキテクチャ図

```
「Azure ハブ＆スポーク構成図を作成して (VNet, Firewall, Bastion を含む)」
```

### Example 3: ドキュメントからの図面生成

```
「inputs/requirements.md の「システム構成」セクションからアーキテクチャ図を作成して」
```

---

## Troubleshooting

| 問題 | 原因 | 対策 |
|:---|:---|:---|
| 図が空白になる | `value` 属性の HTML 特殊文字が未エスケープ | `&`, `<`, `>` をエスケープする |
| アイコンが青い四角になる | Azure アイコンが旧形式 `mxgraph.azure.*` | [cloud-icons.md](references/cloud-icons.md) を参照し `img/lib/azure2/` 形式に修正 |
| エッジが表示されない | `source` / `target` の ID 参照が不正 | ノード ID の一意性と参照整合性を確認 |
| ファイルが開けない | XML が well-formed でない | XML パーサーでバリデーションし、タグの開閉を修正 |
| ノードが重なる | 座標 (`x`, `y`) が未指定または重複 | 各ノードに適切な座標を設定。`references/style-guide.md` 参照 |

---

## References

| ファイル | 内容 | 読み込みタイミング |
|:---|:---|:---|
| [cloud-icons.md](references/cloud-icons.md) | Azure/AWS アイコンの正しいパスと使用法 | Azure/AWS アイコン使用時（Step 2） |
| [mxcell-structure.md](references/mxcell-structure.md) | `mxCell` XML 構造の定義 | XML 生成時（Step 3） |
| [style-guide.md](references/style-guide.md) | ノードの配色、エッジスタイル、レイアウト指針 | XML 生成時（Step 3） |

## Related Skills

| スキル | 関係 | 連携内容 |
|:---|:---|:---|
| **distill** | 前工程 | 蒸留済みの仕様（ドメインモデル・ビジネスルール）を図面の入力ソースとして活用 |
| **story-map** | 前工程 | ストーリーマップの構造を視覚的に表現（フィーチャー・エピックの全体俯瞰図） |
| **ui-design** | 補助 | UI デザインの配色・スペーシング原則を図面のスタイルガイドに反映 |
| **review** | 後工程 | 生成した図面の正確性・網羅性をクリティカルレビューで検証 |
