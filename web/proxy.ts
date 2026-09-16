import { NextRequest, NextResponse } from "next/server";

export function proxy(request: NextRequest) {
  const user = process.env.BASIC_AUTH_USER;
  const password = process.env.BASIC_AUTH_PASSWORD;

  if (!user || !password) {
    return new NextResponse("Basic auth is not configured", { status: 500 });
  }

  const authorization = request.headers.get("authorization");
  if (authorization?.startsWith("Basic ")) {
    const encoded = authorization.slice("Basic ".length).trim();
    try {
      const decoded = atob(encoded);
      const separator = decoded.indexOf(":");
      if (separator !== -1) {
        const providedUser = decoded.slice(0, separator);
        const providedPassword = decoded.slice(separator + 1);
        if (providedUser === user && providedPassword === password) {
          return NextResponse.next();
        }
      }
    } catch {
      // Fall through to 401.
    }
  }

  return new NextResponse("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Protected"',
    },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
