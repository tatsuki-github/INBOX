/**
 * Resolve official meet result page URLs from CSV-derived index
 * (backend/data/meet-result-urls.json).
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { resolveRelativeYears } from "./dates.js";

export type MeetResultUrlEntry = {
  title: string;
  date?: string | null;
  year?: number | null;
  urls: string[];
};

export type MeetResultUrlIndex = {
  version: number;
  meets: MeetResultUrlEntry[];
};

const __dirname = dirname(fileURLToPath(import.meta.url));

let cached: MeetResultUrlEntry[] | null = null;

export function defaultMeetResultUrlIndexPath(): string {
  return join(__dirname, "../../data/meet-result-urls.json");
}

export function loadMeetResultUrlIndex(path = defaultMeetResultUrlIndexPath()): MeetResultUrlEntry[] {
  if (cached && path === defaultMeetResultUrlIndexPath()) return cached;
  try {
    const raw = JSON.parse(readFileSync(path, "utf8")) as MeetResultUrlIndex;
    const meets = Array.isArray(raw.meets) ? raw.meets : [];
    if (path === defaultMeetResultUrlIndexPath()) cached = meets;
    return meets;
  } catch {
    return [];
  }
}

/** Reset cache (tests). */
export function resetMeetResultUrlIndexCache(): void {
  cached = null;
}

const MEET_KEYWORDS = [
  "玉名市民マラソン",
  "市民マラソン",
  "ジュニア駅伝",
  "なごみ駅伝",
  "なごみ",
  "金栗記念",
  "金栗",
  "熊本市陸上競技選手権",
  "熊本市選手権",
  "熊本市陸上",
  "熊本市記録会",
  "中学校陸上選手権",
  "中学選手権",
  "長距離記録会",
  "通信陸上",
  "荒尾選手権",
  "玉名選手権",
  "ナイター",
  "荒玉",
  "中体連",
  "混成",
  "選手権",
  "記録会",
  "駅伝",
  "マラソン",
] as const;

/** Cues too weak to match alone (need a stronger sibling cue). */
const WEAK_CUES = new Set(
  ["記録会", "選手権", "駅伝", "マラソン", "ジュニア", "混成", "なごみ"].map((s) =>
    s.normalize("NFKC").replace(/[\s　]/g, "").toLowerCase(),
  ),
);

export function wantsMeetResultUrl(query: string): boolean {
  return /結果|順位|タイム|成績|記録|公式|リンク|URL|ページ/.test(query);
}

function normalizeTitle(s: string): string {
  return s.normalize("NFKC").replace(/[\s　]/g, "").toLowerCase();
}

/** Extract overlapping cues for fuzzy meet matching. */
function titleCues(title: string): string[] {
  const n = normalizeTitle(title);
  const cues = new Set<string>();
  // longer keywords first so we record specific cues
  const sorted = [...MEET_KEYWORDS].sort((a, b) => b.length - a.length);
  for (const k of sorted) {
    const nk = normalizeTitle(k);
    if (nk.length >= 2 && n.includes(nk)) cues.add(nk);
  }
  return [...cues];
}

function scoreEntry(
  query: string,
  entry: MeetResultUrlEntry,
  years: number[],
): number {
  const q = normalizeTitle(query);
  const title = normalizeTitle(entry.title);
  const qCues = titleCues(query);
  const tCues = titleCues(entry.title);
  const shared = tCues.filter((c) => q.includes(c) || qCues.includes(c));
  const strongShared = shared.filter((c) => !WEAK_CUES.has(c));

  const placeHit =
    (q.includes("熊本市") && title.includes("熊本市")) ||
    (q.includes("熊本県") && title.includes("熊本県")) ||
    (q.includes("金栗") && title.includes("金栗")) ||
    (q.includes("なごみ") && title.includes("なごみ")) ||
    (q.includes("荒玉") && title.includes("荒玉")) ||
    (q.includes("長距離") && title.includes("長距離")) ||
    (q.includes("通信") && title.includes("通信")) ||
    (q.includes("中体連") && title.includes("中体連")) ||
    (q.includes("荒尾") && title.includes("荒尾")) ||
    (q.includes("玉名") && title.includes("玉名"));

  const titleOverlap = q.includes(title) || title.includes(q);

  // Year alone must never attach a URL; need meet-name signal
  if (!titleOverlap && shared.length === 0) return 0;
  if (!titleOverlap && strongShared.length === 0 && !placeHit) return 0;

  let score = 0;
  const y = entry.year ?? (entry.date ? Number(String(entry.date).slice(0, 4)) : NaN);
  if (years.length > 0 && Number.isFinite(y)) {
    if (years.includes(y)) score += 20;
    else score -= 25;
  }

  if (titleOverlap) score += 50;

  for (const cue of shared) {
    score += Math.min(30, cue.length * 3);
  }
  for (const cue of strongShared) {
    score += 15;
  }
  if (placeHit) score += 12;

  // Prefer 選手権 when asked; demote 記録会-only titles
  if (q.includes("選手権")) {
    if (title.includes("選手権")) score += 20;
    if (title.includes("記録会") && !title.includes("選手権")) score -= 40;
  }
  if (q.includes("記録会") && title.includes("記録会")) score += 15;
  if (q.includes("駅伝") && !title.includes("駅伝")) score -= 50;
  if (q.includes("マラソン") && !title.includes("マラソン")) score -= 50;

  // Prefer mid/long distance championship page for 熊本市選手権
  if (q.includes("熊本市") && q.includes("選手権") && title.includes("中長距離")) {
    score += 8;
  }

  if (
    /結果|順位|成績/.test(query) &&
    entry.urls.some((u) => /rel\d+|kekka|kiroku|competition/i.test(u))
  ) {
    score += 5;
  }

  return score;
}

export function findMeetResultUrls(
  query: string,
  entries: MeetResultUrlEntry[],
  opts?: { defaultYear?: number; maxUrls?: number },
): string[] {
  const q = query.trim();
  if (!q || entries.length === 0) return [];
  if (!wantsMeetResultUrl(q)) return [];

  const defaultYear = opts?.defaultYear ?? new Date().getFullYear();
  const maxUrls = opts?.maxUrls ?? 3;
  const mentioned = resolveRelativeYears(q, defaultYear);
  const years = mentioned.length > 0 ? mentioned : [defaultYear];

  let best: MeetResultUrlEntry | null = null;
  let bestScore = 0;
  for (const entry of entries) {
    if (!entry.urls?.length) continue;
    const s = scoreEntry(q, entry, years);
    if (s > bestScore) {
      bestScore = s;
      best = entry;
    }
  }

  if (!best || bestScore < 40) return [];
  return best.urls.slice(0, maxUrls);
}

export function appendMeetResultUrls(text: string, urls: string[]): string {
  const clean = urls.map((u) => u.trim()).filter((u) => /^https?:\/\//i.test(u));
  if (clean.length === 0) return text;
  const existing = new Set(text.match(/https?:\/\/[^\s]+/gi) ?? []);
  const toAdd = clean.filter((u) => !existing.has(u));
  if (toAdd.length === 0) return text;
  return `${text.trim()}\n\n結果ページ:\n${toAdd.join("\n")}`.trim();
}

/** Apply lookup + append for answer text. */
export function withMeetResultUrls(
  text: string,
  query: string,
  opts?: {
    entries?: MeetResultUrlEntry[];
    defaultYear?: number;
    maxUrls?: number;
  },
): string {
  const entries = opts?.entries ?? loadMeetResultUrlIndex();
  const urls = findMeetResultUrls(query, entries, {
    defaultYear: opts?.defaultYear,
    maxUrls: opts?.maxUrls,
  });
  return appendMeetResultUrls(text, urls);
}
