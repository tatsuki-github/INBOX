# ADR 053: LINE bot 使い方・質問例の canned 応答

- Status: Accepted
- Date: 2026-09-21

## Context

「使い方」「このボットは何ができる？」「質問例」などが RAG/LLM に流れると、
回答がぶれたり内部用語が出たりする。初めての利用者には **聞き方の例** が必要。
質問例は個人名を避け、主に荒玉駅伝でアプリ機能を網羅したい。

## Decision

1. `isHelpOrExampleQuestion` でヘルプ／質問例意図を検出する。
2. `matchCannedAnswer` が LLM・retrieve より先に `help-examples` 定型を返す（コース動画 canned より優先）。
3. 文面は個人の実名なし。例の過半は荒玉駅伝。想定Q&Aの現状カバーに合わせ、相対年（去年＝前年度）・チーム結果・区間順位・順位差・県駅伝出場・ライバル・コース地点・なごみ／ジュニア／ナイター・所属名簿・全記録・SB・大会予定を含める。
4. プレースホルダは選手名・学校名に「〇〇／○○」を使う（ADR 021 と整合。実名は入れない）。
5. 文面の正本は `backend/src/domain/canned.ts` の `buildHelpExamplesText()`。prepared FAQ の `help-examples` は短い誘導に留め、詳細は canned「使い方」へ誘導してよい。

## 不採用

| 案 | 理由 |
|:---|:-----|
| LLM に例を生成 | 遅延・幻覚・個人名混入リスク |
| Quick Reply のみ | テキスト質問「使い方」にも同じ内容が必要 |
| 選手実名入りの例 | 要件で個人名禁止 |

## テスト戦略

| 層 | 対象 | 配置 |
|:---|:---|:---|
| ドメイン単体 | matcher / 文面制約 / answer short-circuit | `backend/tests/canned.test.ts` |
| 回帰 | eval-200q meta「このボットは何ができる？」 | any_of 語をヘルプ文面に含む |

## 結果

- ヘルプ意図で即時・決定的な案内が返る
- 関連: ADR 015, ADR 016, ADR 021, ADR 044
