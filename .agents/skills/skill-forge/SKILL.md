---
name: skill-forge
description: >
  知識ソース（PDF/書籍）から高品質な Agent Skill を一貫工程で鋳造するオーケストレーター。
  PDF → Markdown 変換（pdf-convert 委譲）→ 知識蒸留（distill 委譲）→ スキル設計 →
  SKILL.md 構築 → 品質監査（review 委譲）→ CLAUDE.md 統合までのフルパイプラインを管理する。
  Use when user says「スキルを作って」「新しいスキルを鋳造して」「PDFからスキルを作って」
  「書籍をスキル化して」「SKILL.mdを生成して」「スキルを設計して」
  「スキルのパイプラインを実行して」「知識ソースからスキルを作って」
  「ワークフローをチェックして」「ワークフローの品質を検証して」。
  Do NOT use for: 既存スキルの軽微な修正（→ 直接編集）、
  PDF 変換のみ（→ pdf-convert）、知識蒸留のみ（→ distill）。
metadata:
  author: KC-Prop-Foundry
  version: 1.3.0
  category: skill-development
---

# Skill: Skill Forge（知識ソースからスキルを鋳造する）

> **知識を鋳型に流し込み、再利用可能なスキルに仕上げよ**

## Instructions

### ワークフロー内の位置

```
知識ソース（PDF/書籍）              ワークフロー（.agent/workflows/）
  ↓                                    ↓
[skill-forge] ← オーケストレーター ─── Step 7e: ワークフロー品質チェック
  ├─ Step 2: pdf-convert に委譲
  ├─ Step 3: distill に委譲
  ├─ Step 5-6: SKILL.md + references 構築
  ├─ Step 7: review に委譲（品質監査）
  └─ Step 8: CLAUDE.md / INDEX.md 統合
  ↓
完成スキル（.agent/skills/<name>/）
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| PDF / 書籍 | スキル化したい知識ソース | 『Effective TypeScript』PDF |
| inbox 済み Markdown | 既に変換済みの知識ソース | `skills-machine/10_inbox/xxx.md` |
| notes 済み蒸留メモ | 既に蒸留済みの知見 | `skills-machine/20_notes/xxx/` |
| スキル設計案 | 既にドラフトがある場合 | `skills-machine/30_proposal/xxx.md` |

### 出力

| 出力 | 形式 | 説明 |
|:---|:---|:---|
| SKILL.md | Markdown（YAML frontmatter 付き） | スキル定義本体 |
| references/ | Markdown ファイル群 | Progressive Disclosure 第 3 層 |
| CLAUDE.md 差分 | 編集指示 | Skills Catalog / カテゴリ / 連携図の更新 |
| INDEX.md 差分 | 編集指示 | mermaid 図 / テーブル / 逆引きの更新 |

### エントリーポイント判定

開始位置はソースの状態で自動決定する:

| ソースの状態 | 開始ステップ |
|:---|:---|
| PDF ファイルのみ | **Step 1** → Step 2（pdf-convert）から全工程 |
| `skills-machine/10_inbox/` に Markdown 済み | **Step 1** → Step 3（distill）から開始 |
| `skills-machine/20_notes/` に蒸留済み | **Step 1** → Step 4（スキル設計）から開始 |
| `skills-machine/30_proposal/` に設計案あり | **Step 1** → Step 5（SKILL.md 構築）から開始 |
| `.agent/workflows/` にワークフローあり | **Step 1** → Step 7e（ワークフロー品質チェック）のみ実行 |

---

## Step 1: 知識ソースの受領と事前確認

ソースの状態を確認し、パイプラインのエントリーポイントを決定する。

### 1a. ソースの特定

ユーザーに以下を確認する:

| 確認項目 | 質問 |
|:---|:---|
| **知識ソース** | 何の書籍/ガイドをスキル化するか？ |
| **スキル名** | 完成スキルの名前（kebab-case） |
| **カテゴリ** | どのカテゴリに属するか（既存 or 新規） |
| **トリガー** | ユーザーがどんな言葉でこのスキルを呼び出すか |
| **関連スキル** | 既存のどのスキルと連携するか |

### 1b. 既存資産のチェック

```
skills-machine/10_inbox/    → Markdown 化済みか？
skills-machine/20_notes/    → 蒸留済みか？
skills-machine/30_proposal/ → 設計案があるか？
.agent/skills/           → 同名スキルが既存でないか？
```

### 1c. エントリーポイントの決定

上記の状態に基づき、開始ステップを決定してユーザーに報告する。

**チェックリスト**:
- [ ] 知識ソースが特定されている
- [ ] スキル名（kebab-case）が決定している
- [ ] カテゴリが決定している
- [ ] エントリーポイントが決定し、ユーザーに報告した
- [ ] 同名の既存スキルがないことを確認した

---

## Step 2: 知識ソースの変換（pdf-convert に委譲）

> **このステップは pdf-convert スキルに完全委譲する**

PDF / DOCX / PPTX ファイルを Markdown に変換し、`skills-machine/10_inbox/` に配置する。

### 委譲手順

1. pdf-convert スキルを発動する
2. 出力先: `skills-machine/10_inbox/<source-name>.md`
3. 変換品質を確認する（テーブル崩れ、画像参照の欠落など）

### スキップ条件

- `skills-machine/10_inbox/` に既に Markdown が存在する場合 → Step 3 へ

**チェックリスト**:
- [ ] Markdown ファイルが `skills-machine/10_inbox/` に配置されている
- [ ] テーブル・見出し・リストの構造が正しく変換されている
- [ ] 画像参照が適切に処理されている

---

## Step 3: 知識の蒸留（distill に委譲、スキル向けに適応）

> **このステップは distill スキルに委譲し、スキル設計向けの出力を指示する**

inbox の Markdown を読み込み、スキル化に必要な原則・パターン・手順を抽出する。

### 委譲時の追加指示

distill に以下の観点を追加指示する:

| 蒸留観点 | 抽出内容 |
|:---|:---|
| **原則・ルール** | スキルのステップに落とし込める行動指針 |
| **パターン・テンプレート** | references/ に収録する具体的なパターン |
| **判断基準** | Decision Framework、チェックリスト項目 |
| **トラブルシューティング** | よくある問題と対処法 |
| **用語・概念** | 用語集、概念間の関係 |

### 出力先

`skills-machine/20_notes/<skill-name>/` に以下を蒸留:
- `principles.md` — 原則・ルールの一覧
- `patterns.md` — パターン・テンプレート集
- `decisions.md` — 判断基準・Decision Framework
- `glossary.md` — 用語集

### スキップ条件

- `skills-machine/20_notes/` に蒸留メモが既に存在する場合 → Step 4 へ

**チェックリスト**:
- [ ] 知識ソースの主要な原則を抽出した
- [ ] スキルのステップに変換可能なパターンを特定した
- [ ] チェックリスト項目に変換可能な判断基準を特定した
- [ ] references/ に収録すべきコンテンツを特定した

---

## Step 4: スキル設計（proposal/ に設計案を出力）

> **ユーザー確認ポイント — 設計案をレビューしてもらう**

蒸留した知見をもとに、スキルの設計案を策定する。

### 4a. 設計案の構成

`skills-machine/30_proposal/<skill-name>.md` に以下を記述:

```markdown
# <Skill Name> スキル設計案

## 概要
- スキル名: <kebab-case>
- カテゴリ: <category>
- 知識ソース: <source>
- キャッチフレーズ: <one-liner>

## description（frontmatter 用）
<description テキスト — 1024 文字以内>

## ステップ構成（7-9 ステップ）
1. <Step 1 タイトル>: <概要>
2. <Step 2 タイトル>: <概要>
...

## references/ 構成
- <file1.md>: <概要>
- <file2.md>: <概要>

## Examples 案（6 個以上）
1. <Example 1 概要>
2. <Example 2 概要>
...

## Related Skills
- <skill>: <関係性>
```

### 4b. 金型基準の確認

設計段階で以下の金型基準を満たすか検証する:

| 基準 | 目標値 | 参照 |
|:---|:---|:---|
| SKILL.md 行数 | 450-600 行 | [gold-standard-analysis.md](references/gold-standard-analysis.md) |
| ステップ数 | 7-9 ステップ | 同上 |
| Examples 数 | 6 個以上 | 同上 |
| Troubleshooting | 10-12 項目 | 同上 |
| references/ ファイル数 | 3-7 ファイル | 同上 |
| description 文字数 | 1024 文字以内 | Anthropic ガイド |

### 4c. ユーザーレビュー

設計案をユーザーに提示し、以下を確認:
- ステップ構成は適切か
- references の粒度は適切か
- 不足している観点はないか
- スコープは適切か（広すぎ/狭すぎ）

### 4d. スキルパターンの選定

Anthropic 5 パターン（[skill-patterns.md](references/skill-patterns.md)）から、設計中のスキルに適合するパターンを選定する。

| パターン | 判定質問 |
|:---|:---|
| **P1: Sequential Workflow** | 明確な順序ステップで成果物を構築するか？ |
| **P2: Multi-MCP Coordination** | 複数の外部ツール/API を Phase 分離で統合するか？ |
| **P3: Iterative Refinement** | 品質基準に達するまで反復改善するか？ |
| **P4: Context-aware Tool Selection** | 状況に応じて異なるツール/手法を動的に選択するか？ |
| **P5: Domain-specific Intelligence** | 特定ドメインの専門知識を判断ロジックとして埋め込むか？ |

**選定手順**:
1. 上記 5 つの判定質問に Yes/No で回答
2. Yes が最も本質的なものを **Primary パターン** に決定
3. 該当する場合は **Secondary パターン** を併記
4. **Problem-first**（課題解決型）か **Tool-first**（ツール活用型）かを分類
5. skill-patterns.md の該当パターン設計指針（必須 4 要素）を設計に反映

> **注意**: 現在 30 スキル中 60% が Sequential パターン。新規スキルが安易に Sequential に分類されていないか自問すること。Iterative / Domain-specific の適合可能性を必ず検討する。

**チェックリスト**:
- [ ] 設計案が `skills-machine/30_proposal/` に出力されている
- [ ] 金型基準をすべて満たす設計になっている
- [ ] ユーザーのレビューと承認を得た
- [ ] description が 1024 文字以内である
- [ ] 既存スキルとの境界が明確である
- [ ] パターン（P1-P5）を選定し、Primary / Secondary を決定した
- [ ] Problem-first / Tool-first の分類を決定した

---

## Step 5: SKILL.md の構築

設計案に基づき、SKILL.md を構築する。

### 5a. YAML Frontmatter

[skill-template.md](references/skill-template.md) のテンプレートに従い、frontmatter を記述する。

必須フィールド:
- `name`: kebab-case のスキル名
- `description`: 日本語概要 + トリガーフレーズ + Do NOT use for
- `metadata.author`: `KC-Prop-Foundry`
- `metadata.version`: `1.0.0`
- `metadata.category`: カテゴリ名

オプション:
- `metadata.pattern`: スキルパターン（`sequential` / `multi-mcp` / `iterative` / `context-aware` / `domain-specific`）— [skill-patterns.md](references/skill-patterns.md) 参照
- `metadata.based-on`: 知識ソースの書誌情報

### 5b. スキル本文の構築

| セクション | 内容 | 品質基準 |
|:---|:---|:---|
| **Title + キャッチフレーズ** | `# Skill: <Title>` + 引用ブロック | 1行で本質を表現 |
| **Instructions** | ワークフロー図 + 入力/出力テーブル | ASCII で視覚的に |
| **Step 1-N** | 各ステップの詳細手順 | チェックリスト必須 |
| **Examples** | 具体的な使用例 | 6 個以上、多様なシナリオ |
| **Troubleshooting** | 問題/原因/解決策 テーブル | 10-12 項目 |
| **References** | references/ へのリンクテーブル | ファイル名 + 概要 |
| **Related Skills** | 他スキルとの連携テーブル | スキル名 + 関係 + 説明 |

### 5c. 品質基準（各ステップ内）

各ステップには以下を含める:
- **目的の明記**: なぜこのステップが必要か
- **具体的な手順**: テーブルや箇条書きで構造化
- **チェックリスト**: 5-8 項目の確認事項
- **参照リンク**: references/ の該当ファイルへのリンク（必要な場合）

### 5d. description の最終調整

```
日本語概要（1-2文）
Use when user says「...」「...」「...」（6-10個のトリガー）。
Do NOT use for: 除外ケース（2-3個）。
```

### 5e. Skill Slop 防止チェック（Distributional Convergence 対策）

LLM はスキル生成時にも distributional convergence を起こす。全スキルが「同じ構造・同じ表現・同じ粒度」に収束することを防ぐため、以下のアンチパターンを確認する。

| # | Skill Slop パターン | 検出方法 | 対策 |
|:---|:---|:---|:---|
| SS-1 | **キャッチフレーズが汎用的** | 「高品質な」「効率的に」「〇〇を支援する」等の無個性表現 | ドメインの本質を言い切る比喩・命令形を使う（例: 「知識を鋳型に流し込め」「制約された専門家を設計せよ」） |
| SS-2 | **Examples が抽象的** | Example の入力が「〇〇のPDFからスキルを作って」のようにドメイン固有名がない | 具体的な書籍名・ツール名・シナリオを含める。6例中4例以上に固有名詞を入れる |
| SS-3 | **チェックリストがドメイン非依存** | 「品質が十分か」「漏れがないか」等の汎用項目ばかり | ドメイン固有の判断基準を含める（例: data-arch なら「ACID/BASE の選択根拠が明記されている」） |
| SS-4 | **全ステップが同じ粒度** | 各ステップが同じ行数・同じチェックリスト数で均一 | 重要ステップ（核心工程）は詳細に、補助ステップは簡潔に。メリハリをつける |
| SS-5 | **Troubleshooting が想像上の問題** | 実際に遭遇したことのない汎用的なエラーばかり | 知識ソースの特性から導出される具体的な問題を含める |
| SS-6 | **references/ が画一的** | patterns.md / glossary.md / checklist.md の3点セット | 知識ソースの形態に応じた固有の reference を設計する（例: フローチャート、比較表、選定マトリクス） |
| SS-7 | **Related Skills の関係記述が薄い** | 「参照」「前段」「検証」の3語で終わる | 具体的な連携シナリオを記述する（例: 「Step 3 の蒸留結果を入力として受け取り、Step 5 で references/ に変換する」） |
| SS-8 | **description が Type A→B→C→D のテンプレ** | 日本語概要→Use when→Do NOT use for の3部構成が機械的 | ドメインの専門用語を description に含める。トリガーに口語・略語・類義語も網羅する |

> **Why**: スキルが均質化すると、Progressive Disclosure の第1層（description）で差別化できず、
> 誤ったスキルが発動するリスクが高まる。また、全スキルが同じ "金型" から出てきたように見えることで、
> ドメイン固有の知見が薄まり、スキルの実用価値が低下する。

**Skill Slop 防止の核心原則:**

- **金型は共通でも、鋳込む素材はドメイン固有** — 構造テンプレートに従いつつ、各フィールドの中身はドメインの言葉で満たす
- **既存スキルとの差別化を自問する** — 「この Examples / Troubleshooting / references/ を別のスキルに差し替えても違和感がないか？」→ 違和感がないなら Skill Slop

**チェックリスト**:
- [ ] YAML frontmatter が正しくパースできる
- [ ] description が 1024 文字以内
- [ ] 全ステップにチェックリストがある
- [ ] Examples が 6 個以上ある
- [ ] Troubleshooting が 10 項目以上ある
- [ ] References セクションが references/ と対応している
- [ ] Related Skills が定義されている
- [ ] 全体が 450-600 行に収まっている
- [ ] Skill Slop チェック（SS-1〜SS-8）に 2 つ以上該当しない

---

## Step 6: References の作成（Progressive Disclosure 第 3 層）

SKILL.md 本文に収まらない詳細情報を references/ に分離する。

### 6a. references/ の設計原則

| 原則 | 説明 |
|:---|:---|
| **必要な時だけ参照** | SKILL.md の本文で参照リンクを貼り、必要時のみ読み込ませる |
| **自己完結** | 各 reference ファイルは単体で理解できるようにする |
| **テーブル・リスト中心** | 散文より構造化データを優先 |
| **1 ファイル 1 トピック** | 複数トピックを混在させない |
| **知識ソース適合** | 知識ソースの種別（書籍/API/ベストプラクティス/実践ガイド）に応じた構成にする — [reference-design-matrix.md](references/reference-design-matrix.md) 参照 |

### 6b. ファイル命名規則

- kebab-case: `architecture-comparison.md`
- 内容を端的に表す名前
- `reference-` や `ref-` などのプレフィックスは不要

### 6c. ファイル構造

各 reference ファイルの構造:

```markdown
# <タイトル>

> <1行の概要>

## セクション 1
（テーブル、リスト、コード例で構造化）

## セクション 2
...
```

**チェックリスト**:
- [ ] 各 reference ファイルが 1 トピックに集中している
- [ ] SKILL.md 本文から全ての reference がリンクされている
- [ ] reference ファイルが自己完結している
- [ ] テーブル・リスト形式で構造化されている
- [ ] [reference-design-matrix.md](references/reference-design-matrix.md) のセルフテスト 3 項目（ST-1〜ST-3）に合格している

---

## Step 7: 品質監査（review に委譲 + 金型チェック）

> **review スキルに品質監査を委譲し、追加の金型チェックを実施する**

### 7a. review スキルへの委譲

review スキルを発動し、以下の観点でレビューを依頼:
- 構造の一貫性（既存スキルとのフォーマット統一）
- チェックリストの網羅性
- Examples の多様性と具体性
- Troubleshooting の実用性

### 7b. 金型チェック（自動）

[quality-checklist.md](references/quality-checklist.md) の全項目を確認する:

| チェック領域 | 確認項目数 |
|:---|:---|
| Anthropic ガイド準拠 | 10 項目 |
| リポジトリ規約準拠 | 6 項目 |
| 金型基準（メトリクス） | 6 項目 |
| コンテンツ品質 | 9 項目 |
| Skill Slop 防止 | 9 項目 |

### 7c. 金型比較

[gold-standard-analysis.md](references/gold-standard-analysis.md) の構造メトリクスと比較:

| メトリクス | ui-design 実績 | data-arch 実績 | 新スキル |
|:---|:---|:---|:---|
| 総行数 | 502 行 | 610 行 | 450-600 行 |
| ステップ数 | 9 | 9 | 7-9 |
| Examples | 6 | 6 | 6+ |
| Troubleshooting | 12 | 10 | 10-12 |
| references/ | 7 ファイル | 5 ファイル | 3-7 |

### 7d. 修正の実施

レビュー結果と金型チェックに基づき、SKILL.md と references/ を修正する。

### 7e. ワークフロー品質チェック（ワークフロー監査時のみ）

> **スキル鋳造ではなく、ワークフローの品質検証を行う場合に実行する**

`.agent/workflows/` のワークフロー定義と対応する CLAUDE.md テンプレートに対し、[workflow-quality-checklist.md](references/workflow-quality-checklist.md) の **5 領域 30 項目** を適用する。

**チェック手順**:

1. ワークフロー定義を精読
2. [workflow-quality-checklist.md](references/workflow-quality-checklist.md) の全項目を適用（W-A〜W-T）
3. 不合格項目を特定し修正案を提示
4. 修正を適用し再チェックで全項目通過を確認
5. 品質監査レポートを出力（対象 / チェック結果サマリー / 不合格項目と修正内容）

**並列実行パターンの検証**（追加チェック項目）:

| チェック項目 | 確認内容 | 合格基準 |
|:---|:---|:---|
| **Agent Teams セクション** | ワークフローに Agent Teams（Teammate 形式）が定義されているか | 2 Phase 以上で定義 |
| **worktree 分離指示** | ファイル変更を伴う Teammate に `isolation: worktree` が指示されているか | 変更系 Teammate 全てに指定 |
| **Plan Mode 活用** | 要件インテーク/検証フェーズで Plan Mode の活用が明記されているか | Phase 0 に必須記載 |
| **セッション管理** | 長期プロジェクトでのセッション命名・復帰方法が記載されているか | Phase 4 以降に推奨記載 |

**チェックリスト**:
- [ ] review スキルによるレビューが完了した
- [ ] 金型チェックリスト（40 項目）を全て通過した（スキル監査時）
- [ ] ワークフロー品質チェックリスト（30 項目）を全て通過した（ワークフロー監査時）
- [ ] 金型比較で基準範囲内に収まっている（スキル監査時）
- [ ] 指摘事項をすべて修正した

---

## Step 8: CLAUDE.md / INDEX.md への統合

完成したスキルをリポジトリのカタログに統合する。

### 8a. CLAUDE.md の更新

以下の 4 箇所を更新:

1. **Repository Structure**: `.agent/skills/` のツリーに新スキルを追加
2. **Skills Catalog テーブル**: 新行を追加（スキル名 / version / カテゴリ / トリガー例）
3. **カテゴリ一覧テーブル**: 新カテゴリがある場合は追加
4. **スキル間連携図**: ASCII 図に新スキルの位置と接続を追加

### 8d. CLAUDE.md 自己修正サイクル

スキル実行時にエラーや非効率なパターンが発生した場合、修正後に CLAUDE.md をルールとして更新する反復改善サイクルを運用する。

```
スキル実行 → エラー発生 → 原因特定・修正
  ↓
「Update your CLAUDE.md so you don't make that mistake again」
  ↓
CLAUDE.md にルール追記 → 次回実行時に同じ問題を回避
```

| トリガー | 追記先 | 例 |
|:---|:---|:---|
| スキル発動で誤ったスキルが選ばれた | Skills Catalog のトリガー例 | `Do NOT use for` に明確な除外を追加 |
| reference の読み込み漏れ | 該当スキルの Instructions | 「Step N で必ず reference X を読み込む」を明記 |
| 連携スキル間のデータ受け渡し失敗 | スキル連携図 | 入出力のフォーマットを具体的に記載 |
| PR 後の不整合 | notes/ ディレクトリ | PR 完了後に notes/ を更新するルールを追記 |

**原則**: 間違いは2度起こさない。修正→ルール化→再実行のサイクルで CLAUDE.md を「生きたドキュメント」に育てる。

### 8b. INDEX.md の更新

以下の 4 箇所を更新:

1. **mermaid 図**: 新スキルのノードとエッジを追加
2. **カテゴリテーブル**: 該当カテゴリの表に新行を追加
3. **逆引きテーブル**: 新スキルのユースケースを追加
4. **ライフサイクル順フロー**: 必要に応じて更新

### 8c. 整合性確認

- CLAUDE.md と INDEX.md のスキル数が一致する
- バージョン番号が SKILL.md の frontmatter と一致する
- カテゴリ名が 3 ファイル間で一致する

**チェックリスト**:
- [ ] CLAUDE.md の 4 箇所を更新した
- [ ] INDEX.md の 4 箇所を更新した
- [ ] 3 ファイル間（SKILL.md / CLAUDE.md / INDEX.md）でスキル情報が一致する
- [ ] テーブルのアライメントが崩れていない

---

## Step 9: テスト検証と引き渡し

> **Anthropic ガイドの 3 種テスト（Triggering / Functional / Performance）を実施し、品質を定量的に確認する**

### 9a. トリガーテスト（発動精度の検証）

description のトリガーフレーズが正しくスキルを発動させるか検証する。

| テスト種別 | テスト内容 | 件数 |
|:---|:---|:---|
| **Should-trigger** | description のトリガーフレーズで発動するか | 6 件（T-1〜T-6） |
| **Paraphrase** | 言い換え表現でも発動するか | 3 件 |
| **Should-NOT-trigger** | 除外ケースで誤発動しないか | 3 件（NT-1〜NT-3） |

| 指標 | 合格基準 |
|:---|:---|
| Should-trigger 発動率 | **90% 以上**（6 件中 5 件以上） |
| Paraphrase 発動率 | **70% 以上** |
| Should-NOT-trigger 誤発動率 | **0%**（誤発動ゼロ） |

**発動率が基準未満の場合**: [testing-methodology.md](references/testing-methodology.md) の Undertriggering / Overtriggering 修正戦略を適用して description を修正する。

### 9b. ファンクショナルテスト（機能検証）

BDD（Given / When / Then）形式で基本フローの正常動作を確認する。

| # | テストケース | 期待結果 |
|:---|:---|:---|
| F-1 | 基本フロー（最も一般的な入力） | 全ステップが順序通りに実行される |
| F-2 | エントリーポイント分岐 | 指定された開始ステップから正しく実行される |
| F-3 | エッジケース（最小入力） | 適切なエラーメッセージまたはフォールバック |

### 9c. パフォーマンス比較（ベースライン比較）

スキルなし（ベースライン）とスキルあり（テスト対象）の品質を比較する。

| メトリクス | ベースライン | スキルあり | 改善 |
|:---|:---|:---|:---|
| メッセージ往復数 | — | — | — |
| ユーザー補正回数 | — | — | — |
| チェックリスト通過率 | — | — | — |

> **vibes-based assessment**: 定量メトリクスでは捉えきれない品質の差（一貫性、自然さ、専門性の深さ）は、
> Anthropic が認めるように主観的評価も有効。「スキルなしの出力と比較して、明らかに専門的で再現可能か？」を自問する。
> — 詳細は [testing-methodology.md](references/testing-methodology.md) 参照

### 9d. 成果物サマリーの出力

```markdown
## スキル鋳造完了

### 作成ファイル
- `.agent/skills/<name>/SKILL.md` — スキル本体（N 行）
- `.agent/skills/<name>/references/xxx.md` — ...
- ...

### 更新ファイル
- `CLAUDE.md` — Skills Catalog に追加
- `.agent/skills/INDEX.md` — カテゴリマップに追加

### スキル概要
- 名前: <name>
- カテゴリ: <category>
- パターン: <Primary> (+ <Secondary>)
- ステップ数: N
- Examples: N 個
- Troubleshooting: N 項目
- references/: N ファイル

### テスト結果
- トリガーテスト: Should-trigger N/6, Paraphrase N/3, Should-NOT-trigger 0/3 誤発動
- ファンクショナルテスト: F-1〜F-3 [PASS/FAIL]
- パフォーマンス比較: ベースライン比 [改善/同等/要改善]

### 次のアクション
- 回帰テスト: 既存スキルへの影響がないか確認
- 他プロジェクトへのコピー: `.agent/skills/<name>/` をコピー
```

**チェックリスト**:
- [ ] トリガーテスト should-trigger 発動率 90% 以上
- [ ] トリガーテスト should-NOT-trigger 誤発動 0 件
- [ ] ファンクショナルテスト基本フロー（F-1）正常完了
- [ ] パフォーマンス比較ベースライン記録あり
- [ ] 全ファイルが正しいパスに配置されている
- [ ] YAML frontmatter がパース可能
- [ ] 成果物サマリーをユーザーに提示した

---

## Examples

### Example 1: PDF からフルパイプラインでスキル化

```
「『Effective TypeScript』の PDF からスキルを作って」

→ Step 1: エントリーポイント = Step 2（PDF あり）
→ Step 2: pdf-convert で PDF → Markdown 変換
→ Step 3: distill で 83 項目の原則を蒸留
→ Step 4: スキル設計案を作成（7 ステップ構成）→ ユーザー承認
→ Step 5: SKILL.md を構築（500 行、7 ステップ、6 Examples）
→ Step 6: references/ に 4 ファイル作成
→ Step 7: review + 金型チェック → 修正
→ Step 8: CLAUDE.md / INDEX.md を更新
→ Step 9: 完成サマリーを出力
```

### Example 2: inbox 済みの知識ソースからスキル化

```
「inbox にある 'Refactoring-UI.md' をスキルにして」

→ Step 1: エントリーポイント = Step 3（inbox 済み）
→ Step 3: distill で UI 設計原則を蒸留
→ Step 4 以降: フルパイプライン
```

### Example 3: 蒸留済みの notes からスキル化

```
「notes の data-arch メモからスキルを作って」

→ Step 1: エントリーポイント = Step 4（notes 済み）
→ Step 4: 蒸留メモから設計案を策定
→ Step 5 以降: SKILL.md 構築から完成まで
```

### Example 4: 設計案レビュー後の修正と再構築

```
「このスキル設計案を修正して、SKILL.md を作り直して」

→ Step 1: エントリーポイント = Step 5（proposal 済み）
→ Step 5: 修正済み設計案から SKILL.md を再構築
→ Step 6 以降: references + 品質監査
```

### Example 5: 新カテゴリのスキルを作成

```
「DevOps のベストプラクティスをスキル化して。カテゴリは 'devops' で」
→ Step 1: 新カテゴリ 'devops' を登録 → Step 4: 設計案に定義含む → Step 8: CLAUDE.md に追加
```

### Example 6: 既存スキルの大幅リニューアル

```
「review スキルを v7 にリニューアルしたい。新しい書籍の知見を追加して」
→ Step 1: 既存確認 → Step 2-3: 新ソース変換・蒸留 → Step 4: 差分設計
→ Step 5: 既存ベースに再構築（v7.0.0）→ Step 7: 既存版との品質比較含む監査
```

### Example 7: ワークフローの品質チェック

```
「エンジニアリング開発ワークフローをチェックして」

→ Step 1: エントリーポイント = Step 7e（ワークフローあり）
→ Step 7e: workflow-quality-checklist.md の 30 項目を適用
→ 不合格項目を特定（例: Troubleshooting 欠如、Phase 間引き渡し不足）
→ 修正を適用し再チェック
→ 品質監査レポートを出力
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| PDF 変換の品質が悪い | 複雑なレイアウト / スキャン PDF | pdf-convert の OCR モード使用。手動補正を検討 |
| 蒸留結果が浅い | 知識ソースの読み込みが不十分 | distill にチャンク分割を指示。複数パスで蒸留 |
| ステップ数が多すぎる（10+） | スコープが広すぎる | スキルを 2 つに分割。または一部を references/ に移動 |
| ステップ数が少なすぎる（5 以下） | スコープが狭すぎるか抽象度が高い | 具体的な手順に分解。サブステップを昇格 |
| description が 1024 文字を超える | トリガーフレーズが多すぎる | 類似トリガーを統合。Do NOT use for を簡潔に |
| 行数が 450 行に満たない | コンテンツ不足 | Examples / Troubleshooting を追加。ステップの詳細化 |
| 行数が 600 行を超える | 詳細すぎる | 詳細を references/ に分離。Progressive Disclosure を徹底 |
| 既存スキルと境界が曖昧 | スコープの重複 | Do NOT use for で明示的に除外。Related Skills で委譲関係を明記 |
| references/ のファイルが大きすぎる | 1 ファイルに複数トピック | トピック単位でファイルを分割 |
| CLAUDE.md の更新漏れ | 手動更新のため見落とし | Step 8 のチェックリストで 4 箇所を確認 |
| INDEX.md の mermaid 図が崩れる | ノード ID の衝突 | 既存ノード ID を確認してから新 ID を採番 |
| テスト実行でスキルが発動しない | description のトリガーが不適切 | トリガーフレーズを追加・修正 |
| ワークフロー監査で Phase 品質が低い | Phase の構造要素が不足 | W-P1〜P6 を順に確認し、テーブル・チェックリストを補完 |
| ワークフローとテンプレートの不整合 | スキル一覧がワークフローとテンプレートで異なる | W-C6 / W-T2 でマトリクスとカタログの整合を確認 |
| 生成したスキルが他のスキルと似すぎている | Skill Slop（distributional convergence） | SS-1〜SS-8 を確認。キャッチフレーズ・Examples・Troubleshooting がドメイン固有の内容になっているか検証 |
| Examples が全て「〇〇を作って」パターンに収束する | LLM のトリガー生成がテンプレ化 | ユーザー視点で口語・略語・状況説明型（「〇〇が遅いから最適化して」等）を含める |
| references/ が全スキルで同じ構成になる | Skill Slop の references 均質化 | 知識ソースの形態（書籍/ガイド/仕様書/実践知）に応じて固有の reference 構成を設計する。[reference-design-matrix.md](references/reference-design-matrix.md) 参照 |
| パターン選定で迷う | 複数パターンの特徴が当てはまる | Primary パターンを 1 つに絞り、Secondary を併記。3 パターン以上該当する場合はスキル分割を検討。[skill-patterns.md](references/skill-patterns.md) の選定フローチャート参照 |
| トリガー発動率が 90% 未満 | description のトリガーフレーズが不足 | 口語・略語・状況説明型を追加する。[testing-methodology.md](references/testing-methodology.md) の Undertriggering 修正戦略を適用 |

---

## References

| ファイル | 内容 |
|:---|:---|
| [skill-template.md](references/skill-template.md) | SKILL.md テンプレート（プレースホルダー付き、`metadata.pattern` 対応） |
| [quality-checklist.md](references/quality-checklist.md) | スキル品質チェックリスト（5 領域 40 項目 — Anthropic ガイド + リポジトリ規約 + 金型基準 + コンテンツ品質 + Skill Slop 防止） |
| [workflow-quality-checklist.md](references/workflow-quality-checklist.md) | ワークフロー品質チェックリスト（Anthropic 原則 + 構造 + Phase + テンプレート、30 項目） |
| [gold-standard-analysis.md](references/gold-standard-analysis.md) | ui-design / data-arch の構造メトリクス・パターン分類・品質指標分析 |
| [skill-patterns.md](references/skill-patterns.md) | Anthropic 5 スキルパターン定義・選定フロー・30 スキル分類・パターン別設計指針 |
| [testing-methodology.md](references/testing-methodology.md) | 3 種テスト手法（トリガー / ファンクショナル / パフォーマンス）・テンプレート・メトリクス |
| [reference-design-matrix.md](references/reference-design-matrix.md) | 知識ソース種別 → reference 構成マトリクス・4 種別設計指針・5 アンチパターン・3 セルフテスト |

---

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **pdf-convert** | 委譲先（Step 2） | Step 2 で PDF ファイルパスを渡して Markdown 変換を委譲。出力先 `inbox/<source>.md` を Step 3 の入力とする |
| **distill** | 委譲先（Step 3） | Step 3 でスキル向け 5 観点（原則・パターン・判断基準・Troubleshooting・用語）を追加指示して委譲。`notes/<skill-name>/` の 4 ファイルを Step 4 の設計入力とする |
| **review** | 委譲先（Step 7） | Step 7a で構造一貫性・チェックリスト網羅性・Examples 多様性・Troubleshooting 実用性の 4 観点を指定して品質監査を委譲。指摘事項を Step 7d で反映 |
| **agent-craft** | 姉妹スキル | ユーザーが「エージェントを作りたい」と言った場合は agent-craft に委譲。skill-forge は SKILL.md（宣言的定義）を生成し、agent-craft は実行可能なエージェント（命令的コード）を生成する |
