import { classifyScope, OUT_OF_SCOPE_MESSAGE } from "./scope.js";
import {
  currentFiscalYear,
  expandDateQuery,
  parseDateMentions,
  resolveRelativeDates,
  resolveRelativeYears,
} from "./dates.js";
import { matchCannedAnswer } from "./canned.js";
import { matchClarifyAnswer } from "./clarify.js";
import { isLegAthleteQuestion } from "./legs.js";
import {
  detectMeetKind,
  isAragyokuCorpusSource,
  meetDriveTokens,
  meetResultPathBoost,
  type MeetKind,
} from "./meets.js";
import { withMeetResultUrls, type MeetResultUrlEntry } from "./meetResultUrls.js";
import { appendPrimarySourceLinks, findPrimarySourceArtifacts } from "./primarySourceArtifacts.js";
import { routeSources } from "./router.js";
import type { LlmClient } from "./llm.js";
import { buildSystemPrompt, buildUserPrompt, MISSING_INFO_MESSAGE } from "../rag/prompt.js";
import { formatForLine } from "../line/format.js";
import {
  expandWithNeighbors,
  extractAthleteNameHints,
  findSourcesContaining,
  findSourcesWithText,
  isExhaustiveListQuery,
  mergeRetrieved,
  retrieveBySources,
  retrieveContext,
  truncateRetrieved,
  type RetrievedChunk,
} from "../rag/retrieve.js";
import { queryKnowledgeGraph, type KgQueryResult } from "../kg/query.js";
import { RETRIEVAL_BUDGET } from "../rag/budget.js";

export { RETRIEVAL_BUDGET } from "../rag/budget.js";
export { isExhaustiveListQuery } from "../rag/retrieve.js";

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
  /** Override the clock used for relative-date expansion (tests / replay). */
  now?: Date;
};

function finalizeAnswerText(
  text: string,
  question: string,
  deps: AnswerDeps,
  sources: string[],
): string {
  const primaryArtifacts = findPrimarySourceArtifacts(question, sources, {
    defaultYear: deps.defaultYear,
    now: deps.now,
  });
  // A primary PDF is an answer in its own right. Do not leave the generic
  // missing-information fallback next to a valid PDF link (whether it came
  // from the offline path or was echoed by the LLM).
  const formatted = formatForLine(text)
    .split(MISSING_INFO_MESSAGE)
    .join(primaryArtifacts.length > 0 ? "" : MISSING_INFO_MESSAGE)
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  const withResultUrls = withMeetResultUrls(formatted, question, {
    entries: deps.meetResultUrls,
    defaultYear: deps.defaultYear ?? currentFiscalYear(),
  });
  return appendPrimarySourceLinks(
    withResultUrls,
    primaryArtifacts,
  );
}

function offlinePreviewBudget(question: string): number {
  const q = question.normalize("NFKC");
  // 「全て提示」系は正本ダイジェストを広く見せる
  if (isExhaustiveListQuery(q)) {
    return 12_000;
  }
  // Rankings / full team records / win-count tables need wide windows
  if (
    /ランキング|トップ\s*\d+|全記録|全件|一覧|回数|2位まで|2位以内|最速|一番速|何位|順位|準優勝|優勝校|過去\s*\d+\s*年|過去5年|平均ペース|区間賞|区間順/.test(
      q,
    )
  ) {
    return 3600;
  }
  if (isLegAthleteQuestion(q)) {
    return 1400;
  }
  if (/優勝との差|優勝差|上位\s*\d+\s*人平均|上位\d人平均|学校別/.test(q)) {
    return 1600;
  }
  if (/自己ベスト|記録|\bSB\b|\bPB\b|何分|タイム/.test(q)) {
    return 900;
  }
  return 320;
}

function previewForOffline(text: string, question: string, maxChars?: number): string {
  const budget = maxChars ?? offlinePreviewBudget(question);
  const flat = text.replace(/\s+/g, " ");
  const q = question.normalize("NFKC");
  // Exhaustive: keep document head / wide window (do not needle-slice away tables)
  if (isExhaustiveListQuery(q)) {
    return flat.slice(0, budget);
  }
  // Full-record / ranking digests: prefer document head (title + early tables)
  if (/全記録|記録一覧|所属選手|ランキング|トップ\s*\d+|何位/.test(q)) {
    return flat.slice(0, budget);
  }
  // 優勝・準優勝の年度表（直近5年ブロックを先頭に据えた winners-by-year）
  if (/優勝|準優勝|2位/.test(q) && /荒玉|駅伝|過去/.test(q)) {
    for (const needle of ["女子・直近5年", "男子・直近5年", "準優勝校", "優勝・準優勝"]) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        const start = Math.max(0, idx - 40);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
    return flat.slice(0, budget);
  }
  // 「〇位の平均ペース」→ 順位別歴代表を優先
  if (/平均ペース|ペース/.test(q) && /位|歴代|過去/.test(q)) {
    const rankMatch = q.match(/([0-9０-９]+)位/);
    for (const needle of [
      rankMatch ? `総合${rankMatch[1]!.normalize("NFKC")}位の歴代平均ペース` : "",
      "順位別の歴代平均ペース",
      "全チーム・年度別の平均ペース",
      "平均ペースは",
    ].filter(Boolean)) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        const start = Math.max(0, idx - 40);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
  }
  // 「○年の区間賞」→ 該当年セクションを優先
  if (/区間賞|区間順/.test(q)) {
    const years = q.match(/20\d{2}/g) ?? [];
    const gender = /女子/.test(q) ? "女子" : /男子/.test(q) ? "男子" : "";
    const needles: string[] = [];
    for (const y of years) {
      if (gender) needles.push(`### ${y}年${gender}`);
      needles.push(`### ${y}年男子`, `### ${y}年女子`);
    }
    needles.push("区間賞", "区間別上位");
    for (const needle of needles) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        const start = Math.max(0, idx - 20);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
    return flat.slice(0, budget);
  }
  const isos = question.match(/20\d{2}-\d{2}-\d{2}/g) ?? [];
  for (const iso of isos) {
    const idx = flat.indexOf(iso);
    if (idx >= 0) {
      const start = Math.max(0, idx - 140);
      const end = Math.min(flat.length, idx + Math.max(180, budget - 140));
      return flat.slice(start, end);
    }
  }
  // 「優勝との差」列を優先（大会記録ボードより focus / team の差表）
  if (/優勝との差|優勝差|優勝から|優勝まで|離れて/.test(q)) {
    for (const needle of ["優勝との差", "+2:51", "+8:37", "優勝校"]) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        const years = q.match(/20\d{2}/g) ?? [];
        let start = Math.max(0, idx - 80);
        for (const y of years) {
          const yIdx = flat.lastIndexOf(y, idx);
          if (yIdx >= 0 && yIdx > idx - 400) start = Math.max(0, yIdx - 20);
        }
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
  }
  // 合同練習会の「いつ・どこ」質問は、保護者LINE要約の冒頭ではなく
  // 予定セクションを見せる。冒頭だけを返すと日付・会場が同じ文書内に
  // あってもオフライン回答から落ちる。
  if (/合同練習会|おおはま/.test(q)) {
    for (const needle of [
      "### 玉名市合同練習会",
      "おおはまふれあいセンター",
      "2026年9月22日",
    ]) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        const start = Math.max(0, idx - 40);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
  }
  // For a gender/leg record query, jump to the latest matching board row
  // rather than showing the digest's opening year or an unrelated table.
  if (
    /大会記録|区間記録|ボード.*記録/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    /男子.*\d区|女子.*\d区/.test(q)
  ) {
    const gender = /男子/.test(q) ? "男子" : "女子";
    const leg = q.match(/([1-6])区/)?.[1];
    if (leg) {
      const needle = `荒玉駅伝${gender}の${leg}区大会区間記録`;
      const idx = flat.lastIndexOf(needle);
      if (idx >= 0) {
        const start = Math.max(0, idx - 120);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
  }
  if (/距離|何キロ|何km|何ｍ|何メートル/.test(q) && /[1-6]区|区間/.test(q)) {
    const leg = q.match(/([1-6])区/)?.[1];
    const sectionNeedle = /女子/.test(q)
      ? "### 女子（全年度共通）"
      : /現行|2024年以降/.test(q)
        ? "### 男子・2024年以降（現行）"
        : "## 男子";
    const sectionStart = flat.indexOf(sectionNeedle);
    if (leg && sectionStart >= 0) {
      const row = flat.indexOf(`| ${leg}区 |`, sectionStart);
      if (row >= 0) {
        const start = Math.max(sectionStart, row - 70);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
  }
  if (/荒玉|駅伝/.test(q) && /何位|総合タイム|総合は/.test(q) && /20\d{2}/.test(q)) {
    const year = q.match(/20\d{2}/)?.[0];
    const gender = /女子/.test(q) ? "女子" : /男子/.test(q) ? "男子" : "";
    const team = /玉名付属|玉名附属|玉名附/.test(q)
      ? "玉高附属"
      : ["岱明", "玉高附属", "天水", "有明", "南関", "菊水", "玉東", "玉陵", "長洲"].find(
          (stem) => q.includes(stem),
        );
    if (year && gender && team) {
      const idx = flat.indexOf(`${year}年荒玉駅伝${gender} ${team}`);
      if (idx >= 0) {
        return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + budget));
      }
    }
  }
  // 「案浦竜士は何区を走った？」→ `| N | 案浦竜士 |` を N区 として明示
  if (isLegAthleteQuestion(q) && /何区/.test(q)) {
    const who = q.match(/([\u3400-\u9fff]{2,8})は.{0,20}何区/);
    if (who) {
      const name = who[1]!;
      const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const row = flat.match(new RegExp(`\\|\\s*([1-6])\\s*\\|\\s*${escaped}`));
      if (row && row.index != null) {
        const start = Math.max(0, row.index - 80);
        const window = flat.slice(start, Math.min(flat.length, start + budget));
        return `${row[1]}区 ${name}。 ${window}`;
      }
      const phrase = flat.match(new RegExp(`([1-6])区\\s*${escaped}`));
      if (phrase && phrase.index != null) {
        const start = Math.max(0, phrase.index - 40);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
  }
  // 「2025年岱明男子5区は誰」→ year section + `| 5 | 選手` row (not YoY summary)
  const legMatch = q.match(/([1-6])区/);
  if (legMatch && isLegAthleteQuestion(q)) {
    const leg = legMatch[1]!;
    const years = q.match(/20\d{2}/g) ?? [];
    const yearStarts: number[] = [];
    for (const y of years) {
      for (const needle of [
        `#### ${y}年`,
        `### ${y}年`,
        `## ${y}年`,
        `${y}年 区間`,
        `${y}年の区間`,
        `| ${y} |`,
      ]) {
        const idx = flat.indexOf(needle);
        if (idx >= 0) yearStarts.push(idx);
      }
    }
    const searchFrom = yearStarts.length > 0 ? Math.min(...yearStarts) : 0;
    const rowRe = new RegExp(`\\|\\s*${leg}\\s*\\|\\s*[^|\\d]{1,20}\\|`);
    const slice = flat.slice(searchFrom);
    const m = slice.match(rowRe);
    if (m && m.index != null) {
      const idx = searchFrom + m.index;
      const start = Math.max(0, idx - 60);
      return flat.slice(start, Math.min(flat.length, start + budget));
    }
    // Fallback: first `| N |` after year even if name cell is short
    const loose = slice.match(new RegExp(`\\|\\s*${leg}\\s*\\|`));
    if (loose && loose.index != null) {
      const idx = searchFrom + loose.index;
      const start = Math.max(0, idx - 60);
      return flat.slice(start, Math.min(flat.length, start + budget));
    }
  }
  // Prefer year rows in tables (e.g. "| 2023 |" average-pace digests) over title hits
  const years = question.match(/20\d{2}/g) ?? [];
  for (const y of years) {
    for (const needle of [`| ${y} |`, `|${y}|`, ` ${y}年`, y]) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        const start = Math.max(0, idx - 40);
        const end = Math.min(flat.length, start + budget);
        return flat.slice(start, end);
      }
    }
  }
  // Prefer a window around query keywords (LINE FAQ / coaching digests / athlete digests)
  const needles = [
    ...(question.match(
      /手押し車|犬歩き|分割走|ビルド|ペーラン|楽しさ|本気度|43分|2\.855|7:20|銀マット|地点|補強|厚底|ヴェイパー|メンタル|掛け算|高田麻那|高田麻由|隈部|ATRC|3000m|1500m|2位まで/g,
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
    const end = Math.min(flat.length, start + budget);
    return flat.slice(start, end);
  }
  return flat.slice(0, budget);
}

function offlineAnswer(
  question: string,
  retrieved: RetrievedChunk[],
  previewQuery?: string,
  missingInfoMessage = MISSING_INFO_MESSAGE,
): string {
  const lines = ["（オフライン回答）", "", `Q: ${question}`, ""];
  if (retrieved.length === 0) {
    lines.push(missingInfoMessage);
  } else {
    const hint = previewQuery ?? question;
    for (const [i, r] of retrieved.entries()) {
      const preview = previewForOffline(r.chunk.text, hint);
      lines.push(`${i + 1}. ${preview}`);
    }
  }
  return formatForLine(lines.join("\n"));
}

function isDateScheduleQuestion(query: string): boolean {
  return /予定|スケジュール|カレンダー|練習会|練習|集合|会場|場所|何時/.test(
    query.normalize("NFKC"),
  );
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
    const exactPracticeSources = findSourcesContaining(
      mentions.map((m) => m.iso),
      { prefix: "drive-text/練習/", limit: 12 },
    );
    for (const s of exactPracticeSources) push(s);
    push("calendar/events.daiming.yaml");

    // A dated practice/schedule question has a canonical dated practice note.
    // Keep implementation notes and unrelated chat/record sources out of the
    // first retrieval pass when that exact note exists.
    if (isDateScheduleQuestion(expandedQuery) && exactPracticeSources.length > 0) {
      return out;
    }

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
  const q = query.normalize("NFKC");
  // Year-over-year team questions belong to the 2024–2025 focus digest, not
  // the broad athlete/media corpus.
  if (/前年比|前年から|前年度比/.test(q) && /男子|女子/.test(q)) {
    const focus = baseSources.find((s) => /aragyoku_2024_2025_focus_teams/.test(s));
    if (focus) return [focus];
  }
  // A compact year/gender winner query is a meet-result lookup, not an
  // athlete SB lookup, even when it asks for a total time.
  if (/20\d{2}/.test(q) && /優勝/.test(q) && /男子|女子/.test(q) && /総合|タイム/.test(q)) {
    const winners = baseSources.find((s) => /winners-by-year/.test(s));
    if (winners) return [winners];
  }
  // Meet-record questions have a dedicated board digest. Keep the answer
  // focused there instead of letting the generic athlete/SB sources win.
  if (
    /大会記録|区間記録|ボード.*記録|記録保持|歴代記録/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    !/区間賞|区間順/.test(q)
  ) {
    const recordDigest = baseSources.find((s) => /aragyoku_meet_records/.test(s));
    if (recordDigest) return [recordDigest];
  }
  // 有田先輩＝指導相談。選手「有田」の SB/歴代と混同しない
  if (/有田先輩|有田大将|補強メニュー|手押し車|犬歩き|メンタル|楽しさ|本気度/.test(q)) {
    return baseSources.filter(
      (s) =>
        !/sb\/|記録データベース|3000m予想|aragyoku|ekiden-ocr|practice\/|daiming-practice/.test(
          s,
        ),
    );
  }
  if (
    !/自己ベスト|ベストタイム|自己記録|\bSB\b|\bPB\b|ベスト記録|記録|タイム|何分|何秒|800m?|1500m?|3000m?|5000m?|荒尾|玉名|所属|チーム|金栗|岱明|南関|天水|長洲|ATRC|アスリーツ|ランキング|最速|一番速|トップ\s*\d+|全記録|回数|2位まで/.test(
      q,
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
  // Exact athlete digests first (near-homonym safe)
  if (/高田麻那/.test(q)) {
    push("out-analysis/athletes/takada-mana.md");
    push("sb/SBデータベース.csv");
  }
  if (/\bATRC\b|ＡＴＲＣ/.test(q) && /記録|全記録|一覧|SB|タイム|選手/.test(q)) {
    push("out-analysis/arato-tamana-teams/ATRC.md");
    push("drive-text/personal/ATRC.md");
  }
  // Exact team digest for 「〇〇中所属選手の全記録」
  // Longest-first so 「玉名附中」does not also match 「玉名中」.
  const knownTeamFiles = [
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
    "NJAC",
    "ATRC",
    "玉陵",
  ];
  if (/記録|全記録|一覧|所属|選手/.test(q)) {
    const hit = knownTeamFiles.find((stem) => q.includes(stem));
    if (hit) {
      // A school + SB list has a dedicated current-year digest. The wide SB
      // CSV is global and row-chunked, so using it directly can return other
      // schools or only the first matching row.
      if (/\bSB\b|ＳＢ|シーズンベスト/.test(q)) {
        push(`out-analysis/arato-tamana-teams/${hit}_SB.md`);
      }
      push(`out-analysis/arato-tamana-teams/${hit}.md`);
    } else {
      const teamDigestHit = q.match(
        /([一-龥ァ-ヶA-Za-z・]{2,10}(?:高校附属中|附中|第四中|三中|海陽中|中))/u,
      );
      if (teamDigestHit) {
        push(`out-analysis/arato-tamana-teams/${teamDigestHit[1]!}.md`);
      }
    }
  }
  if (
    /3000m|3000ｍ/.test(q) &&
    /速い|一番|最速|ランキング|SB|自己ベスト|荒玉|何位|順位/.test(q)
  ) {
    push("out-analysis/2026_aragyoku_men_3000m_sb_ranking.md");
  }
  if (
    /1500m|1500ｍ/.test(q) &&
    /トップ\s*20|ランキング|SB|自己ベスト|荒玉|何位|順位/.test(q)
  ) {
    push("out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md");
  }
  // 「女子800mで岱明の上位3人平均」は学校別ランキング正本（SB CSV より先）
  const schoolPbRankQ =
    (/学校別|所属別/.test(q) && /ランキング|1500|800|平均/.test(q)) ||
    (/800m|800ｍ|1500m|1500ｍ/.test(q) &&
      /上位\s*\d+\s*人平均|上位\d人平均|学校別|所属別/.test(q));
  if (schoolPbRankQ) {
    if (/800/.test(q) || /女子/.test(q)) {
      push("out-analysis/2026_women_800m_1500m_pb_school_ranking.md");
    }
    if (/1500/.test(q) || /男子/.test(q) || !/800/.test(q)) {
      push("out-analysis/2026_men_1500m_pb_school_ranking.md");
    }
    push("out-analysis/2026_women_800m_1500m_pb_school_ranking.md");
    push("out-analysis/2026_men_1500m_pb_school_ranking.md");
  }
  if (/荒尾|玉名|金栗|岱明|南関|天水|長洲|ATRC|アスリーツ|玉東|有明|荒尾三|荒尾四|海陽|玉陵|玉南|玉高|附中|熊本大/.test(q)) {
    // Prefer exact digest already pushed; only use hub for non-full-record queries
    if (!/全記録|所属選手|記録一覧/.test(q)) {
      push("out-analysis/arato-tamana-teams");
    }
  }
  // 学校別平均ランキングは SB CSV で埋めない
  if (schoolPbRankQ) {
    for (const s of baseSources) {
      if (!s.startsWith("sb/") && !/line-chats/.test(s)) push(s);
    }
    return out;
  }
  push("sb/中学生SB.csv");
  push("sb/SBデータベース.csv");
  push("sb/");
  // 所属全記録は SB CSV で埋めない（exact team digest を優先）
  // かつ KG の広い hub（out-analysis / drive-text）を足さない —
  // retrieveBySources の prefix マッチで全チーム digest が流入するため。
  if (/全記録|所属選手|記録一覧/.test(q)) {
    const teamOnly = out.filter(
      (s) =>
        !s.startsWith("sb/") &&
        !s.includes("記録データベース/") &&
        !s.endsWith("/") &&
        s.includes("/") &&
        (/\.md$/i.test(s) || /\.csv$/i.test(s)) &&
        (s.includes("arato-tamana-teams/") ||
          s.includes("athletes/") ||
          s.includes("3000m_sb") ||
          s.includes("1500m_sb") ||
          s.includes("pb_school") ||
          s.includes("personal/ATRC")),
    );
    if (teamOnly.length > 0) {
      return teamOnly;
    }
  }
  // For a named school SB-list question, the dedicated digest is complete;
  // do not append the all-school CSV as an unfiltered fallback.
  if (/(?:\bSB\b|ＳＢ|シーズンベスト)/.test(q) && /荒尾三中/.test(q)) {
    const teamSb = out.find((s) => s.endsWith("/荒尾三中_SB.md"));
    if (teamSb) return [teamSb];
  }
  // Named athlete PB → stick to SB CSV (avoid 3000m予想ランキング drowning short names)
  const named = extractAthleteNameHints(q).length > 0;
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
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (s: string) => {
    if (!s || seen.has(s)) return;
    seen.add(s);
    out.push(s);
  };

  // なごみ駅伝の集合場所は大会資料だけでなく、保護者LINEの運用案内
  // にも明記される。集合場所を尋ねるときはLINE要約を一次候補にする。
  if (/なごみ駅伝.*集合場所|集合場所.*なごみ駅伝/.test(q)) {
    push("out-analysis/line-chats/daiming-parents.md");
    for (const s of baseSources) push(s);
    return out;
  }

  if (/practice_meets|affect_load|負荷に数え/.test(q)) {
    push("repo-docs/adr/006-practice-meets-not-load.md");
    push("docs/adr/006-practice-meets-not-load.md");
    push("docs/ai-practice-generation.md");
  }
  if (/夕練/.test(q) && /何時|開始|時刻|スタート|から/.test(q)) {
    push("practice/practice.2026.json");
    push("calendar/events.daiming.yaml");
  }

  // 「2025年岱明男子の優勝との差」は結果分析へ（地点分担 LINE ではない）
  if (
    /優勝との差|優勝差|優勝から|優勝まで/.test(q) &&
    /20\d{2}|荒玉|駅伝|男子|女子|岱明|玉高|天水|有明|南関|菊水/.test(q)
  ) {
    return baseSources.filter((s) => !/line-chats/.test(s));
  }
  // 学校別トラック平均は LINE ではなく PB ランキングへ
  if (/上位\s*\d+\s*人平均|上位\d人平均|学校別|所属別/.test(q) && /800|1500|ランキング/.test(q)) {
    return baseSources.filter((s) => !/line-chats/.test(s));
  }

  // 「2025年岱明男子5区は誰」は結果正本へ。地点分担・2.855 距離メモの LINE を先頭にしない
  if (isLegAthleteQuestion(q)) {
    return baseSources.filter((s) => !/line-chats/.test(s));
  }

  const lineOps =
    /岱明|いだてん|銀マット|合同練習|おおはま|三加和|朝練|ナイター|保護者LINE|和水|有田|補強|手押し車|犬歩き|分割走|厚底|ヴェイパー|地点分担|地点|土山コーチ|柴尾|曜日|集合時間|タイム目安|43分|区間配分|補強メニュー|2\.855|2区.*5区|5区.*2区|お別れ会|金栗駅伝|走り納め|体育館前|楽しさ|本気度/.test(
      q,
    );
  // 所属トラック全記録は line-chats ではなく arato-tamana-teams へ
  if (/全記録|所属選手|記録一覧/.test(q) && /中|ATRC|PROJECT|アスリーツ|クラブ/.test(q)) {
    return baseSources;
  }
  // トラック周長は practice 正本へ（岱明キーワードで LINE に流さない）
  if (/トラック/.test(q) && /1周|一周|周長|何メートル|何ｍ/.test(q)) {
    const trackOut: string[] = [];
    const trackSeen = new Set<string>();
    const trackPush = (s: string) => {
      if (!s || trackSeen.has(s)) return;
      trackSeen.add(s);
      trackOut.push(s);
    };
    trackPush("practice/daiming-practice-menus-kpace.md");
    trackPush("docs/data-model.md");
    for (const s of baseSources) {
      if (!/line-chats/.test(s)) trackPush(s);
    }
    return trackOut;
  }
  if (!lineOps && out.length === 0) {
    return baseSources;
  }
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
  if (lineOps) {
    push("out-analysis/line-chats");
  }
  for (const s of baseSources) push(s);
  return out;
}

function isNamedTeamSbListQuery(query: string): boolean {
  const q = query.normalize("NFKC");
  return /荒尾三中/.test(q) && /(?:\bSB\b|ＳＢ|シーズンベスト)/.test(q) && /選手|一覧|所属/.test(q);
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
  let years = resolveRelativeYears(expandedQuery, defaultYear);
  const nagomiOrderQ =
    kind === "nagomi" &&
    /オーダー|\d区|何区|区は誰|ランナー/.test(expandedQuery) &&
    !/結果/.test(expandedQuery);
  if (years.length === 0 && nagomiOrderQ) {
    years = [defaultYear];
  }
  const driveTokens = meetDriveTokens(kind, expandedQuery);
  const legAthleteQ = isLegAthleteQuestion(expandedQuery);
  const aragyokuDistanceQ =
    kind === "aragyoku" &&
    /距離|何キロ|何km|何ｍ|何メートル/.test(expandedQuery) &&
    /[1-6]区|区間/.test(expandedQuery) &&
    !/ペース/.test(expandedQuery);

  if (aragyokuDistanceQ) {
    push("out-analysis/aragyoku-overview.md");
    push("docs/aragyoku-ekiden-distance-definitions.md");
    return out;
  }

  if (driveTokens.length > 0 && kind !== "aragyoku") {
    const driveHits = sortMeetDriveSources(
      findSourcesContaining(driveTokens, { prefix: "drive-text/大会/", limit: 24 }),
      expandedQuery,
    );
    for (const s of driveHits) {
      if (/\.meta\.json/.test(s)) continue;
      if (years.length === 0 || years.some((y) => s.includes(String(y)) || s.includes(`${y}年度`))) {
        push(s);
      }
    }
    // If year filter emptied the list (path uses 年度 folder), retry without year filter
    if (out.length === 0) {
      for (const s of driveHits) {
        if (/\.meta\.json/.test(s)) continue;
        push(s);
      }
    }
  }

  if (kind === "aragyoku") {
    const lineOpsPrefer =
      /地点分担|タイム目安|43分|区間配分|有田|補強|朝練|銀マット|手押し車|犬歩き|2区.*5区|5区.*2区|2\.855/.test(
        expandedQuery,
      );
    const meetRecordQ =
      /大会記録|区間記録|ボード.*記録|総合大会記録|記録保持|歴代記録/.test(expandedQuery) &&
      !/区間賞|区間順/.test(expandedQuery);
    // 「区間賞」「区間順位」は当日結果正本（歴代区間記録ボードとは別）
    const legAwardQ =
      /区間賞|区間1位|区間一位|各区.*賞/.test(expandedQuery) ||
      (/区間順/.test(expandedQuery) && /荒玉|駅伝|\d区|誰|学年|名前/.test(expandedQuery));
    if (legAwardQ) {
      push("out-analysis/aragyoku_leg_awards.md");
    }
    const courseMeta =
      /ペース|距離|コース|\/km|分でいく|分で走/.test(expandedQuery) &&
      !lineOpsPrefer &&
      !meetRecordQ &&
      !legAwardQ &&
      !/何位|誰|選手|区間新|前年比|分析/.test(expandedQuery);
    // 「〇位の平均ペース」は計算正本（全チーム）を優先（距離概要より先）
    const rankPaceQ =
      (/平均ペース|\/km/.test(expandedQuery) || (/ペース/.test(expandedQuery) && /位/.test(expandedQuery))) &&
      /荒玉|駅伝|総合|歴代|過去|位/.test(expandedQuery) &&
      !legAwardQ;
    if (rankPaceQ) {
      push("out-analysis/aragyoku_all_teams_average_pace.md");
      push("out-analysis/aragyoku_top6_historical_average_pace.md");
      push("docs/aragyoku-ekiden-distance-definitions.md");
    }
    // 「○区は誰」「何区を走った」は距離質問ではない
    if (legAthleteQ) {
      const teamStem = [
        "荒尾海陽",
        "玉高附属",
        "荒尾三",
        "荒尾四",
        "三加和",
        "南関",
        "天水",
        "岱明",
        "有明",
        "玉南",
        "玉名",
        "玉東",
        "玉陵",
        "腹栄",
        "荒尾",
        "菊水",
        "長洲",
      ].find((stem) => expandedQuery.includes(stem));
      if (teamStem) push(`out-analysis/aragyoku-teams/${teamStem}.md`);
      else if (/玉名付属|玉名附属|玉名附/.test(expandedQuery)) {
        push("out-analysis/aragyoku-teams/玉高附属.md");
      }
      const names = extractAthleteNameHints(expandedQuery);
      for (const s of findSourcesWithText(names, {
        prefix: "out-analysis/aragyoku-teams/",
        limit: 4,
      })) {
        push(s);
      }
      push("out-analysis/aragyoku_2024_2025_focus_teams.md");
    }
    const focusTeamAnalysis =
      /岱明|玉名付属|玉名附属|玉高附属|天水|有明/.test(expandedQuery) &&
      /2024|2025|前年比|深掘り|分析|何位|短縮|区間新|荒玉|優勝との差|優勝差|優勝から/.test(
        expandedQuery,
      ) &&
      !legAwardQ;
    const winnerMarginQ = /優勝との差|優勝差|優勝から|優勝まで|離れて/.test(expandedQuery);
    if (focusTeamAnalysis || winnerMarginQ) {
      push("out-analysis/aragyoku_2024_2025_focus_teams.md");
    }
    if (meetRecordQ) {
      push("out-analysis/aragyoku_meet_records.md");
    }
    if (/2位まで|2位以内|総合2位|優勝.*回数|回数/.test(expandedQuery)) {
      push("out-analysis/aragyoku_top2_finish_counts.md");
      push("aragyoku/winners-by-year.md");
    }
    // 年度別の優勝・準優勝（回数集計ではなく year×school 表）
    if (
      /準優勝|優勝校|2位は|2位の学校/.test(expandedQuery) ||
      (/優勝/.test(expandedQuery) && /過去|歴代|年/.test(expandedQuery)) ||
      (/20\d{2}/.test(expandedQuery) && /優勝/.test(expandedQuery) && /男子|女子/.test(expandedQuery))
    ) {
      push("aragyoku/winners-by-year.md");
    }
    // Exact team history digest for 「〇〇の荒玉駅伝の過去の順位」/ 区間選手 / 優勝差
    // （区間賞・区間順位の全区間一覧とは別 — leg_awards 正本を優先）
    if (
      !legAwardQ &&
      (/過去|歴代|順位|2024|2025|分析|優勝との差|優勝差|優勝から/.test(expandedQuery) ||
        focusTeamAnalysis ||
        winnerMarginQ ||
        legAthleteQ) &&
      !courseMeta
    ) {
      const aragyokuTeams = [
        "荒尾海陽",
        "玉高附属",
        "荒尾三",
        "荒尾四",
        "三加和",
        "南関",
        "天水",
        "岱明",
        "有明",
        "玉南",
        "玉名",
        "玉東",
        "玉陵",
        "腹栄",
        "荒尾",
        "菊水",
        "長洲",
      ];
      let teamHit = /玉名付属|玉名附属|玉名附/.test(expandedQuery)
        ? "玉高附属"
        : aragyokuTeams.find((stem) => expandedQuery.includes(stem));
      if (teamHit) {
        push(`out-analysis/aragyoku-teams/${teamHit}.md`);
      }
    }
    if (courseMeta) {
      // 概要・距離定義を先頭に（区間ペース質問で結果板ノイズに埋もれないように）
      push("out-analysis/aragyoku-overview.md");
      push("docs/aragyoku-ekiden-distance-definitions.md");
      push("out-analysis/aragyoku_all_teams_average_pace.md");
      push("out-analysis/aragyoku_top6_historical_average_pace.md");
      push("aragyoku/course-videos.md");
    }
    if (!lineOpsPrefer) {
      // Prefer exact team file already pushed; hub only when not a per-team history Q
      if (!legAwardQ && !legAthleteQ && !out.some((s) => /aragyoku-teams\/[^/]+\.md$/.test(s))) {
        push("out-analysis/aragyoku-teams");
      }
      if (!legAwardQ && !legAthleteQ) {
        push("aragyoku/winners-by-year.md");
      }
      for (const y of years) {
        for (const g of ["男子", "女子"] as const) {
          // 区間賞質問では transcript JSON を二次ソースとして残す（学年・名前の突合用）
          if (legAthleteQ) continue;
          push(`aragyoku/transcripts/${y}-${g}.json`);
          if (!legAwardQ) {
            push(`aragyoku/ocr_raw/${y}-${g}.md`);
            push(`ekiden-ocr/${y}-${g}.md`);
          }
        }
      }
      if (years.length === 0 && !courseMeta && !legAwardQ && !legAthleteQ) {
        push("aragyoku");
        if (!out.some((s) => /aragyoku-teams\/[^/]+\.md$/.test(s))) {
          push("out-analysis/aragyoku-teams");
        }
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
    if (legAthleteQ) {
      continue;
    }
    if (
      lineOpsPreferRest &&
      /aragyoku-overview|aragyoku-ekiden-distance|average_pace|all_teams_average_pace|course-videos|aragyoku\/quiz|winners-by-year|aragyoku\/transcripts|ekiden-ocr/.test(
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

/**
 * 「全て提示して」系: 網羅できる正本だけに絞る（OCR/hub を落とす）。
 * preferred 先頭の exact ファイルを最大 4 件残す。
 */
export function narrowExhaustiveSources(query: string, sources: string[]): string[] {
  const q = query.normalize("NFKC");
  const out: string[] = [];
  const seen = new Set<string>();
  const push = (s: string) => {
    if (!s || seen.has(s) || out.length >= 4) return;
    if (!/\.(md|csv|ya?ml|json)$/i.test(s)) return;
    if (/analysis-ocr|ekiden-ocr|ocr_raw|notion-db|media-manifest|repo-docs\/adr/.test(s)) return;
    seen.add(s);
    out.push(s);
  };

  // Topic pins — one digest that alone can satisfy the full list
  if (/優勝|準優勝/.test(q) && /荒玉|駅伝|中体連/.test(q) && !/回数|2位まで|2位以内/.test(q)) {
    push("aragyoku/winners-by-year.md");
    return out;
  }
  if (/2位まで|2位以内|優勝.*回数|回数/.test(q) && /荒玉|駅伝/.test(q)) {
    push("out-analysis/aragyoku_top2_finish_counts.md");
    push("aragyoku/winners-by-year.md");
    return out;
  }
  if ((/平均ペース|\/km/.test(q) || (/ペース/.test(q) && /位|チーム|全/.test(q))) && /荒玉|駅伝/.test(q)) {
    push("out-analysis/aragyoku_all_teams_average_pace.md");
    push("out-analysis/aragyoku_top6_historical_average_pace.md");
    push("docs/aragyoku-ekiden-distance-definitions.md");
    return out;
  }
  if (/大会記録|区間記録|ボード/.test(q) && /荒玉|駅伝/.test(q) && !/区間賞|区間順/.test(q)) {
    push("out-analysis/aragyoku_meet_records.md");
    return out;
  }
  if (
    (/区間賞|区間1位|区間一位/.test(q) || /区間順/.test(q)) &&
    /荒玉|駅伝|\d{4}|区/.test(q)
  ) {
    push("out-analysis/aragyoku_leg_awards.md");
    return out;
  }
  if (/\bATRC\b|ＡＴＲＣ/.test(q) && /記録|選手|一覧/.test(q)) {
    push("out-analysis/arato-tamana-teams/ATRC.md");
    push("drive-text/personal/ATRC.md");
    return out;
  }
  if (/全記録|所属選手|記録一覧/.test(q)) {
    for (const s of sources) {
      if (/arato-tamana-teams\/[^/]+\.md$|athletes\/[^/]+\.md$/.test(s)) push(s);
    }
    if (out.length > 0) return out;
  }
  if (/優勝との差|前年比|深掘り|分析/.test(q) && /2024|2025|岱明|天水|有明|玉高|玉名付属/.test(q)) {
    push("out-analysis/aragyoku_2024_2025_focus_teams.md");
    return out;
  }

  for (const s of sources) push(s);
  return out.length > 0 ? out : sources.filter((s) => /\.(md|csv|json)$/i.test(s)).slice(0, 4);
}

export async function answerQuestion(
  question: string,
  deps: AnswerDeps = {},
): Promise<AnswerResult> {
  const now = deps.now ?? new Date();
  const year = deps.defaultYear ?? currentFiscalYear(now);
  const expanded = expandDateQuery(question, year, now);
  const topK = deps.topK ?? RETRIEVAL_BUDGET.topK;
  const exhaustive = isExhaustiveListQuery(expanded);
  const namedTeamSbList = isNamedTeamSbListQuery(expanded);

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
  // Keep KG intent matching on the user's wording. `expanded` carries the
  // current-fiscal-year retrieval anchor, but its synthetic year token should
  // not drown a topic-specific KG hint (for example, a generic pace query).
  const kg = kgQuery(question);

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

  let preferredSources = boostDaimingLineSources(
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

  if (exhaustive) {
    preferredSources = narrowExhaustiveSources(expanded, preferredSources);
  }

  const exactDatedPractice =
    isDateScheduleQuestion(expanded) &&
    preferredSources.some((s) => s.startsWith("drive-text/練習/"));
  if (exactDatedPractice) {
    preferredSources = preferredSources.filter(
      (s) => s === "calendar/events.daiming.yaml" || s.startsWith("drive-text/練習/"),
    );
  }

  const aragyokuDistanceQ =
    /荒玉|駅伝/.test(expanded) &&
    /距離|何キロ|何km|何ｍ|何メートル/.test(expanded) &&
    /[1-6]区|区間/.test(expanded) &&
    !/ペース/.test(expanded);

  const fromSources = retrieveBySources(preferredSources, {
    query: expanded,
    perSource: exhaustive ? 200 : RETRIEVAL_BUDGET.perSource,
    maxChunks: exhaustive ? 200 : RETRIEVAL_BUDGET.maxChunks,
    coverage: exhaustive ? "full" : "ranked",
  });
  const retrieve = deps.retrieve ?? retrieveContext;
  // Exhaustive: preferred digest coverage alone — BM25 OCR/ADR filler drowns the list
  // Race-leg questions already have a dedicated team/transcript route. A
  // second global BM25 pass can reintroduce the broad yearly analysis digest
  // and hide the requested team's row.
  const fromBm25 =
    exhaustive ||
    exactDatedPractice ||
    namedTeamSbList ||
    isLegAthleteQuestion(expanded) ||
    aragyokuDistanceQ
      ? []
      : retrieve(expanded, topK);
  const mergedCore = mergeRetrieved(
    fromSources,
    fromBm25,
    exhaustive ? Math.max(topK, fromSources.length, 96) : topK,
    { query: expanded, preferPrimaryOrder: exhaustive || isLegAthleteQuestion(expanded) },
  );
  const withNeighbors = expandWithNeighbors(mergedCore, {
    radius: exhaustive ? 0 : RETRIEVAL_BUDGET.neighborRadius,
    maxExtra: exhaustive ? 0 : RETRIEVAL_BUDGET.neighborMaxExtra,
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
    const primaryArtifacts = findPrimarySourceArtifacts(question, sources, {
      defaultYear: deps.defaultYear,
      now: deps.now,
    });
    return {
      kind: "offline",
      text: finalizeAnswerText(
        offlineAnswer(
          question,
          merged,
          expanded,
          primaryArtifacts.length > 0 ? "ご指定のPDFです。" : undefined,
        ),
        question,
        deps,
        sources,
      ),
      sources,
    };
  }

  try {
    const focusNote =
      route.focus && route.focus !== question ? `\n検索焦点: ${route.focus}` : "";
    const relativeDateMentions = resolveRelativeDates(question, now);
    const dateNote =
      relativeDateMentions.length > 0
        ? `\n日付解釈: ${relativeDateMentions.map((m) => m.iso).join(", ")}`
        : "";
    const text = await deps.llm.complete(
      buildSystemPrompt({ exhaustive }),
      buildUserPrompt(question + focusNote + dateNote, merged, { exhaustive }),
    );
    return {
      kind: "answered",
      text: finalizeAnswerText(text, question, deps, sources),
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
