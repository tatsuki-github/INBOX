# ADR 042: Web ホームページ（`inbox`）の封鎖と Git 自動デプロイ停止

- Status: Accepted
- Date: 2026-09-19

## Context

モノレポ `INBOX` には 2 つの Vercel プロジェクトが紐づく。

| プロジェクト | Root Directory | 用途 |
|:---|:---|:---|
| `inbox` | `web` | ホームページ（Next.js） |
| `idaten-line-backend` | `backend` | LINE Q&A |

コミットのたびに両方デプロイされていた。ホームページは封鎖し、**backend だけ** Git 連動デプロイを残したい。

## Decision

1. **Vercel プロジェクト `inbox` を Pause**（本番 traffic を止め、訪問者にはエラーページ）。
2. **Ignored Build Step** を `exit 0`（ビルドを常にスキップ）。
3. リポジトリの `web/vercel.json` に永続設定を書く:
   - `"git": { "deploymentEnabled": false }` — Git からのデプロイ作成自体を止める
   - `"ignoreCommand": "exit 0"` — 万一デプロイが作られてもビルドをキャンセル
4. **`idaten-line-backend` は変更しない**（ignore 未設定・Pause しない）。

## Consequences

- `main` への push では `web/` はデプロイされず、`backend/` のみ更新される。
- ホームページ URL は Pause 中アクセス不可。
- 再開手順: `vercel project resume inbox` → `web/vercel.json` の `git` / `ignoreCommand` を戻す → Ignored Build Step をクリア。

## Test strategy

- 手動: Vercel 上で `inbox.commandForIgnoringBuildStep == "exit 0"` かつ `paused == true`、
  `idaten-line-backend` は ignore なし・未 Pause を API/CLI で確認。
- コード: `web/vercel.json` に `deploymentEnabled: false` があること（レビュー）。
