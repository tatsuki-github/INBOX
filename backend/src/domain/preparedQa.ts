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

type PreparedNormEntry = {
  entry: PreparedQaEntry;
  year: number | null;
  norms: { raw: string; norm: string }[];
};

let cachedNorm: { defaultYear: number; rows: PreparedNormEntry[] } | null = null;

const SYNONYM_GROUPS: string[][] = [
  ["動画", "映像", "ビデオ"],
  ["画像", "図", "図解", "コース図", "写真"],
  ["結果", "成績", "順位"],
  ["優勝", "1位", "一位"],
  ["準優勝", "2位", "二位"],
  ["教えて", "見せて", "知りたい", "どこ", "ある"],
  ["玉名付属", "玉高附属", "玉名附属", "玉名高附", "玉名附", "附中"],
  ["荒玉", "荒玉駅伝", "中体連駅伝", "荒玉中体連"],
  ["ジュニア", "県ジュニア", "ジュニア駅伝"],
  ["なごみ", "なごみ駅伝", "金栗"],
  ["自己ベスト", "sb", "SB"],
  ["予定", "日程", "スケジュール"],
  ["区間距離", "距離"],
  ["名簿", "生徒一覧", "部員名簿", "部員一覧", "陸上部員"],
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
  cachedNorm = null;
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

  // Drop polite / trailing noise.
  // 「とは」は裸のチーム名へ潰れると名簿定型を誤吸するため、意味を残すトークンへ置換する。
  q = q
    .replace(/[?？!！。．、,，・]/g, "")
    .replace(/(を)?(教えて|見せて|知りたい|ください|下さい|お願い|ですか|でしょうか)+$/g, "")
    .replace(/とは$/g, "ってなに")
    .replace(/(は|って)?$/g, "");

  q = applySynonyms(q.toLowerCase());
  // "2025年のジュニア" と "2025年ジュニア" を同一視
  q = q.replace(/の/g, "");
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

const ROSTER_INTENT_KEYS = ["名簿", "生徒", "部員"] as const;

function hasRosterIntent(normalized: string): boolean {
  return ROSTER_INTENT_KEYS.some((k) => normalized.includes(k));
}

function scorePair(nq: string, nCand: string): number {
  if (!nq || !nCand) return 0;
  const yq: string[] = nq.match(/20\d{2}/g) ?? [];
  const yc: string[] = nCand.match(/20\d{2}/g) ?? [];
  const yearsConflict =
    yq.length > 0 && yc.length > 0 && !yq.some((y) => yc.includes(y));
  // 「昨年→2025」付き質問が、年なしの「ジュニアの結果」定型に部分一致して今年へ吸われるのを防ぐ
  const queryYearOnly = yq.length > 0 && yc.length === 0;

  if (nq === nCand) return yearsConflict || queryYearOnly ? 0 : 1;

  let base = 0;
  if (nq.includes(nCand) || nCand.includes(nq)) {
    const ratio = Math.min(nq.length, nCand.length) / Math.max(nq.length, nCand.length);
    base = 0.86 + 0.1 * ratio;
  } else {
    base = jaccard(tokenize(nq), tokenize(nCand));
  }

  // 名簿・生徒一覧の意図がある側と無い側の部分一致を強く減点
  // （「いだてん岱明とは」→短い「いだてん岱明」が名簿定型を includes で誤吸するのを防ぐ）
  if (hasRosterIntent(nq) !== hasRosterIntent(nCand)) {
    base *= 0.4;
  }

  if (yearsConflict) return base * 0.35;
  if (queryYearOnly) return base * 0.4;
  return base;
}

const HIT_THRESHOLD = 0.72;
const AMBIGUITY_GAP = 0.06;

/** Infer the primary year of a prepared entry (id / tags / answer). */
export function preparedEntryYear(entry: PreparedQaEntry): number | null {
  const idMatch = entry.id.match(/(?:^|-)((?:20)\d{2})(?:-|$)/);
  if (idMatch?.[1]) return Number(idMatch[1]);
  for (const tag of entry.tags ?? []) {
    if (typeof tag === "number" && tag >= 2000 && tag <= 2100) return tag;
    if (typeof tag === "string" && /^20\d{2}$/.test(tag)) return Number(tag);
  }
  const years = [...(entry.answer?.match(/20\d{2}/g) ?? [])].map(Number);
  const uniq = [...new Set(years)];
  if (uniq.length === 1) return uniq[0]!;
  return null;
}

function loadPreparedQaNormalized(
  defaultYear: number,
  entries?: PreparedQaEntry[],
): PreparedNormEntry[] {
  if (!entries && cachedNorm && cachedNorm.defaultYear === defaultYear) {
    return cachedNorm.rows;
  }
  const catalog = entries ?? loadPreparedQa();
  const rows = catalog.map((entry) => ({
    entry,
    year: preparedEntryYear(entry),
    norms: entry.questions.map((raw) => ({
      raw,
      norm: normalizePreparedQuestion(raw, { defaultYear }),
    })),
  }));
  if (!entries) cachedNorm = { defaultYear, rows };
  return rows;
}

/**
 * Match a prepared FAQ entry. Returns null when no confident unique hit.
 * Yearless questions are treated as the current fiscal year (defaultYear).
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

  const defaultYear = opts?.defaultYear ?? currentFiscalYear(opts?.now);
  // Keep relative-year resolution available for callers/tests.
  void resolveRelativeYears(q, defaultYear);

  const nq = normalizePreparedQuestion(q, opts);
  if (!nq) return null;
  const queryHasYear = (nq.match(/20\d{2}/g) ?? []).length > 0;

  const catalog = loadPreparedQaNormalized(defaultYear, opts?.entries);
  if (catalog.length === 0) return null;

  type Cand = {
    entry: PreparedQaEntry;
    score: number;
    matchedQuestion: string;
    year: number | null;
  };
  const scored: Cand[] = [];

  for (const row of catalog) {
    let best = 0;
    let bestQ = row.entry.questions[0] ?? "";
    for (const cand of row.norms) {
      const s = scorePair(nq, cand.norm);
      if (s > best) {
        best = s;
        bestQ = cand.raw;
      }
    }
    // 年なし質問は今年度エントリをわずかに優先（同点解消・過去年への誤吸込防止）
    const year = row.year;
    if (!queryHasYear && year != null) {
      if (year === defaultYear) best += 0.02;
      else best -= 0.05;
    }
    if (best >= HIT_THRESHOLD * 0.85) {
      scored.push({ entry: row.entry, score: best, matchedQuestion: bestQ, year });
    }
  }

  scored.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if (!queryHasYear) {
      const aCur = a.year === defaultYear ? 1 : 0;
      const bCur = b.year === defaultYear ? 1 : 0;
      if (bCur !== aCur) return bCur - aCur;
    }
    return 0;
  });
  const top = scored[0];
  if (!top || top.score < HIT_THRESHOLD) return null;
  // 正規化後の完全一致（年ブースト込みで >=1）は採用。
  // 部分一致同士が僅差のときだけ曖昧として見送る。
  if (top.score < 1) {
    const second = scored[1];
    if (
      second &&
      top.entry.id !== second.entry.id &&
      top.score - second.score < AMBIGUITY_GAP
    ) {
      return null;
    }
  }

  return {
    id: top.entry.id,
    text: top.entry.answer,
    score: top.score,
    matchedQuestion: top.matchedQuestion,
    sources: top.entry.sources,
  };
}
