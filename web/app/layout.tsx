import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "INBOX",
  description: "INBOX web viewer",
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
