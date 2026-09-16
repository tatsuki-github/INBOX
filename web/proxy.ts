import { NextResponse } from "next/server";

import { auth } from "@/auth";

export const proxy = auth(() => {
  if (!process.env.BASIC_AUTH_USER || !process.env.BASIC_AUTH_PASSWORD) {
    return new NextResponse("Basic auth is not configured", { status: 500 });
  }
});

export const config = {
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico).*)"],
};
