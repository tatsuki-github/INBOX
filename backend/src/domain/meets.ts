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

/**
 * Distinctive path tokens for named meets that fall under MeetKind "other".
 * Longer phrases first so folder matching prefers specific meets.
 */
const OTHER_MEET_PATH_PHRASES = [
  "玉名市民マラソン",
  "市民マラソン",
  "玉名選手権",
  "荒尾選手権",
  "玉名郡ナイター",
  "ナイター",
  "通信陸上",
  "長距離記録会",
  "記録会",
  "陸上競技選手権",
  "中長距離",
  "金栗記念",
  "ジュニアオリンピック",
  "熊本市駅伝",
  "玉名駅伝",
  "熊日駅伝",
] as const;

/** Path tokens extracted from the user query for MeetKind "other". */
export function otherMeetDriveTokens(query: string): string[] {
  const q = query.trim();
  if (!q) return [];
  const tokens: string[] = [];
  for (const phrase of OTHER_MEET_PATH_PHRASES) {
    if (q.includes(phrase)) tokens.push(phrase);
  }
  if (/玉名市/.test(q) && !tokens.some((t) => t.includes("玉名市") || t.includes("市民マラソン"))) {
    tokens.push("玉名市");
  }
  return [...new Set(tokens)];
}

/** Path tokens to prefer under drive-text/大会/ for each meet kind. */
export function meetDriveTokens(kind: MeetKind, query = ""): string[] {
  switch (kind) {
    case "junior":
      return ["ジュニア"];
    case "nagomi":
      return ["なごみ", "金栗"];
    case "aragyoku":
      return ["荒玉", "中体連"];
    case "other":
      return otherMeetDriveTokens(query);
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
