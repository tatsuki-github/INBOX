# Web (Next.js)

Vercel でホスティングする最小の Next.js アプリです。現時点の表示は **Hello World** のみです。

## ローカル

```bash
cd web
cp .env.example .env.local
# BASIC_AUTH_USER / BASIC_AUTH_PASSWORD を必要に応じて変更
npm install
npm run dev
```

ブラウザで `http://localhost:3000` を開き、Basic 認証ダイアログに `.env.local` の値を入力します。
認証は `proxy.ts` で全ルートに適用されます。

## Vercel

1. **Root Directory** = `web`（Settings → Build and Deployment）
2. Framework Preset: **Next.js**（自動検出）
3. Build Command / Output Directory: **デフォルトのまま**（Output Directory は空）
4. Environment Variables:
   - `BASIC_AUTH_USER`
   - `BASIC_AUTH_PASSWORD`
5. Deploy / Redeploy

### 404 NOT_FOUND / Root Directory does not exist

- Root Directory が `web` 以外 → `web` に直す
- Output Directory を触っている → 空に戻す
- 変更後は **Clear cache and Redeploy**
