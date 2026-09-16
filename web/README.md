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
認証は `proxy.ts`（Next.js のリクエスト入口）で全ルートに適用されます。

## Vercel

1. このリポジトリを Import
2. **Root Directory** を `web` に設定（Settings → General → Root Directory）
3. Environment Variables を設定（Production / Preview 推奨）:
   - `BASIC_AUTH_USER`
   - `BASIC_AUTH_PASSWORD`
4. Deploy

Framework Preset は Next.js（自動検出）で問題ありません。
