import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "荒玉駅伝2026 コース動画",
  description: "荒玉駅伝2026の衛星写真コース動画ライブラリ",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
