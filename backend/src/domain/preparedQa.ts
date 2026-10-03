/**
 * Prepared FAQ answers (ADR 059).
 * Hit → return canned text almost as-is; miss → fall through to RAG/LLM.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { currentFiscalYear, resolveRelativeYears } from "./dates.js";
import { canonicalizeAragyokuNames } from "./aragyokuAliases.js";
import { canonicalizeSchoolNames, schoolSynonymGroups } from "./schoolAliases.js";

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

type PreparedNormCache = {
  defaultYear: number;
  rows: PreparedNormEntry[];
  /** Normalized question → unique entry (ambiguous norms omitted). */
  exact: Map<string, { entry: PreparedQaEntry; raw: string; year: number | null }>;
};

let cachedNorm: PreparedNormCache | null = null;

const SYNONYM_GROUPS: string[][] = [
  ["動画", "映像", "ビデオ"],
  // 長い表記を先に置換（コース図→画像 など）
  ["画像", "コース図", "図解", "地図", "図", "写真"],
  // 「区間順位」を先に正規化（「区間順」は接頭辞衝突するので入れない）
  ["区間順位", "区間結果"],
  ["結果", "成績", "どうだった"],
  // 優勝表現のゆれ（長い語を先に）
  ["優勝", "優勝チーム", "優勝校", "誰が勝った", "1位", "一位"],
  ["準優勝", "2位", "二位"],
  ["教えて", "見せて", "知りたい", "どこ", "ある"],
  // 学校名は schoolAliases.ts に集約（荒尾四/荒尾第四、玉高附属/玉名付属 など）
  ...schoolSynonymGroups(),
  // 荒玉大会名は aragyokuAliases.ts で longest-first 正規化（ここでは同義語置換しない）
  ["ジュニア", "県ジュニア", "ジュニア駅伝"],
  ["なごみ", "なごみ駅伝"],
  // SB 言い換え（長い語優先）
  ["自己ベスト", "ベストタイム", "自己記録", "ベスト記録", "sb", "SB"],
  ["全ての記録", "全記録", "記録一覧", "レース結果一覧"],
  ["オーダー", "区間メンバー", "区間配置", "誰が何区"],
  ["出走歴", "出場記録", "荒玉出場"],
  ["区間賞", "区間最速", "区賞"],
  ["戦力分析", "戦力予想", "数式予想", "校別展開"],
  ["徹底対策", "完全ガイド", "荒玉ガイド"],
  ["予定", "日程", "スケジュール", "開催日"],
  // 「距離」単独は区間距離へ潰さない（○区の距離・総距離と衝突しやすい）
  ["名簿", "生徒一覧", "部員名簿", "部員一覧", "陸上部名簿", "陸上部員"],
  ["差", "タイム差", "秒差", "時差"],
  ["出場できる", "出場出来る", "出られる", "出れる"],
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
  comparisonEntityCache.clear();
}

function applySynonyms(text: string): string {
  let out = text;
  for (const group of SYNONYM_GROUPS) {
    const canon = group[0]!;
    // 長い別名から置換（優勝チーム→優勝 が 優勝→… より先）
    const alts = group.slice(1).filter(Boolean).sort((a, b) => b.length - a.length);
    for (const alt of alts) {
      if (!alt || alt === canon || !out.includes(alt)) continue;
      // alt が canon の部分文字列のときだけ退避（例: 区間距離 ← 距離）
      if (canon.includes(alt)) {
        const protectedOut = out.split(canon).join("\u0000");
        out = protectedOut.split(alt).join(canon).split("\u0000").join(canon);
      } else {
        out = out.split(alt).join(canon);
      }
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
  // 「前年/前年度」も昨年と同義（今年度のひとつ前）。一昨年は defaultYear-2。
  // 「前年比/前年度比」は相対年ではないので先に退避する。
  q = q.replace(/前年比|前年度比/g, "同比");
  q = q.replace(/今年度|今季|今年/g, `${defaultYear}年`);
  q = q.replace(/一昨年|おととし/g, `${defaultYear - 2}年`);
  q = q.replace(/昨年度|前年度|前年|去年|昨年/g, `${defaultYear - 1}年`);

  // 荒尾第四→荒尾四、玉名付属→玉高附属 など（カタログ質問側も同じ正規化）
  q = canonicalizeSchoolNames(q);
  // 荒玉中体連駅伝 / 郡市駅伝 / 玉名荒尾中体連駅伝 → 荒玉（長い表記優先）
  q = canonicalizeAragyokuNames(q);

  // Drop polite / trailing noise.
  // 「とは」は裸のチーム名へ潰れると名簿定型を誤吸するため、意味を残すトークンへ置換する。
  q = q
    .replace(/[?？!！。．、,，・]/g, "")
    .replace(/(を)?(教えて|見せて|知りたい|ください|下さい|お願い|ですか|でしょうか)+$/g, "")
    .replace(/(だった|なの|かな)$/g, "")
    .replace(/って(どんな|どういう)(大会|もの)?$/g, "ってなに")
    .replace(/(は|って)?どんな(大会|もの)?$/g, "ってなに")
    .replace(/(は|って)?どういう(大会|もの)?$/g, "ってなに")
    .replace(/とは$/g, "ってなに")
    // 「〇〇のベストは？」→ 自己ベスト（区間ベスト等は触らない）
    .replace(/のベスト(?!タイム|記録)/g, "の自己ベスト")
    .replace(/(は|って)?$/g, "");

  // 「いつ開催」→「いつ」（日程同義語と組み合わせ）
  q = q.replace(/いつ開催/g, "いつ");

  // 記録系で単位なし距離（1500のベスト → 1500m）
  if (/自己ベスト|ベスト|sb|記録/i.test(q)) {
    q = q.replace(/(?<![0-9.])(800|1500|3000|5000)(?![0-9.a-zｍmメートル])/gi, "$1m");
  }

  q = applySynonyms(q.toLowerCase());
  // Compare equivalent event distances in metres (1.5km = 1500m).
  q = q.replace(/(\d+(?:\.\d+)?)\s*(km|キロメートル|キロ|m|メートル)(?![a-z])/g,
    (_, value: string, unit: string) => `${Number(value) * (/^(km|キロ)/.test(unit) ? 1000 : 1)}m`);
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
    "全ての記録",
    "オーダー",
    "出走歴",
    "区間賞",
    "区間順位",
    "戦力分析",
    "徹底対策",
    "予定",
    "欠席",
    "名簿",
    "差",
    "pdf",
    "成績表",
    "玉高附属",
    "荒尾四",
    "荒尾三",
    "荒尾海陽",
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
const ALL_RECORDS_INTENT_KEYS = ["全ての記録"] as const;

/** 長い表記優先。名簿質問で学校/所属の取り違えを防ぐ。 */
const ROSTER_ENTITY_KEYS = [
  "玉名アスリーツ",
  "玉東クラブ",
  "金栗project",
  "なごみproject", // 金栗PROJECT → なごみPROJECT 正規化後
  "玉高附属",
  "荒尾海陽",
  "荒尾四",
  "荒尾三",
  "熊本大附",
  "三加和",
  "岱明",
  "南関",
  "天水",
  "有明",
  "菊水",
  "長洲",
  "玉陵",
  "玉南",
  "玉東",
  "玉名",
  "atrc",
  "njac",
  "gz",
] as const;

function hasRosterIntent(normalized: string): boolean {
  return ROSTER_INTENT_KEYS.some((k) => normalized.includes(k));
}

function hasAllRecordsIntent(normalized: string): boolean {
  return ALL_RECORDS_INTENT_KEYS.some((k) => normalized.includes(k));
}

/** 「2位と3位の差」など順位間タイム差。準優勝定型への誤吸を防ぐ。 */
function hasTimeGapIntent(normalized: string): boolean {
  if (!normalized.includes("差")) return false;
  // 予実差・偏差などの別系統は除外し、順位/優勝系に限定
  if (/予実|偏差|格差|差出/.test(normalized)) return false;
  return (
    /優勝|準優勝|\d位|一位|二位|三位/.test(normalized) ||
    normalized.includes("位と") ||
    normalized.includes("との差")
  );
}

function rosterEntities(normalized: string): Set<string> {
  const found = new Set<string>();
  let rest = normalized.toLowerCase();
  for (const key of ROSTER_ENTITY_KEYS) {
    const k = key.toLowerCase();
    if (!rest.includes(k)) continue;
    found.add(k);
    rest = rest.split(k).join(" ");
  }
  return found;
}

/** Two-school gaps must preserve both school identities, even with similar wording. */
const comparisonEntityCache = new Map<string, Set<string>>();

function comparisonEntities(normalized: string): Set<string> {
  const cached = comparisonEntityCache.get(normalized);
  if (cached) return cached;
  const found = rosterEntities(normalized);
  if (normalized.includes("腹栄")) found.add("腹栄");
  // Remove longer 荒尾 names before detecting the historical 荒尾 school.
  if (normalized.replace(/荒尾海陽|荒尾四|荒尾三/g, "").includes("荒尾")) found.add("荒尾");
  comparisonEntityCache.set(normalized, found);
  return found;
}

function scorePair(nq: string, nCand: string): number {
  if (!nq || !nCand) return 0;
  // A leg's individual rank and a team's rank at the exchange are different
  // facts. Keep them distinct before either exact or fuzzy containment.
  const qPassing = /通過順位|通過何位|中継順位/.test(nq);
  const cPassing = /通過順位|通過何位|中継順位/.test(nCand);
  const qSplit = /区間順位|区間\d+位|区間賞/.test(nq);
  const cSplit = /区間順位|区間\d+位|区間賞/.test(nCand);
  if ((qPassing && !qSplit && cSplit && !cPassing) ||
      (qSplit && !qPassing && cPassing && !cSplit)) return 0;
  // The なごみ大会's long title includes 金栗四三, but 金栗駅伝 is a
  // separate meet. A bare 金栗 question must not inherit なごみ's results.
  if ((nq.includes("なごみ") && /金栗駅伝|金栗記念/.test(nCand) && !nCand.includes("なごみ")) ||
      (nCand.includes("なごみ") && /金栗駅伝|金栗記念/.test(nq) && !nq.includes("なごみ"))) return 0;
  const days = (text: string) => new Set([
    ...Array.from(text.matchAll(/(?:20\d{2}[-/])?(\d{1,2})[-/](\d{1,2})|(?:20\d{2}年)?(\d{1,2})月(\d{1,2})日/g),
      m => `${Number(m[1] ?? m[3])}/${Number(m[2] ?? m[4])}`),
  ]);
  if (/月|[-/]/.test(nq) && /月|[-/]/.test(nCand)) {
    const qDays = days(nq), cDays = days(nCand);
    if (qDays.size && cDays.size &&
        (qDays.size !== cDays.size || [...qDays].some(day => !cDays.has(day)))) return 0;
  }
  if ((nq.includes("朝練") && nCand.includes("夕練") && !nCand.includes("朝練")) ||
      (nq.includes("夕練") && nCand.includes("朝練") && !nCand.includes("夕練"))) return 0;
  // Similar wording is not evidence that gender, race leg or event agrees.
  // Reject explicit conflicts before containment / similarity bonuses. When
  // either side omits a dimension, leave confidence to the existing scorer.
  // 区間距離の一覧定型（特定区を列挙しない）は、○区の距離質問を落とさない。
  if (/差|何秒|取り戻|相対/.test(nq + nCand)) {
    const qSchools = comparisonEntities(nq);
    const cSchools = comparisonEntities(nCand);
    if ((qSchools.size >= 2 || cSchools.size >= 2) &&
      (qSchools.size !== cSchools.size ||
        [...qSchools].some(school => !cSchools.has(school)))) return 0;
  }

  const candDistanceOverview =
    /区間距離|総距離|合計\d/.test(nCand) && !/\d+区/.test(nCand);
  const dimensions: Array<{ pattern: RegExp; skip?: boolean }> = [
    { pattern: /(?:男子|女子)/g },
    { pattern: /\d+区/g, skip: candDistanceOverview },
    { pattern: /\d+(?:\.\d+)?m/g },
    // 区間タイム目安（9:30 vs 9:32）の取り違えを防ぐ
    { pattern: /\d{1,2}:\d{2}/g },
    // 区間N位基準タイム（5位 vs 6位）の取り違えを防ぐ
    { pattern: /\d+位/g },
  ];
  for (const { pattern, skip } of dimensions) {
    if (skip) continue;
    const queryValues = new Set(nq.match(pattern) ?? []);
    const candidateValues = new Set(nCand.match(pattern) ?? []);
    if (queryValues.size && candidateValues.size &&
      (queryValues.size !== candidateValues.size ||
        [...queryValues].some((value) => !candidateValues.has(value)))) return 0;
  }
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
  const qRoster = hasRosterIntent(nq);
  const cRoster = hasRosterIntent(nCand);
  if (qRoster !== cRoster) {
    base *= 0.4;
  }

  // 「玉名附属中の生徒一覧」が汎用「名簿を見せて」→岱明名簿へ誤吸しないよう、学校/所属を照合
  if (qRoster && cRoster) {
    const qEnt = rosterEntities(nq);
    const cEnt = rosterEntities(nCand);
    let overlap = false;
    for (const e of qEnt) {
      if (cEnt.has(e)) {
        overlap = true;
        break;
      }
    }
    if (qEnt.size > 0 && cEnt.size > 0 && !overlap) {
      base *= 0.15;
    } else if (qEnt.size > 0 && cEnt.size === 0) {
      // クエリに学校名あり・候補が汎用「名簿」のみ
      base *= 0.25;
    } else if (overlap) {
      base = Math.min(1, base + 0.12);
    }
  }

  // 「全ての記録」系は距離別SB定型への誤吸を防ぐ
  const qAll = hasAllRecordsIntent(nq);
  const cAll = hasAllRecordsIntent(nCand);
  if (qAll !== cAll) {
    base *= 0.35;
  } else if (qAll && cAll) {
    base = Math.min(1, base + 0.08);
  }

  // 「2位と3位の差」が準優勝校定型へ誤吸しない
  const qGap = hasTimeGapIntent(nq);
  const cGap = hasTimeGapIntent(nCand);
  if (qGap !== cGap) {
    base *= 0.28;
  } else if (qGap && cGap) {
    base = Math.min(1, base + 0.12);
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
): PreparedNormCache {
  if (!entries && cachedNorm && cachedNorm.defaultYear === defaultYear) {
    return cachedNorm;
  }
  const catalog = entries ?? loadPreparedQa();
  const exact = new Map<
    string,
    { entry: PreparedQaEntry; raw: string; year: number | null } | null
  >();
  const rows = catalog.map((entry) => {
    const year = preparedEntryYear(entry);
    const seenNorm = new Set<string>();
    const norms: { raw: string; norm: string }[] = [];
    for (const raw of entry.questions) {
      const norm = normalizePreparedQuestion(raw, { defaultYear });
      if (!norm || seenNorm.has(norm)) continue;
      seenNorm.add(norm);
      norms.push({ raw, norm });
      if (!exact.has(norm)) {
        exact.set(norm, { entry, raw, year });
      } else {
        // 同一正規化文が複数エントリに載る場合は exact では採用しない
        exact.set(norm, null);
      }
    }
    return { entry, year, norms };
  });
  const exactUnique = new Map<
    string,
    { entry: PreparedQaEntry; raw: string; year: number | null }
  >();
  for (const [k, v] of exact) {
    if (v) exactUnique.set(k, v);
  }
  const cache: PreparedNormCache = { defaultYear, rows, exact: exactUnique };
  if (!entries) cachedNorm = cache;
  return cache;
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

  const loaded = loadPreparedQaNormalized(defaultYear, opts?.entries);
  const catalog = loaded.rows;
  if (catalog.length === 0) return null;

  // 正規化後の完全一致は O(1)（表記ゆれを同義語で潰したあと）
  const exactHit = loaded.exact.get(nq);
  if (exactHit) {
    let score = 1;
    if (!queryHasYear && exactHit.year != null) {
      if (exactHit.year === defaultYear) score += 0.02;
      else score -= 0.05;
    }
    if (score >= HIT_THRESHOLD) {
      return {
        id: exactHit.entry.id,
        text: exactHit.entry.answer.trim(),
        score,
        matchedQuestion: exactHit.raw,
        sources: exactHit.entry.sources,
      };
    }
  }

  type Cand = {
    entry: PreparedQaEntry;
    score: number;
    matchedQuestion: string;
    year: number | null;
  };
  const scored: Cand[] = [];

  for (const row of catalog) {
    // A static help answer must not intercept a request for today's events.
    if (row.entry.id === "calendar-today" && !/方法|聞き方/.test(q)) continue;
    // A dated practice answer cannot answer an unspecified/relative day.
    if (/^(?:calx?-|practice-)/.test(row.entry.id) &&
        row.norms.every((cand) => /20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}月\d{1,2}日/.test(cand.raw)) &&
        !/20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}月\d{1,2}日/.test(q)) continue;
    // A historical entry whose aliases are all explicitly dated must not turn
    // into this year's result through fuzzy containment of a yearless query.
    // Intentionally yearless history/latest-known answers retain their aliases.
    if (
      !queryHasYear &&
      row.year != null &&
      row.year !== defaultYear &&
      row.norms.every((cand) => /20\d{2}/.test(cand.norm))
    ) {
      continue;
    }
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
    // OCR生ダンプ定型が「数式予想／校別展開／戦力分析」へ誤吸しないよう減点し、
    // 専用の予想・校別エントリを優先する。
    const wantsStructuredPreview =
      /数式|校別展開|オーダー予想|戦力予想|区間予想|戦力分析/.test(nq);
    if (wantsStructuredPreview) {
      const id = row.entry.id;
      if (id.includes("analysis-ocr")) best *= 0.25;
      else if (
        id.includes("school-expand") ||
        id.includes("校別展開") ||
        id.includes("formula-") ||
        /-(men|women)-order$/.test(id) ||
        id.includes("preview")
      ) {
        best = Math.min(1.05, best + 0.18);
      }
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
