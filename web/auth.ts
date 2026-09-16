import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  providers: [
    Credentials({
      name: "Basic",
      credentials: {
        username: { label: "ユーザー名", type: "text" },
        password: { label: "パスワード", type: "password" },
      },
      authorize(credentials) {
        const expectedUser = process.env.BASIC_AUTH_USER;
        const expectedPassword = process.env.BASIC_AUTH_PASSWORD;
        if (!expectedUser || !expectedPassword) {
          return null;
        }

        const username = credentials?.username;
        const password = credentials?.password;
        if (username === expectedUser && password === expectedPassword) {
          return { id: "basic-auth", name: expectedUser };
        }
        return null;
      },
    }),
  ],
  session: { strategy: "jwt" },
  pages: {
    signIn: "/login",
  },
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      if (nextUrl.pathname === "/login") {
        return true;
      }
      if (!process.env.BASIC_AUTH_USER || !process.env.BASIC_AUTH_PASSWORD) {
        return false;
      }
      return !!auth?.user;
    },
  },
});
