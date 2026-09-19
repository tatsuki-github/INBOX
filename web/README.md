# Web (Next.js)

荒玉駅伝2026 コース動画ライブラリ（Next.js App Router）。

## ローカル

```bash
cd web
cp .env.example .env.local
# AUTH_SECRET / BASIC_AUTH_USER / BASIC_AUTH_PASSWORD を設定
npm install
npm run dev
```

ブラウザで `http://localhost:3000` を開き、`/login` でユーザー名・パスワード（`.env.local` の Basic 認証用値）を入力します。
認証は [Auth.js](https://authjs.dev/)（Credentials）と `proxy.ts` で全ルートに適用されます。

## Vercel

> **封鎖中（2026-09-19〜）**: プロジェクト `inbox`（Root Directory = `web`）は
> **Paused** かつ Git 自動デプロイ無効（`vercel.json` の `git.deploymentEnabled: false` /
> `ignoreCommand: exit 0`）。コミットしても `web/` はデプロイされない。
> LINE 用の `idaten-line-backend` はそのままデプロイされる。再開時は
> `vercel project resume inbox` と `vercel.json` の git/ignore 解除が必要。詳細は
> [ADR 042](../docs/adr/042-web-homepage-deploy-seal.md)。

1. **Root Directory** = `web`（Settings → Build and Deployment）
2. Framework Preset: **Next.js**（自動検出）
3. Build Command / Output Directory: **デフォルトのまま**（Output Directory は空）
4. Environment Variables:
   - `AUTH_SECRET`（必須。例: `openssl rand -base64 32`）
   - `BASIC_AUTH_USER`
   - `BASIC_AUTH_PASSWORD`
5. Deploy / Redeploy（封鎖中は手動でも本番 traffic は Pause で止まる）

### 404 NOT_FOUND / Root Directory does not exist

- Root Directory が `web` 以外 → `web` に直す
- Output Directory を触っている → 空に戻す
- 変更後は **Clear cache and Redeploy**
