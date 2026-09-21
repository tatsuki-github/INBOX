/** Date mention normalization for calendar / meet / relative-year queries. */

export type DateMention = {
  year: number;
  month: number;
  day: number;
  iso: string;
  mmdd: string;
};

const JAPAN_TIME_ZONE = "Asia/Tokyo";

type CalendarDateParts = {
  year: number;
  month: number;
  day: number;
};

function calendarDateParts(
  now: Date,
  timeZone: string = JAPAN_TIME_ZONE,
): CalendarDateParts {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const values = new Map(
    parts
      .filter((part) => part.type !== "literal")
      .map((part) => [part.type, Number(part.value)]),
  );
  return {
    year: values.get("year") ?? now.getUTCFullYear(),
    month: values.get("month") ?? now.getUTCMonth() + 1,
    day: values.get("day") ?? now.getUTCDate(),
  };
}

/**
 * Return the Japanese fiscal year for a date (April–March).
 *
 * The corpus is organized by 年度, so a question without a year should be
 * anchored to this value rather than the calendar year in January–March.
 */
export function currentFiscalYear(now: Date = new Date()): number {
  const { year, month } = calendarDateParts(now);
  return month >= 4 ? year : year - 1;
}

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

/** Return today's calendar date in Japan Standard Time. */
export function currentDateMention(now: Date = new Date()): DateMention {
  const { year, month, day } = calendarDateParts(now);
  return toMention(year, month, day)!;
}

function shiftDate(mention: DateMention, days: number): DateMention {
  const shifted = new Date(Date.UTC(mention.year, mention.month - 1, mention.day));
  shifted.setUTCDate(shifted.getUTCDate() + days);
  return toMention(
    shifted.getUTCFullYear(),
    shifted.getUTCMonth() + 1,
    shifted.getUTCDate(),
  )!;
}

/** Resolve Japanese relative calendar-day words against the current JST date. */
export function resolveRelativeDates(
  text: string,
  now: Date = new Date(),
): DateMention[] {
  const anchor = currentDateMention(now);
  const hits: DateMention[] = [];
  const seen = new Set<string>();
  const offsets: Record<string, number> = {
    今日: 0,
    きょう: 0,
    明日: 1,
    あした: 1,
    あす: 1,
    明後日: 2,
    あさって: 2,
    明々後日: 3,
    明明後日: 3,
    しあさって: 3,
    昨日: -1,
    きのう: -1,
    一昨日: -2,
    おととい: -2,
  };
  const pattern = /明々後日|明明後日|しあさって|明後日|あさって|一昨日|おととい|昨日|きのう|明日|あした|あす|今日|きょう/g;
  for (const match of text.matchAll(pattern)) {
    const token = match[0];
    const date = shiftDate(anchor, offsets[token]!);
    if (seen.has(date.iso)) continue;
    seen.add(date.iso);
    hits.push(date);
  }
  return hits;
}

/**
 * Extract calendar-like date mentions from Japanese / slash / ISO text.
 * Bare M/D uses `defaultYear` (typically the current system year).
 */
export function parseDateMentions(
  text: string,
  defaultYear: number = currentFiscalYear(),
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
  if (parseDateMentions(text).length > 0 || resolveRelativeDates(text).length > 0) return true;
  return /予定|カレンダー|スケジュール/.test(text) && /\d/.test(text);
}

/**
 * Resolve relative year words and explicit YYYY年 into calendar years.
 * Example (defaultYear=2026): 去年 → 2025, 今年 → 2026, おととし → 2024.
 */
export function resolveRelativeYears(
  text: string,
  defaultYear: number = currentFiscalYear(),
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
  defaultYear: number = currentFiscalYear(),
  now: Date = new Date(),
): string {
  const extras: string[] = [];
  for (const y of resolveRelativeYears(question, defaultYear)) {
    extras.push(String(y), `${y}年`);
  }
  const mentions = parseDateMentions(question, defaultYear);
  for (const m of [...mentions, ...resolveRelativeDates(question, now)]) {
    extras.push(m.iso, m.mmdd);
  }

  // A normal question with no year is a question about the current fiscal
  // year. Keep intentionally broad historical/comparison questions wide.
  const broadTimeScope =
    /歴代|過去|全年度|全期間|年度別|年別|各年度|各年|毎年|近年|これまで|直近\s*[0-9０-９]+\s*年|過去\s*[0-9０-９]+\s*年|前年比|前年度比|比較/.test(
      question.normalize("NFKC"),
    );
  if (extras.length === 0 && !broadTimeScope) {
    extras.push(String(defaultYear), `${defaultYear}年度`);
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
