---
name: agent-craft
description: >
  Claude Code カスタムエージェント（.claude/agents/）の設計・生成を支援する。
  ユーザーの要件からエージェントのロール、ツール制限、モデル選択、システムプロンプトを
  構造化し、即座に使用可能な .md ファイルを出力する。
  Use when user says「カスタムエージェントを作って」「サブエージェントを作成して」
  「エージェントを追加して」「コードレビュー用のエージェントが欲しい」
  「専用のエージェントを設計して」「エージェントチームのメンバーを作って」
  「subagent を作成して」「agent を作って」。
  Do NOT use for: MCP サーバーの設定（→ MCP ドキュメント参照）。
metadata:
  author: KC-Prop-Foundry
  version: 1.0.0
  category: development
---

# Skill: Agent Craft（カスタムエージェントの設計・生成）

> **エージェントは「制約された専門家」— 何ができるかより何をさせないかを設計せよ**

## Instructions

### ワークフロー内の位置

```
要件ヒアリング → [agent-craft] → .claude/agents/<name>.md
                    ↓
               エージェント設計
               ・ロール定義
               ・ツール制限
               ・モデル選択
               ・システムプロンプト
```

### 入力

| 入力 | 説明 | 例 |
|:---|:---|:---|
| 目的・タスク | エージェントに実行させたい作業 | 「コードレビューを自動化したい」 |
| スコープ | 対象範囲と制約 | 「TypeScript のみ」「読み取り専用」 |
| チーム構成 | 単体 or チーム内の役割 | 「テストチームの一員」 |
| 既存エージェント | 参考にしたい既存定義 | `.claude/agents/reviewer.md` |

### 出力

| 出力 | 形式 | 説明 |
|:---|:---|:---|
| エージェント定義ファイル | `.md`（YAML frontmatter 付き） | `.claude/agents/` に配置可能なファイル |
| 設計根拠 | Markdown | アーキタイプ選定・ツール制限の理由 |
| テスト計画 | Markdown | 発動/非発動/制限のテストケース |

---

## Step 1: 要件ヒアリング

エージェントの目的とスコープを 5 軸で明確化する。

### 5 軸の確認

| 軸 | 質問 | 例 |
|:---|:---|:---|
| **目的** | 何を達成するエージェントか？ | コードの品質チェック |
| **スコープ** | 何に対して作用するか？ | TypeScript ファイルのみ |
| **対象ユーザー** | 誰が使うか？ | 開発チーム全員 |
| **チーム** | 単体 or チームの一員か？ | CI/CD パイプラインの一部 |
| **頻度** | どのくらいの頻度で使うか？ | PR ごとに実行 |

### 制約の特定

| 制約タイプ | 確認内容 |
|:---|:---|
| **読み取り/書き込み** | ファイル変更を許可するか？ |
| **Bash 実行** | コマンド実行を許可するか？許可する場合どの範囲？ |
| **外部通信** | WebFetch / WebSearch を許可するか？ |
| **コスト** | 高コストモデル（Opus）を使うか、低コスト（Haiku）で十分か？ |

**チェックリスト**:
- [ ] 5 軸（目的/スコープ/対象/チーム/頻度）を確認した
- [ ] 読み取り/書き込みの制約を決定した
- [ ] Bash 実行の可否と範囲を決定した
- [ ] 外部通信の可否を決定した
- [ ] コスト要件を確認した

---

## Step 2: エージェントタイプの決定

要件に基づき、5 つのアーキタイプから最適なタイプを選定する。

### 5 アーキタイプ

| アーキタイプ | 役割 | ツール傾向 | 典型的な用途 |
|:---|:---|:---|:---|
| **Inspector** | 読み取り分析 | Read / Grep / Glob のみ | コードレビュー、セキュリティ監査、ドキュメント分析 |
| **Worker** | 実装・変更 | 全ツール | コード生成、リファクタリング、テスト作成 |
| **Coordinator** | 調整・委譲 | Task + SendMessage | チームリーダー、ワークフロー管理 |
| **Specialist** | 特定ドメイン特化 | ドメイン依存 | DB 管理、インフラ構築、特定言語エキスパート |
| **Guardian** | 品質ゲート | Read + Bash（テスト実行） | CI ゲート、品質チェック、コンプライアンス |

### 選定基準

```
ファイルを変更するか？
  ├─ No → Inspector or Guardian
  │    └─ テスト/ビルドを実行するか？
  │         ├─ Yes → Guardian
  │         └─ No → Inspector
  │
  └─ Yes → Worker, Coordinator, or Specialist
       └─ 他のエージェントに委譲するか？
            ├─ Yes → Coordinator
            └─ No → 特定ドメインに限定か？
                 ├─ Yes → Specialist
                 └─ No → Worker
```

### アーキタイプ別テンプレート

詳細は [agent-patterns.md](references/agent-patterns.md) を参照。

**チェックリスト**:
- [ ] 5 アーキタイプから最適なタイプを選定した
- [ ] 選定根拠を明確にした
- [ ] 複合タイプの場合はベースタイプを決定した

---

## Step 3: ツールアクセスの設計

最小権限の原則に基づき、必要なツールのみを許可する。

### ツールカテゴリ

| カテゴリ | ツール | 用途 |
|:---|:---|:---|
| **ファイル読み取り** | Read, Glob, Grep | コード/ドキュメントの分析 |
| **ファイル書き込み** | Edit, Write, NotebookEdit | コード/ドキュメントの変更 |
| **実行** | Bash | コマンド実行、テスト、ビルド |
| **Web** | WebFetch, WebSearch | 外部情報の取得 |
| **チーム** | Task, SendMessage, TeamCreate | マルチエージェント連携 |
| **対話** | AskUserQuestion | ユーザーへの質問 |
| **スキル** | Skill | 既存スキルの発動 |

### ツール制限の書き方

```yaml
# 許可リスト方式（推奨 — Inspector / Guardian 向け）
allowedTools:
  - Read
  - Glob
  - Grep

# 拒否リスト方式（Worker / Specialist 向け）
disallowedTools:
  - WebFetch
  - WebSearch
  - TaskCreate
```

### 最小権限の設計パターン

| アーキタイプ | 推奨ツール構成 |
|:---|:---|
| **Inspector** | `allowedTools: [Read, Glob, Grep]` |
| **Worker** | `disallowedTools: [WebFetch, WebSearch]` （書き込み許可） |
| **Coordinator** | `allowedTools: [Read, Glob, Grep, Task, SendMessage, AskUserQuestion]` |
| **Specialist** | ドメインに必要なツールのみ許可 |
| **Guardian** | `allowedTools: [Read, Glob, Grep, Bash]` |

詳細は [tools-reference.md](references/tools-reference.md) を参照。

**チェックリスト**:
- [ ] 許可リスト方式 or 拒否リスト方式を決定した
- [ ] 最小権限の原則を満たしている
- [ ] 不要なツールが許可されていない
- [ ] 必要なツールが漏れていない

---

## Step 4: モデルと動作設定の決定

エージェントの実行パラメータを設定する。

### モデル選択

| モデル | 特徴 | 推奨用途 |
|:---|:---|:---|
| **claude-opus-4-6** | 最高性能。複雑な推論 | Coordinator、複雑な Specialist |
| **claude-sonnet-4-6** | バランス型。コスパ良好 | Worker、Guardian |
| **claude-haiku-4-5** | 高速・低コスト | Inspector、単純な繰り返しタスク |

### 動作設定

| パラメータ | 説明 | デフォルト | 設定例 |
|:---|:---|:---|:---|
| **model** | 使用モデル | 親エージェントと同じ | `claude-haiku-4-5` |
| **permissionMode** | 権限モード | `default` | `bypassPermissions` |
| **maxTurns** | 最大ターン数 | 制限なし | `10` |
| **background** | バックグラウンド実行 | `false` | `true` |
| **isolation** | ワークツリー分離 | なし | `worktree` |

### permissionMode の選択

| モード | 説明 | 推奨場面 |
|:---|:---|:---|
| `default` | 各ツール実行時にユーザー確認 | 初期テスト時 |
| `acceptEdits` | ファイル編集は自動承認 | Worker |
| `bypassPermissions` | 全ツール自動承認 | CI/CD パイプライン |
| `plan` | プラン承認が必要 | 影響範囲が大きい変更 |

**チェックリスト**:
- [ ] モデルをタスクの複雑さとコストに基づいて選定した
- [ ] permissionMode を安全性とユーザビリティのバランスで選定した
- [ ] maxTurns を設定した（無限ループ防止）
- [ ] background / isolation の要否を決定した

---

## Step 5: システムプロンプトの作成

エージェントの振る舞いを定義するプロンプトを作成する。

### プロンプト構成（推奨テンプレート）

```markdown
# <Agent Name>

## Role
<1-2文でエージェントの役割を定義>

## Scope
- 対象: <対象範囲>
- 除外: <対応しない範囲>

## Instructions
1. <手順1>
2. <手順2>
3. <手順3>

## Output Format
<出力の形式と構造>

## Constraints
- <制約1>
- <制約2>
```

### プロンプト設計の原則

| 原則 | 説明 |
|:---|:---|
| **簡潔性** | 500 語以内を推奨。長いプロンプトはコンテキストを圧迫する |
| **具体性** | 「良いコードを書け」ではなく「ESLint ルールに従い...」 |
| **出力形式の指定** | 何をどの形式で出力するかを明示 |
| **スコープの明示** | やること・やらないことを明確に |
| **例の提供** | 1-2 個の入出力例を含める（大きすぎない範囲で） |

### 避けるべきパターン

| パターン | 問題 | 改善 |
|:---|:---|:---|
| 「最善を尽くして」 | 曖昧すぎる | 具体的な基準を記述 |
| 1000 語以上のプロンプト | コンテキスト消費 | 核心だけに絞る |
| ツール使い方の説明 | 冗長（モデルは知っている） | ツール利用の制約のみ |
| 「エラーが起きたら...」の網羅 | 想定しすぎ | 主要なケースのみ |

**チェックリスト**:
- [ ] 500 語以内に収まっている
- [ ] Role / Scope / Instructions / Output Format / Constraints が含まれている
- [ ] スコープ（やること/やらないこと）が明確
- [ ] 出力形式が具体的に指定されている
- [ ] 曖昧な指示がない

---

## Step 6: ファイル生成と配置

エージェント定義ファイルを生成し、適切な場所に配置する。

### 6a. ファイル形式

[agent-file-format.md](references/agent-file-format.md) を参照。

```yaml
---
name: <agent-name>
model: <model-id>
allowedTools:
  - <tool1>
  - <tool2>
modelConfig:
  maxTurns: <number>
---

<システムプロンプト（Markdown）>
```

### 6b. 配置場所

| 場所 | スコープ | 用途 |
|:---|:---|:---|
| `.claude/agents/<name>.md` | プロジェクト固有 | 特定リポジトリ専用のエージェント |
| `~/.claude/agents/<name>.md` | ユーザーグローバル | 全プロジェクトで使えるエージェント |

### 6c. ファイル命名規則

- kebab-case: `code-reviewer.md`
- 役割を端的に表す名前
- 接尾辞に `-agent` は不要（配置場所で明らか）

### 6d. ファイルの検証

- YAML frontmatter がパース可能であること
- 指定したツール名が正しいこと（[tools-reference.md](references/tools-reference.md) 参照）
- モデル ID が正しいこと

**チェックリスト**:
- [ ] YAML frontmatter が正しくパースできる
- [ ] ツール名が正しい（公式ツール名と一致）
- [ ] モデル ID が正しい
- [ ] 配置場所（プロジェクト / グローバル）を決定した
- [ ] ファイル名が kebab-case で役割を表している

---

## Step 7: 検証とテスト

生成したエージェントの動作を検証する。

### 7a. 発動テスト

| テスト | 方法 | 期待結果 |
|:---|:---|:---|
| **正常発動** | Task ツールで `subagent_type` に指定 | エージェントが起動する |
| **名前での呼び出し** | `/agent <name>` で呼び出し | エージェントが起動する |

### 7b. ツール制限テスト

| テスト | 方法 | 期待結果 |
|:---|:---|:---|
| **許可ツール** | 許可されたツールを使うタスクを依頼 | 正常に実行される |
| **制限ツール** | 制限されたツールを使うタスクを依頼 | ツールが使用されない |

### 7c. 出力品質テスト

| テスト | 確認項目 |
|:---|:---|
| **形式** | 指定した出力形式に従っているか |
| **スコープ** | 指定範囲外の作業をしていないか |
| **品質** | 出力の正確性と有用性 |

### 7d. エッジケーステスト

| テスト | 確認項目 |
|:---|:---|
| **大きなファイル** | パフォーマンスに問題がないか |
| **エラーケース** | 不正入力に対して適切にハンドリングするか |
| **maxTurns 到達** | ターン制限時に中間結果を報告するか |

**チェックリスト**:
- [ ] 発動テストが成功した
- [ ] ツール制限が正しく機能している
- [ ] 出力形式が指定通りである
- [ ] スコープ外の作業をしていない
- [ ] エッジケースを確認した

---

## Examples

### Example 1: コードレビュー専用エージェント（Inspector）

```
「TypeScript のコードレビューを自動化するエージェントを作って」

→ Step 1: 目的=品質チェック、スコープ=TS ファイル、読み取り専用
→ Step 2: Inspector タイプを選定
→ Step 3: allowedTools = [Read, Glob, Grep]
→ Step 4: model = haiku, maxTurns = 10
→ Step 5: ESLint ルール + Effective TypeScript 原則をプロンプトに
→ Step 6: .claude/agents/ts-reviewer.md に配置
→ Step 7: テスト実行で動作確認
```

### Example 2: テスト生成エージェント（Worker）

```
「既存コードに単体テストを追加するエージェントを作って」

→ Step 1: 目的=テスト生成、スコープ=全言語、書き込み必要
→ Step 2: Worker タイプを選定
→ Step 3: disallowedTools = [WebFetch, WebSearch]
→ Step 4: model = sonnet, maxTurns = 20
→ Step 5: AAA パターン + test スキルの原則をプロンプトに
→ Step 6: .claude/agents/test-writer.md に配置
```

### Example 3: チームリーダーエージェント（Coordinator）

```
「フロントエンド開発チームのリーダーエージェントを作って」

→ Step 1: 目的=タスク分配、スコープ=フロントエンド、チーム管理
→ Step 2: Coordinator タイプを選定
→ Step 3: allowedTools = [Read, Glob, Grep, Task, SendMessage, AskUserQuestion]
→ Step 4: model = opus, permissionMode = plan
→ Step 5: タスク分割・進捗管理のプロンプト
→ Step 6: .claude/agents/frontend-lead.md に配置
```

### Example 4: セキュリティ監査エージェント（Guardian）

```
「コミット前にセキュリティチェックを行うエージェントが欲しい」

→ Step 1: 目的=セキュリティ監査、スコープ=全コード、テスト実行
→ Step 2: Guardian タイプを選定
→ Step 3: allowedTools = [Read, Glob, Grep, Bash]
→ Step 4: model = sonnet, maxTurns = 15
→ Step 5: OWASP Top 10 + Bandit/ESLint セキュリティルールをプロンプトに
→ Step 6: .claude/agents/security-guard.md に配置
```

### Example 5: ドキュメント翻訳エージェント（Specialist）

```
「日本語ドキュメントを英語に翻訳するエージェントを作って」

→ Step 1: 目的=翻訳、スコープ=Markdown ファイル、書き込み必要
→ Step 2: Specialist タイプを選定
→ Step 3: allowedTools = [Read, Glob, Grep, Edit, Write]
→ Step 4: model = sonnet, maxTurns = 30
→ Step 5: 翻訳ガイドライン（技術用語表、スタイル）をプロンプトに
→ Step 6: ~/.claude/agents/translator.md（グローバル）に配置
```

### Example 6: データベース管理エージェント（Specialist）

```
「PostgreSQL のスキーマ管理と最適化を行うエージェントを作って」

→ Step 1: 目的=DB管理、スコープ=PostgreSQL、Bash 実行必要
→ Step 2: Specialist タイプを選定
→ Step 3: allowedTools = [Read, Glob, Grep, Bash, Edit, Write]
→ Step 4: model = sonnet, permissionMode = default（破壊的操作防止）
→ Step 5: PostgreSQL ベストプラクティス + マイグレーション手順をプロンプトに
→ Step 6: .claude/agents/db-admin.md に配置
→ Step 7: DROP/TRUNCATE が制限されていることを確認
```

---

## Troubleshooting

| 問題 | 原因 | 解決策 |
|:---|:---|:---|
| エージェントが起動しない | ファイルパスまたは YAML 構文エラー | YAML frontmatter をバリデーション。パスを確認 |
| 制限したツールが使われる | `allowedTools` / `disallowedTools` のスペルミス | [tools-reference.md](references/tools-reference.md) でツール名を確認 |
| 出力品質が低い | プロンプトが曖昧 | 具体的な基準と出力形式をプロンプトに追加 |
| コストが高すぎる | Opus を不必要に使用 | Haiku / Sonnet に変更。maxTurns を制限 |
| スコープ外の作業をする | プロンプトのスコープ定義が不十分 | Constraints セクションで明示的に除外 |
| エージェントが無限ループする | 終了条件がない / maxTurns 未設定 | maxTurns を設定。プロンプトに終了条件を明記 |
| チーム内で連携できない | SendMessage / Task ツールが制限されている | Coordinator には連携ツールを許可 |
| ファイル変更が反映されない | permissionMode = default でユーザーが拒否 | acceptEdits / bypassPermissions を検討 |
| Bash コマンドが失敗する | 環境差異（Windows / Mac / Linux） | プロンプトに OS 依存の注意を記載 |
| エージェントがスキルと混同される | 名前や説明が Agent Skill に類似 | エージェントとスキルの違いを明確化 |
| worktree 分離が機能しない | Git リポジトリ外で実行 | isolation は Git リポジトリ内でのみ有効 |
| 大きなリポジトリでタイムアウトする | maxTurns が小さすぎる | maxTurns を増やす。スコープを絞る |

---

## References

| ファイル | 内容 |
|:---|:---|
| [agent-file-format.md](references/agent-file-format.md) | .claude/agents/ ファイル形式のリファレンス |
| [agent-patterns.md](references/agent-patterns.md) | 5 アーキタイプのテンプレート集 |
| [tools-reference.md](references/tools-reference.md) | ツールカタログと制限パターン |

---

## Related Skills

| スキル | 関係 | 説明 |
|:---|:---|:---|
| **review** | 連携 | 生成したエージェントの品質レビュー |
| **effective-typescript** | 参考 | TypeScript 関連エージェントのプロンプト素材 |
| **robust-python** | 参考 | Python 関連エージェントのプロンプト素材 |
