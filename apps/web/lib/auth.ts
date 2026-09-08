// Client-side session helpers. Token lives in a plain (non-httpOnly) cookie so
// both client components and server components can read it. Trade-off: an XSS
// bug could read it — the production approach (httpOnly cookie + refresh
// rotation) is described in Prescreening-Answers.docx Q5.

const MAX_AGE = 8 * 60 * 60; // matches API access_ttl_seconds
const KEYS = ["access_token", "role", "name"] as const;

export type Session = { access_token: string; role: string; name: string };

export function setSession(s: Session): void {
  const opts = `path=/; max-age=${MAX_AGE}; samesite=lax`;
  document.cookie = `access_token=${encodeURIComponent(s.access_token)}; ${opts}`;
  document.cookie = `role=${encodeURIComponent(s.role)}; ${opts}`;
  document.cookie = `name=${encodeURIComponent(s.name)}; ${opts}`;
}

export function clearSession(): void {
  for (const k of KEYS) document.cookie = `${k}=; path=/; max-age=0`;
}

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]+)`));
  return m ? decodeURIComponent(m[1]) : null;
}
