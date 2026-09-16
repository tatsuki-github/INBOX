import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { auth } from "@/auth";

export const dynamic = "force-dynamic";

export default async function ProtectedLayout({ children }: { children: ReactNode }) {
  if (!process.env.BASIC_AUTH_USER || !process.env.BASIC_AUTH_PASSWORD) {
    throw new Error("Basic auth is not configured");
  }

  const session = await auth();
  if (!session?.user) {
    redirect("/login");
  }

  return children;
}
