# ADR Template & Process Management Guide

> Source: Fundamentals of Software Architecture, 2nd Edition (Mark Richards & Neal Ford, O'Reilly 2025)
> Progressive Disclosure: Step 6（ADR 作成と承認判定）で参照するテンプレートとプロセスガイド
>
> **software-architecture/references/adr-template.md との差分**:
> software-architecture 版は ADR の「内容記述」に重点を置く。本テンプレートは
> ADR の「プロセス管理」（作成→レビュー→承認→追跡→更新→棚卸し）に重点を置く。

---

## ADR Template（7 セクション構造）

```markdown
# ADR-NNN: [Short descriptive title]

## Status

[RFC (deadline: YYYY-MM-DD) | Proposed | Accepted | Superseded by ADR-NNN | Rejected | Deprecated]

**Status History**:
| Date | From | To | Changed by | Reason |
|:---|:---|:---|:---|:---|
| YYYY-MM-DD | — | Proposed | [Author] | Initial creation |
| YYYY-MM-DD | Proposed | Accepted | [Approver] | Approved at [meeting/review] |

## Context

[Describe the forces at play. What situation is forcing this decision?
 Include the specific area affected (system, process, organization).
 List the alternatives being considered, concisely.
 Reference related ADRs if applicable.]

**Driving forces**:
- [Force 1: e.g., "Performance requirements have changed"]
- [Force 2: e.g., "Team size is growing from 5 to 15"]

**Constraints**:
- [Constraint 1: e.g., "Budget limited to $X"]
- [Constraint 2: e.g., "Must be compatible with existing system Y"]

## Decision

[State the decision in affirmative, commanding voice.
 "We will use..." NOT "I think we should..."
 Focus on WHY this decision was made -- this is the most important part.
 Reference the trade-off analysis and risk assessment that informed this decision.]

**Why this decision**:
- [Justification 1]
- [Justification 2]

**Why NOT the alternatives**:
- [Alternative A was rejected because...]
- [Alternative B was rejected because...]

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Trade-off 1]
- [Trade-off 2]

### Risks
- [Risk and mitigation strategy]

## Compliance

[How will this decision be governed and enforced?]

### Automated Compliance (preferred)
- [ ] [Fitness function: description, tool, threshold]

### Manual Compliance
- [ ] [Review process: frequency, reviewer, checklist]

### Compliance Review Schedule
- Next review: YYYY-MM-DD
- Review frequency: [Quarterly / Semi-annually / On trigger event]

## Alternatives

### Alternative 1: [Name]
- **Pros**: [advantages]
- **Cons**: [disadvantages]
- **Trade-off score**: [Reference to trade-off matrix if available]
- **Rejected because**: [reason]

### Alternative 2: [Name]
- **Pros**: [advantages]
- **Cons**: [disadvantages]
- **Trade-off score**: [Reference to trade-off matrix if available]
- **Rejected because**: [reason]

## Notes

- **Author**: [name]
- **Approved by**: [name or governance body]
- **Created**: [YYYY-MM-DD]
- **Last reviewed**: [YYYY-MM-DD]
- **Next review**: [YYYY-MM-DD]
- **Related ADRs**: [ADR-NNN, ADR-NNN]
- **Supersedes**: [ADR-NNN (if applicable)]
- **Superseded by**: [ADR-NNN (if applicable)]
- **DACI**: Driver=[name], Approver=[name]
- **Tags**: [architecture, security, performance, etc.]
```

---

## ADR ステータスライフサイクル

### ステータス定義

| ステータス | 意味 | 遷移元 | 遷移先 |
|:---|:---|:---|:---|
| **RFC** | フィードバック募集中（期限付き） | — | Proposed, Rejected |
| **Proposed** | 承認待ち | RFC, — | Accepted, Rejected |
| **Accepted** | 承認済み・実施中 | Proposed | Superseded, Deprecated |
| **Superseded** | 新しい ADR に置換された | Accepted | — |
| **Rejected** | 棄却された | RFC, Proposed | — |
| **Deprecated** | 対象領域が廃止された | Accepted | — |

### ステータス遷移図

```
              ┌──────────────┐
              │     RFC      │
              │ (期限付き)    │
              └──────┬───────┘
                     │
              フィードバック期限到来
                     │
              ┌──────▼───────┐
     ┌────────│   Proposed   │────────┐
     │        └──────┬───────┘        │
     │               │               │
   棄却           承認              棄却
     │               │               │
     ▼        ┌──────▼───────┐        ▼
┌─────────┐   │   Accepted   │   ┌─────────┐
│ Rejected│   └───┬──────┬───┘   │ Rejected│
└─────────┘       │      │      └─────────┘
                  │      │
           新ADRで  対象領域
           置換    の廃止
                  │      │
           ┌──────▼──┐  ┌▼──────────┐
           │Superseded│  │Deprecated │
           └─────────┘  └───────────┘
```

---

## プロセス管理ガイド

### 1. ADR 作成プロセス

```
判断の必要性を認識
  │
  ├── 緊急度が低い → RFC として公開（フィードバック期限を設定）
  │     └── 期限到来 → フィードバックを反映 → Proposed に遷移
  │
  └── 緊急度が高い → 直接 Proposed として作成
        │
        ├── 自己承認基準を満たす → Accepted に遷移
        │   （コスト閾値内 AND 他チーム影響なし AND セキュリティ影響なし）
        │
        └── エスカレーション必要 → ガバナンス体（ARB 等）に審査を依頼
              └── 承認 → Accepted に遷移
              └── 差し戻し → Context / Decision を修正 → 再審査
```

### 2. ADR レビュープロセス

| レビュー観点 | 確認事項 |
|:---|:---|
| **完全性** | 7 セクション全てが記入されているか |
| **Why の十分性** | Decision セクションで「なぜ」が十分に説明されているか |
| **トレードオフの明示** | Consequences に正・負両面が記載されているか |
| **代替案の網羅** | Alternatives に 2 つ以上の候補が記載されているか |
| **コンプライアンス** | 遵守の確認方法（自動/手動）が具体的か |
| **断定的表現** | "We will use..." 形式で記述されているか（"I think..." は不可） |

### 3. ADR 棚卸しプロセス（四半期推奨）

```
全 Accepted ADR を一覧化
  │
  各 ADR について以下を確認:
  │
  ├── Context は現在も有効か？
  │     ├── はい → Accepted を維持
  │     └── いいえ → RFC に戻して再評価
  │
  ├── 後続の ADR で Superseded されるべきか？
  │     ├── はい → Superseded に更新 + 後継 ADR へのリンクを追加
  │     └── いいえ → Accepted を維持
  │
  └── 対象領域が廃止されたか？
        ├── はい → Deprecated に更新
        └── いいえ → Accepted を維持
```

### 4. ADR の採番規則

| 方式 | 説明 | 推奨 |
|:---|:---|:---:|
| 連番（ADR-001, ADR-002, ...） | シンプル、管理しやすい | 推奨 |
| 日付ベース（ADR-20260228-001） | 作成時期が一目で分かる | 許容 |
| カテゴリプレフィックス（ARCH-001, SEC-001） | ドメイン別の管理が容易 | 許容 |

> **重要**: 一度採番した番号は変更しない。Superseded されても元の番号を保持する。

---

## 自己承認 vs エスカレーション判断マトリクス

| 判断基準 | 自己承認 | エスカレーション |
|:---|:---|:---|
| **コスト** | 閾値以内（組織で定義） | 閾値超過 |
| **他チームへの影響** | 自チーム内で完結 | 他チームに影響 |
| **セキュリティ** | セキュリティ影響なし | セキュリティ影響あり |
| **可逆性** | 容易に覆せる決定 | 覆すのが困難な決定 |
| **期間** | 短期的な影響 | 長期的な影響（1年以上） |

> **原則**: 1つでもエスカレーション条件に該当すれば、ガバナンス体に審査を依頼する。

---

## ADR の保管と発見性

### 推奨ディレクトリ構成

```
project-root/
├── docs/
│   └── adr/
│       ├── index.md          ← 全 ADR の一覧（ステータス付き）
│       ├── ADR-001-xxxx.md
│       ├── ADR-002-xxxx.md
│       └── ...
```

### index.md の構成

```markdown
# Architecture Decision Records

| ADR | Title | Status | Date | Author |
|:---|:---|:---|:---|:---|
| [ADR-001](ADR-001-xxxx.md) | [Title] | Accepted | 2026-01-15 | [Author] |
| [ADR-002](ADR-002-xxxx.md) | [Title] | Superseded by ADR-005 | 2026-02-01 | [Author] |
```

---

## 意思決定アンチパターンの検出チェックリスト

ADR 作成時に以下を確認し、アンチパターンに陥っていないかを検証する。

- [ ] **Covering Your Assets**: 決定を先送りにしていないか。最終責任時点を明確にしたか
- [ ] **Groundhog Day**: 過去に同様の決定がないか。既存 ADR を検索したか
- [ ] **Email-Driven Architecture**: 決定をメールやチャットだけで済ませていないか。ADR として記録したか
- [ ] **Analysis Paralysis**: 完璧な情報を待ち続けていないか。70% の情報で判断するルールを適用したか
- [ ] **Groupthink**: 反対意見を十分に検討したか。Alternatives に棄却理由を明記したか
- [ ] **HiPPO**: 地位の高い人の意見が無条件で通っていないか。定量的な根拠で議論したか
