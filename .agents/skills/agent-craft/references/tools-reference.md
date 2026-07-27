# ツールカタログと制限パターン

> Claude Code で利用可能な全ツールのカタログと、エージェント設計向けの制限パターン。

---

## ツール一覧

### ファイル操作

| ツール名 | 機能 | 読み取り | 書き込み |
|:---|:---|:---:|:---:|
| **Read** | ファイルの読み取り（テキスト、画像、PDF） | Yes | No |
| **Write** | ファイルの新規作成・上書き | No | Yes |
| **Edit** | ファイルの部分編集（文字列置換） | No | Yes |
| **NotebookEdit** | Jupyter Notebook のセル編集 | No | Yes |
| **Glob** | ファイルパターンマッチング検索 | Yes | No |
| **Grep** | ファイル内容の正規表現検索 | Yes | No |

### 実行

| ツール名 | 機能 | リスク |
|:---|:---|:---|
| **Bash** | シェルコマンドの実行 | 高（破壊的操作の可能性） |

### Web アクセス

| ツール名 | 機能 | 外部通信 |
|:---|:---|:---:|
| **WebFetch** | URL からコンテンツを取得 | Yes |
| **WebSearch** | Web 検索の実行 | Yes |

### マルチエージェント

| ツール名 | 機能 | 用途 |
|:---|:---|:---|
| **Task** | サブエージェントの起動 | タスク委譲 |
| **SendMessage** | チームメイトへのメッセージ送信 | チーム内通信 |
| **TeamCreate** | チームの作成 | チーム管理 |
| **TeamDelete** | チームの削除 | チーム管理 |

### タスク管理

| ツール名 | 機能 | 用途 |
|:---|:---|:---|
| **TaskCreate** | タスクの作成 | タスク管理 |
| **TaskGet** | タスクの取得 | タスク管理 |
| **TaskUpdate** | タスクの更新 | タスク管理 |
| **TaskList** | タスク一覧の取得 | タスク管理 |

### 対話・制御

| ツール名 | 機能 | 用途 |
|:---|:---|:---|
| **AskUserQuestion** | ユーザーへの質問 | 要件確認 |
| **Skill** | スキルの発動 | スキル連携 |
| **EnterPlanMode** | プランモードへの移行 | 計画立案 |
| **ExitPlanMode** | プランモードからの退出 | 計画承認 |
| **EnterWorktree** | ワークツリーの作成 | 分離実行 |

---

## アーキタイプ別推奨ツール構成

### Inspector（読み取り分析）

```yaml
allowedTools:
  - Read
  - Glob
  - Grep
```

**バリエーション**:
- Web 調査付き: `+ WebFetch, WebSearch`
- 質問付き: `+ AskUserQuestion`

### Worker（実装・変更）

```yaml
disallowedTools:
  - WebFetch
  - WebSearch
  - TeamCreate
  - TeamDelete
```

**バリエーション**:
- テスト実行付き: Bash を許可
- Notebook 対応: `+ NotebookEdit`
- Web 調査付き: `disallowedTools` から Web 系を除外

### Coordinator（調整・委譲）

```yaml
allowedTools:
  - Read
  - Glob
  - Grep
  - Task
  - SendMessage
  - TeamCreate
  - TeamDelete
  - TaskCreate
  - TaskGet
  - TaskUpdate
  - TaskList
  - AskUserQuestion
```

### Specialist（特定ドメイン特化）

ドメインに応じてカスタマイズ:

```yaml
# DB Specialist の例
allowedTools:
  - Read
  - Glob
  - Grep
  - Edit
  - Write
  - Bash
```

### Guardian（品質ゲート）

```yaml
allowedTools:
  - Read
  - Glob
  - Grep
  - Bash
```

**バリエーション**:
- 質問付き: `+ AskUserQuestion`
- スキル連携: `+ Skill`

---

## ツール制限の設計パターン

### パターン 1: 最小権限（推奨）

```yaml
# 必要なツールだけを明示的に許可
allowedTools:
  - Read
  - Glob
  - Grep
```

**メリット**: 安全性が高い。新しいツールが追加されても影響しない。
**デメリット**: 必要なツールを見落とすリスク。

### パターン 2: 除外リスト

```yaml
# 危険なツールだけを除外
disallowedTools:
  - WebFetch
  - WebSearch
```

**メリット**: 柔軟性が高い。ほとんどのツールが使える。
**デメリット**: 新しいツールが自動的に許可される。

### パターン 3: ハイブリッド

ファイル上は `allowedTools` で制限し、プロンプト内で追加の行動制約を記述:

```yaml
allowedTools:
  - Read
  - Glob
  - Grep
  - Bash
```

```markdown
## Constraints
- Bash は以下のコマンドのみ実行可能:
  - `npm test`
  - `npm run lint`
  - `npm run build`
- 上記以外の Bash コマンドは実行しない
```

---

## よくあるツール設定ミス

| ミス | 問題 | 修正 |
|:---|:---|:---|
| `allowedTools` と `disallowedTools` を併用 | パースエラー | どちらか一方のみ使用 |
| ツール名のタイポ（`read` → `Read`） | ツールが利用不可 | 大文字小文字を正確に |
| Inspector に `Edit` を許可 | 読み取り専用の原則に反する | `Edit` を除外 |
| Coordinator に `Edit/Write` を許可 | 直接変更の原則に反する | サブエージェントに委譲 |
| Guardian に `Write` を許可 | 品質ゲートの原則に反する | レポートは標準出力で |
| `maxTurns` 未設定で Worker を起動 | 無限ループのリスク | 必ず設定する |
| `Bash` を無制限に許可 | 破壊的コマンドのリスク | プロンプトで制約を追加 |
