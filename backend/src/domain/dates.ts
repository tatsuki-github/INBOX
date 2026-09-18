/** Date mention normalization for calendar / meet / relative-year queries. */

export type DateMention = {
  year: number;
  month: number;
  day: number;
  iso: string;
  mmdd: string;
};

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function toMention(year: number, month: number, day: number): DateMention | null {
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  // Lightweight validity: reject obviously impossible days
  if (day > 30 && [4, 6, 9, 11].includes(month)) return null;
  if (month === 2 && day > 29) return null;
  return {
    year,
    month,
    day,
    iso: `${year}-${pad2(month)}-${pad2(day)}`,
    mmdd: `${pad2(month)}${pad2(day)}`,
  };
}

/**
 * Extract calendar-like date mentions from Japanese / slash / ISO text.
 * Bare M/D uses `defaultYear` (typically the current system year).
 */
export function parseDateMentions(
  text: string,
  defaultYear: number = new Date().getFullYear(),
): DateMention[] {
  const hits: DateMention[] = [];
  const seen = new Set<string>();

  const push = (m: DateMention | null) => {
    if (!m || seen.has(m.iso)) return;
    seen.add(m.iso);
    hits.push(m);
  };

  // YYYY-MM-DD or YYYY/M/D
  for (const m of text.matchAll(/\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b/g)) {
    push(toMention(Number(m[1]), Number(m[2]), Number(m[3])));
  }

  // M月D日 (optional year prefix)
  for (const m of text.matchAll(/(?:(20\d{2})\s*年\s*)?(\d{1,2})\s*月\s*(\d{1,2})\s*日/g)) {
    const year = m[1] ? Number(m[1]) : defaultYear;
    push(toMention(year, Number(m[2]), Number(m[3])));
  }

  // M/D without year (skip if already captured as YYYY/M/D above)
  for (const m of text.matchAll(/(?<!\d)(\d{1,2})\/(\d{1,2})(?!\d)/g)) {
    const full = m[0];
    const idx = m.index ?? 0;
    const before = text.slice(Math.max(0, idx - 5), idx);
    if (/20\d{2}[-/]?$/.test(before)) continue;
    if (/^\d{4}\//.test(text.slice(idx - 4, idx + full.length))) continue;
    push(toMention(defaultYear, Number(m[1]), Number(m[2])));
  }

  return hits;
}

/** True when the question looks like a date / schedule lookup. */
export function looksLikeDateQuestion(text: string): boolean {
  if (parseDateMentions(text).length > 0) return true;
  return /予定|カレンダー|スケジュール/.test(text) && /\d/.test(text);
}

/**
 * Resolve relative year words and explicit YYYY年 into calendar years.
 * Example (defaultYear=2026): 去年 → 2025, 今年 → 2026, おととし → 2024.
 */
export function resolveRelativeYears(
  text: string,
  defaultYear: number = new Date().getFullYear(),
): number[] {
  const years = new Set<number>();
  if (/今年/.test(text)) years.add(defaultYear);
  if (/去年|昨年/.test(text)) years.add(defaultYear - 1);
  if (/おととし|一昨年/.test(text)) years.add(defaultYear - 2);
  for (const m of text.matchAll(/\b(20\d{2})\s*年?/g)) {
    years.add(Number(m[1]));
  }
  return [...years].sort((a, b) => b - a);
}

/**
 * Append ISO + MMDD + relative/explicit year tokens so BM25 / KG can match
 * folder names like `0920_…`, calendar lines like `2026-09-20`, and
 * `aragyoku/transcripts/2025-男子.json` for 「去年の荒玉」.
 */
export function expandDateQuery(
  question: string,
  defaultYear: number = new Date().getFullYear(),
): string {
  const extras: string[] = [];
  for (const y of resolveRelativeYears(question, defaultYear)) {
    extras.push(String(y), `${y}年`);
  }
  const mentions = parseDateMentions(question, defaultYear);
  for (const m of mentions) {
    extras.push(m.iso, m.mmdd);
  }
  if (extras.length === 0) return question;
  // Dedupe while preserving order
  const seen = new Set<string>();
  const unique: string[] = [];
  for (const e of extras) {
    if (seen.has(e)) continue;
    seen.add(e);
    unique.push(e);
  }
  return `${question} ${unique.join(" ")}`.trim();
}
