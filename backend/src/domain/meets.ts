/**
 * Meet-kind disambiguation for KG / retrieval routing.
 * Prevents 「ジュニア駅伝」etc. from being treated as 荒玉.
 */

import { isLegAthleteQuestion } from "./legs.js";

export type MeetKind = "aragyoku" | "junior" | "nagomi" | "other" | "none";

const JUNIOR_RE = /ジュニア|県ジュニア/;
/** なごみ大会。金栗駅伝・金栗記念は別大会なので含めない */
const NAGOMI_RE = /なごみ|金栗四三/;
const ARAGYOKU_EXPLICIT_RE = /荒玉|aragyoku|中体連/;
/** Other named meets that must not fall through to aragyoku boost */
const OTHER_MEET_RE =
  /玉名市|記録会|陸上競技|チャレンジカップ|通信大会|通信陸上|新人大会|金栗駅伝|金栗記念/;

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

  // Local school + rank/leg without naming another meet → 荒玉 default
  if (
    /岱明|玉高附属|玉名付属|玉名附属|天水|有明|菊水|南関|長洲|玉陵|玉東|荒尾三|三加和/.test(q) &&
    /何位|区|前年比|総合|区間新|大会記録|区間記録/.test(q)
  ) {
    return "aragyoku";
  }

  // 「案浦竜士は何区を走った？」— unnamed race-leg defaults to club 荒玉, not 通信陸上
  if (isLegAthleteQuestion(q)) return "aragyoku";

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
  "金栗駅伝",
  "金栗記念選抜",
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
      return ["なごみ"];
    case "aragyoku":
      return ["荒玉", "中体連"];
    case "other":
      return otherMeetDriveTokens(query);
    default:
      return [];
  }
}

/** なごみ大会（金栗四三生誕の地）。金栗駅伝とは別。 */
export function isNagomiMeetQuestion(query: string): boolean {
  return NAGOMI_RE.test(query);
}

/** 3/15 金栗駅伝。なごみ大会を名乗っていないときだけ。 */
export function isKanaguriEkidenQuestion(query: string): boolean {
  return /金栗駅伝/.test(query) && !NAGOMI_RE.test(query);
}

/** Prefer result files when asking about 結果 / 順位 / 岱明成績. */
export function meetResultPathBoost(source: string, query: string): number {
  if (/\.meta\.json/.test(source)) return -200;
  const orderQ = /オーダー|\d区|何区|区は誰|ランナー/.test(query) && !/結果/.test(query);
  if (orderQ) {
    let score = 0;
    if (/区間オーダーリスト/.test(source)) score += 120;
    else if (/区間オーダー/.test(source) && !/SB予想|coverage/.test(source)) score += 60;
    if (/SB予想|coverage\.csv|開催要項|プログラム|エントリーリスト/.test(source)) score -= 50;
    if (/岱明の結果|結果\.pdf|結果\.heic/.test(source)) score -= 40;
    if (/金栗駅伝|金栗記念/.test(source) && !/なごみ/.test(source)) score -= 80;
    return score;
  }
  let score = 0;
  if (/結果|順位|タイム|成績/.test(query) && /結果|岱明の結果/.test(source)) {
    score += 40;
  }
  if (/岱明/.test(query) && /岱明の結果/.test(source) && !/オーダー/.test(query)) {
    score += 60;
  }
  return score;
}
