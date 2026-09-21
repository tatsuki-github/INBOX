import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isLegAthleteQuestion } from "../domain/legs.js";
import { isKanaguriEkidenQuestion, isNagomiMeetQuestion } from "../domain/meets.js";

export type RagChunk = {
  id: string;
  source: string;
  text: string;
  metadata?: Record<string, unknown>;
};

export type RagIndex = {
  version: number;
  corpus: string;
  chunk_count: number;
  chunks: RagChunk[];
};

export type RetrievedChunk = {
  chunk: RagChunk;
  score: number;
};

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Only allow reading the packaged index under backend/data. */
export function defaultIndexPath(): string {
  return join(__dirname, "../../data/rag_index.json");
}

const STOPWORDS = new Set([
  "です",
  "ます",
  "した",
  "して",
  "ある",
  "いる",
  "する",
  "なる",
  "よう",
  "こと",
  "もの",
  "ため",
  "the",
  "a",
  "an",
  "is",
  "are",
  "of",
  "to",
  "and",
]);

/**
 * Shared tokenizer (RAG + aligned with KG expectations).
 * NFKC normalize, keep ISO dates, preserve MMDD-like tokens, CJK bigrams.
 */
export function tokenize(text: string): string[] {
  const lower = text.normalize("NFKC").toLowerCase();
  const isoDates = lower.match(/20\d{2}-\d{2}-\d{2}/g) ?? [];
  const withoutIso = lower.replace(/20\d{2}-\d{2}-\d{2}/g, " ");
  const tokens = withoutIso.match(
    /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]+|[\w\d]+/gu,
  );
  const out: string[] = [...isoDates];
  if (!tokens) {
    return out;
  }
  for (const t of tokens) {
    if (STOPWORDS.has(t)) continue;
    if (/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/u.test(t) && t.length > 1) {
      out.push(t);
      for (let i = 0; i < t.length - 1; i += 1) {
        out.push(t.slice(i, i + 2));
      }
    } else {
      out.push(t);
    }
  }
  return out;
}

const NON_NAME_HINTS = new Set([
  "自分",
  "私",
  "俺",
  "僕",
  "誰",
  "何",
  "最新",
  "今",
  "今年",
  "去年",
  "昨年",
  "今季",
  "今年度",
  "前回",
  "今回",
  "自己ベスト",
  "ベストタイム",
  "自己記録",
  "ベスト記録",
  "ベスト",
  "記録",
  "タイム",
  "教えて",
  "知りたい",
]);

/**
 * Extract athlete-name-like tokens for SB CSV row matching.
 * Supports 「Xの…」「X 3000m」「X自己ベスト」 forms.
 */
export function extractAthleteNameHints(query: string): string[] {
  const q = query.trim();
  const hints: string[] = [];
  const push = (s: string) => {
    const t = s.trim();
    if (!t || t.length > 12) return;
    if (NON_NAME_HINTS.has(t)) return;
    if (hints.includes(t)) return;
    hints.push(t);
  };
  const cjk = "[\\u3400-\\u9fff\\uf900-\\ufaff\\u{20000}-\\u{2fa1f}]";
  const nameTok = `(?:[A-Za-z]{2,}|[ァ-ヶヴー]{1,8}|${cjk}{1,8})`;

  for (const m of q.matchAll(
    new RegExp(`(${nameTok})(?:[（(][^）)]{1,24}[）)])?の`, "gu"),
  )) {
    push(m[1]!);
  }
  // 「森 3000m」「今村昇磨 1500m自己ベスト」「FESTUS 5000m SB」
  for (const m of q.matchAll(
    new RegExp(
      `(${nameTok})(?:[（(][^）)]{1,24}[）)])?(?:\\s+)?(?=\\d+\\s*(?:m|km)|自己ベスト|ベストタイム|自己記録|\\bSB\\b|\\bPB\\b)`,
      "giu",
    ),
  )) {
    push(m[1]!);
  }
  // 「案浦竜士は何区を走った？」「倉田裕斗は2025年何区？」
  for (const m of q.matchAll(new RegExp(`(${nameTok})は.{0,20}何区`, "gu"))) {
    push(m[1]!);
  }
  return hints;
}

/** Boost when chunk contains an exact CSV name cell (line-start `Name,`). */
export function csvNameRowBoost(text: string, names: string[]): number {
  if (names.length === 0) return 0;
  let boost = 0;
  for (const name of names) {
    const esc = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    if (new RegExp(`(^|\\n)${esc},`, "u").test(text)) {
      boost += 80;
    }
    // Exact full-name hit anywhere (markdown tables / digests)
    if (name.length >= 3 && text.includes(name)) {
      boost += 120;
    }
  }
  return boost;
}

/**
 * Penalize near-homonym athletes (高田麻由 when query is 高田麻那).
 * Only when the query has a full CJK name (≥3 chars) that is absent from the chunk,
 * but a same-family-name different given-name appears.
 */
export function nearHomonymNamePenalty(text: string, names: string[]): number {
  let penalty = 0;
  for (const name of names) {
    if (!/^[\u3400-\u9fff]{3,8}$/u.test(name)) continue;
    if (text.includes(name)) continue;
    const family = name.slice(0, 2);
    // Look for family+different given (2–3 more kanji) in table cells
    const re = new RegExp(`${family}[\\u3400-\\u9fff]{1,3}`, "gu");
    for (const m of text.matchAll(re)) {
      if (m[0] !== name) {
        penalty -= 100;
        break;
      }
    }
  }
  return penalty;
}

function scoreChunkAgainstQuery(
  chunk: RagChunk,
  qTokens: string[],
  nameHints: string[],
  opts?: { preferSbName?: boolean },
): number {
  let score = 0.1;
  const lower = chunk.text.toLowerCase();
  const sourceLower = chunk.source.toLowerCase();
  const tf = new Map<string, number>();
  for (const t of tokenize(chunk.text)) {
    tf.set(t, (tf.get(t) ?? 0) + 1);
  }
  // IDF-ish: rarer query tokens weigh more (approx via inverse doc-frequency proxy = 1/tf in chunk capped)
  for (const t of qTokens) {
    const freq = tf.get(t) ?? 0;
    if (freq > 0) {
      score += 1 + Math.min(2, 1 / Math.sqrt(freq));
    } else if (lower.includes(t) || sourceLower.includes(t)) {
      score += 0.5;
    }
  }
  for (const t of qTokens) {
    if (/^\d{4}-\d{2}-\d{2}$/.test(t) && lower.includes(t)) score += 500;
    if (/^20\d{2}$/.test(t) && (lower.includes(t) || sourceLower.includes(t))) score += 15;
    if (
      /^(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$/.test(t) &&
      (lower.includes(t) || sourceLower.includes(t))
    ) {
      score += 40;
    }
  }
  const isSb =
    opts?.preferSbName ||
    chunk.source.includes("sb/") ||
    chunk.source.includes("中学生SB");
  if (isSb || nameHints.length > 0) {
    score += csvNameRowBoost(chunk.text, nameHints);
    score += nearHomonymNamePenalty(chunk.text, nameHints);
  }
  return score;
}

export class Bm25Retriever {
  private readonly chunks: RagChunk[];
  private readonly docTokens: string[][];
  private readonly docLens: number[];
  private readonly avgdl: number;
  private readonly df = new Map<string, number>();
  private readonly k1: number;
  private readonly b: number;

  constructor(chunks: RagChunk[], opts?: { k1?: number; b?: number }) {
    this.chunks = chunks;
    this.k1 = opts?.k1 ?? 1.5;
    this.b = opts?.b ?? 0.75;
    this.docTokens = chunks.map((c) => tokenize(c.text));
    this.docLens = this.docTokens.map((t) => t.length);
    this.avgdl = this.docLens.reduce((a, n) => a + n, 0) / Math.max(this.docLens.length, 1);
    for (const tokens of this.docTokens) {
      for (const term of new Set(tokens)) {
        this.df.set(term, (this.df.get(term) ?? 0) + 1);
      }
    }
  }

  private idf(term: string): number {
    const n = this.df.get(term) ?? 0;
    const nd = this.chunks.length;
    return Math.log(1 + (nd - n + 0.5) / (n + 0.5));
  }

  search(query: string, topK = 5): RetrievedChunk[] {
    const qTokens = tokenize(query);
    const nameHints = extractAthleteNameHints(query);
    if (qTokens.length === 0 && nameHints.length === 0) {
      return [];
    }
    const scored: RetrievedChunk[] = [];
    for (let i = 0; i < this.docTokens.length; i += 1) {
      const tokens = this.docTokens[i]!;
      const tf = new Map<string, number>();
      for (const t of tokens) {
        tf.set(t, (tf.get(t) ?? 0) + 1);
      }
      const dl = this.docLens[i]!;
      let score = 0;
      for (const term of qTokens) {
        const freq = tf.get(term);
        if (!freq) continue;
        const idf = this.idf(term);
        const denom = freq + this.k1 * (1 - this.b + (this.b * dl) / this.avgdl);
        score += (idf * (freq * (this.k1 + 1))) / denom;
      }
      const chunk = this.chunks[i]!;
      score += csvNameRowBoost(chunk.text, nameHints);
      score += nearHomonymNamePenalty(chunk.text, nameHints);
      for (const name of nameHints) {
        if (name.length >= 2 && chunk.text.includes(name)) score += 120;
      }
      const lower = chunk.text.toLowerCase();
      const sourceLower = chunk.source.toLowerCase();
      for (const t of qTokens) {
        if (/^\d{4}-\d{2}-\d{2}$/.test(t) && lower.includes(t)) score += 500;
        if (/^20\d{2}$/.test(t) && (lower.includes(t) || sourceLower.includes(t))) score += 15;
        if (
          /^(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$/.test(t) &&
          (lower.includes(t) || sourceLower.includes(t))
        ) {
          score += 40;
        }
      }
      if (score > 0) {
        scored.push({ chunk, score });
      }
    }
    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, topK);
  }
}

let cached: Bm25Retriever | null = null;

export function loadIndex(path: string = defaultIndexPath()): RagIndex {
  const raw = readFileSync(path, "utf8");
  const data = JSON.parse(raw) as RagIndex;
  if (!data.chunks || !Array.isArray(data.chunks)) {
    throw new Error("Invalid rag_index.json: missing chunks");
  }
  if (data.corpus !== "input/idaten-corpus") {
    throw new Error(`Unexpected corpus root: ${data.corpus}`);
  }
  return data;
}

export function getRetriever(path: string = defaultIndexPath()): Bm25Retriever {
  if (!cached) {
    const index = loadIndex(path);
    cached = new Bm25Retriever(index.chunks);
  }
  return cached;
}

/** Test helper to reset singleton. */
export function resetRetrieverCache(): void {
  cached = null;
}

export function retrieveContext(
  query: string,
  topK = 5,
  path: string = defaultIndexPath(),
): RetrievedChunk[] {
  return getRetriever(path).search(query, topK);
}

function chunkBaseSource(source: string): string {
  const m = source.match(/^(.*):\d+$/);
  return m ? m[1]! : source;
}

/** Discover drive-text/大会 sources whose path contains any of the given tokens (e.g. 0920). */
export function findSourcesContaining(
  tokens: string[],
  opts?: { prefix?: string; path?: string; limit?: number },
): string[] {
  if (tokens.length === 0) return [];
  const path = opts?.path ?? defaultIndexPath();
  const prefix = opts?.prefix ?? "drive-text/大会/";
  const limit = opts?.limit ?? 8;
  const index = loadIndex(path);
  const found: string[] = [];
  const seen = new Set<string>();
  for (const chunk of index.chunks) {
    const base = chunkBaseSource(chunk.source);
    if (!base.startsWith(prefix)) continue;
    if (base.includes(".meta.json")) continue;
    const lower = base.toLowerCase();
    if (!tokens.some((t) => t && lower.includes(t.toLowerCase()))) continue;
    if (seen.has(base)) continue;
    seen.add(base);
    found.push(base);
    if (found.length >= limit) break;
  }
  return found;
}

/** Find corpus sources whose chunk text contains any needle (not path tokens). */
export function findSourcesWithText(
  needles: string[],
  opts?: { prefix?: string; path?: string; limit?: number },
): string[] {
  const tokens = needles.map((n) => n.trim()).filter((n) => n.length >= 2);
  if (tokens.length === 0) return [];
  const path = opts?.path ?? defaultIndexPath();
  const prefix = opts?.prefix ?? "";
  const limit = opts?.limit ?? 8;
  const index = loadIndex(path);
  const found: string[] = [];
  const seen = new Set<string>();
  for (const chunk of index.chunks) {
    const base = chunkBaseSource(chunk.source);
    if (prefix && !base.startsWith(prefix)) continue;
    if (!tokens.some((t) => chunk.text.includes(t))) continue;
    if (seen.has(base)) continue;
    seen.add(base);
    found.push(base);
    if (found.length >= limit) break;
  }
  return found;
}

function chunkIndex(chunk: RagChunk): number {
  return Number((chunk.id.match(/:(\d+)$/) || chunk.source.match(/:(\d+)$/) || [])[1] ?? 0);
}

/** Fetch chunks whose source matches any of the given corpus sources (prefix OK). */
export function retrieveBySources(
  sources: string[],
  opts?: {
    query?: string;
    perSource?: number;
    maxChunks?: number;
    path?: string;
    /**
     * `full`: document order, all chunks up to perSource (for 「全て提示」網羅).
     * `ranked` (default): BM25 / query scoring.
     */
    coverage?: "ranked" | "full";
  },
): RetrievedChunk[] {
  if (sources.length === 0) return [];
  const path = opts?.path ?? defaultIndexPath();
  const index = loadIndex(path);
  const perSource = opts?.perSource ?? 12;
  const maxChunks = opts?.maxChunks ?? 96;
  const query = opts?.query ?? "";
  const coverage = opts?.coverage ?? "ranked";
  const qTokens = query ? tokenize(query) : [];
  const nameHints = query ? extractAthleteNameHints(query) : [];

  const bySource = new Map<string, RagChunk[]>();
  // Longer / exact paths first so `out-analysis` does not steal siblings of `…/玉南中.md`
  const sourcesBySpecificity = [...sources].sort((a, b) => b.length - a.length);
  for (const chunk of index.chunks) {
    const base = chunkBaseSource(chunk.source);
    const matched =
      sources.find((s) => base === s) ??
      sourcesBySpecificity.find((s) => base.startsWith(s + "/"));
    if (!matched) continue;
    const list = bySource.get(matched) ?? [];
    list.push(chunk);
    bySource.set(matched, list);
  }

  const scored: RetrievedChunk[] = [];
  for (const src of sources) {
    const chunks = bySource.get(src) ?? [];
    if (chunks.length === 0) continue;
    // Exact preferred files get a floor so directory-prefix pools cannot drown them
    const exactFloor =
      /\.(md|csv|ya?ml|json)$/i.test(src) && !src.endsWith("/") ? 200 : 0;

    if (coverage === "full") {
      const ordered = [...chunks].sort((a, b) => chunkIndex(a) - chunkIndex(b));
      for (const [i, c] of ordered.slice(0, perSource).entries()) {
        // High base + tiny index delta keeps document order after score sort
        scored.push({
          chunk: c,
          score: 5000 - i + exactFloor + pathQueryBonus(c.source, query),
        });
      }
      continue;
    }

    const ranked =
      qTokens.length > 0 || nameHints.length > 0
        ? new Bm25Retriever(chunks).search(query, perSource)
        : chunks.slice(0, perSource).map((c) => ({
            chunk: c,
            score: scoreChunkAgainstQuery(c, qTokens, nameHints, {
              preferSbName: src.startsWith("sb/") || src.includes("中学生SB"),
            }),
          }));
    // Exact file routes must not disappear when BM25 score is 0 (tiny digests)
    if (ranked.length === 0 && !src.endsWith("/") && chunks.length > 0) {
      for (const c of chunks.slice(0, Math.min(perSource, chunks.length))) {
        ranked.push({
          chunk: c,
          score: 50 + pathQueryBonus(c.source, query),
        });
      }
    }
    for (const r of ranked) {
      scored.push({
        chunk: r.chunk,
        score: r.score + exactFloor + pathQueryBonus(r.chunk.source, query),
      });
    }
  }

  if (coverage === "full") {
    // Preserve preferred-source order: do not re-sort across sources by raw score
    return scored.slice(0, maxChunks);
  }
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, maxChunks);
}

/**
 * Path-aware bonus so routed meet/SB/calendar sources beat unrelated BM25
 * (e.g. repo-docs that quote the same question in ADRs).
 */
function pathQueryBonus(source: string, query: string): number {
  if (!query) return 0;
  const q = query.normalize("NFKC");
  const s = source;
  let bonus = 0;
  if (
    /なごみ駅伝.*集合場所|集合場所.*なごみ駅伝/.test(q) &&
    /line-chats\/daiming-parents/.test(s)
  ) {
    bonus += 600;
  }
  if (isLegAthleteQuestion(q) && /aragyoku-teams\/([^/]+)\.md$/.test(s)) {
    const teamStem = s.match(/aragyoku-teams\/([^/]+)\.md$/)?.[1] ?? "";
    const aliases =
      teamStem === "玉高附属" ? ["玉高附属", "玉名付属", "玉名附属", "玉名附"] : [teamStem];
    if (teamStem && aliases.some((alias) => q.includes(alias))) bonus += 1200;
  }
  if (/ジュニア/.test(q) && s.includes("ジュニア")) bonus += 120;
  if (isNagomiMeetQuestion(q) && /なごみ/.test(s)) bonus += 120;
  if (
    isNagomiMeetQuestion(q) &&
    /区間オーダーリスト/.test(s) &&
    /オーダー|\d区|何区|誰/.test(q)
  ) {
    bonus += 200;
  }
  if (isKanaguriEkidenQuestion(q) && /金栗駅伝/.test(s)) bonus += 120;
  if (/金栗記念/.test(q) && !isNagomiMeetQuestion(q) && /金栗記念/.test(s)) bonus += 120;
  if (/荒玉|aragyoku|中体連/.test(q) && /aragyoku|荒玉|ekiden-ocr|aragyoku-teams/.test(s)) bonus += 80;
  if (
    /荒玉|aragyoku|中体連/.test(q) &&
    /2024|2025|前年比|深掘り|分析|岱明|玉名付属|玉高附属|天水|有明|優勝との差|優勝差|優勝から/.test(
      q,
    ) &&
    /aragyoku_2024_2025_focus_teams/.test(s)
  ) {
    bonus += 160;
  }
  if (
    /優勝との差|優勝差|優勝から|優勝まで|離れて/.test(q) &&
    /aragyoku_2024_2025_focus_teams|aragyoku-teams\//.test(s)
  ) {
    bonus += 220;
  }
  if (
    /上位\s*\d+\s*人平均|上位\d人平均|学校別|所属別/.test(q) &&
    /800|1500/.test(q) &&
    /pb_school_ranking|women_800m_1500m/.test(s)
  ) {
    bonus += 220;
  }
  if (
    /大会記録|区間記録|ボード|記録保持|meet_records/.test(q) &&
    !/区間賞|区間順/.test(q) &&
    /aragyoku_meet_records/.test(s)
  ) {
    bonus += 180;
  }
  if (
    (/区間賞|区間1位|区間一位|区間順/.test(q) || (/各区/.test(q) && /賞|上位/.test(q))) &&
    /aragyoku_leg_awards/.test(s)
  ) {
    bonus += 220;
  }
  if (
    /荒玉|aragyoku|中体連/.test(q) &&
    /ペース|距離|コース|\/km|分で/.test(q) &&
    !/大会記録|区間記録|区間賞|誰|何位/.test(q) &&
    /aragyoku-overview|aragyoku-ekiden-distance|average_pace/.test(s)
  ) {
    bonus += 140;
  }
  if (/荒尾|玉名|金栗PROJECT|アスリーツ|所属別/.test(q) && /arato-tamana-teams/.test(s)) bonus += 100;
  // 「○区は誰」「何区を走った」結果質問では LINE を上げない（2区/5区距離メモと衝突するため）
  const legAthleteQ = isLegAthleteQuestion(q);
  if (
    !legAthleteQ &&
    /岱明|いだてん|銀マット|合同練習|おおはま|三加和|朝練|ナイター|和水|有田|補強|手押し車|犬歩き|分割走|厚底|地点分担|地点|土山コーチ|柴尾|曜日|集合時間|タイム目安|43分|区間配分|2\.855|2区.*5区|5区.*2区|お別れ会|金栗駅伝|走り納め|体育館前|補強メニュー/.test(
      q,
    ) &&
    /line-chats/.test(s)
  ) {
    bonus += 130;
  }
  // Ops / coaching LINE beats generic 荒玉 overview when both match
  if (
    /地点分担|朝練|銀マット|タイム目安|43分|区間配分|有田|補強|手押し車|犬歩き|2区.*5区|5区.*2区|補強メニュー/.test(
      q,
    ) &&
    /line-chats/.test(s)
  ) {
    bonus += 100;
  }
  if (/arita-taisho/.test(s) && /有田|補強|手押し車|犬歩き|補強メニュー|43分|タイム目安/.test(q)) {
    bonus += 120;
  }
  // 2区/5区 alone is race-leg wording; require ops markers for staff digest
  if (
    /daiming-staff/.test(s) &&
    /地点分担|地点|朝練|2\.855|曜日|7:20|集合/.test(q) &&
    !legAthleteQ
  ) {
    bonus += 120;
  }
  if (
    legAthleteQ &&
    /aragyoku-teams\/|aragyoku_2024_2025_focus_teams|ekiden-ocr|aragyoku\/transcripts/.test(s)
  ) {
    bonus += 200;
  }
  if (legAthleteQ && /スタートリスト|タイムテーブル|通信陸上/.test(s)) {
    bonus -= 240;
  }
  if (
    /地点分担|タイム目安|43分切り|区間配分イメージ|有田|補強メニュー|2区.*5区|5区.*2区/.test(q) &&
    /aragyoku-overview|aragyoku-ekiden-distance|average_pace|course-videos|quiz/.test(s)
  ) {
    bonus -= 100;
  }
  if ((s.startsWith("sb/") || s.includes("中学生SB")) && /自己ベスト|\bSB\b|\bPB\b|\d+\s*m/.test(q)) {
    bonus += 60;
  }
  if (s.includes("calendar") && /予定|大会|\d{4}-\d{2}-\d{2}|月.*日/.test(q)) bonus += 60;
  if (
    /夕練/.test(q) &&
    /何時|開始|時刻|スタート|から/.test(q) &&
    (/practice\//.test(s) || /calendar/.test(s) || /events\.daiming/.test(s))
  ) {
    bonus += 140;
  }
  if (
    /practice_meets|affect_load|負荷に数え/.test(q) &&
    /006-practice-meets|ai_generation_rules|ai-practice-generation/.test(s)
  ) {
    bonus += 160;
  }
  if (
    /\bATRC\b|ＡＴＲＣ/.test(q) &&
    /arato-tamana-teams\/ATRC\.md|personal\/ATRC\.md/.test(s)
  ) {
    bonus += 200;
  }
  // Exact team file name in path (longest stem first)
  if (/全記録|所属選手|記録一覧/.test(q)) {
    const known = [
      "玉名高校附属中",
      "荒尾第四中",
      "荒尾海陽中",
      "熊本大附中",
      "玉・有明中",
      "玉名アスリーツ",
      "玉東クラブ",
      "金栗PROJECT",
      "荒尾三中",
      "玉名高附",
      "玉名附中",
      "玉陵中",
      "玉名中",
      "玉南中",
      "南関中",
      "天水中",
      "岱明中",
      "長洲中",
      "ＮＪＡＣ",
      "ATRC",
      "玉陵",
    ];
    const hit = known.find((stem) => q.includes(stem));
    if (hit && (s.includes(`arato-tamana-teams/${hit}.md`) || s.endsWith(`/${hit}.md`))) {
      bonus += 320;
    }
  }
  if (
    /3000m|3000ｍ/.test(q) &&
    /速い|一番|最速|ランキング|SB|自己ベスト|何位|順位/.test(q) &&
    /3000m_sb_ranking|notion_records_2026|arato-tamana-teams/.test(s)
  ) {
    bonus += 180;
  }
  if (
    /1500m|1500ｍ/.test(q) &&
    /トップ\s*20|ランキング|SB|自己ベスト|荒玉地区/.test(q) &&
    /1500m_sb_individual_top20|1500m_pb_school_ranking|notion_records_2026/.test(s)
  ) {
    bonus += 180;
  }
  if (
    /2位まで|総合2位|優勝.*回数|2位以内/.test(q) &&
    /top2_finish_counts|winners-by-year/.test(s)
  ) {
    bonus += 200;
  }
  if (
    /平均ペース|歴代.*ペース|位.*ペース|ペース.*位/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    /all_teams_average_pace|top6_historical_average_pace/.test(s)
  ) {
    bonus += 240;
  }
  if (
    /平均ペース|位.*ペース/.test(q) &&
    /all_teams_average_pace/.test(s)
  ) {
    bonus += 80;
  }
  // 年度別優勝・準優勝質問では回数集計を下げ、年度表を勝たせる
  if (
    /準優勝|優勝校/.test(q) &&
    /過去|年|歴代/.test(q) &&
    /top2_finish_counts/.test(s) &&
    !/回数|2位まで|2位以内/.test(q)
  ) {
    bonus -= 120;
  }
  if (/高田麻那/.test(q) && /takada-mana|athletes\/takada|SBデータベース/.test(s)) {
    bonus += 250;
  }
  if (/ドライブ|drive-text\/大会/.test(s) && /結果|大会|駅伝/.test(q) && /大会\//.test(s)) {
    bonus += 40;
  }
  return bonus;
}

function pathQueryPenalty(source: string, query: string): number {
  if (!query) return 0;
  const q = query.normalize("NFKC");
  // ADR / implementation-flow docs often contain the literal eval questions
  if (/ジュニア|なごみ|荒玉|自己ベスト|駅伝/.test(q) && source.startsWith("repo-docs/")) {
    return -80;
  }
  if (/ジュニア|なごみ|金栗/.test(q) && (/aragyoku|ekiden-ocr/.test(source))) {
    return -100;
  }
  if (isNagomiMeetQuestion(q) && /aragyoku-teams|focus_teams/.test(source)) {
    return -200;
  }
  // 高田麻那 ≠ 岱明の同姓別人: demote 岱明/駅伝板 when asking for 麻那
  if (/高田麻那/.test(q) && !/takada-mana|SBデータベース/.test(source)) {
    if (/岱明中|aragyoku\/|ekiden-ocr\/|ocr_raw|women_800m_1500m/.test(source)) {
      return -200;
    }
  }
  if (
    /地点分担|タイム目安|43分|区間配分|有田|補強メニュー|2区.*5区|5区.*2区/.test(q) &&
    /aragyoku-overview|aragyoku-ekiden-distance|average_pace|course-videos|aragyoku\/quiz/.test(
      source,
    )
  ) {
    return -120;
  }
  // Race-leg athlete Q: demote LINE ops digests that mention 2区/5区距離
  if (/line-chats/.test(source) && isLegAthleteQuestion(q)) {
    return -220;
  }
  if (
    isLegAthleteQuestion(q) &&
    !/ジュニア|なごみ|金栗|通信大会|通信陸上/.test(q) &&
    /スタートリスト|タイムテーブル|通信陸上/.test(source)
  ) {
    return -240;
  }
  // 優勝差・学校別平均は meet_records / SB CSV より分析正本へ
  if (
    /優勝との差|優勝差|優勝から|優勝まで|離れて/.test(q) &&
    /aragyoku_meet_records/.test(source)
  ) {
    return -180;
  }
  // 区間賞・区間順位: focus / winners / 歴代記録ボードを下げ、leg_awards を勝たせる
  if (/区間賞|区間1位|区間一位|区間順/.test(q)) {
    if (/aragyoku_2024_2025_focus_teams|winners-by-year|aragyoku_meet_records/.test(source)) {
      return -250;
    }
    if (/aragyoku-teams\/|ekiden-ocr|ocr_raw/.test(source) && !/leg_awards/.test(source)) {
      return -120;
    }
  }
  if (
    /上位\s*\d+\s*人平均|上位\d人平均/.test(q) &&
    /800|1500/.test(q) &&
    (source.startsWith("sb/") || /line-chats/.test(source))
  ) {
    return -200;
  }
  return 0;
}

/** Drop aragyoku/OCR/wrong-meet noise for named non-aragyoku meets (wide topK must not reintroduce them). */
function isBlockedCorpusForQuery(source: string, query: string): boolean {
  if (!query) return false;
  const q = query.normalize("NFKC");
  if (/\.meta\.json/.test(source)) return true;
  // 大会名なしの区間選手質問: 通信陸上スタートリストは正本ではない
  if (
    isLegAthleteQuestion(q) &&
    !/ジュニア|なごみ|金栗四三|通信大会|通信陸上/.test(q) &&
    /スタートリスト|タイムテーブル|通信陸上/.test(source)
  ) {
    return true;
  }
  // 区間賞・区間順位: 分析深掘り・優勝表・歴代記録ボードは正本と混同しやすいので除外
  if (
    /区間賞|区間1位|区間一位|区間順/.test(q) &&
    /aragyoku_2024_2025_focus_teams|winners-by-year|aragyoku_meet_records/.test(source)
  ) {
    return true;
  }
  // Empty Drive stubs must not fill ranking / history answers
  if (/_EMPTY\.md|export\.status\.json/.test(source)) {
    return true;
  }
  // README / PDF generation howtos must not answer 所属選手の全記録
  if (
    /全記録|所属選手|記録一覧|自己ベスト|ランキング|何位/.test(q) &&
    (/docs\/README\.md|generate_arato_tamana|repo-docs\/README/.test(source) ||
      source === "docs/README.md")
  ) {
    return true;
  }
  // LINE ops / coaching digests beat generic 荒玉 overview noise
  if (
    /地点分担|タイム目安|43分|区間配分|有田先輩|有田大将|補強メニュー|手押し車|犬歩き|メンタル|楽しさ|本気度|2区.*5区|5区.*2区/.test(
      q,
    ) &&
    (/aragyoku-overview|aragyoku-ekiden-distance|average_pace|course-videos|aragyoku\/quiz|winners-by-year|aragyoku\/transcripts|aragyoku\/ocr|ekiden-ocr|out-analysis\/aragyoku|aragyoku-teams/.test(
      source,
    ) ||
      (/有田先輩|有田大将|補強メニュー|手押し車|犬歩き|メンタル|楽しさ|本気度/.test(q) &&
        !/line-chats/.test(source) &&
        /aragyoku|ekiden-ocr|drive-text\/大会|drive-text\/記録|calendar|events\.daiming|repo-docs|docs\/|practice\/|daiming-practice|sb\//.test(
          source,
        )))
  ) {
    return true;
  }
  const namedNonAragyoku =
    /ジュニア/.test(q) ||
    isNagomiMeetQuestion(q) ||
    isKanaguriEkidenQuestion(q) ||
    /金栗記念/.test(q);
  if (!(namedNonAragyoku && !/荒玉|aragyoku|中体連/.test(q))) {
    return false;
  }
  if (
    source === "aragyoku" ||
    source.startsWith("aragyoku/") ||
    source.startsWith("ekiden-ocr/") ||
    source.startsWith("repo-docs/") ||
    source.startsWith("docs/")
  ) {
    return true;
  }
  if (/notion-db\/.*荒玉/.test(source) || source.startsWith("notion-pages/ekiden-history")) {
    return true;
  }
  if (/analysis-ocr|out-analysis/.test(source) && /荒玉/.test(source)) {
    return true;
  }
  // Wrong meet folder under drive-text/大会 (岱明の結果 is common across meets)
  if (/drive-text\/大会/.test(source)) {
    if (/ジュニア/.test(q) && !/ジュニア/.test(source)) return true;
    if (isNagomiMeetQuestion(q) && !/なごみ/.test(source)) return true;
    if (isKanaguriEkidenQuestion(q) && !/金栗駅伝/.test(source)) return true;
    if (/金栗記念/.test(q) && !isNagomiMeetQuestion(q) && !/金栗記念/.test(source)) return true;
  }
  return false;
}

/** Meta docs that quote the refuse template must not pollute answer context. */
function isRefuseTemplateNoise(text: string): boolean {
  return text.includes("コーチに直接聞いてください");
}

/** Text-level guard: practice calendars / misc docs quoting 荒玉 must not fill junior/nagomi context. */
function isBlockedChunkForQuery(chunk: { source: string; text: string }, query: string): boolean {
  if (isRefuseTemplateNoise(chunk.text)) return true;
  if (isBlockedCorpusForQuery(chunk.source, query)) return true;
  if (!query) return false;
  const q = query.normalize("NFKC");
  if (!(/ジュニア|なごみ|金栗/.test(q) && !/荒玉|aragyoku|中体連/.test(q))) return false;
  if (/ジュニア/.test(q) && /荒玉中体連|winners-by-year/.test(chunk.text) && !/ジュニア/.test(chunk.source)) {
    return true;
  }
  if (
    isNagomiMeetQuestion(q) &&
    !/ジュニア/.test(q) &&
    /荒玉中体連|winners-by-year/.test(chunk.text) &&
    !/なごみ/.test(chunk.source)
  ) {
    return true;
  }
  return false;
}

/**
 * Merge routed (primary) and BM25 (secondary) hits by score fusion.
 * Weak preferred no longer gets a flat +1000 that drowns strong BM25.
 */
function digestPinForQuery(chunk: RagChunk, query: string): number {
  const qn = query.normalize("NFKC");
  const base = chunkBaseSource(chunk.source);
  if (/全記録|所属選手|記録一覧/.test(qn)) {
    const stem = base.split("/").pop()?.replace(/\.md$/, "") ?? "";
    if (/arato-tamana-teams\/[^/]+\.md$/.test(base) && stem && query.includes(stem)) {
      return 500;
    }
  }
  if (/過去|歴代|順位/.test(qn) && /荒玉|駅伝/.test(qn) && !/区間賞|区間順/.test(qn)) {
    const stem = base.split("/").pop()?.replace(/\.md$/, "") ?? "";
    if (/aragyoku-teams\/[^/]+\.md$/.test(base) && stem && query.includes(stem)) {
      return 500;
    }
  }
  if (/区間賞|区間1位|区間一位|区間順/.test(qn) && /aragyoku_leg_awards/.test(base)) {
    return 900;
  }
  if (isNagomiMeetQuestion(qn) && /区間オーダーリスト/.test(base) && /オーダー|\d区|何区|誰/.test(qn)) {
    return 800;
  }
  if (
    isLegAthleteQuestion(qn) &&
    !isNagomiMeetQuestion(qn) &&
    !/ジュニア/.test(qn) &&
    /aragyoku-teams\/[^/]+\.md$|focus_teams/.test(base)
  ) {
    const teamStem = base.match(/aragyoku-teams\/([^/]+)\.md$/)?.[1] ?? "";
    const teamAliases =
      teamStem === "玉高附属" ? ["玉高附属", "玉名付属", "玉名附属", "玉名附"] : [teamStem];
    if (teamStem && teamAliases.some((alias) => qn.includes(alias))) return 900;
    const names = extractAthleteNameHints(qn);
    if (names.some((n) => chunk.text.includes(n))) return 700;
    return 200;
  }
  if (
    /何位|総合タイム|総合は|総合/.test(qn) &&
    /男子|女子/.test(qn) &&
    /20\d{2}/.test(qn) &&
    /aragyoku-teams\/([^/]+)\.md$/.test(base)
  ) {
    const teamStem = base.match(/aragyoku-teams\/([^/]+)\.md$/)?.[1] ?? "";
    const 玉名付属表記 = /玉名付属|玉名附属|玉名附/.test(qn);
    if (teamStem === "玉名" && 玉名付属表記) return 0;
    const aliases =
      teamStem === "玉高附属" ? ["玉高附属", "玉名付属", "玉名附属", "玉名附"] : [teamStem];
    if (teamStem && aliases.some((alias) => qn.includes(alias))) return 900;
  }
  if (
    /前年比|前年から|短縮|何分/.test(qn) &&
    /aragyoku-teams\/([^/]+)\.md$/.test(base)
  ) {
    const teamStem = base.match(/aragyoku-teams\/([^/]+)\.md$/)?.[1] ?? "";
    if (teamStem && qn.includes(teamStem)) return 850;
  }
  if (/トラック/.test(qn) && /1周|一周|周長|何メートル/.test(qn)) {
    if (/daiming-practice-menus-kpace|data-model\.md/.test(chunk.source)) {
      return 500;
    }
  }
  // 「全て提示」系: 正本ダイジェストを強くピン（OCR / hub に埋もれない）
  if (isExhaustiveListQuery(qn)) {
    if (/winners-by-year/.test(base) && /優勝|準優勝/.test(qn)) return 900;
    if (/top2_finish_counts/.test(base) && /2位まで|2位以内|回数/.test(qn)) return 900;
    if (/all_teams_average_pace|top6_historical_average_pace/.test(base) && /ペース|\/km/.test(qn))
      return 900;
    if (/aragyoku_leg_awards/.test(base) && /区間賞|区間順/.test(qn)) return 900;
    if (/arato-tamana-teams\/[^/]+\.md$/.test(base) && /記録|選手|一覧/.test(qn)) return 900;
    if (/aragyoku-teams\/[^/]+\.md$/.test(base) && /区間|順位|歴代|過去/.test(qn) && !/区間賞/.test(qn))
      return 800;
    if (/2024_2025_focus_teams/.test(base) && /優勝との差|前年比|深掘り|分析/.test(qn)) return 800;
    if (/meet_records/.test(base) && /大会記録|区間記録/.test(qn) && !/区間賞/.test(qn)) return 800;
    if (/\.(md|csv|json)$/i.test(base) && !base.endsWith("/") && !/ocr|notion-db|transcripts\//.test(base)) {
      return 400;
    }
  }
  return 0;
}

/** 「全て / 全部 / すべて提示」など網羅列挙の意図。 */
export function isExhaustiveListQuery(query: string): boolean {
  const q = query.normalize("NFKC");
  return /全て|すべて|全部|残らず|漏れなく|全件|フル(リスト|一覧)|一覧(を|で)?(全部|全て|すべて)|全部(出|教え|提示|列挙|見せ)|全て(出|教え|提示|列挙|見せ)|すべて(出|教え|提示|列挙|見せ)/.test(
    q,
  );
}

export function mergeRetrieved(
  primary: RetrievedChunk[],
  secondary: RetrievedChunk[],
  topK = 10,
  opts?: { query?: string; preferPrimaryOrder?: boolean },
): RetrievedChunk[] {
  const query = opts?.query ?? "";
  const preferPrimaryOrder = opts?.preferPrimaryOrder ?? false;
  const byId = new Map<string, RetrievedChunk>();

  const upsert = (r: RetrievedChunk, extra: number) => {
    if (isBlockedChunkForQuery(r.chunk, query)) return;
    const nextScore = r.score + extra;
    const prev = byId.get(r.chunk.id);
    if (!prev || nextScore > prev.score) {
      byId.set(r.chunk.id, { chunk: r.chunk, score: nextScore });
    }
  };

  for (const r of primary) {
    // Strong signals (name row ~80+, ISO date ~500) keep a clear edge.
    // Weak preferred (headers / low overlap) only get a tiny routed bonus.
    const strengthBonus = r.score >= 80 ? 50 : r.score >= 40 ? 25 : 5;
    const pathBonus = pathQueryBonus(r.chunk.source, query);
    const pin = digestPinForQuery(r.chunk, query);
    upsert(r, strengthBonus + pathBonus + pin);
  }
  for (const r of secondary) {
    const pathBonus = pathQueryBonus(r.chunk.source, query);
    const pin = digestPinForQuery(r.chunk, query);
    // Exhaustive: BM25 filler must not outrank full preferred digests
    const fillerPenalty = preferPrimaryOrder || isExhaustiveListQuery(query) ? -200 : 0;
    upsert(r, pathQueryPenalty(r.chunk.source, query) + pathBonus + pin + fillerPenalty);
  }

  const merged = [...byId.values()].sort((a, b) => b.score - a.score);
  if (!preferPrimaryOrder && !isExhaustiveListQuery(query)) {
    return merged.slice(0, topK);
  }
  // Prefer primary document order for exhaustive listings, then fill by score
  const out: RetrievedChunk[] = [];
  const seen = new Set<string>();
  for (const r of primary) {
    const hit = byId.get(r.chunk.id);
    if (!hit || seen.has(hit.chunk.id)) continue;
    seen.add(hit.chunk.id);
    out.push(hit);
    if (out.length >= topK) return out;
  }
  for (const r of merged) {
    if (seen.has(r.chunk.id)) continue;
    seen.add(r.chunk.id);
    out.push(r);
    if (out.length >= topK) break;
  }
  return out;
}

/** Truncate retrieved texts to a character budget for LLM context. */
export function truncateRetrieved(
  retrieved: RetrievedChunk[],
  maxChars = 100_000,
): RetrievedChunk[] {
  const out: RetrievedChunk[] = [];
  let used = 0;
  for (const r of retrieved) {
    const len = r.chunk.text.length;
    if (used + len > maxChars && out.length > 0) break;
    if (used + len > maxChars) {
      out.push({
        ...r,
        chunk: { ...r.chunk, text: r.chunk.text.slice(0, Math.max(0, maxChars - used)) },
      });
      break;
    }
    out.push(r);
    used += len;
  }
  return out;
}

/**
 * Expand hits with neighboring chunks from the same source (by :N index)
 * so calendar / long docs don't lose surrounding context.
 */
export function expandWithNeighbors(
  hits: RetrievedChunk[],
  opts?: { radius?: number; path?: string; maxExtra?: number; query?: string },
): RetrievedChunk[] {
  if (hits.length === 0) return hits;
  const radius = opts?.radius ?? 2;
  const maxExtra = opts?.maxExtra ?? 160;
  const path = opts?.path ?? defaultIndexPath();
  const query = opts?.query ?? "";
  const index = loadIndex(path);

  const bySource = new Map<string, RagChunk[]>();
  for (const chunk of index.chunks) {
    const base = chunkBaseSource(chunk.source);
    const list = bySource.get(base) ?? [];
    list.push(chunk);
    bySource.set(base, list);
  }
  for (const [, list] of bySource) {
    list.sort((a, b) => {
      const ia = Number((a.id.match(/:(\d+)$/) || [])[1] ?? 0);
      const ib = Number((b.id.match(/:(\d+)$/) || [])[1] ?? 0);
      return ia - ib;
    });
  }

  const out: RetrievedChunk[] = [];
  const seen = new Set<string>();
  let extra = 0;
  for (const hit of hits) {
    if (!seen.has(hit.chunk.id)) {
      seen.add(hit.chunk.id);
      out.push(hit);
    }
    const base = chunkBaseSource(hit.chunk.source);
    const list = bySource.get(base);
    if (!list || list.length <= 1) continue;
    const idx = list.findIndex((c) => c.id === hit.chunk.id);
    if (idx < 0) continue;
    for (let d = 1; d <= radius; d += 1) {
      for (const j of [idx - d, idx + d]) {
        if (j < 0 || j >= list.length) continue;
        const chunk = list[j]!;
        if (seen.has(chunk.id)) continue;
        if (isBlockedChunkForQuery(chunk, query)) continue;
        if (extra >= maxExtra) break;
        seen.add(chunk.id);
        out.push({ chunk, score: hit.score * 0.85 });
        extra += 1;
      }
    }
  }
  return out;
}
