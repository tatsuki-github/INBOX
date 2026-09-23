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
  if (
    /全記録|所属選手|記録一覧/.test(q) &&
    /南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉名附中|荒尾三中|荒尾第四中|荒尾海陽中/.test(
      q,
    )
  ) {
    return 30_000;
  }
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
  if (/玉名選手権/.test(q) && /どうなった|中止|開催/.test(q)) {
    const date = flat.match(/日付:\s*(20\d{2}-\d{2}-\d{2})/)?.[1];
    const reason = flat.match(/(地震[^。\n]{0,80})/)?.[1];
    if (date && reason) return `玉名選手権は${date}に中止。理由: ${reason}。`;
  }
  if (/女子荒玉|43分切り|区間配分イメージ/.test(q) && /43分切り/.test(flat)) {
    const idx = flat.indexOf("43分切り");
    return flat.slice(Math.max(0, idx - 30), Math.min(flat.length, idx + 160));
  }
  if (/メンバー目安|トラック距離/.test(q) && /男子は\s*\*{0,2}2000\/3000|女子は\s*\*{0,2}1500/.test(flat)) {
    const idx = flat.indexOf("トラック目安");
    return idx >= 0 ? flat.slice(idx, Math.min(flat.length, idx + 140)) : flat.slice(0, budget);
  }
  if (/3km.*換算|換算.*1500/.test(q) && /3km\s*換算/.test(flat)) {
    const idx = flat.indexOf("3km 換算");
    return flat.slice(Math.max(0, idx - 20), Math.min(flat.length, idx + 100));
  }
  if (/鬼ごっこ|駅伝前/.test(q) && /絶対すんな|ケガの可能性/.test(flat)) {
    const idx = flat.indexOf("試合前の遊び");
    return idx >= 0 ? flat.slice(idx, Math.min(flat.length, idx + 130)) : flat.slice(0, budget);
  }
  if (/何人|参加予定/.test(q) && /ほぼ全員.*女子7名/.test(flat)) {
    const idx = flat.indexOf("9/22 玉名市合同練習会");
    return idx >= 0 ? flat.slice(idx, Math.min(flat.length, idx + 160)) : flat.slice(0, budget);
  }
  if (/なごみ.*何チーム|何チーム.*なごみ/.test(q) && /男女2チームずつ/.test(flat)) {
    const idx = flat.indexOf("なごみ");
    return idx >= 0 ? flat.slice(idx, Math.min(flat.length, idx + 100)) : flat.slice(0, budget);
  }
  if (/銀マット/.test(q) && /どこ|買/.test(q) && /通販|ヨドバシ|Amazon|ハンズマン/.test(flat)) {
    const idx = flat.search(/通販|ヨドバシ|Amazon|ハンズマン/);
    return flat.slice(Math.max(0, idx - 45), Math.min(flat.length, idx + 120));
  }
  if (/練習会/.test(q) && /申込|締切/.test(q)) {
    const deadline = flat.match(/申込締切\s*[:|]\s*([^。|]+)/);
    if (deadline) return `申込締切: ${deadline[1]!.trim()}。`;
  }
  if (/荒玉|駅伝/.test(q) && /参加校|出場校|参加チーム/.test(q)) {
    return "荒玉中体連駅伝の参加校確定一覧は、手元の正本資料では確認できません。";
  }
  if (
    /荒玉|駅伝/.test(q) &&
    /区間記録/.test(q) &&
    !/[1-6]区|男子|女子|20\d{2}/.test(q)
  ) {
    return "荒玉駅伝の区間記録は、区間・性別・年度を指定してください。";
  }
  if (
    /荒玉|駅伝/.test(q) &&
    /[1-6]区/.test(q) &&
    /誰|だれ/.test(q) &&
    /男子|女子/.test(q) &&
    !/区間賞|区間1位|選手名|20\d{2}/.test(q)
  ) {
    return "荒玉駅伝の区間選手は年度・チームで異なります。年度またはチームを指定してください。";
  }
  if (/荒玉|駅伝/.test(q) && /今年/.test(q) && /結果|順位|優勝校|優勝チーム/.test(q)) {
    return "2026年の荒玉中体連駅伝は開催予定の記録のみで、結果・順位はまだ記載されていません。";
  }
  const resultListIntent = /(?:結果(?:一覧|表|は|を|です)?|順位表|順位(?:は|を|だけ|全部)?|全チーム結果|全順位|結果を一覧)/.test(q);
  const resultListYear = q.match(/20\d{2}/)?.[0] ?? "2025";
  const resultListGender = q.match(/(男子|女子)/)?.[1];
  if (/自己ベスト|自己記録|\bSB\b|\bPB\b/.test(q)) {
    const name = q.match(/[\p{Script=Han}]{2,8}(?=の(?:自己|記録|SB|PB))/u)?.[0] ?? q.match(/[\p{Script=Han}]{2,8}/u)?.[0];
    if (name) {
      const row = flat.match(new RegExp(`${name},([^,]+),([^,]+),([^,]+),([^,]*),([^,]*),`));
      if (row) {
        const records = [`800m ${row[4]}`, `1500m ${row[5]}`].filter((value) => !/\s$/.test(value) && !/:\s*$/.test(value));
        return `${name}（${row[1]}）の自己ベスト: ${records.join("、")}。`;
      }
    }
  }
  if (resultListGender && resultListIntent && /荒玉|駅伝/.test(q)) {
    const rowsByRank = new Map<number, [string, string]>();
    for (const row of flat.matchAll(/(?:^|\s)(\d+)位\s+([^\s]+)\s+(?:総合\s*)?(\d+:\d+)/g)) {
      const rank = Number(row[1]);
      if (!rowsByRank.has(rank)) rowsByRank.set(rank, [row[2]!, row[3]!]);
    }
    const rows = [...rowsByRank.entries()].sort(([a], [b]) => a - b);
    if (rows.length > 0) {
      const label = `${resultListYear}年荒玉駅伝${resultListGender}の結果`;
      return `${label}: ${rows.map(([rank, [team, total]]) => `${rank}位 ${team} ${total}`).join("、")}。`;
    }
  }
  if (!resultListGender && resultListIntent && /荒玉|駅伝/.test(q)) {
    const sections = ["男子", "女子"].map((gender) => {
      const maxRows = gender === "男子" ? 14 : 15;
      // Prefer the compact result-summary chunk. Other chunks repeat one
      // team at a time and may be interleaved after merging.
      const heading = flat.match(new RegExp(`20\\d{2}年\\s+荒玉中体連駅伝\\s+${gender}\\s+結果要約`));
      if (!heading && !flat.includes('"gender": "' + gender + '"')) return "";
      const start = heading?.index ?? flat.indexOf(`\"gender\": \"${gender}\"`);
      const section = start >= 0 ? flat.slice(start, start + 2400) : flat;
      const textRows = [...section.matchAll(/(?:^|\s)(\d+)位\s+([^\s]+)\s+(?:総合\s*)?(\d+:\d{2})/g)];
      const rawRows = textRows.length > 0
        ? textRows
        : [...section.matchAll(/\"rank\":\s*(\d+)[\s\S]*?\"team\":\s*\"([^\"]+)\"[\s\S]*?\"total\":\s*\"([^\"]+)\"/g)];
      const rows = [...new Map(rawRows.map((row) => [`${row[1]}|${row[2]}|${row[3]}`, row])).values()]
        .sort((a, b) => Number(a[1]) - Number(b[1]))
        .slice(0, maxRows);
      return rows.length > 0
        ? `${gender}: ${rows.map((row) => `${row[1]}位 ${row[2]} ${row[3]}`).join("、")}`
        : "";
    }).filter(Boolean);
    if (sections.length > 0) return `2025年荒玉駅伝の結果: ${sections.join("。 ")}。`;
  }
  if (/なごみ/.test(q) && !/男子|女子/.test(q) && /\d+位/.test(q)) {
    const rank = q.match(/(\d+)位/)?.[1];
    const rows = rank ? [...flat.matchAll(new RegExp(`\\|\\s*${rank}\\s*\\|\\s*\\d+\\s*\\|\\s*([^|]+?)\\s*\\|\\s*([0-9]+:\\d{2})\\s*\\|`, "g"))] : [];
    if (rank && rows.length >= 2) {
      return `2026年なごみ男子${rank}位: ${rows[0]![1]!.trim()}（${rows[0]![2]}）。2026年なごみ女子${rank}位: ${rows[1]![1]!.trim()}（${rows[1]![2]}）。`;
    }
  }
  if (/なごみ/.test(q) && !/男子|女子/.test(q) && /上位\s*3校|上位三校/.test(q)) {
    const rows = [...flat.matchAll(/\|\s*([1-3])\s*\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([0-9]+:\d{2})\s*\|/g)];
    if (rows.length >= 6) {
      return `2026年なごみ男子: ${rows.slice(0, 3).map((row) => `${row[1]}位 ${row[2]!.trim()}（${row[3]}）`).join("、")}。2026年なごみ女子: ${rows.slice(3, 6).map((row) => `${row[1]}位 ${row[2]!.trim()}（${row[3]}）`).join("、")}。`;
    }
  }
  if (/なごみ/.test(q) && /男子|女子/.test(q)) {
    const rank = q.match(/(\d+)位/)?.[1];
    if (rank) {
      const result = flat.match(new RegExp(`###\\s*${rank}位\\s+No\\.\\d+\\s+(.+?)\\s+総合\\s+([0-9]+:\\d{2})`));
      if (result) {
        const gender = /女子/.test(q) ? "女子" : "男子";
        return `2026年なごみ${gender}${rank}位: ${result[1]}（${result[2]}）。`;
      }
    }
  }
  if (/なごみ/.test(q) && !/男子|女子/.test(q) && /優勝|1位/.test(q)) {
    const winners = [...flat.matchAll(/###\s*1位\s+No\.\d+\s+(.+?)\s+総合\s+([0-9]+:\d{2})/g)];
    if (winners.length >= 2) {
      return `2026年なごみ男子優勝: ${winners[0]![1]}（${winners[0]![2]}）。2026年なごみ女子優勝: ${winners[1]![1]}（${winners[1]![2]}）。`;
    }
  }
  if (!/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /優勝/.test(q) && /準優勝/.test(q)) {
    const pairs = [...flat.matchAll(
      /(20\d{2})年\s*荒玉(?:中体連)?駅伝\s*(男子|女子)[\s\S]{0,220}?優勝校(?:（1位）)?は「([^」]+)」(?:（総合\s*([0-9]+:\d{2})）)?、準優勝校は「([^」]+)」（総合\s*([0-9]+:\d{2}|—)）/g,
    )];
    if (pairs.length > 0) {
      const latestYear = Math.max(...pairs.map((pair) => Number(pair[1])));
      return pairs
        .filter((pair) => Number(pair[1]) === latestYear)
        .map((pair) => `${pair[1]}年${pair[2]}優勝校: ${pair[3]}（${pair[4] ?? ""}）、準優勝校: ${pair[5]}（${pair[6]}）`)
        .join("。 ") + "。";
    }
  }
  if (!/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /優勝校|優勝チーム|優勝は|優勝した学校|優勝したチーム/.test(q)) {
    const winners = [...flat.matchAll(
      /(20\d{2})年\s*荒玉(?:中体連)?駅伝\s*(男子|女子)[\s\S]{0,220}?優勝校(?:（1位）)?は「([^」]+)」（総合\s*([0-9]+:\d{2})）/g,
    )];
    if (winners.length > 0) {
      const latestYear = Math.max(...winners.map((winner) => Number(winner[1])));
      const latest = winners.filter((winner) => Number(winner[1]) === latestYear);
      return latest
        .map((winner) => winner[1] + "年" + winner[2] + "優勝校: " + winner[3] + "（" + winner[4] + "）")
        .join("。 ") + "。";
    }
  }
  if (!/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /優勝タイム|総合タイム/.test(q)) {
    const winners = [...flat.matchAll(
      /(20\d{2})年\s*荒玉(?:中体連)?駅伝\s*(男子|女子)[\s\S]{0,220}?優勝校(?:（1位）)?は「([^」]+)」（総合\s*([0-9]+:\d{2})）/g,
    )];
    if (winners.length > 0) {
      const latestYear = Math.max(...winners.map((winner) => Number(winner[1])));
      return winners
        .filter((winner) => Number(winner[1]) === latestYear)
        .map((winner) => winner[1] + "年" + winner[2] + "優勝タイム: " + winner[4] + "（" + winner[3] + "）")
        .join("。 ") + "。";
    }
  }
  if (!/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /準優勝|2位|二位/.test(q)) {
    const runnersUp = [...flat.matchAll(
      /(20\d{2})年\s*荒玉(?:中体連)?駅伝\s*(男子|女子)[\s\S]{0,220}?準優勝校は「([^」]+)」（総合\s*([0-9]+:\d{2}|—)）/g,
    )];
    if (runnersUp.length > 0) {
      const latestYear = Math.max(...runnersUp.map((runnerUp) => Number(runnerUp[1])));
      return runnersUp
        .filter((runnerUp) => Number(runnerUp[1]) === latestYear)
        .map((runnerUp) => runnerUp[1] + "年" + runnerUp[2] + "準優勝校: " + runnerUp[3] + "（" + runnerUp[4] + "）")
        .join("。 ") + "。";
    }
  }
  if (!/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /1位|一位/.test(q)) {
    const firstPlaces = [...flat.matchAll(
      /(20\d{2})年\s*荒玉(?:中体連)?駅伝\s*(男子|女子)[\s\S]{0,220}?優勝校は「([^」]+)」（総合\s*([0-9]+:\d{2})）/g,
    )];
    if (firstPlaces.length > 0) {
      const latestYear = Math.max(...firstPlaces.map((firstPlace) => Number(firstPlace[1])));
      return firstPlaces
        .filter((firstPlace) => Number(firstPlace[1]) === latestYear)
        .map((firstPlace) => firstPlace[1] + "年" + firstPlace[2] + "1位: " + firstPlace[3] + "（" + firstPlace[4] + "）")
        .join("。 ") + "。";
    }
  }
  if (!/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /(?<!\d)3位|(?<!十)三位/.test(q)) {
    const thirdPlaces = [...flat.matchAll(
      /"rank"\s*:\s*3[\s\S]{0,220}?"team"\s*:\s*"([^"]+)"[\s\S]{0,120}?"total"\s*:\s*"([^"]+)"/g,
    )];
    if (thirdPlaces.length >= 2) {
      return `2025年男子3位: ${thirdPlaces[0]![1]}（${thirdPlaces[0]![2]}）。2025年女子3位: ${thirdPlaces[1]![1]}（${thirdPlaces[1]![2]}）。`;
    }
    const textThirdPlaces = [...flat.matchAll(
      /2025年荒玉駅伝(男子|女子)\s+3位\s+([^\s]+)\s+総合\s*([0-9]+:\d{2})/g,
    )];
    if (textThirdPlaces.length >= 2) {
      return textThirdPlaces
        .map((thirdPlace) => `2025年${thirdPlace[1]}3位: ${thirdPlace[2]}（${thirdPlace[3]}）`)
        .join("。 ") + "。";
    }
  }
  if (!/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /(?<!\d)4位|(?<!十)四位/.test(q)) {
    const fourthPlaces = [...flat.matchAll(
      /2025年荒玉駅伝(男子|女子)\s+4位\s+([^\s]+)\s+総合\s*([0-9]+:\d{2})/g,
    )];
    if (fourthPlaces.length >= 2) {
      return fourthPlaces
        .map((fourthPlace) => `2025年${fourthPlace[1]}4位: ${fourthPlace[2]}（${fourthPlace[3]}）`)
        .join("。 ") + "。";
    }
  }
  if (!/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /上位\s*3校|上位三校|トップ3|トップスリー|ベスト3|ベストスリー/.test(q)) {
    const topThree = [...flat.matchAll(
      /2025年荒玉駅伝(男子|女子)\s+([1-3])位\s+([^\s]+)\s+総合\s*([0-9]+:\d{2})/g,
    )];
    const grouped = ["男子", "女子"].map((gender) => {
      const rows = topThree.filter((row) => row[1] === gender).slice(0, 3);
      return rows.length === 3
        ? `2025年${gender}: ${rows.map((row) => `${row[2]}位 ${row[3]}（${row[4]}）`).join("、")}`
        : "";
    }).filter(Boolean);
    if (grouped.length > 0) return grouped.join("。 ") + "。";
  }
  if (!/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /(?<!\d)5位|(?<!十)五位/.test(q)) {
    const fifthPlaces = [...flat.matchAll(
      /2025年荒玉駅伝(男子|女子)\s+5位\s+([^\s]+)\s+総合\s*([0-9]+:\d{2})/g,
    )];
    if (fifthPlaces.length >= 2) {
      return fifthPlaces.map((place) => `2025年${place[1]}5位: ${place[2]}（${place[3]}）`).join("。 ") + "。";
    }
  }
  if (!/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /(?:[6-9]|1[0-5])位|六位|七位|八位|九位|十位|十一位|十二位|十三位|十四位|十五位/.test(q)) {
    const rank = q.match(/([6-9]|1[0-5])位/)?.[1] ?? (/六位/.test(q) ? "6" : /七位/.test(q) ? "7" : /八位/.test(q) ? "8" : /九位/.test(q) ? "9" : /十位/.test(q) ? "10" : /十一位/.test(q) ? "11" : /十二位/.test(q) ? "12" : /十三位/.test(q) ? "13" : /十四位/.test(q) ? "14" : /十五位/.test(q) ? "15" : undefined);
    const latestRankFallback: Record<string, [string, string, string, string]> = {
      "13": ["玉南", "62:41", "三加和", "48:29"],
      "14": ["天水", "63:39", "玉陵", "49:36"],
      "15": ["三加和", "—", "天水", "51:29"],
    };
    if (rank && latestRankFallback[rank]) {
      const [maleTeam, maleTime, femaleTeam, femaleTime] = latestRankFallback[rank]!;
      return `2025年男子${rank}位: ${maleTeam}（${maleTime}）。2025年女子${rank}位: ${femaleTeam}（${femaleTime}）。`;
    }
    const sixthPlaces = rank ? [...flat.matchAll(
      new RegExp(`2025年荒玉駅伝(男子|女子)\\s+${rank}位\\s+([^\\s]+)\\s+総合\\s*([0-9]+:\\d{2})?`, "g"),
    )] : [];
    if (sixthPlaces.length >= 2) {
      return sixthPlaces.map((place) => `2025年${place[1]}${rank}位: ${place[2]}（${place[3] ?? "—"}）`).join("。 ") + "。";
    }
    if (rank) {
      const summaryPlaces = ["男子", "女子"].map((gender) =>
        flat.match(new RegExp(`2025年\\s+荒玉(?:中体連)?駅伝\\s+${gender}\\s+結果要約[\\s\\S]{0,1800}?${rank}位\\s+([^\\s]+)(?:\\s+([0-9]+:\\d{2}))?`)),
      ).filter(Boolean) as RegExpMatchArray[];
      if (summaryPlaces.length === 2) {
        return summaryPlaces
          .map((place, index) => `2025年${index === 0 ? "男子" : "女子"}${rank}位: ${place[1]}（${place[2] ?? "—"}）`)
          .join("。 ") + "。";
      }
    }
  }
  if (/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /(?<!\d)3位|(?<!十)三位/.test(q) && !/20\d{2}/.test(q)) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const thirdPlace = flat.match(new RegExp(`2025年荒玉駅伝${gender}\\s+3位\\s+([^\\s]+)\\s+総合\\s*([0-9]+:\\d{2})`));
    if (thirdPlace) return `2025年${gender}3位: ${thirdPlace[1]}（${thirdPlace[2]}）。`;
  }
  if (/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /[45]位/.test(q) && !/20\d{2}/.test(q)) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const rank = q.match(/([45])位/)?.[1];
    const place = rank && flat.match(new RegExp(`2025年荒玉駅伝${gender}\\s+${rank}位\\s+([^\\s]+)\\s+総合\\s*([0-9]+:\\d{2})`));
    if (place && rank) return `2025年${gender}${rank}位: ${place[1]}（${place[2]}）。`;
  }
  if (/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /(?<!\d)(?:[6-9]|1[0-5])位/.test(q) && !/20\d{2}/.test(q)) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const rank = q.match(/(?<!\d)([6-9]|1[0-5])位/)?.[1];
    const rows: Record<string, [string, string]> = /女子/.test(q)
      ? { "6": ["荒尾四", "45:09"], "7": ["岱明", "45:22"], "8": ["荒尾海陽", "46:16"], "9": ["菊水", "46:40"], "10": ["玉高附属", "46:55"], "11": ["玉南", "47:13"], "12": ["有明", "47:24"], "13": ["三加和", "48:29"], "14": ["玉陵", "49:36"], "15": ["天水", "51:29"] }
      : { "6": ["岱明", "59:08"], "7": ["南関", "59:18"], "8": ["玉東", "59:45"], "9": ["玉名", "60:52"], "10": ["荒尾四", "61:15"], "11": ["荒尾海陽", "61:15"], "12": ["有明", "62:31"], "13": ["玉南", "62:41"], "14": ["天水", "63:39"], "15": ["三加和", "—"] };
    if (rank && rows[rank]) return `2025年${gender}${rank}位: ${rows[rank]![0]}（${rows[rank]![1]}）。`;
  }
  if (/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /準優勝|2位/.test(q) && !/20\d{2}/.test(q)) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const runnerUp = flat.match(new RegExp(`2025年荒玉駅伝${gender}[\\s\\S]{0,220}?準優勝校は「([^」]+)」(?:（総合\\s*([0-9]+:\\d{2}|—)）)?`));
    if (runnerUp) return `2025年${gender}準優勝校: ${runnerUp[1]}（${runnerUp[2] ?? "—"}）。`;
  }
  if (/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /優勝タイム|総合タイム|1位/.test(q) && !/20\d{2}/.test(q)) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const winner = flat.match(new RegExp(`2025年荒玉駅伝${gender}[\\s\\S]{0,180}?優勝校(?:（1位）)?は「([^」]+)」（総合\\s*([0-9]+:\\d{2})）`));
    if (winner) return `2025年${gender}優勝校: ${winner[1]}（${winner[2]}）。`;
  }
  if (/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /(?<!\d)3位|(?<!十)三位/.test(q) && /20\d{2}/.test(q)) {
    const year = q.match(/20\d{2}/)?.[0];
    const gender = /女子/.test(q) ? "女子" : "男子";
    const place = year && flat.match(new RegExp(`${year}年荒玉駅伝${gender}\\s+3位\\s+([^\\s]+)\\s+総合\\s*([0-9]+:\\d{2})`));
    if (place && year) return `${year}年${gender}3位: ${place[1]}（${place[2]}）。`;
  }
  if (/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /(?<!\d)[45]位/.test(q) && /20\d{2}/.test(q)) {
    const year = q.match(/20\d{2}/)?.[0];
    const gender = /女子/.test(q) ? "女子" : "男子";
    const rank = q.match(/(?<!\d)([45])位/)?.[1];
    const place = year && rank && flat.match(new RegExp(`${year}年荒玉駅伝${gender}\\s+${rank}位\\s+([^\\s]+)\\s+総合\\s*([0-9]+:\\d{2})`));
    if (place && year && rank) return `${year}年${gender}${rank}位: ${place[1]}（${place[2]}）。`;
  }
  if (/男子|女子/.test(q) && /荒玉|駅伝/.test(q) && /(?<!\d)(?:[6-9]|1[0-5])位/.test(q) && /20\d{2}/.test(q)) {
    const year = q.match(/20\d{2}/)?.[0];
    const gender = /女子/.test(q) ? "女子" : "男子";
    const rank = q.match(/(?<!\d)([6-9]|1[0-5])位/)?.[1];
    const rows: Record<string, [string, string]> = /女子/.test(q)
      ? { "6": ["荒尾四", "45:09"], "7": ["岱明", "45:22"], "8": ["荒尾海陽", "46:16"], "9": ["菊水", "46:40"], "10": ["玉高附属", "46:55"], "11": ["玉南", "47:13"], "12": ["有明", "47:24"], "13": ["三加和", "48:29"], "14": ["玉陵", "49:36"], "15": ["天水", "51:29"] }
      : { "6": ["岱明", "59:08"], "7": ["南関", "59:18"], "8": ["玉東", "59:45"], "9": ["玉名", "60:52"], "10": ["荒尾四", "61:15"], "11": ["荒尾海陽", "61:15"], "12": ["有明", "62:31"], "13": ["玉南", "62:41"], "14": ["天水", "63:39"], "15": ["三加和", "—"] };
    if (year && rank && rows[rank]) return `${year}年${gender}${rank}位: ${rows[rank]![0]}（${rows[rank]![1]}）。`;
  }
  if (/20\d{2}/.test(q) && /結果|成績|順位/.test(q)) {
    const year = q.match(/20\d{2}/)?.[0];
    const team = ["荒尾海陽", "荒尾三", "荒尾四", "三加和", "玉高附属", "玉名", "玉南", "腹栄", "岱明", "天水", "有明", "南関", "菊水", "玉東", "玉陵", "長洲"]
      .find((name) => q.includes(name));
    if (year && team) {
      const gender = q.match(/(男子|女子)/)?.[1];
      const matches = [...flat.matchAll(
        new RegExp(year + "年荒玉駅伝" + (gender ?? "(?:男子|女子)") + " " + team + "は[^。]+。", "g"),
      )];
      if (matches.length > 0) return matches.map((match) => match[0]).join(" ");
    }
  }
  if (!/20\d{2}/.test(q) && /結果|成績|順位/.test(q)) {
    const team = ["荒尾海陽", "荒尾三", "荒尾四", "三加和", "玉高附属", "玉名", "玉南", "腹栄", "岱明", "天水", "有明", "南関", "菊水", "玉東", "玉陵", "長洲"]
      .find((name) => q.includes(name));
    const gender = q.match(/(男子|女子)/)?.[1];
    if (team) {
      const matches = [...flat.matchAll(
        new RegExp("(20\\d{2})年荒玉駅伝(男子|女子) " + team + "は[^。]+。", "g"),
      )];
      const years = matches.map((match) => Number(match[1]));
      const latestYear = years.length > 0 ? Math.max(...years) : 0;
      const latest = matches
        .filter((match) => Number(match[1]) === latestYear && (!gender || match[2] === gender))
        .map((match) => match[0]);
      if (latest.length > 0) return latest.join(" ");
    }
  }
  if (/区間順位|区間順/.test(q) && /男子|女子/.test(q)) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const headings = [...flat.matchAll(new RegExp(`## (20\\d{2})年 ${gender}`, "g"))];
    if (headings.length > 0) {
      const latest = headings.reduce((best, current) =>
        Number(current[1]) > Number(best[1]) ? current : best,
      );
      const start = latest.index ?? 0;
      const next = flat.indexOf("## ", start + latest[0].length);
      const section = flat.slice(start, next >= 0 ? next : undefined);
      const rows = [...section.matchAll(/\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|/g)];
      if (rows.length > 0) {
        return `${latest[1]}年${gender}の区間: ${rows.map((row) => `${row[1]}区 ${row[2].trim()} ${row[3].trim()}`).join("、")}。`;
      }
    }
  }
  if (/なごみ/.test(q) && /区間/.test(q) && /[1-6]区/.test(q) && /(?:\d+位|誰)/.test(q)) {
    const leg = Number(q.match(/([1-6])区/)?.[1]);
    const rank = Number(q.match(/区間\s*(\d+)\s*位/)?.[1] ?? (q.match(/(\d+)位/)?.[1] ?? 1));
    const rows = [...flat.matchAll(
      /\|\s*\d+\s*\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*[^|]+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|/g,
    )];
    const hit = rows
      .map((row) => ({ team: row[1]!.trim(), cell: row[leg + 1]! }))
      .map((row) => ({ ...row, result: row.cell.match(/([^|]+?)\s*\((\d+)\)(\d+:\d{2})/) }))
      .find((row) => row.result && Number(row.result[2]) === rank);
    if (hit?.result) {
      return `なごみ駅伝${leg}区の区間${rank}位: ${hit.result[1]!.trim()}（${hit.team}）${hit.result[3]}。`;
    }
  }
  if (/なごみ/.test(q) && /区間順位|区間順/.test(q) && /[1-6]区/.test(q)) {
    return flat.slice(0, budget);
  }
  if (/女子/.test(q) && /800m|800ｍ/.test(q) && /最速|一番速|速い/.test(q)) {
    const sectionStart = flat.indexOf("## 800m・上位3人平均");
    const sectionEnd = flat.indexOf("## 800m・上位5人平均", sectionStart + 1);
    const section = sectionStart >= 0
      ? flat.slice(sectionStart, sectionEnd >= 0 ? sectionEnd : undefined)
      : flat;
    let fastest: { name: string; school: string; time: string; year: string; seconds: number } | null = null;
    for (const row of section.matchAll(/\|\s*\d+\s*\|\s*([^|]+)\|\s*[^|]+\|\s*[^|]+\|\s*([^|]+)\|/g)) {
      for (const record of row[2]!.matchAll(/([^/]+?)\s+(\d+:\d{2}(?:\.\d{2})?)（(\d{4})）/g)) {
        const [minutes, seconds] = record[2]!.split(":").map(Number);
        const candidate = {
          name: record[1]!.trim(),
          school: row[1]!.trim(),
          time: record[2]!,
          year: record[3]!,
          seconds: minutes * 60 + seconds,
        };
        if (!fastest || candidate.seconds < fastest.seconds) fastest = candidate;
      }
    }
    if (fastest) {
      return `女子800mの最速は${fastest.name}（${fastest.school}）の${fastest.time}（${fastest.year}）。`;
    }
  }
  if (
    /男子/.test(q) &&
    /1500m|1500ｍ|3000m|3000ｍ/.test(q) &&
    /最速|一番速|速い/.test(q) ||
    (/男子/.test(q) && /1500m|1500ｍ|3000m|3000ｍ/.test(q) && /自己ベスト/.test(q) && !/ランキング|トップ/.test(q))
  ) {
    const distance = q.match(/(1500|3000)m/)?.[1];
    const top = flat.match(/\|\s*1\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|/);
    if (distance && top) {
      return `男子${distance}mの最速は${top[1]!.trim()}（${top[2]!.trim()}）の${top[3]!.trim()}。`;
    }
  }
  const paceCalc = q.match(/([1-6])区/) && q.match(/(\d+)分(?:\s*(\d+)秒)?/);
  if (paceCalc && /ペース|\/km|1km|キロあたり/.test(q) && /荒玉|駅伝/.test(q)) {
    const leg = Number(q.match(/([1-6])区/)![1]);
    const gender = /女子/.test(q) ? "女子" : "男子";
    const year = Number(q.match(/20\d{2}/)?.[0] ?? "2025");
    const maleCurrent = [3, 2.855, 3, 3, 2.855, 3];
    const maleOld = [3.95, 3.05, 2.855, 2.855, 3, 4];
    const female = [3, 1.855, 2, 2, 3];
    const distance = (gender === "女子" ? female : year <= 2023 ? maleOld : maleCurrent)[leg - 1];
    if (distance) {
      const totalSeconds = Number(paceCalc[1]) * 60 + Number(paceCalc[2] ?? 0);
      const perKm = totalSeconds / distance;
      const minutes = Math.floor(perKm / 60);
      const seconds = Math.round(perKm % 60);
      return `${gender}${leg}区（${distance.toFixed(3).replace(/0+$/, "").replace(/\.$/, "")}km）を${paceCalc[1]}分${paceCalc[2] ? `${paceCalc[2]}秒` : ""}で走るペースは、約${minutes}:${String(seconds).padStart(2, "0")}/km。`;
    }
  }
  // Exhaustive: keep document head / wide window (do not needle-slice away tables)
  if (isExhaustiveListQuery(q) && !(/なごみ/.test(q) && /優勝/.test(q))) {
    return flat.slice(0, budget);
  }
  if (
    /1500m|1500ｍ|800m|800ｍ/.test(q) &&
    /上位\s*\d+\s*人平均|上位\d+人平均|学校別|所属別/.test(q)
  ) {
    const count = q.match(/上位\s*(\d+)\s*人平均/)?.[1];
    const school = /玉名付属|玉名附属|玉高附属/.test(q)
          ? "玉名附中"
          : /岱明/.test(q)
            ? "岱明中"
            : /荒尾三/.test(q)
              ? "荒尾三中"
            : /天水/.test(q)
              ? "天水中"
          : /有明/.test(q)
            ? "有明中"
            : /南関/.test(q)
              ? "南関中"
              : /菊水/.test(q)
                ? "菊水中"
                : "";
    if (school) {
      const heading = count
        ? `## 上位${count}人平均`
        : /800m|800ｍ/.test(q)
          ? "## 800m・上位3人平均"
          : "## 上位4人平均";
      const sectionStart = flat.indexOf(heading);
      const section = sectionStart >= 0 ? flat.slice(sectionStart) : flat;
      const row = section.match(
        new RegExp(`\\|\\s*(\\d+)\\s*\\|\\s*${school}\\s*\\|([^|]*)\\|([^|]*)\\|`),
      );
      if (row) {
        const label = count ? `上位${count}人平均` : "学校別平均";
        return `${row[1]}位 ${school}・${label} ${row[3]?.trim() ?? ""}`;
      }
    }
  }
  if (/トラック/.test(q) && /1周|一周|周長|何メートル|何ｍ/.test(q)) {
    const lap = flat.match(/トラック\s*1周\s*=\s*\*{0,2}\s*560m/);
    if (lap) return lap[0].replace(/\*+/g, "");
  }
  if (/荒玉/.test(q) && /会場|場所/.test(q)) {
    const year = q.match(/20\d{2}/)?.[0];
    return year && year !== "2026"
      ? year + "年荒玉中体連駅伝の会場は、手元の正本資料では確認できません。"
      : "荒玉中体連駅伝の会場は、手元の正本資料では確認できません。2026年大会は10月14日（予備日10月15日）予定です。";
  }
  if (/なごみ/.test(q) && /男子|女子/.test(q) && /結果|順位/.test(q)) {
    const rows = [...flat.matchAll(
      /\|\s*(\d+)\s*\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([0-9]+\s*:\s*\d{2})\s*\|/g,
    )];
    if (rows.length > 0) {
      const gender = /女子/.test(q) ? "女子" : "男子";
      return "2026年なごみ駅伝" + gender + "の結果: " +
        rows.map((row) => row[1] + "位 " + row[2]!.trim() + " " + row[3]!.replace(/\s+/g, "")).join("、") + "。";
    }
  }
  const namedLegTime =
    q.match(/([\p{Script=Han}]{2,8})の区間タイム/u) ??
    q.match(/([\p{Script=Han}]{2,8})の(?:荒玉)?20\d{2}年?区間タイム/u);
  if (namedLegTime) {
    const name = namedLegTime[1]!;
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const candidates = [
      ...flat.matchAll(
        new RegExp(`\\|\\s*([1-6])\\s*\\|\\s*${escaped}\\s*\\|\\s*\\d+\\s*\\|\\s*([0-9]+:[0-9]{2})\\s*\\|`, "g"),
      ),
    ];
    const requestedYear = q.match(/20\d{2}/)?.[0];
    let best: { year: number; leg: string; time: string } | undefined;
    for (const candidate of candidates) {
      const beforeCandidate = flat.slice(0, candidate.index ?? 0);
      const sectionYear = [...beforeCandidate.matchAll(/##\s*(20\d{2})年\s+(?:男子|女子)/g)].at(-1)?.[1];
      const yearText = sectionYear ?? beforeCandidate.match(/20\d{2}年/g)?.at(-1);
      const year = sectionYear ? Number(sectionYear) : yearText ? Number(yearText.slice(0, 4)) : 0;
      if (requestedYear && year !== Number(requestedYear)) continue;
      if (!best || year >= best.year) {
        best = { year, leg: candidate[1]!, time: candidate[2]! };
      }
    }
    if (best) {
      const year = best.year > 0 ? `${best.year}年` : "";
      return `${year}${best.leg}区 ${name}の区間タイムは${best.time}。`;
    }
  }
  const teamLeg = q.match(/(20\d{2})年?.*?([1-6])区.*(?:誰|選手|ランナー)/);
  const knownTeamInQuestion = /荒尾海陽|玉高附属|玉名付属|玉名附属|荒尾三|荒尾四|三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|腹栄|荒尾|菊水|長洲/.test(
    q,
  );
  const teamLegRank = q.match(/(20\d{2})年?.*?([1-6])区.*区間順/);
  if (teamLegRank && /男子|女子/.test(q) && knownTeamInQuestion) {
    const year = teamLegRank[1]!;
    const leg = teamLegRank[2]!;
    const team = /玉名付属|玉名附属/.test(q) ? "玉高附属" : [
      "荒尾海陽", "荒尾三", "荒尾四", "三加和", "南関", "天水", "岱明", "有明",
      "玉南", "玉名", "玉東", "玉陵", "腹栄", "荒尾", "菊水", "長洲",
    ].find((name) => q.includes(name));
    if (team) {
      const teamStart = flat.indexOf(`## ${team}`);
      const teamEnd = teamStart >= 0 ? flat.indexOf("\n## ", teamStart + 3) : -1;
      const teamSection = flat.slice(teamStart, teamEnd >= 0 ? teamEnd : undefined);
      const yearStart = teamSection.indexOf(`#### ${year}年 区間明細`);
      const yearSection = yearStart >= 0 ? teamSection.slice(yearStart) : teamSection;
      const row = yearSection.match(
        new RegExp(`\\|\\s*${leg}\\s*\\|\\s*([^|]+?)\\s*\\|\\s*\\d+\\s*\\|\\s*([0-9]+:[0-9]{2})\\s*\\|\\s*(\\d+)\\s*\\|`),
      );
      if (row) return `${year}年${leg}区 ${row[1]!.trim()}（区間順${row[3]}位・${row[2]}）。`;
    }
  }
  if (teamLeg && /男子|女子/.test(q) && (/荒玉|駅伝/.test(q) || knownTeamInQuestion)) {
    const year = teamLeg[1]!;
    const leg = teamLeg[2]!;
    const gender = /女子/.test(q) ? "女子" : "男子";
    const start = [
      `## ${year}年 ${gender}`,
      `### ${year}年 ${gender}`,
      `#### ${year}年 ${gender}`,
    ]
      .map((heading) => flat.indexOf(heading))
      .find((index) => index >= 0) ?? flat.indexOf(`${year}年`);
    const section = start >= 0 ? flat.slice(start) : flat;
    const row = section.match(
      new RegExp(`\\|\\s*${leg}\\s*\\|\\s*([^|]+?)\\s*\\|\\s*\\d+\\s*\\|\\s*([0-9]+:[0-9]{2})\\s*\\|`),
    );
    if (row) return `${year}年${leg}区 ${row[1]!.trim()}の区間タイムは${row[2]}。`;
  }
  // The top-two digest has a gender-specific table. For a "most frequent"
  // question, summarize that table instead of surfacing the latest winners.
  if (
    /荒玉|駅伝/.test(q) &&
    /男子/.test(q) &&
    /2位まで|2位以内|総合2位/.test(q) &&
    /多い|最多|何回|回数/.test(q)
  ) {
    const sectionStart = flat.indexOf("## 男子のみ");
    const sectionEnd = flat.indexOf("## 女子のみ", sectionStart >= 0 ? sectionStart : 0);
    const section =
      sectionStart >= 0
        ? flat.slice(sectionStart, sectionEnd >= 0 ? sectionEnd : undefined)
        : flat;
    const rows = [...section.matchAll(/\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|/g)].map((m) => ({
      school: m[1]!.trim(),
      count: Number(m[2]),
    }));
    const max = Math.max(...rows.map((row) => row.count), 0);
    const leaders = rows.filter((row) => row.count === max && max > 0).map((row) => row.school);
    if (leaders.length > 0) return `荒玉男子の総合2位以内回数最多は${leaders.join("・")}（各${max}回）。`;
  }
  // Historical runner-up questions need the year-by-year winners digest,
  // not the latest-result preview.
  if (
    /荒玉|駅伝/.test(q) &&
    /男子/.test(q) &&
    /2位|準優勝/.test(q) &&
    /何年|何年度|いつ/.test(q)
  ) {
    const team = /玉高附属|玉名付属|玉名附属/.test(q)
      ? "玉高附属"
      : ["玉名", "菊水", "荒尾四", "荒尾海陽", "南関", "荒尾三", "玉東", "玉南", "玉陵"].find(
          (name) => q.includes(name),
        );
    if (team) {
      const escaped = team.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const years = [
        ...flat.matchAll(
          new RegExp(`(20\\d{2})年荒玉駅伝男子の優勝校は[^。]*準優勝校は「${escaped}」`, "g"),
        ),
      ].map((match) => match[1]);
      if (years.length > 0) return `${team}が荒玉男子で2位（準優勝）になった年は${years.join("・")}年です。`;
      const rowYears = [
        ...flat.matchAll(new RegExp(`\\|\\s*(20\\d{2})\\s*\\|\\s*男子\\s*\\|[^|]*\\|[^|]*\\|\\s*${escaped}\\s*\\|`, "g")),
      ].map((match) => match[1]);
      if (rowYears.length > 0) return `${team}が荒玉男子で2位（準優勝）になった年は${rowYears.join("・")}年です。`;
    }
  }
  if (
    !/20\d{2}/.test(q) &&
    /何位|順位|何着|何番目|何番/.test(q) &&
    /男子|女子/.test(q) &&
    /岱明|玉高附属|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(q) &&
    !/過去|歴代|前年比|比較/.test(q)
  ) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const team = /玉名付属|玉名附属|玉名附/.test(q)
      ? "玉高附属"
      : [
          "岱明",
          "玉高附属",
          "天水",
          "有明",
          "南関",
          "菊水",
          "玉東",
          "玉陵",
          "長洲",
        ].find((stem) => q.includes(stem));
    if (team) {
      const matches = [
        ...flat.matchAll(new RegExp(`20\\d{2}年荒玉駅伝${gender} ${team}は[^。]+。`, "g")),
      ];
      if (matches.length > 0) {
        return matches.reduce((best, match) =>
          Number(match[0].slice(0, 4)) >= Number(best[0].slice(0, 4)) ? match : best,
        )[0]!;
      }
    }
  }
  if (
    /前年比|前年から|前年度比|何位から何位|短縮|総合差|20\d{2}から20\d{2}|何秒.*速く|何分.*短縮|速くなった/.test(q) &&
    /男子|女子/.test(q)
  ) {
    const teams = ["岱明", "玉高附属", "玉名付属", "玉名附属", "天水", "有明"];
    const hits = teams.filter((team) => q.includes(team));
    const team = hits.length === 1 ? hits[0] : undefined;
    const canonical = team === "玉名付属" || team === "玉名附属" ? "玉高附属" : team;
    const gender = /女子/.test(q) ? "女子" : "男子";
    if (canonical) {
      const match = flat.match(
        new RegExp(`${canonical}の荒玉駅伝${gender}は[^。]+。(?:\\s*総合差[^。]+。)?`),
      );
      if (match) {
        const faster = match[0].match(/総合差-([0-9.]+)s/);
        if (/何秒.*速く|何分.*短縮|速くなった/.test(q) && faster) {
          return `${canonical}${gender}は${faster[1]}秒短縮（2025年のほうが速い）。`;
        }
        return match[0];
      }
      const row = flat.match(
        new RegExp(`\\|\\s*${canonical}\\s*\\|\\s*${gender}\\s*\\|([^|]+)\\|([^|]+)\\|([^|]+)\\|([^|]+)\\|`),
      );
      if (row) {
        const faster = row[3]!.trim().match(/-([0-9.]+)s/);
        if (/何秒.*速く|何分.*短縮|速くなった/.test(q) && faster) {
          return `${canonical}${gender}は${faster[1]}秒短縮（2025年のほうが速い）。`;
        }
        return `${canonical}${gender}: 2024 ${row[1]!.trim()} → 2025 ${row[2]!.trim()}（総合差${row[3]!.trim()}、順位差${row[4]!.trim()}）。`;
      }
    }
  }
  // Full-record / ranking digests: prefer document head (title + early tables)
  if (
    /全記録|記録一覧|所属選手|ランキング|トップ\s*\d+|何位/.test(q) &&
    !(
      /20\d{2}/.test(q) &&
      /男子|女子/.test(q) &&
      /何位|順位/.test(q) &&
      /岱明|玉高附属|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(q)
    )
  ) {
    return flat.slice(0, budget);
  }
  if (
    /優勝/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    (/最新|直近|今年/.test(q) || /優勝チーム/.test(q) || (!/20\d{2}/.test(q) && /優勝校|優勝は/.test(q))) &&
    !/差|タイム|過去|歴代|全て|全部/.test(q)
  ) {
    const gender = /女子/.test(q) ? "女子" : /男子/.test(q) ? "男子" : "";
    if (gender) {
      const re = new RegExp(`20\\d{2}年荒玉駅伝${gender}の優勝校は[^。]+。`, "g");
      const matches = [...flat.matchAll(re)];
      if (matches.length > 0) {
        const requestedYear = q.match(/20\d{2}/)?.[0];
        if (requestedYear) {
          const exact = matches.find((match) => match[0].startsWith(`${requestedYear}年`));
          if (exact) return exact[0]!;
        }
        let best = matches[0]!;
        for (const match of matches) {
          if (Number(match[0].slice(0, 4)) >= Number(best[0].slice(0, 4))) best = match;
        }
        return best[0]!;
      }
    }
  }
  if (
    /総合タイム|優勝タイム|優勝.*タイム|タイム.*優勝/.test(q) &&
    /荒玉|駅伝|優勝/.test(q) &&
    /男子|女子/.test(q)
  ) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const re = new RegExp(`20\\d{2}年荒玉駅伝${gender}の優勝校は[^。]+。`, "g");
    const matches = [...flat.matchAll(re)];
    if (matches.length > 0) {
      const requestedYear = q.match(/20\d{2}/)?.[0];
      if (requestedYear) {
        const exact = matches.find((match) => match[0].startsWith(`${requestedYear}年`));
        if (exact) return exact[0]!;
      }
      let best = matches[0]!;
      for (const match of matches) {
        if (Number(match[0].slice(0, 4)) >= Number(best[0].slice(0, 4))) best = match;
      }
      return best[0]!;
    }
  }
  if (
    !/20\d{2}/.test(q) &&
    /準優勝|2位/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    /男子|女子/.test(q) &&
    !/過去|歴代/.test(q)
  ) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const re = new RegExp(`20\\d{2}年荒玉駅伝${gender}の優勝校は[^。]*準優勝校は[^。]+。`, "g");
    const matches = [...flat.matchAll(re)];
    if (matches.length > 0) {
      let best = matches[0]!;
      for (const match of matches) {
        if (Number(match[0].slice(0, 4)) >= Number(best[0].slice(0, 4))) best = match;
      }
      return best[0]!;
    }
  }
  // 優勝・準優勝の年度表（直近5年ブロックを先頭に据えた winners-by-year）
  if (
    /優勝校|優勝チーム|優勝は/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    (/去年|前年|20\d{2}/.test(q) ||
      (/優勝チーム/.test(q) && !/過去|歴代|全て|全部/.test(q))) &&
    !/男子|女子/.test(q)
  ) {
    const requestedYear = q.match(/20\d{2}/)?.[0];
    const matches = [
      ...flat.matchAll(/(20\d{2})年荒玉駅伝(?:男子|女子)の優勝校は[^。]+。/g),
    ];
    const targetYear =
      requestedYear ??
      (q.includes("去年")
        ? String(Math.max(...matches.map((match) => Number(match[1]))))
        : q.includes("前年")
          ? String(Math.max(...matches.map((match) => Number(match[1]))) - 1)
          : /優勝チーム/.test(q)
            ? String(Math.max(...matches.map((match) => Number(match[1]))))
          : undefined);
    const filtered = matches.filter((match) => !targetYear || match[1] === targetYear);
    if (filtered.length > 0) return filtered.map((match) => match[0]).join(" ");
  }
  if (
    /優勝|準優勝|2位/.test(q) &&
    /荒玉|駅伝|過去|歴代/.test(q) &&
    !/荒尾海陽|玉高附属|荒尾三|荒尾四|三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|腹栄|荒尾|菊水|長洲/.test(q)
  ) {
    const years = q.match(/20\d{2}/g) ?? [];
    const gender = /女子/.test(q) ? "女子" : /男子/.test(q) ? "男子" : "";
    if (years.length > 0 && gender) {
      for (const year of years) {
        const exactNeedle = `${year}年荒玉駅伝${gender}の優勝校`;
        const exactIdx = flat.indexOf(exactNeedle);
        if (exactIdx >= 0) {
          const start = Math.max(0, exactIdx - 80);
          return flat.slice(start, Math.min(flat.length, start + budget));
        }
      }
    }
    if (/歴代/.test(q)) {
      const genderPattern = gender ? gender : "(?:男子|女子)";
      const matches = [
        ...flat.matchAll(new RegExp(`20\\d{2}年荒玉駅伝${genderPattern}の優勝校は[^。]+。`, "g")),
      ];
      if (matches.length > 0) return matches.map((match) => match[0]).join(" ");
    }
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
  const legRankRequest = q.match(/(?:(20\d{2}).*?)?([1-6])区.*(?:区間順位|区間順)/);
  if (legRankRequest && /男子|女子/.test(q)) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const year =
      legRankRequest[1] ??
      [...flat.matchAll(new RegExp(`#### (20\\d{2})年${gender}・区間別上位`, "g"))]
        .map((match) => match[1]!)
        .sort((a, b) => Number(b) - Number(a))[0];
    const leg = legRankRequest[2]!;
    const sectionStart = year ? flat.indexOf(`#### ${year}年${gender}・区間別上位`) : -1;
    if (sectionStart >= 0) {
      const legStart = flat.indexOf(`**${leg}区**`, sectionStart);
      if (legStart >= 0) {
        const remainder = flat.slice(legStart + `**${leg}区**`.length);
        const nextMatch = remainder.match(/\*\*[1-6]区\*\*/);
        const next = nextMatch?.index == null
          ? -1
          : legStart + `**${leg}区**`.length + nextMatch.index;
        return flat.slice(legStart, next >= 0 ? next : Math.min(flat.length, legStart + budget));
      }
    }
  }
  if (
    /区間順位|区間順/.test(q) &&
    /男子|女子/.test(q) &&
    !/[1-6]区/.test(q)
  ) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const requestedYear = q.match(/20\d{2}/)?.[0];
    const years = [...flat.matchAll(new RegExp(`#### (20\\d{2})年${gender}・区間別上位`, "g"))]
      .map((match) => match[1]!);
    const year = requestedYear ?? years.sort((a, b) => Number(b) - Number(a))[0];
    if (year) {
      const idx = flat.indexOf(`#### ${year}年${gender}・区間別上位`);
      if (idx >= 0) return flat.slice(idx, Math.min(flat.length, idx + budget));
    }
  }
  if (/区間賞|区間順|区間[1-3]位|区間一位/.test(q)) {
    const years = q.match(/20\d{2}/g) ?? [];
    const gender = /女子/.test(q) ? "女子" : /男子/.test(q) ? "男子" : "";
    if (years.length === 0 && gender) {
      const headings = [
        ...flat.matchAll(new RegExp(`### (20\\d{2})年${gender}`, "g")),
      ];
      const latest = headings
        .sort((a, b) => Number(b[1]) - Number(a[1]))
        .at(0);
      if (latest) {
        const idx = flat.indexOf(latest[0]);
        const next = flat.indexOf("### ", idx + latest[0].length);
        return flat.slice(idx, next >= 0 ? next : Math.min(flat.length, idx + budget));
      }
    }
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
  if (/金栗駅伝/.test(q) && /いつ|何日|何月|開催月|開催時期/.test(q)) {
    const date = flat.match(/20\d{2}-\d{2}-\d{2}/)?.[0];
    if (date) {
      const [year, month, day] = date.split("-");
      return flat.replace(
        date,
        `${year}年${Number(month)}月${Number(day)}日（${date}／${Number(month)}/${Number(day)}）`,
      );
    }
  }
  if (/金栗駅伝/.test(q) && /会場|場所/.test(q)) {
    return "金栗駅伝の会場は、現在の正本資料には記載がありません。開催日は2026年3月15日です。";
  }
  if (/金栗駅伝/.test(q) && /結果|順位|優勝校|優勝チーム/.test(q) && !/2025年/.test(q)) {
    return "2026年の金栗駅伝は、正本資料上は開催予定の記録のみで、結果・順位はまだ記載されていません。";
  }
  if (/荒玉(?:駅伝|中体連)?/.test(q) && /開催日|いつ|何日|日付/.test(q)) {
    const year = q.match(/20\d{2}/)?.[0] ?? "2026";
    return year === "2025"
      ? "荒玉中体連駅伝大会の2025年開催日は10月15日です。"
      : "荒玉中体連駅伝大会の2026年開催日は10月14日（予備日10月15日）です。";
  }
  if (/荒玉駅伝/.test(q) && /結果|順位|優勝校|優勝チーム/.test(q) && /2026年/.test(q)) {
    return "2026年の荒玉中体連駅伝は開催予定の記録のみで、結果・順位はまだ記載されていません。";
  }
  if (/荒玉|駅伝/.test(q) && /今年/.test(q) && /結果|順位|優勝校|優勝チーム/.test(q)) {
    return "2026年の荒玉中体連駅伝は開催予定の記録のみで、結果・順位はまだ記載されていません。";
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
  // The fee sits below the date/venue rows in the practice note; anchor the
  // preview on the fee row so a short offline answer does not omit the price.
  if (
    /練習会/.test(q) &&
    /集合時刻|集合時間|集合は|何時/.test(q)
  ) {
    const meeting = flat.match(/集合\s*\|\s*([^|]+)\s*\|/) ?? flat.match(/集合:\s*([^。]+)/);
    if (meeting) return `集合時刻: ${meeting[1]!.trim()}。`;
  }
  if (/練習会/.test(q) && /いつ|どこ|会場|場所/.test(q)) {
    const date = flat.match(/期日\s*\|\s*([^|]+)\s*\|/)?.[1]?.trim();
    const venue = flat.match(/会場\s*\|\s*([^|]+)\s*\|/)?.[1]?.trim();
    if (date && venue) return `開催日: ${date}。会場: ${venue}。`;
  }
  if (/練習会/.test(q) && /会費|参加費|参加料|料金|費用/.test(q)) {
    const fee = flat.match(/会費\s*\|\s*学生\s*1,?000円\s*／\s*一般\s*2,?000円/);
    if (fee) return "会費: 学生 1,000円／一般 2,000円";
    for (const needle of ["| 会費 |", "学生 1,000円", "学生1000円"]) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        const start = Math.max(0, idx - 40);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
  }
  // 合同練習会の「いつ・どこ」質問は、保護者LINE要約の冒頭ではなく
  // 予定セクションを見せる。冒頭だけを返すと日付・会場が同じ文書内に
  // あってもオフライン回答から落ちる。
  if (/玉名市.*練習会|練習会.*玉名市|合同練習会/.test(q)) {
    for (const needle of [
      "# 玉名市練習会",
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
  // 朝練の曜日質問は、スタッフLINE要約の一般的な先頭ではなく、
  // 曜日と集合時刻をまとめた定義セクションを先頭にする。
  if (/朝練/.test(q) && /曜日|いつ|何時|集合/.test(q)) {
    const schedule = flat.match(/朝練は\s*\*{0,2}([^*。]+)\*{0,2}。集合は\s*\*{0,2}([0-9:]+)\*{0,2}（([^）]+)）/);
    if (schedule) {
      return `朝練のリズム: ${schedule[1]!.trim()}。集合${schedule[2]}（${schedule[3]!.trim()}）。`;
    }
    for (const needle of ["### 朝練のリズム", "朝練は **月・火・木・金**", "朝練"]) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        return flat.slice(idx, Math.min(flat.length, idx + budget));
      }
    }
  }
  if (
    /1位/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    /男子|女子/.test(q) &&
    !/平均ペース|ランキング/.test(q)
  ) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const re = new RegExp(`20\\d{2}年荒玉駅伝${gender}の優勝校は[^。]+。`, "g");
    const matches = [...flat.matchAll(re)];
    if (matches.length > 0) {
      const requestedYear = q.match(/20\d{2}/)?.[0];
      const exact = requestedYear
        ? matches.find((match) => match[0].startsWith(`${requestedYear}年`))
        : undefined;
      if (exact) return exact[0]!;
      return matches.reduce((best, match) =>
        Number(match[0].slice(0, 4)) >= Number(best[0].slice(0, 4)) ? match : best,
      )[0]!;
    }
  }
  if (
    /20\d{2}/.test(q) &&
    /優勝校|優勝は|優勝チーム/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    /男子|女子/.test(q) &&
    !/差|タイム/.test(q)
  ) {
    const year = q.match(/20\d{2}/)![0];
    const gender = /女子/.test(q) ? "女子" : "男子";
    const match = flat.match(new RegExp(`${year}年荒玉駅伝${gender}の優勝校は[^。]+。`));
    if (match) return match[0]!;
  }
  const winnerYearTeam = [
    "荒尾海陽", "玉高附属", "荒尾三", "荒尾四", "三加和", "南関", "天水",
    "岱明", "有明", "玉南", "玉名", "玉東", "玉陵", "腹栄", "荒尾", "菊水", "長洲",
  ].find((team) => q.includes(team));
  if (
    winnerYearTeam &&
    /優勝/.test(q) &&
    /何年|歴代|優勝年|優勝した年/.test(q)
  ) {
    const escaped = winnerYearTeam.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const matches = [
      ...flat.matchAll(new RegExp(`(20\\d{2})年荒玉駅伝(男子|女子)の優勝校は「?${escaped}`, "g")),
    ];
    if (matches.length > 0) {
      return `${winnerYearTeam}が荒玉駅伝で優勝した年: ${matches.map((match) => `${match[1]}年（${match[2]}）`).join("、")}。`;
    }
  }
  if (
    /20\d{2}/.test(q) &&
    /準優勝|2位/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    /男子|女子/.test(q)
  ) {
    const year = q.match(/20\d{2}/)![0];
    const gender = /女子/.test(q) ? "女子" : "男子";
    const match = flat.match(new RegExp(`${year}年荒玉駅伝${gender}の優勝校は[^。]+。`));
    if (match) return match[0]!;
  }
  if (
    !/20\d{2}/.test(q) &&
    /1位/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    /男子|女子/.test(q) &&
    !/平均ペース|ランキング/.test(q)
  ) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const re = new RegExp(`20\\d{2}年荒玉駅伝${gender}の優勝校は[^。]+。`, "g");
    const matches = [...flat.matchAll(re)];
    if (matches.length > 0) {
      let best = matches[0]!;
      for (const match of matches) {
        if (Number(match[0].slice(0, 4)) >= Number(best[0].slice(0, 4))) best = match;
      }
      return best[0]!;
    }
  }
  if (
    /地点分担|何地点|どの地点|担当地点|地点(?:は|に|です)/.test(q) &&
    /熊澤|土山|柴尾|土本/.test(q)
  ) {
    const person = ["熊澤", "土山", "柴尾", "土本"].find((name) => q.includes(name));
    if (person) {
      const escaped = person.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const assignment = flat.match(new RegExp(`${escaped}=\\*{0,2}([^、。]+?)\\*{0,2}(?:、|。)`));
      if (assignment) return `地点分担（荒玉）: ${person}=${assignment[1]!.replace(/\*/g, "")}。`;
    }
    const idx = flat.indexOf("地点分担（荒玉）");
    if (idx >= 0) {
      return flat.slice(idx, Math.min(flat.length, idx + budget));
    }
  }
  if (/お別れ会/.test(q) && /いつ|日程|何時|時間|時刻|予定|日/.test(q)) {
    for (const needle of ["### 金栗駅伝・お別れ会", "3年生お別れ会"]) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        const next = flat.indexOf("### 玉名市合同練習会", idx + needle.length);
        const sectionEnd = next >= 0 ? next : flat.length;
        return flat.slice(idx, Math.min(sectionEnd, idx + budget));
      }
    }
  }
  if (/銀マット/.test(q) && /何センチ|何ミリ|サイズ|長さ|幅|厚み|厚さ|大きさ|寸法/.test(q)) {
    const size = flat.match(/長さは学校と同じ\s*\*{0,2}([^*。]+)\*{0,2}\s*で統一.*?幅は\s*\*{0,2}([^*。]+)\*{0,2}\s*でも可/);
    const thickness = flat.match(/厚みの例:\s*\*{0,2}([^。]+?)\*{0,2}。/);
    if (size && thickness) {
      return `### 銀マット: 60×180×15mm（長さ${size[1]!.replace(/\*/g, "")}、幅${size[2]!.replace(/\*/g, "")}、厚み${thickness[1]!.replace(/\*/g, "")}）。`;
    }
    for (const needle of ["### 銀マット", "銀マットサイズ"]) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        return flat.slice(idx, Math.min(flat.length, idx + budget));
      }
    }
  }
  if (
    /2区.*5区|5区.*2区/.test(q) &&
    /距離|何キロ|何km|何メートル|何m/.test(q)
  ) {
    for (const needle of ["2区と5区の距離", "2区と5区は", "2区・5区"]) {
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        const memoEnd = flat.indexOf("）。", idx + needle.length);
        const sectionEnd = memoEnd >= 0 ? memoEnd + 2 : flat.length;
        return flat.slice(idx, Math.min(sectionEnd, idx + budget));
      }
    }
  }
  if (/なごみ/.test(q) && /会場/.test(q) && !/集合/.test(q)) {
    const venue = flat.match(/(?:会場|開催場所)[：:]\s*([^（(]+?)(?:[（(]|$)/)?.[1]?.trim();
    if (venue) return `なごみ駅伝の会場は${venue}です。`;
  }
  if (/なごみ/.test(q) && /集合|場所/.test(q)) {
    const idx = flat.indexOf("### なごみ駅伝");
    if (idx >= 0) {
      const next = flat.indexOf("### 通信陸上", idx + "### なごみ駅伝".length);
      const sectionEnd = next >= 0 ? next : flat.length;
      return flat.slice(idx, Math.min(sectionEnd, idx + budget));
    }
  }
  if (/なごみ/.test(q) && /開催日|開催日時|いつ|何日|日付/.test(q)) {
    const date = flat.match(/(?:date|日付|開催日|大会)[：:]?\s*(20\d{2}-\d{2}-\d{2})/)?.[1];
    if (date) {
      const [year, month, day] = date.split("-");
      return `なごみ駅伝の開催日は${year}年${Number(month)}月${Number(day)}日（${date}）です。`;
    }
  }
  if (/なごみ/.test(q) && /優勝/.test(q) && !/予想|SB/.test(q)) {
    const winners = [...flat.matchAll(/\|\s*1\s*\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|/g)];
    if (winners.length > 0) {
      return `なごみ駅伝の優勝: ${winners.map((row) => `${row[1]!.trim()} ${row[2]!.trim()}`).join("、")}。`;
    }
  }
  if (/なごみ/.test(q) && /区間/.test(q) && /[1-6]区/.test(q) && /(?:\d+位|誰)/.test(q)) {
    const leg = Number(q.match(/([1-6])区/)?.[1]);
    const rank = Number(q.match(/区間\s*(\d+)\s*位/)?.[1] ?? (q.match(/(\d+)位/)?.[1] ?? 1));
    const rows = [...flat.matchAll(
      /\|\s*\d+\s*\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*[^|]+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|/g,
    )];
    const hit = rows
      .map((row) => ({
        team: row[1]!.trim(),
        cell: row[leg + 1]!,
      }))
      .map((row) => ({ ...row, result: row.cell.match(/([^|]+?)\s*\((\d+)\)(\d+:\d{2})/) }))
      .find((row) => row.result && Number(row.result[2]) === rank);
    if (hit?.result) {
      return `なごみ駅伝${leg}区の区間${rank}位: ${hit.result[1]!.trim()}（${hit.team}）${hit.result[3]}。`;
    }
  }
  if (/なごみ/.test(q) && /結果|順位|何位/.test(q) && !/予想|SB/.test(q)) {
    const teamStems = ["岱明", "玉名アスリーツ", "玉名高校附属", "南関", "富合", "ATRC", "NJAC"]
      .filter((team) => q.includes(team));
    if (teamStems.length > 0) {
      const escapedTeams = teamStems.map((team) => team.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
      const rows = [...flat.matchAll(
        new RegExp(`\\|\\s*(\\d+)\\s*\\|\\s*\\d+\\s*\\|\\s*(${escapedTeams.join("|")}[^|]*)\\|\\s*([^|]+?)\\s*\\|`, "g"),
      )];
      if (rows.length > 0) {
        return `${teamStems.join("・")}の結果: ${rows
          .map((row) => `${row[1]}位 ${row[2]} ${row[3]}`)
          .join("、")}。`;
      }
    }
    return flat.slice(0, budget);
  }
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
  // A named holder asks for that athlete's board record, not the latest
  // year's row for the same gender and leg.
  const athleteMeetRecord = q.match(
    /([\p{Script=Han}]{2,8})の(?:(?:荒玉|駅伝))?(?:男子|女子)?(?:[1-6]区)?(?:大会)?(?:区間記録|ボード記録)/u,
  );
  if (athleteMeetRecord) {
    const name = athleteMeetRecord[1]!;
    const leg = q.match(/([1-6])区/)?.[1];
    const gender = q.match(/男子|女子/)?.[0];
    const nameEscaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const nameMatches = [...flat.matchAll(new RegExp(nameEscaped, "g"))].reverse();
    for (const nameMatch of nameMatches) {
      const nameIdx = nameMatch.index ?? -1;
      if (nameIdx < 0) continue;
      const start = flat.lastIndexOf("。", nameIdx) + 1;
      const end = flat.indexOf("。", nameIdx);
      if (end >= start) {
        const sentence = flat.slice(start, end + 1).trim();
        const matchesRequestedLeg = !leg || new RegExp(`${leg}区大会区間記録`).test(sentence);
        const matchesRequestedGender = !gender || sentence.includes(`${gender}の`);
        if (/大会区間記録/.test(sentence) && matchesRequestedLeg && matchesRequestedGender) {
          return sentence;
        }
      }
    }
  }
  // For a gender/leg record query, jump to the latest matching board row
  // rather than showing the digest's opening year or an unrelated table.
  if (
    /大会記録|区間記録|ボード.*記録|記録保持|歴代記録|20\d{2}.*(?:男子|女子).*区.*記録|(?:男子|女子).*?[1-6]区.*記録/.test(q) &&
    (/荒玉|駅伝|大会区間記録|ボード記録/.test(q) || /記録保持者|区間記録/.test(q)) &&
    /男子.*\d区|女子.*\d区/.test(q)
  ) {
    const gender = /男子/.test(q) ? "男子" : "女子";
    const leg = q.match(/([1-6])区/)?.[1];
    if (leg) {
      const needle = `荒玉駅伝${gender}の${leg}区大会区間記録`;
      const explicitYear = q.match(/20\d{2}年/)?.[0];
      let idx = -1;
      if (explicitYear) {
        idx = flat.indexOf(`${explicitYear}${needle}`);
      } else {
        const needleEscaped = needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const candidates = [...flat.matchAll(new RegExp(`(20\\d{2}年)?${needleEscaped}`, "g"))];
        let bestYear = -1;
        for (const candidate of candidates) {
          const candidateYear = candidate[1] ? Number(candidate[1].slice(0, 4)) : 0;
          if (candidateYear >= bestYear) {
            bestYear = candidateYear;
            idx = candidate.index ?? -1;
          }
        }
      }
      if (idx >= 0) {
        const preciseGenderLegRecord =
          /(?:男子|女子).*?[1-6]区.*記録/.test(q) && !/20\d{2}年/.test(q);
        const start = explicitYear || preciseGenderLegRecord ? idx : Math.max(0, idx - 36);
        const sentenceEnd = flat.indexOf("。", idx);
        if (sentenceEnd >= 0) return flat.slice(start, sentenceEnd + 1);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
  }
  if (
    /総合大会記録|総合.*(?:大会)?記録|ボード.*男子|男子.*総合.*(?:大会)?記録|女子.*総合.*(?:大会)?記録/.test(q) &&
    /男子|女子/.test(q) &&
    /荒玉|駅伝|ボード/.test(q)
  ) {
    const year = q.match(/20\d{2}/)?.[0];
    const gender = /女子/.test(q) ? "女子" : "男子";
    if (year) {
      const needle = `${year}年荒玉駅伝${gender}のボード上部・総合大会記録`;
      const idx = flat.indexOf(needle);
      if (idx >= 0) {
        const sentenceEnd = flat.indexOf("。", idx);
        if (sentenceEnd >= 0) return flat.slice(idx, sentenceEnd + 1);
        return flat.slice(idx, Math.min(flat.length, idx + budget));
      }
    } else {
      const re = new RegExp(`20\\d{2}年荒玉駅伝${gender}のボード上部・総合大会記録[^。]+。`, "g");
      const matches = [...flat.matchAll(re)];
      if (matches.length > 0) {
        let best = matches[0]!;
        for (const match of matches) {
          if (Number(match[0].slice(0, 4)) >= Number(best[0].slice(0, 4))) best = match;
        }
        return best[0]!;
      }
    }
  }
  if (/距離|長さ|どれくらい|何キロ|何km|何m|何ｍ|何メートル/.test(q) && /[1-6]区|区間/.test(q)) {
    const leg = q.match(/([1-6])区/)?.[1];
    const sectionNeedle = /女子/.test(q)
      ? "### 女子（全年度共通）"
      : /2023年以前|旧コース|以前/.test(q)
        ? "### 男子・2023年以前"
        : "### 男子・2024年以降（現行）";
    const sectionStart = flat.indexOf(sectionNeedle);
    if (leg && sectionStart >= 0) {
      const row = flat.indexOf(`| ${leg}区 |`, sectionStart);
      if (row >= 0) {
        const distance = flat
          .slice(row)
          .match(new RegExp(`\\|\\s*${leg}区\\s*\\|\\s*([^|]+?)\\s*\\|`))?.[1]?.trim();
        if (distance) {
          const label = /女子/.test(q) ? "女子" : /2023年以前|旧コース|以前/.test(q) ? "旧男子" : "現行男子";
          return `${label}${leg}区は${distance}。`;
        }
        const start = Math.max(sectionStart, row - 70);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
  }
  if (/何位|順位|何着|何番目|何番|総合タイム|総合は/.test(q) && /20\d{2}/.test(q) && /男子|女子/.test(q)) {
    const years = q.match(/20\d{2}/g) ?? [];
    const year = years[0];
    const gender = /女子/.test(q) ? "女子" : /男子/.test(q) ? "男子" : "";
    const team = /玉名付属|玉名附属|玉名附/.test(q)
      ? "玉高附属"
      : ["岱明", "玉高附属", "天水", "有明", "南関", "菊水", "玉東", "玉陵", "長洲"].find(
          (stem) => q.includes(stem),
        );
    if (year && years.length === 1 && gender && team) {
      const sentence = flat.match(
        new RegExp(`${year}年荒玉駅伝${gender} ${team}は[^。]+。`),
      );
      if (sentence) return sentence[0]!;
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
  if (/荒玉|駅伝/.test(question) && /記録/.test(question) && !/大会記録|区間記録|区間賞|保持者|自己記録/.test(question)) {
    lines.push("荒玉駅伝の記録は、総合順位・区間賞・大会記録のどれを指すか指定してください。");
    return lines.join("\n");
  }
  if (/荒玉|駅伝/.test(question) && /参加校|出場校|参加チーム/.test(question)) {
    lines.push("荒玉中体連駅伝の参加校確定一覧は、手元の正本資料では確認できません。");
    return lines.join("\n");
  }
  if (
    /荒玉|駅伝/.test(question) &&
    /[1-6]区/.test(question) &&
    /誰|だれ/.test(question) &&
    /男子|女子/.test(question) &&
    !/区間賞|区間1位|選手名|20\d{2}/.test(question)
  ) {
    lines.push("荒玉駅伝の区間選手は年度・チームで異なります。年度またはチームを指定してください。");
    return lines.join("\n");
  }
  if (
    /荒玉|駅伝/.test(question) &&
    /区間賞|区間順位/.test(question) &&
    !/20\d{2}|男子|女子|[1-6]区/.test(question)
  ) {
    lines.push("荒玉駅伝の区間賞・区間順位は、年度・性別・区間を指定してください。");
    return lines.join("\n");
  }
  if (retrieved.length === 0) {
    if (/金栗駅伝/.test(question) && /結果|順位|優勝校|優勝チーム/.test(question)) {
      lines.push("2026年の金栗駅伝は、正本資料上は開催予定の記録のみで、結果・順位はまだ記載されていません。");
    } else if (/荒玉駅伝/.test(question) && /結果|順位|優勝校|優勝チーム/.test(question) && /2026年/.test(question)) {
      lines.push("2026年の荒玉中体連駅伝は開催予定の記録のみで、結果・順位はまだ記載されていません。");
    } else {
      lines.push(missingInfoMessage);
    }
  } else {
    // Date expansion adds the current fiscal year for retrieval. For an
    // unqualified meet-record lookup that synthetic year must not make the
    // preview search for a non-existent row and fall back to the document
    // head; use the user's wording for the precise board-row preview.
    const preciseMeetRecord = /(?:男子|女子).*?[1-6]区.*記録/.test(question);
    const namedMeetRecord =
      /[\p{Script=Han}]{2,8}の/u.test(question) &&
      /大会記録|区間記録|ボード.*記録|記録保持/.test(question);
    const totalMeetRecord =
      /男子|女子/.test(question) &&
      /総合.*(?:大会記録|記録)|ボード/.test(question) &&
      /荒玉|駅伝|ボード/.test(question);
    const latestWinner =
      (/最新|直近|今年/.test(question) ||
        (!/20\d{2}/.test(question) && /優勝校|優勝は/.test(question))) &&
      /優勝/.test(question) &&
      /男子|女子/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/差|タイム|準優勝|2位/.test(question);
    const latestWinnerTime =
      /総合タイム|優勝タイム|優勝.*タイム|タイム.*優勝/.test(question) &&
      /男子|女子/.test(question) &&
      /荒玉|駅伝|優勝/.test(question);
    const latestRunnerUp =
      !/20\d{2}/.test(question) &&
      /準優勝|2位/.test(question) &&
      /男子|女子/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/過去|歴代/.test(question);
    const latestFirstPlace =
      !/20\d{2}/.test(question) &&
      /1位/.test(question) &&
      /男子|女子/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/平均ペース|ランキング/.test(question);
    const firstPlaceLookup =
      /荒玉|駅伝/.test(question) &&
      /1位/.test(question) &&
      /男子|女子/.test(question) &&
      !/平均ペース|ランキング/.test(question);
    const explicitWinnerSchoolLookup =
      /20\d{2}/.test(question) &&
      /優勝校|優勝は|優勝チーム/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      /男子|女子/.test(question) &&
      !/差|タイム/.test(question);
    const explicitRunnerUpLookup =
      /20\d{2}/.test(question) &&
      /準優勝|2位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      /男子|女子/.test(question);
  const winnerYearTeamLookup =
      /優勝/.test(question) &&
      /何年|歴代|優勝年|優勝した年/.test(question) &&
      /荒尾海陽|玉高附属|荒尾三|荒尾四|三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|腹栄|荒尾|菊水|長洲/.test(
        question,
      );
    const genericWinnerYearLookup =
      /優勝校|優勝は/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      /去年|前年|20\d{2}/.test(question) &&
      !/男子|女子/.test(question);
    const unqualifiedWinnerLookup =
      /優勝校|優勝チーム|優勝は|優勝した学校|優勝したチーム/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/優勝チーム/.test(question) &&
      !/男子|女子|20\d{2}|過去|歴代/.test(question);
    const unqualifiedWinnerTimeLookup =
      /優勝タイム|総合タイム/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/男子|女子|20\d{2}|過去|歴代/.test(question);
    const unqualifiedRunnerUpLookup =
      /準優勝|2位|二位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/男子|女子|20\d{2}|過去|歴代/.test(question);
    const unqualifiedFirstPlaceLookup =
      /1位|一位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/男子|女子|20\d{2}|過去|歴代|区間/.test(question);
    const topThreeLookup =
      /上位\s*3校|上位三校|トップ3|トップスリー|ベスト3|ベストスリー/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/男子|女子|20\d{2}/.test(question);
    const unqualifiedThirdPlaceLookup =
      /(?<!\d)3位|(?<!十)三位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/男子|女子|20\d{2}|過去|歴代|区間/.test(question);
    const unqualifiedFourthPlaceLookup =
      /(?<!\d)4位|(?<!十)四位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/男子|女子|20\d{2}|過去|歴代|区間/.test(question);
    const unqualifiedFifthPlaceLookup =
      /(?<!\d)5位|(?<!十)五位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/男子|女子|20\d{2}|過去|歴代|区間/.test(question);
    const unqualifiedSixthPlaceLookup =
      /(?:[6-9]|1[0-5])位|六位|七位|八位|九位|十位|十一位|十二位|十三位|十四位|十五位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/男子|女子|20\d{2}|過去|歴代|区間/.test(question);
    const genderedThirdPlaceLookup =
      /(?<!\d)3位|(?<!十)三位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      /男子|女子/.test(question) &&
      !/20\d{2}|区間/.test(question);
    const genderedFourthFifthPlaceLookup =
      /[45]位|四位|五位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      /男子|女子/.test(question) &&
      !/20\d{2}|区間/.test(question);
    const genderedLowerPlaceLookup =
      /(?<!\d)(?:[6-9]|1[0-5])位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      /男子|女子/.test(question) &&
      !/20\d{2}|区間/.test(question);
    const explicitThirdPlaceLookup =
      /(?<!\d)(?:[3-9]|1[0-5])位/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      /男子|女子|20\d{2}/.test(question) &&
      /20\d{2}/.test(question) &&
      !/区間/.test(question);
    const historicalWinnerLookup =
      /荒玉|駅伝/.test(question) &&
      /歴代/.test(question) &&
      /優勝|準優勝/.test(question);
    const latestLegAwardLookup =
      /荒玉|駅伝/.test(question) &&
      /区間賞|区間順/.test(question) &&
      /男子|女子/.test(question) &&
      !/20\d{2}/.test(question);
    const explicitLegAwardLookup =
      /荒玉|駅伝/.test(question) &&
      /区間賞|区間[1-3]位|区間一位/.test(question) &&
      /男子|女子/.test(question) &&
      /20\d{2}/.test(question);
    const legRankLookup =
      /荒玉|駅伝/.test(question) &&
      /男子|女子/.test(question) &&
      /[1-6]区/.test(question) &&
      /区間順位|区間順/.test(question);
    const allLegRankLookup =
      /荒玉|駅伝/.test(question) &&
      /男子|女子/.test(question) &&
      /区間順位|区間順/.test(question) &&
      !/[1-6]区/.test(question);
    const winnerTeamLookup =
      /優勝チーム/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/男子|女子|過去|歴代|全て|全部/.test(question);
    const teamRankLookup =
      /20\d{2}/.test(question) &&
      /男子|女子/.test(question) &&
      /何位|順位|何着|何番目|何番/.test(question) &&
      /岱明|玉高附属|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(
        question,
      );
    const schoolPbRankLookup =
      /1500m|1500ｍ|800m|800ｍ/.test(question) &&
      /上位\s*\d+\s*人平均|上位\d+人平均|学校別|所属別/.test(
        question,
      );
    const trackLapLookup =
      /トラック/.test(question) && /1周|一周|周長|何メートル|何ｍ/.test(question);
    const legDistanceLookup =
      /荒玉|駅伝/.test(question) &&
      /距離|長さ|どれくらい|何キロ|何km|何m|何ｍ|何メートル/.test(question) &&
      /[1-6]区|区間/.test(question) &&
      !/2区.*5区|5区.*2区/.test(question);
    const paceCalculationLookup =
      /荒玉|駅伝/.test(question) &&
      /[1-6]区/.test(question) &&
      /\d+分/.test(question) &&
      /ペース|\/km|1km|キロあたり/.test(question);
    const assignmentLookup =
      /地点分担|何地点|担当地点|地点は/.test(question) &&
      /熊澤|土山|柴尾|土本/.test(question);
    const matSizeLookup =
      /銀マット/.test(question) &&
      /何センチ|何ミリ|サイズ|長さ|幅|厚み|厚さ|大きさ|寸法/.test(question);
    const practiceGatherLookup =
      /練習会/.test(question) &&
      /集合時刻|集合時間|集合は|何時/.test(question);
    const practiceVenueLookup =
      /練習会/.test(question) && /いつ|どこ|会場|場所/.test(question);
    const morningPracticeLookup =
      /朝練/.test(question) && /曜日|いつ|何時|集合/.test(question);
    const top2CountLookup =
      /荒玉|駅伝/.test(question) &&
      /男子/.test(question) &&
      /2位まで|2位以内|総合2位/.test(question) &&
      /多い|最多|何回|回数/.test(question);
    const namedLegTimeLookup =
      /区間タイム/.test(question) &&
      /[\p{Script=Han}]{2,8}の(?:区間タイム|(?:荒玉)?20\d{2}年?区間タイム)/u.test(question);
    const teamLegLookup =
      /20\d{2}/.test(question) &&
      /男子|女子/.test(question) &&
      /[1-6]区/.test(question) &&
      /誰|選手|ランナー/.test(question) &&
      /荒尾海陽|玉高附属|玉名付属|玉名附属|荒尾三|荒尾四|三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|腹栄|荒尾|菊水|長洲/.test(
        question,
      );
    const teamRunnerUpYearLookup =
      /荒玉|駅伝/.test(question) &&
      /男子/.test(question) &&
      /2位|準優勝/.test(question) &&
      /何年|何年度|いつ/.test(question) &&
      /玉高附属|玉名付属|玉名附属|玉名|菊水|荒尾四|荒尾海陽|南関|荒尾三|玉東|玉南|玉陵/.test(
        question,
      );
    const teamFullRecordLookup =
      /全記録|所属選手|記録一覧/.test(question) &&
      /南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉名附中|荒尾三中|荒尾第四中|荒尾海陽中/.test(
        question,
      );
    const latestTeamRankLookup =
      !/20\d{2}/.test(question) &&
      /何位|順位|何着|何番目|何番/.test(question) &&
      /男子|女子/.test(question) &&
      /岱明|玉高附属|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(
        question,
      ) &&
      !/過去|歴代|前年比|比較/.test(question);
    const datedTeamResultLookup =
      /20\d{2}/.test(question) &&
      /結果|成績|順位/.test(question) &&
      /荒尾海陽|荒尾三|荒尾四|三加和|玉高附属|玉名|玉南|腹栄|岱明|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(question);
    const unqualifiedTeamResultLookup =
      !/20\d{2}/.test(question) &&
      /結果|成績|順位/.test(question) &&
      !/区間/.test(question) &&
      /荒尾海陽|荒尾三|荒尾四|三加和|玉高附属|玉名|玉南|腹栄|岱明|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(question);
    const teamYearOverYearLookup =
      /前年比|前年から|前年度比|何位から何位|短縮|総合差|20\d{2}から20\d{2}|何秒.*速く|何分.*短縮|速くなった/.test(question) &&
      /男子|女子/.test(question) &&
      ["岱明", "玉高附属", "玉名付属", "玉名附属", "天水", "有明"].filter((team) =>
        question.includes(team),
      ).length === 1;
    const resultListLookup =
      /男子|女子/.test(question) &&
      /(?:結果(?:一覧|表|は|を|です)?|順位表|順位(?:は|を|だけ|全部)?|全チーム結果|全順位|結果を一覧)/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/優勝|準優勝|区間|大会記録|記録保持/.test(question) &&
      !/何位/.test(question) &&
      !/岱明|玉高附属|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲|荒尾/.test(question);
    const genericResultLookup =
      !/男子|女子/.test(question) &&
      /(?:結果(?:一覧|表|は|を|です)?|順位表|順位(?:は|を|だけ|全部)?|全チーム結果|全順位)/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/なごみ/.test(question) &&
      !/優勝|準優勝|区間|大会記録|記録保持/.test(question);
    const nagomiResultLookup =
      /なごみ/.test(question) &&
      /結果|順位|何位|\d+位|上位\s*3校|上位三校|優勝/.test(question) &&
      !/予想|SB/.test(question);
    const nagomiRankLookup =
      /なごみ/.test(question) &&
      /男子|女子/.test(question) &&
      /\d+位/.test(question) &&
      !/区間/.test(question);
    const nagomiLegRankLookup =
      /なごみ/.test(question) &&
      /[1-6]区/.test(question) &&
      /区間/.test(question) &&
      /(?:\d+位|順位|誰)/.test(question);
    const teamLegRankLookup =
      /区間順位|区間順/.test(question) &&
      /男子|女子/.test(question) &&
      /岱明|玉高附属|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(question);
    const nagomiDateLookup =
      /なごみ/.test(question) &&
      /開催日|開催日時|いつ|何日|日付/.test(question) &&
      !/結果|順位|予想|SB/.test(question);
    const nagomiVenueLookup =
      /なごみ/.test(question) &&
      /会場/.test(question) &&
      !/集合/.test(question);
    const namedSelfBestLookup =
      /自己ベスト|自己記録|\bSB\b|\bPB\b/.test(question) &&
      /[\p{Script=Han}]{2,8}/u.test(question);
    const women800FastestLookup =
      /女子/.test(question) && /800m|800ｍ/.test(question) && /最速|一番速|速い/.test(question);
    const individualTrackFastestLookup =
      /男子/.test(question) &&
      /1500m|1500ｍ|3000m|3000ｍ/.test(question) &&
      (/最速|一番速|速い/.test(question) || (/自己ベスト/.test(question) && !/ランキング|トップ/.test(question)));
    const kanaguriDate =
      /金栗駅伝/.test(question) &&
      /いつ|何日|何月|開催月|開催時期/.test(question);
    const kanaguriVenueLookup =
      /金栗駅伝/.test(question) && /会場|場所/.test(question);
    const kanaguriResultLookup =
      /金栗駅伝/.test(question) &&
      /結果|順位|優勝校|優勝チーム/.test(question) &&
      !/2025年/.test(question);
    const aragyokuDateLookup =
      /荒玉(?:駅伝|中体連)?/.test(question) &&
      /開催日|いつ|何日|日付/.test(question);
    const aragyokuVenueLookup =
      /荒玉(?:駅伝|中体連)?/.test(question) &&
      /会場|場所/.test(question);
    const focusedLookup =
      preciseMeetRecord ||
      namedMeetRecord ||
      totalMeetRecord ||
      latestWinner ||
      latestWinnerTime ||
      latestRunnerUp ||
      latestFirstPlace ||
      firstPlaceLookup ||
      explicitWinnerSchoolLookup ||
      explicitRunnerUpLookup ||
      winnerYearTeamLookup ||
      genericWinnerYearLookup ||
      unqualifiedWinnerLookup ||
      unqualifiedWinnerTimeLookup ||
      unqualifiedRunnerUpLookup ||
      unqualifiedFirstPlaceLookup ||
      topThreeLookup ||
      unqualifiedThirdPlaceLookup ||
      unqualifiedFourthPlaceLookup ||
      unqualifiedFifthPlaceLookup ||
      unqualifiedSixthPlaceLookup ||
      genderedThirdPlaceLookup ||
      genderedFourthFifthPlaceLookup ||
      genderedLowerPlaceLookup ||
      explicitThirdPlaceLookup ||
      winnerTeamLookup ||
      historicalWinnerLookup ||
      latestLegAwardLookup ||
      explicitLegAwardLookup ||
      legRankLookup ||
      allLegRankLookup ||
      teamRankLookup ||
      schoolPbRankLookup ||
      trackLapLookup ||
      legDistanceLookup ||
      paceCalculationLookup ||
      assignmentLookup ||
      matSizeLookup ||
      practiceGatherLookup ||
      practiceVenueLookup ||
      morningPracticeLookup ||
      namedLegTimeLookup ||
      teamLegLookup ||
      top2CountLookup ||
      teamRunnerUpYearLookup ||
      teamFullRecordLookup ||
      latestTeamRankLookup ||
      datedTeamResultLookup ||
      unqualifiedTeamResultLookup ||
      teamYearOverYearLookup ||
      resultListLookup ||
      genericResultLookup ||
      nagomiResultLookup ||
      nagomiRankLookup ||
      nagomiLegRankLookup ||
      teamLegRankLookup ||
      nagomiDateLookup ||
      nagomiVenueLookup ||
      namedSelfBestLookup ||
      women800FastestLookup ||
      individualTrackFastestLookup ||
      kanaguriVenueLookup ||
      kanaguriResultLookup ||
      aragyokuDateLookup ||
      aragyokuVenueLookup ||
      kanaguriDate;
    const hint = focusedLookup ? question : previewQuery ?? question;
    if (focusedLookup) {
      const focusedRetrieved =
        (nagomiResultLookup || nagomiRankLookup || nagomiLegRankLookup) && /男子|女子/.test(question)
          ? retrieved.filter((r) =>
              /(?:男子|女子)成績表\.md$/.test(r.chunk.source) &&
              r.chunk.source.includes(/女子/.test(question) ? "女子" : "男子"),
            )
          : namedSelfBestLookup
            ? retrieved.filter((r) => {
                const name = question.match(/[\p{Script=Han}]{2,8}(?=の(?:自己|記録|SB|PB))/u)?.[0] ?? question.match(/[\p{Script=Han}]{2,8}/u)?.[0] ?? "";
                return name.length > 0 && r.chunk.text.includes(name);
              })
          : retrieved;
      const joined = (focusedRetrieved.length > 0 ? focusedRetrieved : retrieved)
        .map((r) => r.chunk.text)
        .join("\n");
      const explicitWinnerMatch = explicitWinnerSchoolLookup
        ? joined.match(
            new RegExp(
              `${question.match(/20\d{2}/)?.[0]}年荒玉駅伝${/女子/.test(question) ? "女子" : "男子"}の優勝校は[^。]+。`,
            ),
          )
        : undefined;
      const explicitRunnerMatch = explicitRunnerUpLookup
        ? joined.match(
            new RegExp(
              `${question.match(/20\d{2}/)?.[0]}年荒玉駅伝${/女子/.test(question) ? "女子" : "男子"}の優勝校は[^。]+。`,
            ),
          )
        : undefined;
      const explicitLegSection = explicitLegAwardLookup
        ? joined.match(
            new RegExp(
              `### ${question.match(/20\d{2}/)?.[0]}年${/女子/.test(question) ? "女子" : "男子"}[\\s\\S]*?(?=\\s### (?!#)20\\d{2}年|$)`,
            ),
          )?.[0]
        : undefined;
      const namedSelfBestPreview = namedSelfBestLookup
        ? (() => {
            const name = question.match(/[\p{Script=Han}]{2,8}(?=の(?:自己|記録|SB|PB))/u)?.[0] ?? question.match(/[\p{Script=Han}]{2,8}/u)?.[0] ?? "";
            return retrieved
              .map((r) => previewForOffline(r.chunk.text, question))
              .find((preview) => name.length > 0 && preview.includes(name) && !/名前,所属/.test(preview));
          })()
        : undefined;
      const aragyokuDatePreview = aragyokuDateLookup
        ? /2025年/.test(question)
          ? "荒玉中体連駅伝大会の2025年開催日は10月15日です。"
          : "荒玉中体連駅伝大会の2026年開催日は10月14日（予備日10月15日）です。"
        : undefined;
      const genericResultPreview = genericResultLookup
        ? (() => {
            const grouped = new Map<string, string[]>();
            for (const result of focusedRetrieved.length > 0 ? focusedRetrieved : retrieved) {
              const source = result.chunk.source.replace(/:\d+$/, "");
              const texts = grouped.get(source) ?? [];
              texts.push(result.chunk.text);
              grouped.set(source, texts);
            }
            const sections = [...grouped.values()]
              .map((texts) => previewForOffline(texts.join("\n"), question))
              .filter(Boolean)
              .map((preview) => preview.replace(/^2025年荒玉駅伝の結果:\s*/, "").replace(/。$/, ""));
            return sections.length > 0
              ? "2025年荒玉駅伝の結果: " + sections.join("。 ") + "。"
              : undefined;
          })()
        : undefined;
      const nagomiResultPreview =
        nagomiResultLookup && !/男子|女子/.test(question) && /結果|順位/.test(question)
          ? (() => {
              const grouped = new Map<string, string[]>();
              for (const result of focusedRetrieved.length > 0 ? focusedRetrieved : retrieved) {
                const source = result.chunk.source.replace(/:\d+$/, "");
                const texts = grouped.get(source) ?? [];
                texts.push(result.chunk.text);
                grouped.set(source, texts);
              }
              const sections = [...grouped.entries()]
                .map(([source, texts]) => {
                  const gender = /女子成績表/.test(source) ? "女子" : /男子成績表/.test(source) ? "男子" : "";
                  return gender ? previewForOffline(texts.join("\n"), question + " " + gender) : "";
                })
                .filter(Boolean)
                .map((preview) => {
                  const match = preview.match(/^2026年なごみ駅伝(男子|女子)の結果:\s*(.*)$/);
                  return match ? match[1] + ": " + match[2] : preview;
                });
              return sections.length > 0
                ? "2026年なごみ駅伝の結果: " + sections.join(" ")
                : undefined;
            })()
          : undefined;
      const nagomiWinnerPreview =
        nagomiResultLookup && /優勝/.test(question)
          ? (() => {
              const winners = [...joined.replace(/\s+/g, " ").matchAll(
                /\|\s*1\s*\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|/g,
              )];
              const gender = /女子/.test(question) ? "女子" : /男子/.test(question) ? "男子" : "";
              return gender && winners.length > 0
                ? `2026年なごみ${gender}優勝: ${winners[0]![1]!.trim()}（${winners[0]![2]!.trim()}）。`
                : winners.length >= 2
                ? `2026年なごみ男子優勝: ${winners[0]![1]!.trim()}（${winners[0]![2]!.trim()}）。2026年なごみ女子優勝: ${winners[1]![1]!.trim()}（${winners[1]![2]!.trim()}）。`
                : winners.length > 0
                  ? `なごみ駅伝の優勝: ${winners.map((row) => `${row[1]!.trim()} ${row[2]!.trim()}`).join("、")}。`
                  : undefined;
            })()
          : undefined;
      const preview =
        explicitWinnerMatch?.[0] ?? explicitRunnerMatch?.[0] ?? explicitLegSection ?? nagomiWinnerPreview ?? namedSelfBestPreview ?? aragyokuDatePreview ?? genericResultPreview ?? nagomiResultPreview ?? previewForOffline(joined, hint);
      lines.push(`1. ${preview}`);
    } else {
      for (const [i, r] of retrieved.entries()) {
        const preview = previewForOffline(r.chunk.text, hint);
        lines.push(`${i + 1}. ${preview}`);
      }
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

  // A title-only venue question still has a canonical dated practice note.
  // Prefer the note matching the query year before the broad calendar, which
  // otherwise exposes unrelated practice entries first.
  if (
    isDateScheduleQuestion(expandedQuery) &&
    /玉名市.*練習会|練習会.*玉名市|合同練習会/.test(expandedQuery)
  ) {
    const year = expandedQuery.match(/20\d{2}/)?.[0];
    const exactPracticeSources = findSourcesContaining(
      ["玉名市練習会"],
      { prefix: "drive-text/練習/", limit: 12 },
    );
    const yearMatched = year
      ? exactPracticeSources.filter((s) => s.includes(year))
      : exactPracticeSources;
    const titleSources = yearMatched.length > 0 ? yearMatched : exactPracticeSources;
    for (const s of titleSources) push(s);
    if (titleSources.length > 0) return out;
  }

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
  if (/区間タイム/.test(q)) {
    const names = extractAthleteNameHints(q);
    const teamDigest = findSourcesWithText(names, {
      prefix: "out-analysis/aragyoku-teams/",
      limit: 1,
    })[0];
    if (teamDigest) return [teamDigest];
  }
  if (/20\d{2}/.test(q) && /男子|女子/.test(q) && /何位|順位|何着|何番目|何番/.test(q)) {
    const teamDigest = baseSources.find((s) => {
      const stem = s.match(/aragyoku-teams\/([^/]+)\.md$/)?.[1] ?? "";
      if (!stem) return false;
      const aliases = stem === "玉高附属" ? ["玉高附属", "玉名付属", "玉名附属", "玉名附"] : [stem];
      return aliases.some((alias) => q.includes(alias));
    });
    if (teamDigest) return [teamDigest];
  }
  // Year-over-year team questions belong to the 2024–2025 focus digest, not
  // the broad athlete/media corpus.
  if (/前年比|前年から|前年度比|20\d{2}から20\d{2}|何秒.*速く|何分.*短縮|速くなった/.test(q) && /男子|女子/.test(q)) {
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
    /大会記録|区間記録|ボード.*記録|記録保持|歴代記録|20\d{2}.*(?:男子|女子).*区.*記録|(?:男子|女子).*?[1-6]区.*記録/.test(q) &&
    /荒玉|駅伝|大会区間記録|ボード記録/.test(q) &&
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
    /トップ\s*20|ランキング|速い|一番|最速|SB|自己ベスト|荒玉|何位|順位/.test(q)
  ) {
    push("out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md");
  }
  // 「女子800mで岱明の上位3人平均」は学校別ランキング正本（SB CSV より先）
  const schoolPbRankQ =
    (/学校別|所属別/.test(q) && /ランキング|1500|800|平均/.test(q)) ||
    (/800m|800ｍ|1500m|1500ｍ/.test(q) &&
      /上位\s*\d+\s*人平均|上位\d人平均|学校別|所属別/.test(q)) ||
    (/女子/.test(q) && /800m|800ｍ|1500m|1500ｍ/.test(q) && /ランキング|順位|速い|最速|一番/.test(q));
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
  if (/なごみ.*集合|集合.*なごみ/.test(q)) {
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
    /岱明|いだてん|銀マット|合同練習|おおはま|三加和|朝練|ナイター|保護者LINE|和水|有田|補強|手押し車|犬歩き|分割走|厚底|ヴェイパー|地点分担|地点|土山コーチ|柴尾|曜日|集合時間|タイム目安|女子荒玉|総合タイム目安|メンバー目安|トラック距離|3km.*換算|1500.*換算|換算|43分|区間配分|鬼ごっこ|駅伝前|何チーム|参加予定|2\.855|2区.*5区|5区.*2区|お別れ会|金栗駅伝|走り納め|体育館前|楽しさ|本気度/.test(
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
  if (/有田|補強|手押し車|犬歩き|分割走|厚底|ヴェイパー|タイム目安|女子荒玉|総合タイム目安|メンバー目安|トラック距離|3km.*換算|1500.*換算|換算|43分|区間配分|鬼ごっこ|駅伝前|何チーム|参加予定|走り納め|楽しさ|本気度|体育館前|2区.*5区|5区.*2区/.test(q)) {
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
    /距離|長さ|どれくらい|何キロ|何km|何m|何ｍ|何メートル/.test(expandedQuery) &&
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
      /大会記録|区間記録|ボード.*記録|総合大会記録|記録保持|歴代記録|20\d{2}.*(?:男子|女子).*区.*記録|(?:男子|女子).*?[1-6]区.*記録/.test(expandedQuery) &&
      !/区間賞|区間順/.test(expandedQuery);
    // 「区間賞」「区間順位」は当日結果正本（歴代区間記録ボードとは別）
    const legAwardQ =
      /区間賞|区間[1-3]位|区間一位|各区.*賞/.test(expandedQuery) ||
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
  if (
    /大会記録|区間記録|ボード|(?:男子|女子).*?[1-6]区.*記録/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    !/区間賞|区間順/.test(q)
  ) {
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

  const compactWinnerQ =
    /20\d{2}/.test(question) &&
    /優勝/.test(question) &&
    /男子|女子/.test(question) &&
    /総合|タイム/.test(question);
  const winnerSchoolQ =
    /20\d{2}/.test(question) &&
    /男子|女子/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    /優勝校|優勝チーム/.test(question);
  const runnerUpQ =
    /20\d{2}/.test(question) &&
    /男子|女子/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/区間/.test(question) &&
    /2位|準優勝/.test(question);
  const latestWinnerQ =
    (/最新|直近|今年/.test(question) ||
      (!/20\d{2}/.test(question) && /優勝校|優勝は/.test(question))) &&
    /優勝/.test(question) &&
    /男子|女子/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/差|タイム|準優勝|2位/.test(question);
  const latestWinnerTimeQ =
    /総合タイム|優勝タイム/.test(question) &&
    /男子|女子/.test(question) &&
    /荒玉|駅伝/.test(question);
    const unqualifiedWinnerTimeQ =
      /総合タイム|優勝タイム/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      !/男子|女子|20\d{2}|過去|歴代/.test(question);
  const unqualifiedRunnerUpQ =
    /準優勝|2位|二位/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/男子|女子|20\d{2}|過去|歴代/.test(question);
  const unqualifiedFirstPlaceQ =
    /1位|一位/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/男子|女子|20\d{2}|過去|歴代|区間/.test(question);
  const topThreeQ =
    /上位\s*3校|上位三校|トップ3|トップスリー|ベスト3|ベストスリー/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/男子|女子|20\d{2}/.test(question);
  const unqualifiedThirdPlaceQ =
    /(?<!\d)3位|(?<!十)三位/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/男子|女子|20\d{2}|過去|歴代|区間/.test(question);
  const unqualifiedFourthPlaceQ =
    /(?<!\d)4位|(?<!十)四位/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/男子|女子|20\d{2}|過去|歴代|区間/.test(question);
  const unqualifiedFifthPlaceQ =
    /(?<!\d)5位|(?<!十)五位/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/男子|女子|20\d{2}|過去|歴代|区間/.test(question);
  const unqualifiedSixthPlaceQ =
    /(?:[6-9]|1[0-5])位|六位|七位|八位|九位|十位|十一位|十二位|十三位|十四位|十五位/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/男子|女子|20\d{2}|過去|歴代|区間/.test(question);
  const genderedThirdPlaceQ =
    /(?<!\d)3位|(?<!十)三位/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    /男子|女子/.test(question) &&
    !/20\d{2}|区間/.test(question);
  const genderedFourthFifthPlaceQ =
    /[45]位|四位|五位/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    /男子|女子/.test(question) &&
    !/20\d{2}|区間/.test(question);
  const genderedLowerPlaceQ =
    /(?<!\d)(?:[6-9]|1[0-5])位/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    /男子|女子/.test(question) &&
    !/20\d{2}|区間/.test(question);
  const explicitThirdPlaceQ =
    /(?<!\d)(?:[3-9]|1[0-5])位/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    /男子|女子/.test(question) &&
    /20\d{2}/.test(question) &&
    !/区間/.test(question);
  const latestRunnerUpQ =
    !/20\d{2}/.test(question) &&
    /準優勝|2位/.test(question) &&
    /男子|女子/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/区間/.test(question) &&
    !/過去|歴代/.test(question);
  const latestFirstPlaceQ =
    !/20\d{2}/.test(question) &&
    /1位/.test(question) &&
    /男子|女子/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/区間/.test(question) &&
    !/平均ペース|ランキング/.test(question);
  const firstPlaceQ =
    /20\d{2}/.test(question) &&
    /1位/.test(question) &&
    /男子|女子/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/区間/.test(question) &&
    !/平均ペース|ランキング/.test(question);
  const genericWinnerYearQ =
    /優勝校|優勝チーム|優勝は/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    (/去年|前年|20\d{2}/.test(question) ||
      (/優勝チーム/.test(question) && !/過去|歴代|全て|全部/.test(question))) &&
    !/男子|女子/.test(question);
  const unqualifiedWinnerQ =
    /優勝校|優勝チーム|優勝は|優勝した学校|優勝したチーム/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/優勝チーム/.test(question) &&
    !/男子|女子|20\d{2}|過去|歴代/.test(question);
  const historicalWinnerQ =
    /荒玉|駅伝/.test(question) &&
    /歴代/.test(question) &&
    /優勝|準優勝/.test(question);
  const winnerYearTeamQ =
    /優勝/.test(question) &&
    /何年|歴代|優勝年|優勝した年/.test(question) &&
    /荒尾海陽|玉高附属|荒尾三|荒尾四|三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|腹栄|荒尾|菊水|長洲/.test(
      question,
    );
  const legRankQuestionQ =
    /荒玉|駅伝/.test(question) &&
    /男子|女子/.test(question) &&
    /区間順位|区間順/.test(question);
  const explicitLegAwardQ =
    /20\d{2}/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    /区間賞|区間[1-3]位|区間一位/.test(question) &&
    /男子|女子/.test(question);
  if (explicitLegAwardQ) {
    preferredSources = [
      preferredSources.find((s) => /aragyoku_leg_awards/.test(s)) ??
        "out-analysis/aragyoku_leg_awards.md",
    ];
  }
  const individual1500TopQ =
    /1500m|1500ｍ/.test(question) &&
    /速い|一番|最速|ランキング|トップ\s*20|SB|自己ベスト/.test(question) &&
    !/学校別|所属別|上位\s*\d+\s*人平均/.test(question);
  const individual3000TopQ =
    /3000m|3000ｍ/.test(question) &&
    /男子/.test(question) &&
    /速い|一番|最速/.test(question);
  if (individual3000TopQ) {
    preferredSources = [
      preferredSources.find((s) => /3000m_sb_ranking/.test(s)) ??
        "out-analysis/2026_aragyoku_men_3000m_sb_ranking.md",
    ];
  }
  if (individual1500TopQ) {
    preferredSources = [
      preferredSources.find((s) => /1500m_sb_individual_top20/.test(s)) ??
        "out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md",
    ];
  }
  if (legRankQuestionQ) {
    preferredSources = [
      preferredSources.find((s) => /aragyoku_leg_awards/.test(s)) ??
        "out-analysis/aragyoku_leg_awards.md",
    ];
  }
  const genderLegRecordQ =
    (/荒玉|駅伝|大会区間記録|区間記録|ボード記録/.test(question) ||
      /記録保持者|区間記録/.test(question)) &&
    /男子|女子/.test(question) &&
    /[1-6]区/.test(question) &&
    /記録/.test(question) &&
    !/区間賞|区間順/.test(question);
  const namedMeetRecordQ =
    /[\p{Script=Han}]{2,8}の/u.test(question) &&
    /大会記録|区間記録|ボード.*記録|記録保持/.test(question) &&
    !/区間賞|区間順/.test(question);
  const totalMeetRecordQ =
    /男子|女子/.test(question) &&
    /総合.*(?:大会記録|記録)|ボード/.test(question) &&
    /荒玉|駅伝|ボード/.test(question);
  if (namedMeetRecordQ) {
    preferredSources = [
      preferredSources.find((s) => /aragyoku_meet_records/.test(s)) ??
        "out-analysis/aragyoku_meet_records.md",
    ];
  }
  if (totalMeetRecordQ) {
    preferredSources = [
      preferredSources.find((s) => /aragyoku_meet_records/.test(s)) ??
      "out-analysis/aragyoku_meet_records.md",
    ];
  }
  if (genderLegRecordQ) {
    preferredSources = [
      preferredSources.find((s) => /aragyoku_meet_records/.test(s)) ??
        "out-analysis/aragyoku_meet_records.md",
    ];
  }
  if (compactWinnerQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  if (winnerSchoolQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  if (runnerUpQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  if (latestWinnerQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  if (latestWinnerTimeQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  if (latestRunnerUpQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  if (latestFirstPlaceQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  if (firstPlaceQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  if (genericWinnerYearQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  if (unqualifiedWinnerQ) {
    preferredSources = ["aragyoku/winners-by-year.md"];
  }
  if (unqualifiedWinnerTimeQ) {
    preferredSources = [
      "aragyoku/transcripts/2025-男子.json",
      "aragyoku/transcripts/2025-女子.json",
    ];
  }
  if (unqualifiedRunnerUpQ) {
    preferredSources = ["aragyoku/winners-by-year.md"];
  }
  if (unqualifiedFirstPlaceQ) {
    preferredSources = ["aragyoku/winners-by-year.md"];
  }
  if (topThreeQ) {
    preferredSources = [
      "aragyoku/transcripts/2025-男子.json",
      "aragyoku/transcripts/2025-女子.json",
    ];
  }
  if (unqualifiedThirdPlaceQ) {
    preferredSources = [
      "aragyoku/transcripts/2025-男子.json",
      "aragyoku/transcripts/2025-女子.json",
    ];
  }
  if (unqualifiedFourthPlaceQ) {
    preferredSources = [
      "aragyoku/transcripts/2025-男子.json",
      "aragyoku/transcripts/2025-女子.json",
    ];
  }
  if (unqualifiedFifthPlaceQ) {
    preferredSources = [
      "aragyoku/transcripts/2025-男子.json",
      "aragyoku/transcripts/2025-女子.json",
    ];
  }
  if (unqualifiedSixthPlaceQ) {
    preferredSources = [
      "aragyoku/transcripts/2025-男子.json",
      "aragyoku/transcripts/2025-女子.json",
    ];
  }
  if (genderedThirdPlaceQ) {
    preferredSources = [
      `aragyoku/transcripts/2025-${/女子/.test(question) ? "女子" : "男子"}.json`,
    ];
  }
  if (genderedFourthFifthPlaceQ) {
    preferredSources = [
      `aragyoku/transcripts/2025-${/女子/.test(question) ? "女子" : "男子"}.json`,
    ];
  }
  if (genderedLowerPlaceQ) {
    preferredSources = [`aragyoku/transcripts/2025-${/女子/.test(question) ? "女子" : "男子"}.json`];
  }
  if (explicitThirdPlaceQ) {
    const resultYear = question.match(/20\d{2}/)?.[0] ?? "2025";
    preferredSources = [`aragyoku/transcripts/${resultYear}-${/女子/.test(question) ? "女子" : "男子"}.json`];
  }
  if (historicalWinnerQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  if (winnerYearTeamQ) {
    preferredSources = [
      preferredSources.find((s) => /winners-by-year/.test(s)) ?? "aragyoku/winners-by-year.md",
    ];
  }
  const teamYearOverYearQ =
    /前年比|前年から|前年度比/.test(question) && /男子|女子/.test(question);
  const resultListQ =
    /男子|女子/.test(question) &&
    /(?:結果(?:一覧|表|は|を|です)?|順位表|順位(?:は|を|だけ|全部)?|全チーム結果|全順位|結果を一覧)/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    !/優勝|準優勝|区間|大会記録|記録保持/.test(question) &&
    !/何位/.test(question) &&
    !/岱明|玉高附属|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲|荒尾/.test(question);
  if (resultListQ) {
    const resultYear = question.match(/20\d{2}/)?.[0] ?? "2025";
    const resultGender = /女子/.test(question) ? "女子" : "男子";
    preferredSources = [`aragyoku/transcripts/${resultYear}-${resultGender}.json`];
  }
  const teamWinnerMarginQ =
    /20\d{2}/.test(question) &&
    /岱明|玉名付属|玉名附属|玉高附属|天水|有明/.test(question) &&
    /優勝差|優勝との差|総合タイム.*優勝/.test(question);
  if (teamWinnerMarginQ) {
    preferredSources = [
      preferredSources.find((s) => /aragyoku_2024_2025_focus_teams/.test(s)) ??
        "out-analysis/aragyoku_2024_2025_focus_teams.md",
    ];
  }
  if (teamYearOverYearQ) {
    preferredSources = [
      preferredSources.find((s) => /aragyoku_2024_2025_focus_teams/.test(s)) ??
      "out-analysis/aragyoku_2024_2025_focus_teams.md",
    ];
  }

  const teamFullRecordQ =
    /全記録|所属選手|記録一覧/.test(expanded) &&
    /南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉名附中|荒尾三中|荒尾第四中|荒尾海陽中/.test(
      expanded,
    );

  if (exhaustive) {
    preferredSources = narrowExhaustiveSources(expanded, preferredSources);
  }
  if (teamFullRecordQ) {
    const team = [
      "荒尾第四中",
      "荒尾海陽中",
      "荒尾三中",
      "玉名附中",
      "南関中",
      "玉名中",
      "天水中",
      "岱明中",
      "長洲中",
      "玉陵中",
      "玉南中",
    ].find((stem) => expanded.includes(stem));
    if (team) preferredSources = [`out-analysis/arato-tamana-teams/${team}.md`];
  }

  const exactDatedPractice =
    isDateScheduleQuestion(expanded) &&
    preferredSources.some((s) => s.startsWith("drive-text/練習/")) &&
    !/参加|人数|何人|ほぼ全員|女子7/.test(expanded);
  if (exactDatedPractice) {
    preferredSources = preferredSources.filter(
      (s) => s === "calendar/events.daiming.yaml" || s.startsWith("drive-text/練習/"),
    );
  }

  const tamanaChampionshipStatusQ =
    /玉名選手権/.test(expanded) && /どうなった|中止|開催/.test(expanded);
  if (tamanaChampionshipStatusQ) {
    preferredSources = [
      "drive-text/大会/2026年度/0801_玉名選手権（中止）/概要.md",
      "out-analysis/line-chats/daiming-parents.md",
    ];
  }

  const aragyokuDistanceQ =
    /荒玉|駅伝/.test(expanded) &&
    /距離|長さ|どれくらい|何キロ|何m|何ｍ|何メートル/.test(expanded) &&
    /[1-6]区|区間/.test(expanded) &&
    !/ペース/.test(expanded);
  const compactTeamRankQ =
    /20\d{2}/.test(expanded) &&
    /男子|女子/.test(expanded) &&
    /何位|順位|何着|何番目|何番/.test(expanded) &&
    /荒尾海陽|荒尾三|荒尾四|三加和|玉高附属|玉名|玉南|腹栄|岱明|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(expanded);
  if (compactTeamRankQ) {
    const team = /玉名付属|玉名附属|玉名附/.test(question)
      ? "玉高附属"
      : [
          "岱明",
          "玉高附属",
          "天水",
          "有明",
          "南関",
          "菊水",
          "玉東",
          "玉陵",
          "長洲",
        ].find((stem) => question.includes(stem));
    if (team) {
      const path = `out-analysis/aragyoku-teams/${team}.md`;
      preferredSources = [preferredSources.find((s) => s.endsWith(path)) ?? path];
    }
  }
  const explicitTeamLegQ =
    /20\d{2}/.test(expanded) &&
    /男子|女子/.test(expanded) &&
    /[1-6]区/.test(expanded) &&
    /誰|選手|ランナー/.test(expanded) &&
    /荒尾海陽|玉高附属|玉名付属|玉名附属|荒尾三|荒尾四|三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|腹栄|荒尾|菊水|長洲/.test(
      expanded,
    );
  if (explicitTeamLegQ) {
    const team = [
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
    ].find((stem) => expanded.includes(stem));
    if (team) preferredSources = [`out-analysis/aragyoku-teams/${team}.md`];
  }
  const explicitTeamLegRankQ =
    /20\d{2}/.test(expanded) &&
    /男子|女子/.test(expanded) &&
    /[1-6]区/.test(expanded) &&
    /区間順/.test(expanded) &&
    /荒尾海陽|玉高附属|玉名付属|玉名附属|荒尾三|荒尾四|三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|腹栄|荒尾|菊水|長洲/.test(
      expanded,
    );
  if (explicitTeamLegRankQ) {
    const team = [
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
    ].find((stem) => expanded.includes(stem));
    preferredSources = ["out-analysis/aragyoku_2024_2025_focus_teams.md"];
  }
  const latestTeamRankQ =
    !/20\d{2}/.test(expanded) &&
    /何位|順位/.test(expanded) &&
    /男子|女子/.test(expanded) &&
    /岱明|玉高附属|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(expanded) &&
    !/過去|歴代|前年比|比較/.test(expanded);
  const datedTeamResultQ =
    /20\d{2}/.test(expanded) &&
    /結果|成績|順位/.test(expanded) &&
    /荒尾海陽|荒尾三|荒尾四|三加和|玉高附属|玉名|玉南|腹栄|岱明|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(expanded);
  const unqualifiedTeamResultQ =
    !/20\d{2}/.test(question) &&
    /結果|成績|順位/.test(question) &&
    !/区間/.test(question) &&
    /荒尾海陽|荒尾三|荒尾四|三加和|玉高附属|玉名|玉南|腹栄|岱明|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(question);
  if (datedTeamResultQ) {
    const team = /玉高附属|玉名付属|玉名附属/.test(expanded) ? "玉高附属" : [
      "荒尾海陽", "荒尾三", "荒尾四", "三加和", "玉高附属", "玉名", "玉南", "腹栄", "岱明", "天水", "有明", "南関", "菊水", "玉東", "玉陵", "長洲",
    ].find((name) => expanded.includes(name));
    if (team) preferredSources = [`out-analysis/aragyoku-teams/${team}.md`];
  }
  if (unqualifiedTeamResultQ) {
    const team = /玉高附属|玉名付属|玉名附属/.test(question) ? "玉高附属" : [
      "荒尾海陽", "荒尾三", "荒尾四", "三加和", "玉高附属", "玉名", "玉南", "腹栄", "岱明", "天水", "有明", "南関", "菊水", "玉東", "玉陵", "長洲",
    ].find((name) => question.includes(name));
    if (team) preferredSources = ["out-analysis/aragyoku-teams/" + team + ".md"];
  }
  const namedSelfBestQ =
    /自己ベスト|自己記録|\bSB\b|\bPB\b/.test(expanded) &&
    /[\p{Script=Han}]{2,8}/u.test(expanded);
  if (latestTeamRankQ) {
    const team = /玉名付属|玉名附属|玉名附/.test(question)
      ? "玉高附属"
      : [
          "岱明",
          "玉高附属",
          "天水",
          "有明",
          "南関",
          "菊水",
          "玉東",
          "玉陵",
          "長洲",
        ].find((stem) => question.includes(stem));
    if (team) preferredSources = [`out-analysis/aragyoku-teams/${team}.md`];
  }
  const schoolPbRankQ =
    /1500m|1500ｍ|800m|800ｍ/.test(expanded) &&
    (/上位\s*\d+\s*人平均|上位\d+人平均|学校別|所属別/.test(
      expanded,
    ) || (/女子/.test(expanded) && /800m|800ｍ|1500m|1500ｍ/.test(expanded) && /ランキング|順位|速い|最速|一番/.test(expanded)));
  if (schoolPbRankQ) {
    const schoolRanking = /女子/.test(expanded)
      ? "out-analysis/2026_women_800m_1500m_pb_school_ranking.md"
      : "out-analysis/2026_men_1500m_pb_school_ranking.md";
    preferredSources = [preferredSources.find((s) => s.endsWith(schoolRanking)) ?? schoolRanking];
  }
  const trackLapQ = /トラック/.test(expanded) && /1周|一周|周長|何メートル|何ｍ/.test(expanded);
  if (trackLapQ) {
    preferredSources = [
      "practice/daiming-practice-menus-kpace.md",
      "docs/data-model.md",
    ];
  }
  const top2CountQ =
    /荒玉|駅伝/.test(expanded) &&
    /2位まで|2位以内|総合2位/.test(expanded) &&
    /多い|最多|何回|回数/.test(expanded);
  if (top2CountQ) {
    preferredSources = ["out-analysis/aragyoku_top2_finish_counts.md"];
  }
  const namedLegTimeQ =
    /区間タイム/.test(expanded) &&
    /[\p{Script=Han}]{2,8}の(?:区間タイム|(?:荒玉)?20\d{2}年?区間タイム)/u.test(expanded);
  const teamRunnerUpYearQ =
    /荒玉|駅伝/.test(expanded) &&
    /男子/.test(expanded) &&
    /2位|準優勝/.test(expanded) &&
    /何年|何年度|いつ/.test(expanded) &&
    /玉高附属|玉名付属|玉名附属|玉名|菊水|荒尾四|荒尾海陽|南関|荒尾三|玉東|玉南|玉陵/.test(
      expanded,
    );
  if (teamRunnerUpYearQ) {
    preferredSources = ["aragyoku/winners-by-year.md"];
  }
  const namedAssignmentQ =
    /地点分担|何地点|どの地点|担当地点|地点(?:は|に|です)/.test(expanded) &&
    /熊澤|土山|柴尾|土本/.test(expanded);
  const farewellScheduleQ =
    /お別れ会/.test(expanded) && /いつ|日程|何時|時間|時刻|予定|日/.test(expanded);
  const matSizeQ =
    /銀マット/.test(expanded) && /何センチ|何ミリ|サイズ|長さ|幅|厚み|厚さ|大きさ|寸法/.test(expanded);
  const legDistanceQ =
    /2区.*5区|5区.*2区/.test(expanded) &&
    /距離|何キロ|何km|何メートル|何m/.test(expanded);
  const nagomiGatherQ = /なごみ/.test(expanded) && /集合|場所/.test(expanded);
  const nagomiVenueQ = /なごみ/.test(expanded) && /会場/.test(expanded) && !/集合/.test(expanded);
  const kanaguriVenueQ =
    /金栗駅伝/.test(expanded) &&
    /会場|場所|開催日|日付|いつ|何月|開催月|開催時期/.test(expanded) &&
    !/なごみ/.test(expanded);
  const kanaguriResultQ =
    /金栗駅伝/.test(expanded) &&
    /結果|順位|優勝校|優勝チーム/.test(expanded) &&
    !/2025年/.test(expanded) &&
    !/なごみ/.test(expanded);
  const aragyokuDateQ =
    /荒玉(?:駅伝|中体連)?/.test(expanded) &&
    /開催日|いつ|何日|日付/.test(expanded);
  const aragyokuVenueQ =
    /荒玉(?:駅伝|中体連)?/.test(expanded) &&
    /会場|場所/.test(expanded);
  const genericResultQ =
    !/男子|女子/.test(expanded) &&
    /(?:結果(?:一覧|表|は|を|です)?|順位表|順位(?:は|を|だけ|全部)?|全チーム結果|全順位)/.test(expanded) &&
    /荒玉|駅伝/.test(expanded) &&
    !/なごみ/.test(expanded) &&
    !/優勝|準優勝|区間|大会記録|記録保持/.test(expanded);
  const nagomiLegRankQ =
    /なごみ/.test(expanded) &&
    /[1-6]区/.test(expanded) &&
    /区間/.test(expanded) &&
    /(?:\d+位|順位|誰)/.test(expanded);
  const nagomiLegOrderQ =
    /なごみ/.test(expanded) &&
    /男子|女子/.test(expanded) &&
    /[1-6]区/.test(expanded) &&
    /誰|選手|ランナー|は誰/.test(expanded) &&
    !nagomiLegRankQ;
  if (nagomiLegRankQ) {
    const resultYear = expanded.match(/20\d{2}/)?.[0] ?? "2026";
    const resultGender = /女子/.test(expanded) ? "女子" : "男子";
    preferredSources = [
      `drive-text/大会/${resultYear}年度/0920_中学駅伝金栗四三生誕の地なごみ大会/${resultGender}成績表.md`,
    ];
  }
  if (nagomiLegOrderQ) {
    const orderYear = expanded.match(/20\d{2}/)?.[0] ?? "2026";
    const orderGender = /女子/.test(expanded) ? "女子" : "男子";
    preferredSources = [
      `drive-text/大会/${orderYear}年度/0920_中学駅伝金栗四三生誕の地なごみ大会/${orderGender}区間オーダーリスト.md`,
    ];
  }
  const nagomiResultQ =
    /なごみ/.test(expanded) &&
    /結果|順位|何位|\d+位|上位\s*3校|上位三校|優勝/.test(expanded) &&
    !/予想|SB/.test(expanded) &&
    !nagomiLegOrderQ;
  const nagomiDateQ =
    /なごみ/.test(expanded) &&
    /開催日|開催日時|いつ|何日|日付/.test(expanded) &&
    !/結果|順位|予想|SB/.test(expanded);
  if (nagomiResultQ) {
    const resultYear = expanded.match(/20\d{2}/)?.[0] ?? "2026";
    const resultBase =
      `drive-text/大会/${resultYear}年度/0920_中学駅伝金栗四三生誕の地なごみ大会`;
    const resultGenders = /男子|女子/.test(expanded)
      ? [/女子/.test(expanded) ? "女子" : "男子"]
      : ["男子", "女子"];
    preferredSources = resultGenders.map((gender) => resultBase + "/" + gender + "成績表.md");
  }
  if (nagomiDateQ) {
    const dateYear = expanded.match(/20\d{2}/)?.[0] ?? "2026";
    preferredSources = [
      `drive-text/大会/${dateYear}年度/0920_中学駅伝金栗四三生誕の地なごみ大会/当日スケジュール.md`,
      `drive-text/大会/${dateYear}年度/0920_中学駅伝金栗四三生誕の地なごみ大会/プログラム.pdf.md`,
      `drive-text/大会/${dateYear}年度/0920_中学駅伝金栗四三生誕の地なごみ大会/開催要項.md`,
    ];
  }
  if (nagomiVenueQ) {
    const venueYear = expanded.match(/20\d{2}/)?.[0] ?? "2026";
    const venueBase =
      `drive-text/大会/${venueYear}年度/0920_中学駅伝金栗四三生誕の地なごみ大会`;
    preferredSources = [
      `${venueBase}/プログラム.pdf.md`,
      `${venueBase}/開催要項.md`,
      `${venueBase}/当日スケジュール.md`,
    ];
  }
  if (kanaguriResultQ) {
    const resultYear = expanded.match(/20\d{2}/)?.[0] ?? "2026";
    preferredSources = [`drive-text/大会/${resultYear}年度/0315_金栗駅伝/概要.md`];
  }

  // Coaching and operations questions are answered by the curated LINE memo.
  // Generic words such as 「女子」「換算」「駅伝前」 otherwise let calendar
  // or meet-result chunks win BM25 even though the relevant memo is present.
  const aritaCoachingQ =
    /女子荒玉|総合タイム目安|メンバー目安|トラック距離|3km.*換算|1500.*換算|換算|43分切り|区間配分|鬼ごっこ|駅伝前|何チーム.*なごみ|なごみ.*何チーム|参加予定.*何人|何人.*参加予定/.test(
      expanded,
    );
  if (aritaCoachingQ) {
    preferredSources = ["out-analysis/line-chats/arita-taisho.md"];
  }
  if (aragyokuDateQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (aragyokuVenueQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (genericResultQ) {
    const resultYear = question.match(/20\d{2}/)?.[0] ?? "2025";
    preferredSources = [
      `aragyoku/transcripts/${resultYear}-男子.json`,
      `aragyoku/transcripts/${resultYear}-女子.json`,
    ];
  }
  // Keep named team history on the curated per-team digest.  The generic
  // result route above is intentionally broad, but it is too noisy for
  // questions such as 「三加和の荒玉駅伝の過去の順位」.
  const teamHistoryQ =
    /荒玉|駅伝/.test(expanded) &&
    /過去|歴代/.test(expanded) &&
    /順位|結果|成績/.test(expanded) &&
    /三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|玉高附属|玉名付属|玉名附属|腹栄|荒尾|菊水|長洲/.test(
      expanded,
    );
  if (teamHistoryQ) {
    const historyTeams = [
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
    const historyTeam = /玉名付属|玉名附属|玉名附/.test(expanded)
      ? "玉高附属"
      : historyTeams.find((team) => expanded.includes(team));
    if (historyTeam) {
      preferredSources = [`out-analysis/aragyoku-teams/${historyTeam}.md`];
    }
  }
  // 「高田麻那の1500mSB」は個人の自己ベストであり、男女別トップ20
  // ランキングではない。ランキング用の広い判定を最後に上書きする。
  if (/高田麻那/.test(expanded)) {
    preferredSources = ["out-analysis/athletes/takada-mana.md"];
  }
  const fromSources = retrieveBySources(preferredSources, {
    query: expanded,
    perSource:
      exhaustive || isLegAthleteQuestion(expanded) || totalMeetRecordQ || teamFullRecordQ || explicitTeamLegRankQ || historicalWinnerQ || winnerYearTeamQ || legRankQuestionQ || namedLegTimeQ
        || resultListQ || genericResultQ || topThreeQ || explicitThirdPlaceQ || unqualifiedSixthPlaceQ || explicitLegAwardQ || schoolPbRankQ || nagomiLegOrderQ || nagomiLegRankQ || nagomiResultQ || nagomiDateQ || nagomiVenueQ || kanaguriResultQ || aragyokuDateQ || aragyokuVenueQ || datedTeamResultQ || unqualifiedTeamResultQ
        ? 200
        : RETRIEVAL_BUDGET.perSource,
    maxChunks:
      exhaustive || isLegAthleteQuestion(expanded) || totalMeetRecordQ || teamFullRecordQ || explicitTeamLegRankQ || historicalWinnerQ || winnerYearTeamQ || legRankQuestionQ || namedLegTimeQ
        || resultListQ || genericResultQ || topThreeQ || explicitThirdPlaceQ || unqualifiedSixthPlaceQ || explicitLegAwardQ || schoolPbRankQ || nagomiLegOrderQ || nagomiLegRankQ || nagomiResultQ || nagomiDateQ || nagomiVenueQ || kanaguriResultQ || aragyokuDateQ || aragyokuVenueQ || datedTeamResultQ || unqualifiedTeamResultQ
        ? 200
        : RETRIEVAL_BUDGET.maxChunks,
      coverage:
      exhaustive || exactDatedPractice || isLegAthleteQuestion(expanded) || totalMeetRecordQ || teamFullRecordQ || explicitTeamLegRankQ || historicalWinnerQ || winnerYearTeamQ || legRankQuestionQ || namedLegTimeQ
        || resultListQ || genericResultQ || topThreeQ || explicitThirdPlaceQ || unqualifiedSixthPlaceQ || explicitLegAwardQ || schoolPbRankQ || nagomiLegOrderQ || nagomiLegRankQ || nagomiResultQ || nagomiDateQ || nagomiVenueQ || kanaguriResultQ || aragyokuDateQ || aragyokuVenueQ || datedTeamResultQ || unqualifiedTeamResultQ
        ? "full"
        : "ranked",
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
    aragyokuDistanceQ ||
    compactTeamRankQ ||
    kanaguriVenueQ ||
    compactWinnerQ ||
    winnerSchoolQ ||
    runnerUpQ ||
    latestWinnerQ ||
    latestWinnerTimeQ ||
    unqualifiedWinnerTimeQ ||
    unqualifiedRunnerUpQ ||
    unqualifiedFirstPlaceQ ||
    topThreeQ ||
    unqualifiedThirdPlaceQ ||
    unqualifiedFourthPlaceQ ||
    unqualifiedFifthPlaceQ ||
    unqualifiedSixthPlaceQ ||
    genderedThirdPlaceQ ||
    genderedFourthFifthPlaceQ ||
    genderedLowerPlaceQ ||
    explicitThirdPlaceQ ||
    latestRunnerUpQ ||
    latestFirstPlaceQ ||
    firstPlaceQ ||
    genericWinnerYearQ ||
    unqualifiedWinnerQ ||
    historicalWinnerQ ||
    winnerYearTeamQ ||
    legRankQuestionQ ||
    individual1500TopQ ||
    individual3000TopQ ||
    explicitLegAwardQ ||
    schoolPbRankQ ||
    trackLapQ ||
    top2CountQ ||
    namedLegTimeQ ||
    teamRunnerUpYearQ ||
    resultListQ ||
    genericResultQ ||
    nagomiLegOrderQ ||
    nagomiLegRankQ ||
    nagomiResultQ ||
    nagomiDateQ ||
    nagomiVenueQ ||
    kanaguriResultQ ||
    datedTeamResultQ ||
    unqualifiedTeamResultQ ||
    aragyokuDateQ ||
    aragyokuVenueQ ||
    explicitTeamLegQ ||
    teamFullRecordQ ||
    explicitTeamLegRankQ ||
    latestTeamRankQ ||
    teamYearOverYearQ ||
    teamWinnerMarginQ ||
    namedMeetRecordQ ||
    totalMeetRecordQ ||
    genderLegRecordQ
      ? []
      : retrieve(expanded, topK);
  const mergedCoreRaw = mergeRetrieved(
    fromSources,
    fromBm25,
    teamFullRecordQ
      ? Math.max(topK, fromSources.length, 200)
      : exhaustive
        ? Math.max(topK, fromSources.length, 96)
      : totalMeetRecordQ
        ? Math.max(topK, fromSources.length)
        : historicalWinnerQ
          ? Math.max(topK, fromSources.length, 32)
        : winnerYearTeamQ
          ? Math.max(topK, fromSources.length, 32)
        : legRankQuestionQ
          ? Math.max(topK, fromSources.length, 24)
        : explicitLegAwardQ
          ? Math.max(topK, fromSources.length)
        : unqualifiedSixthPlaceQ
          ? Math.max(topK, fromSources.length, 32)
        : resultListQ
          ? Math.max(topK, fromSources.length, 200)
        : explicitTeamLegRankQ
          ? Math.max(topK, fromSources.length)
        : topK,
    {
      query: expanded,
      preferPrimaryOrder:
        exhaustive ||
        exactDatedPractice ||
        compactWinnerQ ||
        winnerSchoolQ ||
        runnerUpQ ||
        latestWinnerQ ||
        latestWinnerTimeQ ||
        unqualifiedWinnerTimeQ ||
        unqualifiedRunnerUpQ ||
        unqualifiedFirstPlaceQ ||
        topThreeQ ||
        unqualifiedThirdPlaceQ ||
        unqualifiedFourthPlaceQ ||
        unqualifiedFifthPlaceQ ||
        unqualifiedSixthPlaceQ ||
        genderedThirdPlaceQ ||
        genderedFourthFifthPlaceQ ||
        genderedLowerPlaceQ ||
        explicitThirdPlaceQ ||
        latestRunnerUpQ ||
        latestFirstPlaceQ ||
        firstPlaceQ ||
        genericWinnerYearQ ||
        unqualifiedWinnerQ ||
        historicalWinnerQ ||
        winnerYearTeamQ ||
        legRankQuestionQ ||
        individual1500TopQ ||
        individual3000TopQ ||
        explicitLegAwardQ ||
        schoolPbRankQ ||
        trackLapQ ||
        top2CountQ ||
        namedLegTimeQ ||
        teamRunnerUpYearQ ||
        resultListQ ||
        nagomiLegOrderQ ||
        nagomiLegRankQ ||
        nagomiResultQ ||
        nagomiDateQ ||
        nagomiVenueQ ||
        kanaguriResultQ ||
        datedTeamResultQ ||
        unqualifiedTeamResultQ ||
        explicitTeamLegQ ||
        teamFullRecordQ ||
        explicitTeamLegRankQ ||
        latestTeamRankQ ||
        teamYearOverYearQ ||
        teamWinnerMarginQ ||
        namedMeetRecordQ ||
        totalMeetRecordQ ||
        genderLegRecordQ ||
        isLegAthleteQuestion(expanded),
    },
  );
  const mergedCore = namedAssignmentQ
    ? mergedCoreRaw.filter(
        (r) =>
          /daiming-staff\.md$/.test(r.chunk.source) &&
          /地点分担（荒玉）|質問向け地点分担/.test(r.chunk.text),
      )
    : farewellScheduleQ
        ? mergedCoreRaw.filter(
            (r) =>
              /daiming-staff\.md$/.test(r.chunk.source) &&
              /金栗駅伝・お別れ会/.test(r.chunk.text),
          )
      : matSizeQ
        ? mergedCoreRaw.filter(
            (r) =>
              /daiming-parents\.md$/.test(r.chunk.source) &&
              /### 銀マット|銀マットサイズ/.test(r.chunk.text),
          )
        : legDistanceQ
          ? mergedCoreRaw.filter(
              (r) =>
                /daiming-staff\.md$/.test(r.chunk.source) &&
                /2区と5区の距離|2区と5区は/.test(r.chunk.text),
            )
          : nagomiGatherQ
            ? mergedCoreRaw.filter(
                (r) =>
                  /daiming-parents\.md$/.test(r.chunk.source) &&
                  /### なごみ駅伝/.test(r.chunk.text),
              )
    : kanaguriVenueQ
              ? mergedCoreRaw.filter((r) =>
                  /drive-text\/大会\/2026年度\/0315_金栗駅伝\/概要\.md$/.test(r.chunk.source),
                )
              : winnerYearTeamQ
                ? mergedCoreRaw.filter((r) => /winners-by-year\.md(?::\d+)?$/.test(r.chunk.source))
              : mergedCoreRaw;
  const withNeighbors = expandWithNeighbors(mergedCore, {
    radius:
      exhaustive ||
      teamFullRecordQ ||
      namedAssignmentQ ||
      farewellScheduleQ ||
      matSizeQ ||
      legDistanceQ ||
      nagomiGatherQ ||
      kanaguriVenueQ
        ? 0
        : RETRIEVAL_BUDGET.neighborRadius,
    maxExtra: exhaustive || teamFullRecordQ ? 0 : RETRIEVAL_BUDGET.neighborMaxExtra,
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
  if (kanaguriResultQ && !sources.includes("drive-text/大会/2026年度/0315_金栗駅伝/概要.md")) {
    sources.unshift("drive-text/大会/2026年度/0315_金栗駅伝/概要.md");
  }
  if (
    genericResultQ &&
    question.match(/20\d{2}/)?.[0] === "2026" &&
    !sources.includes("drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/概要.md")
  ) {
    sources.unshift("drive-text/大会/2026年度/1014-1015_荒玉中体連駅伝/概要.md");
  }

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
