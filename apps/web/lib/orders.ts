/**
 * Parse the `?after=` keyset cursor from a raw search-param value.
 * Returns `undefined` for missing / non-numeric / non-positive input so a
 * tampered URL simply falls back to the first page instead of 500-ing.
 */
export function parseCursor(raw: string | undefined): number | undefined {
  if (!raw) return undefined;
  const n = Number(raw);
  return Number.isInteger(n) && n > 0 ? n : undefined;
}
