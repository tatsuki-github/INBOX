import { classifyScope, OUT_OF_SCOPE_MESSAGE } from "./scope.js";
import { expandDateQuery, parseDateMentions, resolveRelativeYears } from "./dates.js";
import { matchCannedAnswer } from "./canned.js";
import { matchClarifyAnswer } from "./clarify.js";
import {
  detectMeetKind,
  isAragyokuCorpusSource,
  meetDriveTokens,
  meetResultPathBoost,
  type MeetKind,
} from "./meets.js";
import { withMeetResultUrls, type MeetResultUrlEntry } from "./meetResultUrls.js";
import { routeSources } from "./router.js";
import type { LlmClient } from "./llm.js";
import { buildSystemPrompt, buildUserPrompt, MISSING_INFO_MESSAGE } from "../rag/prompt.js";
import { formatForLine } from "../line/format.js";
import {
  expandWithNeighbors,
  extractAthleteNameHints,
  findSourcesContaining,
  mergeRetrieved,
  retrieveBySources,
  retrieveContext,
  truncateRetrieved,
  type RetrievedChunk,
} from "../rag/retrieve.js";
import { queryKnowledgeGraph, type KgQueryResult } from "../kg/query.js";
import { RETRIEVAL_BUDGET } from "../rag/budget.js";

export { RETRIEVAL_BUDGET } from "../rag/budget.js";

export type AnswerResult =
  | { kind: "refused"; text: string }
  | { kind: "answered"; text: string; sources: string[] }
  | { kind: "offline"; text: string; sources: string[] }
  | { kind: "error"; text: string };

export type AnswerDeps = {
  retrieve?: (question: string, topK?: number) => RetrievedChunk[];
  llm?: LlmClient | null;
  topK?: number;
  /** Inject KG query for tests */
  kgQuery?: (question: string) => KgQueryResult;
  /** Skip router LLM (use KG fallback sources) */
  skipRouter?: boolean;
  defaultYear?: number;
  /** Inject meet result URL index (tests / overrides) */
  meetResultUrls?: MeetResultUrlEntry[];
};

function finalizeAnswerText(
  text: string,
  question: string,
  deps: AnswerDeps,
): string {
  const formatted = formatForLine(text);
  return withMeetResultUrls(formatted, question, {
    entries: deps.meetResultUrls,
    defaultYear: deps.defaultYear ?? new Date().getFullYear(),
  });
}

function previewForOffline(text: string, question: string, maxChars = 320): string {
  const flat = text.replace(/\s+/g, " ");
  const isos = question.match(/20\d{2}-\d{2}-\d{2}/g) ?? [];
  for (const iso of isos) {
    const idx = flat.indexOf(iso);
    if (idx >= 0) {
      const start = Math.max(0, idx - 140);
      const end = Math.min(flat.length, idx + 180);
      return flat.slice(start, end);
    }
  }
  // Bare M月D日 → try zero-padded MMDD in ISO-like form already expanded into question
  return flat.slice(0, maxChars);
}

function offlineAnswer(
  question: string,
  retrieved: RetrievedChunk[],
  previewQuery?: string,
): string {
  const lines = ["（オフライン回答）", "", `Q: ${question}`, ""];
  if (retrieved.length === 0) {
    lines.push(MISSING_INFO_MESSAGE);
  } else {
    const hint = previewQuery ?? question;
    for (const [i, r] of retrieved.entries()) {
      const preview = previewForOffline(r.chunk.text, hint);
      lines.push(`${i + 1}. ${preview}`);
    }
  }
  return formatForLine(lines.join("\n"));
}

function boostDateMeetSources(expandedQuery: string, baseSources: string[]): string[] {
  const mentions = parseDateMentions(expandedQuery);
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (s: string) => {
    if (!s || seen.has(s)) return;
    seen.add(s);
    out.push(s);
  };

  if (mentions.length > 0) {
    push("calendar/events.daiming.yaml");
    const mmdds = mentions.map((m) => m.mmdd);
    for (const s of findSourcesContaining(mmdds, { prefix: "drive-text/大会/", limit: 12 })) {
      push(s);
    }
  }
  for (const s of baseSources) push(s);
  return out;
}

function sortMeetDriveSources(sources: string[], query: string): string[] {
  return [...sources].sort(
    (a, b) => meetResultPathBoost(b, query) - meetResultPathBoost(a, query),
  );
}

/** Prefer SB / 記録データベース sources for athlete-record questions. */
function boostAthleteRecordSources(query: string, baseSources: string[]): string[] {
  if (
    !/自己ベスト|ベストタイム|自己記録|\bSB\b|\bPB\b|ベスト記録|記録|タイム|何分|何秒|800m?|1500m?|3000m?|5000m?|荒尾|玉名|所属|チーム|金栗|岱明|南関|天水|長洲|ATRC|アスリーツ/.test(
      query,
    )
  ) {
    return baseSources;
  }
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (s: string) => {
    if (!s || seen.has(s)) return;
    seen.add(s);
    out.push(s);
  };
  if (/荒尾|玉名|金栗|岱明|南関|天水|長洲|ATRC|アスリーツ|玉東|有明|荒尾三|荒尾四|海陽|玉陵|玉南|玉高|附中/.test(query)) {
    push("out-analysis/arato-tamana-teams");
  }
  push("sb/中学生SB.csv");
  push("sb/");
  // Named athlete PB → stick to SB CSV (avoid 3000m予想ランキング drowning short names)
  const named = extractAthleteNameHints(query).length > 0;
  if (!named) {
    for (const s of findSourcesContaining(["SB", "記録"], {
      prefix: "drive-text/記録データベース/",
      limit: 12,
    })) {
      push(s);
    }
  }
  for (const s of baseSources) push(s);
  return out;
}

/** Prefer LINE ops digests for 岱明の連絡・集合・マット等. */
function boostDaimingLineSources(query: string, baseSources: string[]): string[] {
  if (
    !/岱明|いだてん|銀マット|合同練習|おおはま|三加和|朝練|ナイター|保護者LINE|和水町/.test(
      query,
    )
  ) {
    return baseSources;
  }
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (s: string) => {
    if (!s || seen.has(s)) return;
    seen.add(s);
    out.push(s);
  };
  push("out-analysis/line-chats");
  for (const s of baseSources) push(s);
  return out;
}

/**
 * Meet-aware source boost.
 * - 荒玉 / bare 駅伝 / 優勝・歴代 → aragyoku transcripts for resolved years
 * - ジュニア / なごみ 等の固有大会 → drive-text の該大会のみ（荒玉を先頭に入れない）
 */
function boostMeetYearSources(
  expandedQuery: string,
  baseSources: string[],
  defaultYear: number,
): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (s: string) => {
    if (!s || seen.has(s)) return;
    seen.add(s);
    out.push(s);
  };

  const kind: MeetKind = detectMeetKind(expandedQuery);
  const years = resolveRelativeYears(expandedQuery, defaultYear);
  const driveTokens = meetDriveTokens(kind, expandedQuery);

  if (driveTokens.length > 0 && kind !== "aragyoku") {
    const driveHits = sortMeetDriveSources(
      findSourcesContaining(driveTokens, { prefix: "drive-text/大会/", limit: 16 }),
      expandedQuery,
    );
    for (const s of driveHits) {
      if (years.length === 0 || years.some((y) => s.includes(String(y)) || s.includes(`${y}年度`))) {
        push(s);
      }
    }
    // If year filter emptied the list (path uses 年度 folder), retry without year filter
    if (out.length === 0) {
      for (const s of driveHits) push(s);
    }
  }

  if (kind === "aragyoku") {
    const courseMeta =
      /ペース|距離|区間|コース|\/km|分でいく|分で走/.test(expandedQuery);
    if (courseMeta) {
      // 概要・距離定義を先頭に（区間ペース質問で結果板ノイズに埋もれないように）
      push("out-analysis/aragyoku-overview.md");
      push("docs/aragyoku-ekiden-distance-definitions.md");
      push("out-analysis/aragyoku_top6_historical_average_pace.md");
      push("aragyoku/course-videos.md");
    }
    push("out-analysis/aragyoku-teams");
    push("aragyoku/winners-by-year.md");
    for (const y of years) {
      for (const g of ["男子", "女子"] as const) {
        push(`aragyoku/transcripts/${y}-${g}.json`);
        push(`aragyoku/ocr_raw/${y}-${g}.md`);
        push(`ekiden-ocr/${y}-${g}.md`);
      }
    }
    if (years.length === 0 && !courseMeta) {
      push("aragyoku");
      push("out-analysis/aragyoku-teams");
    }
  }

  const rest =
    kind === "junior" || kind === "nagomi" || kind === "other"
      ? baseSources.filter((s) => !isAragyokuCorpusSource(s))
      : baseSources;
  for (const s of rest) push(s);
  return out;
}

function kgSuggestsInScope(kg: KgQueryResult): boolean {
  if (kg.matched_nodes.some((n) => n.score >= 4)) return true;
  if (
    kg.matched_nodes.some(
      (n) =>
        (n.type === "Athlete" || n.type === "Entity" || n.id.startsWith("meet:")) &&
        n.score >= 2,
    )
  ) {
    return true;
  }
  return kg.corpus_sources.length > 0 && kg.matched_nodes.length > 0;
}

export async function answerQuestion(
  question: string,
  deps: AnswerDeps = {},
): Promise<AnswerResult> {
  const year = deps.defaultYear ?? new Date().getFullYear();
  const expanded = expandDateQuery(question, year);
  const topK = deps.topK ?? RETRIEVAL_BUDGET.topK;

  const canned = matchCannedAnswer(question);
  if (canned) {
    return {
      kind: "answered",
      text: formatForLine(canned.text),
      sources: [`canned:${canned.id}`],
    };
  }

  const clarify = matchClarifyAnswer(question);
  if (clarify) {
    return {
      kind: "answered",
      text: formatForLine(clarify.text),
      sources: [`clarify:${clarify.id}`],
    };
  }

  const kgQuery =
    deps.kgQuery ??
    ((q: string) => queryKnowledgeGraph(q, { topK: 16, expandHops: 2 }));
  const kg = kgQuery(expanded);

  let scope = classifyScope(question);
  if (
    scope.kind === "out_of_scope" &&
    !scope.hard &&
    kgSuggestsInScope(kg)
  ) {
    scope = { kind: "in_scope", reason: "kg_match" };
  }
  if (scope.kind === "out_of_scope") {
    return { kind: "refused", text: scope.message || OUT_OF_SCOPE_MESSAGE };
  }

  const route = deps.skipRouter
    ? {
        sources: boostDaimingLineSources(
          question,
          boostAthleteRecordSources(
            question,
            boostMeetYearSources(
              expanded,
              boostDateMeetSources(expanded, kg.corpus_sources),
              year,
            ),
          ),
        ).slice(0, RETRIEVAL_BUDGET.routeSources),
        focus: question,
        reason: "skip_router",
        via: "fallback" as const,
      }
    : await routeSources(expanded, kg, deps.llm);

  const preferredSources = boostDaimingLineSources(
    question,
    boostAthleteRecordSources(
      question,
      boostMeetYearSources(
        expanded,
        boostDateMeetSources(expanded, route.sources),
        year,
      ),
    ),
  ).slice(0, RETRIEVAL_BUDGET.routeSources);

  const fromSources = retrieveBySources(preferredSources, {
    query: expanded,
    perSource: RETRIEVAL_BUDGET.perSource,
    maxChunks: RETRIEVAL_BUDGET.maxChunks,
  });
  const retrieve = deps.retrieve ?? retrieveContext;
  const fromBm25 = retrieve(expanded, topK);
  const mergedCore = mergeRetrieved(fromSources, fromBm25, topK, { query: expanded });
  const withNeighbors = expandWithNeighbors(mergedCore, {
    radius: RETRIEVAL_BUDGET.neighborRadius,
    maxExtra: RETRIEVAL_BUDGET.neighborMaxExtra,
    query: expanded,
  });
  const merged = truncateRetrieved(withNeighbors, RETRIEVAL_BUDGET.maxChars);
  const sources = [
    ...new Set(
      merged.map((r) => {
        const m = r.chunk.source.match(/^(.*):\d+$/);
        return m ? m[1]! : r.chunk.source;
      }),
    ),
  ];

  if (!deps.llm) {
    return {
      kind: "offline",
      text: finalizeAnswerText(offlineAnswer(question, merged, expanded), question, deps),
      sources,
    };
  }

  try {
    const focusNote =
      route.focus && route.focus !== question ? `\n検索焦点: ${route.focus}` : "";
    const text = await deps.llm.complete(
      buildSystemPrompt(),
      buildUserPrompt(question + focusNote, merged),
    );
    return {
      kind: "answered",
      text: finalizeAnswerText(text, question, deps),
      sources,
    };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error("answerQuestion llm failed:", msg.slice(0, 300));
    return {
      kind: "error",
      text: "回答生成中にエラーが起きました。しばらくしてから、もう一度短い質問で試してください。",
    };
  }
}
