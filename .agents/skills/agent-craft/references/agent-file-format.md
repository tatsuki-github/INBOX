# エージェント定義ファイル形式リファレンス

> `.claude/agents/<name>.md` のファイル形式と各フィールドの仕様。

---

## ファイル構造

```yaml
---
# === 必須フィールド ===
name: <agent-name>           # エージェントの表示名

# === オプション: モデル ===
model: <model-id>            # 使用するモデル（省略時: 親エージェントと同じ）

# === オプション: ツール制限（どちらか一方のみ） ===
allowedTools:                # 許可リスト方式
  - <tool1>
  - <tool2>
# または
disallowedTools:             # 拒否リスト方式
  - <tool1>
  - <tool2>

# === オプション: 動作設定 ===
modelConfig:
  maxTurns: <number>         # 最大ターン数（API ラウンドトリップ）
  permissionMode: <mode>     # 権限モード
---

<システムプロンプト（Markdown 形式）>
```

---

## フィールド詳細

### name（必須）

| 項目 | 説明 |
|:---|:---|
| 型 | 文字列 |
| 用途 | Task ツールの `subagent_type` やチーム内の識別名として使用 |
| 規則 | 自由形式。スペース可。ただし kebab-case を推奨 |
| 例 | `code-reviewer`, `test-writer`, `frontend-lead` |

### model（オプション）

| 項目 | 説明 |
|:---|:---|
| 型 | 文字列（モデル ID） |
| デフォルト | 親エージェント（呼び出し元）と同じモデル |
| 選択肢 | `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5` |

| モデル ID | 略称 | 特徴 |
|:---|:---|:---|
| `claude-opus-4-6` | Opus | 最高性能。複雑な推論、長文生成 |
| `claude-sonnet-4-6` | Sonnet | バランス型。コスパ良好 |
| `claude-haiku-4-5` | Haiku | 高速・低コスト。単純タスク向き |

### allowedTools / disallowedTools（オプション）

| 項目 | 説明 |
|:---|:---|
| 型 | 文字列の配列 |
| 排他 | `allowedTools` と `disallowedTools` は同時使用不可 |
| 省略時 | 全ツールが利用可能 |

**ツール名一覧**（[tools-reference.md](tools-reference.md) も参照）:

```
Read, Write, Edit, Glob, Grep, Bash,
NotebookEdit, WebFetch, WebSearch,
Task, SendMessage, TeamCreate, TeamDelete,
AskUserQuestion, Skill,
EnterPlanMode, ExitPlanMode, EnterWorktree,
TaskCreate, TaskGet, TaskUpdate, TaskList
```

### modelConfig.maxTurns（オプション）

| 項目 | 説明 |
|:---|:---|
| 型 | 正の整数 |
| 用途 | エージェントの最大 API ラウンドトリップ数を制限 |
| 推奨 | Inspector: 5-10、Worker: 15-30、Coordinator: 20-50 |
| 省略時 | 制限なし（無限ループのリスクあり） |

### modelConfig.permissionMode（オプション）

| モード | 説明 |
|:---|:---|
| `default` | 各ツール実行時にユーザー確認を求める |
| `acceptEdits` | ファイル編集（Edit/Write）を自動承認 |
| `bypassPermissions` | 全ツール実行を自動承認 |
| `plan` | プランモードでの承認が必要 |
| `dontAsk` | ユーザーに質問しない |

---

## 配置場所

| パス | スコープ | 説明 |
|:---|:---|:---|
| `.claude/agents/<name>.md` | プロジェクトローカル | そのリポジトリでのみ利用可能 |
| `~/.claude/agents/<name>.md` | ユーザーグローバル | 全プロジェクトで利用可能 |

### 優先順位

プロジェクトローカルとグローバルに同名ファイルがある場合、**プロジェクトローカルが優先**。

---

## 呼び出し方法

### Task ツール経由

```json
{
  "subagent_type": "<agent-name>",
  "prompt": "タスクの説明",
  "name": "teammate-name"
}
```

### チーム内でのスポーン

```json
{
  "subagent_type": "<agent-name>",
  "prompt": "タスクの説明",
  "team_name": "my-team",
  "name": "agent-role"
}
```

---

## 完全な例

### Inspector 型の例

```yaml
---
name: ts-reviewer
model: claude-haiku-4-5
allowedTools:
  - Read
  - Glob
  - Grep
modelConfig:
  maxTurns: 10
---

# TypeScript Code Reviewer

## Role
TypeScript コードの品質をレビューし、改善提案を出力する読み取り専用エージェント。

## Scope
- 対象: `.ts`, `.tsx` ファイル
- 除外: テストファイル（`*.test.ts`, `*.spec.ts`）、設定ファイル

## Instructions
1. 指定されたファイルまたはディレクトリの TypeScript コードを読み取る
2. 以下の観点でレビューする:
   - 型安全性（any の使用、型の絞り込み）
   - エラーハンドリング
   - 命名規則
   - コードの複雑度
3. 問題点と改善提案を構造化して出力する

## Output Format
問題ごとに: ファイルパス、行番号、問題の説明、改善案を記載。
重要度を Critical / Warning / Info の 3 段階で分類する。

## Constraints
- ファイルの変更は行わない
- テストファイルはレビュー対象外
- 1 ファイルあたり最大 10 個の指摘に制限する
```
