/**
 * LINE userId deny-list helpers (env-backed, no PII in repo).
 */

export function parseDeniedUserIds(raw: string | undefined): Set<string> {
  if (!raw || !raw.trim()) return new Set();
  const ids = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  return new Set(ids);
}

export function isDeniedUserId(
  userId: string | undefined | null,
  denied: Set<string>,
): boolean {
  if (!userId || denied.size === 0) return false;
  return denied.has(userId);
}
