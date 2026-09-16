import { authenticate } from "./actions";

type LoginPageProps = {
  searchParams: Promise<{ error?: string }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { error } = await searchParams;
  const configured = Boolean(process.env.BASIC_AUTH_USER && process.env.BASIC_AUTH_PASSWORD);

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="eyebrow">ARATAMA EKIDEN 2026</div>
        <h1>ログイン</h1>
        <p className="login-copy">コース動画ライブラリは Basic 認証（Auth.js）で保護されています。</p>
        {!configured ? (
          <p className="login-error">BASIC_AUTH_USER / BASIC_AUTH_PASSWORD が未設定です。</p>
        ) : (
          <form action={authenticate} className="login-form">
            <label>
              ユーザー名
              <input autoComplete="username" name="username" required type="text" />
            </label>
            <label>
              パスワード
              <input autoComplete="current-password" name="password" required type="password" />
            </label>
            {error === "invalid" ? <p className="login-error">ユーザー名またはパスワードが正しくありません。</p> : null}
            <button type="submit">ログイン</button>
          </form>
        )}
      </section>
    </main>
  );
}
