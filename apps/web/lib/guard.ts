import { cookies } from "next/headers";
import { redirect } from "next/navigation";

/** For Server Components: get the token or bounce to /login. */
export async function requireToken(): Promise<string> {
  const token = (await cookies()).get("access_token")?.value;
  if (!token) redirect("/login");
  return token;
}

/** For Server Components that also gate on role. */
export async function requireRole(...roles: string[]): Promise<string> {
  const jar = await cookies();
  const token = jar.get("access_token")?.value;
  if (!token) redirect("/login");
  const role = jar.get("role")?.value ?? "";
  if (!roles.includes(role)) redirect("/orders");
  return token;
}
