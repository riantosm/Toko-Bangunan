import { jwtVerify } from "jose";
import { NextResponse, type NextRequest } from "next/server";

const PUBLIC_PREFIXES = ["/login"];
const secret = new TextEncoder().encode(process.env.JWT_SECRET ?? "");

async function tokenIsValid(token: string): Promise<boolean> {
  if (secret.length === 0) return false;
  try {
    // HS256 inferred from the key type; jwtVerify also checks `exp`.
    await jwtVerify(token, secret, { issuer: "tokobangunan" });
    return true;
  } catch {
    return false;
  }
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = req.cookies.get("access_token")?.value;
  if (!token || !(await tokenIsValid(token))) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    const res = NextResponse.redirect(url);
    if (token) res.cookies.delete("access_token"); // stale / tampered → clear it
    return res;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.svg$).*)"],
};
