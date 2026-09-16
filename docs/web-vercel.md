# Web (Next.js on Vercel)

リポジトリ直下の Next.js アプリです。現時点の表示は **Hello World** のみです。

## ローカル

```bash
cp .env.example .env.local
# BASIC_AUTH_USER / BASIC_AUTH_PASSWORD を必要に応じて変更
npm install
npm run dev
```

ブラウザで `http://localhost:3000` を開き、Basic 認証ダイアログに `.env.local` の値を入力します。
認証は `proxy.ts`（Next.js のリクエスト入口）で全ルートに適用されます。

## Vercel

1. このリポジトリを Import（または既存プロジェクトを Redeploy）
2. **Root Directory は空（リポジトリ直下）のまま** — `web` は使わない
3. Framework Preset: **Next.js**（自動検出）
4. Build Command / Output Directory: デフォルトのまま（Output Directory は空）
5. Environment Variables（Production / Preview 推奨）:
   - `BASIC_AUTH_USER`
   - `BASIC_AUTH_PASSWORD`
6. Deploy（設定変更後は Redeploy が必要）

### 404 NOT_FOUND になるとき

Vercel の `404 NOT_FOUND`（`This page doesn’t exist`）は、だいたい次が原因です。

- Root Directory が誤って `web` のまま（この構成では直下に Next.js がある）
- Output Directory を `.next` などに上書きしている（空に戻す）
- Framework Preset が Other / 空で、Next.js としてビルドされていない

Settings → Build and Deployment で上記を確認し、**Clear cache and Redeploy** してください。
