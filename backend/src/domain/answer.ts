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
  // Prefer a window around query keywords (LINE FAQ / coaching digests)
  const needles = [
    ...(question.match(
      /手押し車|犬歩き|分割走|ビルド|ペーラン|楽しさ|本気度|43分|2\.855|7:20|銀マット|地点|補強|厚底|ヴェイパー|メンタル|掛け算/g,
    ) ?? []),
    ...((question.match(/[\u3040-\u30ff\u3400-\u9fff]{2,8}/g) ?? []).filter(
      (t) => t.length >= 2 && !/^(先輩|教えて|ください|どう|なに|何|は|を|の|が)$/.test(t),
    )),
  ];
  let bestIdx = -1;
  for (const n of needles) {
    const idx = flat.indexOf(n);
    if (idx >= 0 && (bestIdx < 0 || idx < bestIdx)) bestIdx = idx;
  }
  if (bestIdx >= 0) {
    const start = Math.max(0, bestIdx - 80);
    const end = Math.min(flat.length, start + maxChars);
    return flat.slice(start, end);
  }
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
  // 有田先輩＝指導相談。選手「有田」の SB/歴代と混同しない
  if (/有田先輩|有田大将|補強メニュー|手押し車|犬歩き|メンタル|楽しさ|本気度/.test(query)) {
    return baseSources.filter(
      (s) =>
        !/sb\/|記録データベース|3000m予想|aragyoku|ekiden-ocr|practice\/|daiming-practice/.test(
          s,
        ),
    );
  }
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

/** Prefer LINE ops digests for 岱明の連絡・集合・マット・朝練・地点分担・有田指導など. */
function boostDaimingLineSources(query: string, baseSources: string[]): string[] {
  const q = query.normalize("NFKC");
  const lineOps =
    /岱明|いだてん|銀マット|合同練習|おおはま|三加和|朝練|ナイター|保護者LINE|和水|有田|補強|手押し車|犬歩き|分割走|厚底|ヴェイパー|地点分担|地点|土山コーチ|柴尾|曜日|集合時間|タイム目安|43分|区間配分|補強メニュー|2\.855|2区.*5区|5区.*2区|お別れ会|金栗駅伝|走り納め|体育館前|楽しさ|本気度/.test(
      q,
    );
  if (!lineOps) {
    return baseSources;
  }
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (s: string) => {
    if (!s || seen.has(s)) return;
    seen.add(s);
    out.push(s);
  };
  // Specific digests first so 荒玉 preferred に埋もれない
  if (/有田|補強|手押し車|犬歩き|分割走|厚底|ヴェイパー|タイム目安|43分|区間配分|走り納め|楽しさ|本気度|体育館前|2区.*5区|5区.*2区/.test(q)) {
    push("out-analysis/line-chats/arita-taisho.md");
  }
  if (/朝練|曜日|地点分担|地点|土山コーチ|柴尾|2\.855|2区.*5区|5区.*2区|お別れ会|金栗駅伝|7:20|7時20/.test(q)) {
    push("out-analysis/line-chats/daiming-staff.md");
  }
  if (/銀マット|合同練習|おおはま|三加和|和水|保護者|会費|玉名選手権|地震/.test(q)) {
    push("out-analysis/line-chats/daiming-parents.md");
  }
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
    const lineOpsPrefer =
      /地点分担|タイム目安|43分|区間配分|有田|補強|朝練|銀マット|手押し車|犬歩き|2区.*5区|5区.*2区|2\.855/.test(
        expandedQuery,
      );
    const courseMeta =
      /ペース|距離|区間|コース|\/km|分でいく|分で走/.test(expandedQuery) &&
      !lineOpsPrefer;
    if (courseMeta) {
      // 概要・距離定義を先頭に（区間ペース質問で結果板ノイズに埋もれないように）
      push("out-analysis/aragyoku-overview.md");
      push("docs/aragyoku-ekiden-distance-definitions.md");
      push("out-analysis/aragyoku_top6_historical_average_pace.md");
      push("aragyoku/course-videos.md");
    }
    if (!lineOpsPrefer) {
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
  }

  const rest =
    kind === "junior" || kind === "nagomi" || kind === "other"
      ? baseSources.filter((s) => !isAragyokuCorpusSource(s))
      : baseSources;
  const lineOpsPreferRest =
    /地点分担|タイム目安|43分|区間配分|有田|補強|朝練|銀マット|手押し車|犬歩き|2区.*5区|5区.*2区|2\.855/.test(
      expandedQuery,
    );
  for (const s of rest) {
    if (
      lineOpsPreferRest &&
      /aragyoku-overview|aragyoku-ekiden-distance|average_pace|course-videos|aragyoku\/quiz|winners-by-year|aragyoku\/transcripts|ekiden-ocr/.test(
        s,
      )
    ) {
      continue;
    }
    push(s);
  }
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
