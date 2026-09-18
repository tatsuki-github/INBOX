/**
 * Meet-kind disambiguation for KG / retrieval routing.
 * Prevents 「ジュニア駅伝」etc. from being treated as 荒玉.
 */

export type MeetKind = "aragyoku" | "junior" | "nagomi" | "other" | "none";

const JUNIOR_RE = /ジュニア|県ジュニア/;
const NAGOMI_RE = /なごみ|金栗四三|金栗/;
const ARAGYOKU_EXPLICIT_RE = /荒玉|aragyoku|中体連/;
/** Other named meets that must not fall through to aragyoku boost */
const OTHER_MEET_RE = /玉名市|記録会|陸上競技|チャレンジカップ|通信大会|新人大会/;

export function detectMeetKind(query: string): MeetKind {
  const q = query.trim();
  if (!q) return "none";

  // Named non-aragyoku meets win even if the query also contains 駅伝
  if (JUNIOR_RE.test(q)) return "junior";
  if (NAGOMI_RE.test(q)) return "nagomi";
  if (OTHER_MEET_RE.test(q) && !ARAGYOKU_EXPLICIT_RE.test(q)) return "other";

  if (ARAGYOKU_EXPLICIT_RE.test(q)) return "aragyoku";

  // Historical winners / 歴代 without another meet → club default 荒玉
  if (/優勝|歴代/.test(q) && /駅伝|大会/.test(q)) return "aragyoku";
  if (/優勝|歴代/.test(q) && !/大会/.test(q)) return "aragyoku";

  // Bare 駅伝 (club default) — but never when another meet was already matched above
  if (/駅伝/.test(q)) return "aragyoku";

  return "none";
}

export function isAragyokuCorpusSource(source: string): boolean {
  return (
    source === "aragyoku" ||
    source.startsWith("aragyoku/") ||
    source.startsWith("ekiden-ocr/")
  );
}

/** Path tokens to prefer under drive-text/大会/ for each meet kind. */
export function meetDriveTokens(kind: MeetKind): string[] {
  switch (kind) {
    case "junior":
      return ["ジュニア"];
    case "nagomi":
      return ["なごみ", "金栗"];
    case "aragyoku":
      return ["荒玉", "中体連"];
    default:
      return [];
  }
}

/** Prefer result files when asking about 結果 / 順位 / 岱明成績. */
export function meetResultPathBoost(source: string, query: string): number {
  let score = 0;
  if (/結果|順位|タイム|成績/.test(query) && /結果|岱明の結果/.test(source)) {
    score += 40;
  }
  if (/岱明/.test(query) && /岱明の結果/.test(source)) {
    score += 60;
  }
  return score;
}
