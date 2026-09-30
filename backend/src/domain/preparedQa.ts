/**
 * Prepared FAQ answers (ADR 059).
 * Hit → return canned text almost as-is; miss → fall through to RAG/LLM.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { currentFiscalYear, resolveRelativeYears } from "./dates.js";

export type PreparedQaEntry = {
  id: string;
  questions: string[];
  answer: string;
  sources: string[];
  tags?: string[];
};

export type PreparedQaIndex = {
  version: number;
  total: number;
  entries: PreparedQaEntry[];
};

export type PreparedQaMatch = {
  id: string;
  text: string;
  score: number;
  matchedQuestion: string;
  sources: string[];
};

const __dirname = dirname(fileURLToPath(import.meta.url));

let cached: PreparedQaEntry[] | null = null;

const SYNONYM_GROUPS: string[][] = [
  ["動画", "映像", "ビデオ"],
  ["画像", "図", "図解", "コース図", "写真"],
  ["結果", "成績", "順位"],
  ["優勝", "1位", "一位"],
  ["準優勝", "2位", "二位"],
  ["教えて", "見せて", "知りたい", "どこ", "ある"],
  ["玉名付属", "玉高附属", "玉名附属", "玉名附"],
  ["荒玉", "荒玉駅伝", "中体連駅伝", "荒玉中体連"],
  ["ジュニア", "県ジュニア", "ジュニア駅伝"],
  ["なごみ", "なごみ駅伝", "金栗"],
  ["自己ベスト", "sb", "SB"],
  ["予定", "日程", "スケジュール"],
  ["区間距離", "距離"],
];

export function defaultPreparedQaPath(): string {
  return join(__dirname, "../../data/prepared-qa.json");
}

export function loadPreparedQa(path = defaultPreparedQaPath()): PreparedQaEntry[] {
  if (cached && path === defaultPreparedQaPath()) return cached;
  try {
    const raw = JSON.parse(readFileSync(path, "utf8")) as PreparedQaIndex;
    const entries = Array.isArray(raw.entries) ? raw.entries : [];
    if (path === defaultPreparedQaPath()) cached = entries;
    return entries;
  } catch {
    return [];
  }
}

export function resetPreparedQaCache(): void {
  cached = null;
}

function applySynonyms(text: string): string {
  let out = text;
  for (const group of SYNONYM_GROUPS) {
    const canon = group[0]!;
    for (const alt of group.slice(1)) {
      if (!alt) continue;
      out = out.split(alt).join(canon);
    }
  }
  return out;
}

/** Normalize question text for fuzzy matching. */
export function normalizePreparedQuestion(
  question: string,
  opts?: { defaultYear?: number; now?: Date },
): string {
  let q = question.normalize("NFKC").trim();
  if (!q) return "";

  const defaultYear = opts?.defaultYear ?? currentFiscalYear(opts?.now);
  // Expand relative years to absolute before comparing.
  q = q.replace(/今年/g, `${defaultYear}年`);
  q = q.replace(/昨年度|一昨年/g, (m) =>
    m === "一昨年" ? `${defaultYear - 2}年` : `${defaultYear - 1}年`,
  );
  q = q.replace(/去年|昨年/g, `${defaultYear - 1}年`);

  // Drop polite / trailing noise
  q = q
    .replace(/[?？!！。．、,，・]/g, "")
    .replace(/(を)?(教えて|見せて|知りたい|ください|下さい|お願い|ですか|でしょうか)+$/g, "")
    .replace(/(は|って|とは)?$/g, "");

  q = applySynonyms(q.toLowerCase());
  q = q.replace(/\s+/g, "");
  return q;
}

function tokenize(normalized: string): string[] {
  // Prefer longer keyword chunks + year/number tokens.
  const years = normalized.match(/20\d{2}/g) ?? [];
  const nums = normalized.match(/\d+(?:\.\d+)?(?:km|区|位|分)?/g) ?? [];
  const keys = [
    "荒玉",
    "ジュニア",
    "なごみ",
    "岱明",
    "男子",
    "女子",
    "優勝",
    "準優勝",
    "区間賞",
    "大会記録",
    "コース",
    "画像",
    "動画",
    "距離",
    "ペース",
    "自己ベスト",
    "予定",
    "欠席",
    "名簿",
    "pdf",
    "成績表",
    "玉高附属",
    "天水",
    "有明",
    "菊水",
    "南関",
    "atrc",
    "金栗project",
    "gz",
    "ヘルプ",
    "使い方",
  ];
  const toks = new Set<string>();
  for (const y of years) toks.add(y);
  for (const n of nums) toks.add(n);
  for (const k of keys) {
    if (normalized.includes(k.toLowerCase()) || normalized.includes(k)) toks.add(k.toLowerCase());
  }
  // Character bigrams for short residual matching
  const compact = normalized.replace(/20\d{2}/g, "");
  for (let i = 0; i < compact.length - 1; i += 1) {
    const bg = compact.slice(i, i + 2);
    if (/[a-z0-9\u3040-\u30ff\u4e00-\u9fff]{2}/i.test(bg)) toks.add(bg);
  }
  return [...toks];
}

function jaccard(a: string[], b: string[]): number {
  if (a.length === 0 || b.length === 0) return 0;
  const as = new Set(a);
  const bs = new Set(b);
  let inter = 0;
  for (const x of as) if (bs.has(x)) inter += 1;
  const union = as.size + bs.size - inter;
  return union === 0 ? 0 : inter / union;
}

function scorePair(nq: string, nCand: string): number {
  if (!nq || !nCand) return 0;
  if (nq === nCand) return 1;
  if (nq.includes(nCand) || nCand.includes(nq)) {
    const ratio = Math.min(nq.length, nCand.length) / Math.max(nq.length, nCand.length);
    return 0.86 + 0.1 * ratio;
  }
  const jq = jaccard(tokenize(nq), tokenize(nCand));
  // Require overlapping years when both sides mention a year.
  const yq: string[] = nq.match(/20\d{2}/g) ?? [];
  const yc: string[] = nCand.match(/20\d{2}/g) ?? [];
  if (yq.length && yc.length && !yq.some((y) => yc.includes(y))) {
    return jq * 0.35;
  }
  return jq;
}

const HIT_THRESHOLD = 0.72;
const AMBIGUITY_GAP = 0.06;

/**
 * Match a prepared FAQ entry. Returns null when no confident unique hit.
 */
export function matchPreparedAnswer(
  question: string,
  opts?: {
    defaultYear?: number;
    now?: Date;
    entries?: PreparedQaEntry[];
  },
): PreparedQaMatch | null {
  const q = question.trim();
  if (!q) return null;

  // Keep relative-year resolution available for callers/tests.
  void resolveRelativeYears(q, opts?.defaultYear ?? currentFiscalYear(opts?.now));

  const nq = normalizePreparedQuestion(q, opts);
  if (!nq) return null;

  const catalog = opts?.entries ?? loadPreparedQa();
  if (catalog.length === 0) return null;

  type Cand = { entry: PreparedQaEntry; score: number; matchedQuestion: string };
  const scored: Cand[] = [];

  for (const entry of catalog) {
    let best = 0;
    let bestQ = entry.questions[0] ?? "";
    for (const candQ of entry.questions) {
      const nCand = normalizePreparedQuestion(candQ, opts);
      const s = scorePair(nq, nCand);
      if (s > best) {
        best = s;
        bestQ = candQ;
      }
    }
    if (best >= HIT_THRESHOLD * 0.85) {
      scored.push({ entry, score: best, matchedQuestion: bestQ });
    }
  }

  scored.sort((a, b) => b.score - a.score);
  const top = scored[0];
  if (!top || top.score < HIT_THRESHOLD) return null;
  const second = scored[1];
  if (second && top.entry.id !== second.entry.id && top.score - second.score < AMBIGUITY_GAP) {
    return null;
  }

  return {
    id: top.entry.id,
    text: top.entry.answer,
    score: top.score,
    matchedQuestion: top.matchedQuestion,
    sources: top.entry.sources,
  };
}
