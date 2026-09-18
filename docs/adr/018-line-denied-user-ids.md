# ADR 018: LINE userId 拒否リスト（env + Runtime Logs）

## 状況

LINE 公式アカウント側から友だちを削除・ブロックできない。迷惑利用への対抗として、アプリ側で特定 `userId` への回答を止めたい。
運用者が拒否対象の ID を知る手段も必要。

## 決定

1. **拒否リスト**は環境変数 `LINE_DENIED_USER_IDS`（カンマ区切り）。Git に userId を置かない。Vercel Project Env（Production）で管理する。
2. **拒否時は無応答**（`replyMessage` しない・LLM/RAG も呼ばない）。Webhook HTTP は 200。
3. **ログ**: メッセージ受信時に `line message userId=U...`、拒否時に `line denied userId=U...` を `console` 出力し、Vercel Runtime Logs で検索可能にする。**メッセージ本文はログに出さない**。
4. `event.source.userId` 欠落時は誤拒否しない（従来どおり応答）。

## 不採用

| 案 | 理由 |
|:---|:---|
| リポジトリ内 JSON の拒否リスト | 個人識別子のコミットと PR 履歴汚染 |
| 拒否時の定型返信 | 対話を続けたくないケース向け。必要なら別イテレーション |
| 表示名の自動取得・名簿紐付け | スコープ外。ログは userId のみ |

## 運用

1. 対象がボットにメッセージを送る
2. Vercel → `idaten-line-backend` → Logs で `line message userId=` を検索
3. `LINE_DENIED_USER_IDS` に追加して env 反映
4. 以降は無応答 + `line denied userId=` ログ

## 結果

- 関連: ADR 015 / 016
- 実装: `backend/src/domain/deny.ts`、`backend/src/line/webhook.ts`
