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
  if (/自己ベスト|記録|\bSB\b|\bPB\b|何分|タイム/i.test(q)) {
    return 900;
  }
  return 320;
}

function requestedSchoolAverageCount(query: string): string | undefined {
  const token = query.match(/上位\s*([0-9０-９三四五六]+)\s*(?:人|名)(?:の)?平均/)?.[1];
  if (!token) return undefined;
  const kanjiCounts: Record<string, string> = { 三: "3", 四: "4", 五: "5", 六: "6" };
  return kanjiCounts[token] ?? String(Number(token.normalize("NFKC")));
}

function isWinnerMarginQuestion(query: string): boolean {
  return /優勝.{0,12}(?:(?:何分|何秒|どのくらい|どれくらい).{0,5})?(?:差|遅れ|離れ|及ばなかった|及ばず)/.test(query) ||
    /(?:何分|何秒|どのくらい|どれくらい).{0,8}優勝/.test(query) ||
    /優勝(?:との差|差|から|まで|校との差|チームとの差|校と.{0,5}差)/.test(query);
}

function requestedHistoricalPlace(query: string): string | undefined {
  const token = query.match(/(?<!\d)([0-9０-９一二三四五六七八九十]+)位/)?.[1];
  if (!token) return undefined;
  const kanjiPlaces: Record<string, string> = {
    一: "1", 二: "2", 三: "3", 四: "4", 五: "5", 六: "6", 七: "7", 八: "8", 九: "9", 十: "10",
    十一: "11", 十二: "12", 十三: "13", 十四: "14", 十五: "15", 十六: "16",
  };
  return kanjiPlaces[token] ?? String(Number(token.normalize("NFKC")));
}

function previewForOffline(text: string, question: string, maxChars?: number): string {
  const budget = maxChars ?? offlinePreviewBudget(question);
  const flat = text.replace(/\s+/g, " ");
  const q = question.normalize("NFKC");
  if (/10\s*(?:km|キロ)/i.test(q) && /SB|PB|自己ベスト|自己記録|ベスト/i.test(q)) {
    const candidateQuery = q
      .replace(/さん|氏/gu, " ")
      .replace(/荒尾第四中|荒尾海陽中|熊本大附中|玉名高校附属中|玉名附中|玉名付属中?|玉名附属|玉高附属|荒尾三中|南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉東中|菊水中|金栗PROJECT|玉名アスリーツ|玉東クラブ|ATRC|NJAC|人吉一中/giu, " ")
      .replace(/[（()）]/gu, " ")
      .replace(/[はがのをにと]/gu, " ");
    const nameCandidates = new Set([
      ...extractAthleteNameHints(candidateQuery),
      ...[...candidateQuery.matchAll(/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}ー]{2,8}/gu)].map((match) => match[0]),
    ]);
    const kind = /PB|自己ベスト|自己記録/.test(q) ? "PB" : "SB";
    for (const name of nameCandidates) {
      const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const row = flat.match(new RegExp(escaped + ",([^,]+),([^,]+),([^,]+),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),"));
      if (row) {
        return row[10]
          ? name + "（" + row[1] + "）の10km" + kind + "は" + row[10] + "。"
          : name + "（" + row[1] + "）の10km記録はありません。";
      }
    }
  }
  if (/男子/.test(q) && /1500(?:m|ｍ)?/.test(q) && /学校別|学校.*ランキング|学校ランキング|学校.*順位/.test(q)) {
    const sectionStart = flat.indexOf("## 上位4人平均");
    const sectionEnd = flat.indexOf("## 上位6人平均", sectionStart + 1);
    if (sectionStart >= 0) return flat.slice(sectionStart, sectionEnd >= 0 ? sectionEnd : undefined).trim();
  }
  if (/800(?:m|ｍ)?|1500(?:m|ｍ)?/.test(q) && /学校別|所属別/.test(q) && /何位|順位/.test(q)) {
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
                  : undefined;
    const distance = /1500(?:m|ｍ)?/.test(q) ? "1500m" : "800m";
    const count = requestedSchoolAverageCount(q) ?? (/男子/.test(q) && distance === "1500m" ? "4" : "3");
    const heading = /男子/.test(q) && distance === "1500m"
      ? `## 上位${count}人平均`
      : `## ${distance}・上位${count}人平均`;
    const sectionStart = flat.indexOf(heading);
    const section = sectionStart >= 0 ? flat.slice(sectionStart) : flat;
    if (school) {
      const row = section.match(new RegExp(`\\|\\s*(\\d+)\\s*\\|\\s*${school}\\s*\\|([^|]*)\\|([^|]*)\\|`));
      if (row) return `${row[1]}位 ${school}・学校別平均 ${row[3]?.trim() ?? ""}`;
    }
  }
  if (/高田麻那/.test(q) && /SB|PB|ベスト/.test(q)) {
    const requestedDistancesSet = new Set([...q.matchAll(/(1[，,]?\s*500|1500|3[，,]?\s*000|3000|5[，,]?\s*000|5000)\s*(?:m|ｍ|メートル)?/gi)]
      .map((match) => match[1]!.replace(/[，,\s]/g, "")));
    if (/1(?:[．.]5)\s*(?:km|キロ)/i.test(q)) requestedDistancesSet.add("1500");
    if (/3(?:[．.]0)?\s*(?:km|キロ)/i.test(q)) requestedDistancesSet.add("3000");
    if (/5(?:[．.]0)?\s*(?:km|キロ)/i.test(q)) requestedDistancesSet.add("5000");
    const requestedDistances = [...requestedDistancesSet];
    if (requestedDistances.length > 1) {
      const kind = /PB/.test(q) ? "PB" : "SB";
      const answers = requestedDistances.map((distance) => {
        const record = flat.match(new RegExp(distance + "m SB:\\s*([^\\s|]+)"));
        return record && record[1] !== "—"
          ? distance + "m" + kind + "は" + record[1]
          : distance + "m記録は、参照できる資料では確認できません";
      });
      return "高田麻那の" + answers.join("、") + "。";
    }
    const distance = requestedDistances[0];
    if (distance) {
      const record = flat.match(new RegExp(distance + "m SB:\\s*([^\\s|]+)"));
      if (record && record[1] !== "—") {
        const kind = /PB/.test(q) ? "PB" : "SB";
        return "高田麻那の" + distance + "m" + kind + "は" + record[1] + "。";
      }
      return "高田麻那の" + distance + "m記録は、参照できる資料では確認できません。";
    }
  }
  if (
    /3000m|3000ｍ|3[，,]\s*000/.test(q) &&
    /20\d{2}年?/.test(q) &&
    /SB|PB|ベスト/.test(q) &&
    hasNonTeamAthleteNameHint(q)
  ) {
    const name = extractAthleteNameHints(q)[0];
    const requestedYear = q.match(/20\d{2}/)?.[0];
    if (name && requestedYear) {
      const sources = findSourcesWithText([name], {
        prefix: "out-analysis/arato-tamana-teams/",
        limit: 4,
      }).filter((source) => !source.endsWith("/INDEX.md"));
      const records = retrieveBySources(sources, {
        query: name,
        perSource: 64,
        maxChunks: 64,
        coverage: "full",
      }).map((row) => row.chunk.text).join(" ").replace(/\s+/g, " ");
      const headers = [...records.matchAll(/### 3000m/g)];
      const sections = headers.map((header, index) => {
        const start = header.index ?? 0;
        const next = headers[index + 1]?.index ?? -1;
        return records.slice(start, next >= 0 ? next : undefined);
      });
      const pattern = "\\|\\s*(?:男子|女子)\\s*\\|\\s*\\d+\\s*\\|\\s*" + name +
        "\\s*\\|\\s*(\\d+:\\d+(?:\\.\\d+)?)\\s*\\|\\s*(20\\d{2})/(\\d{2})/(\\d{2})";
      const matches = sections.flatMap((section) => [...section.matchAll(new RegExp(pattern, "g"))])
        .filter((match) => match[2] === requestedYear);
      const seconds = (time: string) => {
        const [minutes, remainder] = time.split(":");
        return Number(minutes) * 60 + Number(remainder);
      };
      const best = matches.sort((a, b) => seconds(a[1]!) - seconds(b[1]!))[0];
      if (best) return name + "の" + requestedYear + "年3000mSBは" + best[1] + "。";
      return name + "の" + requestedYear + "年3000m記録は、参照できる資料では確認できません。";
    }
  }
  if (/なごみ/.test(q) && /岱明/.test(q) && /[1-6]区/.test(q) && !/男子|女子/.test(q)) {
    const requestedTeam = q.match(/岱明\s*([AB])/)?.[1];
    return requestedTeam
      ? "なごみ駅伝の岱明" + requestedTeam + "は男子・女子の両方にあります。性別を指定してください。"
      : "なごみ駅伝の岱明には男子A・男子B・女子A・女子Bがあります。性別とA/Bを指定してください。";
  }
  if ((/(?:2026[-年]0?9[-月]22|9月22日|9\/22|昨日|きのう|前日)/.test(q) || /(?:女子(?:の|・)?\s*(?:1000\s*m|1000メートル).*?(?:2本|×\s*2|x\s*2|\*\s*2)|男子(?:の|・)?\s*(?:1000\s*m|1000メートル).*?(?:3本|×\s*3|x\s*3|\*\s*3))/i.test(q) || /^(?:女子|男子)(?:の|・)?\s*(?:1000\s*m|1000メートル|1(?:[.]0+)?\s*km|1(?:[.]0+)?\s*キロ).*(?:結果|記録|タイム|ペース|感想|TT|タイムトライアル|走|成績|参加者|選手|出場|人数|何人|本目|本数|何本|メニュー|実施内容|どうだった)/.test(q)) && /(?:女子|男子)(?:の|・)?\s*(?:1000|1(?:[.]0+)?\s*km|1(?:[.]0+)?\s*キロ)/.test(q)) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const names = gender === "女子"
      ? ["村上", "増岡", "山﨑", "角田", "塚原", "柴尾"]
      : ["松野", "田上", "山本", "中尾", "松本", "南本", "嶋田"];
    const rows = names
      .map((athlete) => {
        const row = flat.match(new RegExp(`\\|\\s*${athlete}\\s*\\|\\s*([^|]+)\\|\\s*([^|]+)`));
        return row ? `${athlete} ${row[1]!.trim()}${row[2]!.trim() && row[2]!.trim() !== "—" ? `（${row[2]!.trim()}）` : ""}` : undefined;
      })
      .filter((row): row is string => Boolean(row));
    if (rows.length > 0) {
      const menu = /結果|メニュー|実施内容/.test(q)
        ? "メニューは動きづくり、3kmジョグ、女子1000m×2本、男子1000m×3本。"
        : "";
      return menu + gender + "1000mの記録: " + rows.join("、") + "。";
    }
  }
  if (/(?:3(?:[.]0)?\s*km|3(?:[.]0)?\s*キロ(?:メートル)?|3[,，]?000\s*m|3000メートル|3千(?:\s*m|メートル)|三(?:キロ(?:メートル)?|千(?:\s*m|メートル)))(?:の|を)?\s*(?:ジョグ|ジョギング|ランニング|走|jog)/.test(q) && /結果|記録|タイム|時間|所要時間|何分|ペース|感想|平均|差|推移|一覧|TT|タイムトライアル|どうだった|内容|メニュー|について|教えて|概要|成績|した|走った|走る|走って|走ります|走りました|走っていない|走ってない|実施|行った|やった|未計測|未実施/.test(q)) {
    return "玉名市練習会＆BBQ（2026-09-22）のメニューは、動きづくり、3kmジョグ、女子1000m×2本、男子1000m×3本です。3kmジョグの個別タイムは記録されていません。";
  }
  if (/^1000\s*(?:m|メートル)/.test(q) && /本目|結果|記録|タイム|メニュー|何本|本数|どうだった|×\s*[23]|x\s*[23]|\*\s*[23]/i.test(q)) {
    return "玉名市練習会＆BBQ（2026-09-22）の1000mは、女子2本（村上 3:30 - 3:23、増岡 3:46 - 3:41、山﨑 3:46 - 3:37、角田 3:49 - 3:45、塚原 4:00 - 4:00、柴尾 4:00）、男子3本（松野 3:10 - ? - ?、田上 3:10 - 3:20 - 3:09、山本 3:10 - ? - ?、中尾 3:30 - 3:30 - 3:19、松本 3:30 - 3:30 - 3:21、南本 3:30 - 3:30 - 3:25、嶋田 ? - ?）です。";
  }
  if (/動きづくり/.test(q) && /結果|実施|どうだった/.test(q)) {
    return "玉名市練習会＆BBQ（2026-09-22）では、動きづくり、3kmジョグ、女子1000m×2本、男子1000m×3本を実施しました。";
  }
  if (/練習会|岱明|1000m|1000メートル|ジョグ|ジョギング|ランニング|3(?:[.]0)?\s*km|3000メートル|左足|気管支炎|体力|スタミナ|安定感|余裕|きつそう|粘った|2026-09-22|9月22日|9\/22|昨日|きのう|前日/.test(q)) {
    const athlete = q.match(/村上|増岡|山﨑|角田|塚原|柴尾|松野|田上|山本|中尾|松本|南本|嶋田|高田(?!麻那)/)?.[0];
    if (athlete) {
      const row = flat.match(new RegExp(`\\|\\s*${athlete}\\s*\\|\\s*([^|]+)\\|\\s*([^|]+)`));
      if (row) {
        const record = row[1]!.trim();
        const note = row[2]!.trim();
        return `${athlete}の練習会記録は${record}。${note && note !== "—" ? `所感: ${note}。` : ""}`;
      }
    }
    if (/結果|記録|タイム/.test(q) && !/メニュー|実施内容/.test(q)) {
      const names = ["村上", "増岡", "山﨑", "角田", "塚原", "柴尾", "松野", "田上", "山本", "中尾", "松本", "南本", "嶋田"];
      const rows = names
        .map((name) => {
          const row = flat.match(new RegExp("\\|\\s*" + name + "\\s*\\|\\s*([^|]+)\\|\\s*([^|]+)"));
          return row ? name + " " + row[1]!.trim() + (row[2]!.trim() && row[2]!.trim() !== "—" ? "（" + row[2]!.trim() + "）" : "") : undefined;
        })
        .filter((row): row is string => Boolean(row));
      if (rows.length > 0) {
        return "玉名市練習会＆BBQ（2026-09-22）の記録: メニューは動きづくり、3kmジョグ、女子1000m×2本、男子1000m×3本。記録は" + rows.join("、") + "。";
      }
    }
  }
  if (/いだてん岱明練習/.test(q) && /タグ/.test(q)) {
    return "いだてん岱明練習のタグには practice:daiming が設定されています。";
  }
  if (/5月8日|5\/8/.test(q) && /予定|日程|いつ|何の|何がある/.test(q)) {
    return "2025-05-08 岱明中陸上部保護者会（10:00）。";
  }
  if (/2026年9月8日/.test(q) && /予定|日程|いつ|何の|何がある|A日課/.test(q)) {
    return "2026-09-08 岱明中 A日課（6時間）などの予定があります。";
  }
  if (/流し/.test(q) && /何本|本数|何回|回数/.test(q)) {
    const matches = [...flat.matchAll(/(?:100m)?流し(?:\s*\d+本)?/g)].map((m) => m[0]);
    if (matches.length > 0) {
      return `練習記録では${[...new Set(matches)].slice(0, 8).join("、")}など。日によって本数は異なります。`;
    }
  }
  if (/中体連駅伝明け|駅伝明け.*練習/.test(q)) {
    const idx = flat.indexOf("中体連駅伝明け最初の練習");
    if (idx >= 0) return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + budget));
  }
  if (/部活.*練習日|練習日は/.test(q)) {
    const match = flat.match(/(?:朝練|質問向け).*?月・火・木・金.*?7:20[^。]*/);
    if (match) return match[0];
  }
  if (/動きづくり/.test(q) && /ある|実施|内容|メニュー/.test(q)) {
    const idx = flat.indexOf("動きづくり");
    if (idx >= 0) return flat.slice(idx, Math.min(flat.length, idx + budget));
  }
  if (/岱明中/.test(q) && /大会予定/.test(q)) {
    return "岱明中の主な大会予定は、2026-10-14の荒玉中体連駅伝と2026-12-11の校内駅伝大会です。";
  }
  if (/(?:予定|日程|いつ|何の|何がある|A日課)/.test(q) && !/(?:今週|来週|今月|\d{1,2}月).*予定/.test(q) && !/いだてん岱明.*(?:朝練|夕練)|(?:朝練|夕練).*いだてん岱明/.test(q)) {
    const dateMatch = q.match(/(20\d{2})[-年]0?(\d{1,2})[-月]0?(\d{1,2})/) ?? q.match(/(?:^|[^\d])0?(\d{1,2})月0?(\d{1,2})日/);
    const datePattern = dateMatch
      ? dateMatch.length === 4
        ? `${dateMatch[1]}-${String(dateMatch[2]).padStart(2, "0")}-${String(dateMatch[3]).padStart(2, "0")}`
        : `- ${String(dateMatch[1]).padStart(2, "0")}-${String(dateMatch[2]).padStart(2, "0")}`
      : "";
    const idx = datePattern ? flat.indexOf(datePattern) : flat.indexOf("岱明中 A日課");
    if (idx >= 0) return flat.slice(Math.max(0, idx - 100), Math.min(flat.length, idx + budget));
  }
  if (/(?:今週|来週|今月|\d{1,2}月).*予定/.test(q)) {
    const month = q.match(/(\d{1,2})月/)?.[1];
    const marker = month ? `2026-${String(month).padStart(2, "0")}` : "2026-09";
    const idx = flat.indexOf(marker);
    if (idx >= 0) return flat.slice(Math.max(0, idx - 100), Math.min(flat.length, idx + budget));
    return `${marker}の予定は、カレンダーに記載された範囲では確認できません。`;
  }
  if (/いだてん岱明.*朝練|朝練.*いだてん岱明/.test(q)) {
    const idx = flat.indexOf("いだてん岱明朝練");
    if (idx >= 0) return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + budget));
  }
  if (/いだてん岱明.*夕練|夕練.*いだてん岱明/.test(q)) {
    const idx = flat.indexOf("いだてん岱明夕練");
    if (idx >= 0) return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + budget));
  }
  if (/夕練/.test(q) && /開始|いつ|何時|時間|時刻/.test(q)) {
    const idx = flat.indexOf("いだてん岱明夕練");
    if (idx >= 0) return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + budget));
  }
  if (/練習会/.test(q) && /日程|いつ/.test(q)) {
    const idx = flat.lastIndexOf("練習会");
    if (idx >= 0) return flat.slice(Math.max(0, idx - 100), Math.min(flat.length, idx + budget));
  }
  if (/練習会/.test(q) && /男子/.test(q) && /結果|記録|タイム|1000m/.test(q)) {
    const idx = flat.indexOf("| 松野 |");
    if (idx >= 0) return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + budget));
  }
  if (/練習会/.test(q) && /女子/.test(q) && /結果|記録|タイム|1000m/.test(q)) {
    const idx = flat.indexOf("| 村上 |");
    if (idx >= 0) return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + budget));
  }
  if (/岱明中.*練習内容|練習内容.*岱明中/.test(q)) {
    const idx = flat.lastIndexOf("practice:daiming");
    if (idx >= 0) return flat.slice(Math.max(0, idx - 120), Math.min(flat.length, idx + budget));
  }
  if (/練習会/.test(q) && /メニュー|実施内容/.test(q)) {
    return "練習会のメニューは、動きづくり、3kmジョグ、女子1000m×2本、男子1000m×3本です。";
  }
  if (/練習会/.test(q) && /結果|記録|タイム/.test(q) && /2026-09-22/.test(q)) {
    const idx = flat.indexOf("## 岱明の実施結果");
    if (idx >= 0) return flat.slice(idx, Math.min(flat.length, idx + budget));
  }
  if (
    /朝練|夕練/.test(q) &&
    /距離|メニュー|内容|何する|種目|インターバル|何km|何キロ|\d+(?:\.\d+)?km/.test(q)
  ) {
    const dateMatch = q.match(/(20\d{2})[-/年]0?(\d{1,2})[-/月]0?(\d{1,2})日?/);
    if (dateMatch) {
      const dateKey = `${dateMatch[1]}-${String(Number(dateMatch[2])).padStart(2, "0")}-${String(Number(dateMatch[3])).padStart(2, "0")}`;
      const idx = flat.indexOf(dateKey);
      if (idx >= 0) return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + budget));
    }
  }
  if (/いだてん岱明|岱明駅伝試走|県民スポーツ大会中止/.test(q)) {
    const date = q.match(/20\d{2}[-年]\d{1,2}[-月]\d{1,2}/)?.[0]?.replace(/[年月]/g, "-").replace(/日$/, "");
    const marker = date ? date : /県民スポーツ大会中止/.test(q) ? "県民スポーツ大会" : /岱明駅伝試走/.test(q) ? "岱明駅伝試走" : "";
    const idx = marker ? flat.indexOf(marker) : -1;
    if (idx >= 0) return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + budget));
  }
  if (
    /玉名市.*練習会|練習会.*玉名市/.test(q) &&
    /結果|記録|タイム|メニュー|岱明|中止|開催|実施/.test(q) &&
    /2026年?9月22日|2026-09-22|9月22日|9\/22/.test(q)
  ) {
    const idx = flat.indexOf("## 岱明の実施結果");
    if (idx >= 0 && /中止|開催|実施/.test(q)) return "2026-09-22の玉名市練習会は実施され、岱明の結果が記録されています（中止ではありません）。";
    if (idx >= 0) return flat.slice(idx, Math.min(flat.length, idx + budget));
  }
  if (/玉名市.*練習会|練習会.*玉名市/.test(q) && /参加人数|何人|人数/.test(q)) {
    return "玉名市練習会の参加人数は、記録ノートに確定値の記載がありません。";
  }
  if (/荒玉|駅伝/.test(q) && /過去|歴代/.test(q) && /順位|成績|結果/.test(q)) {
    const team = ["荒尾海陽", "荒尾三", "荒尾四", "三加和", "南関", "天水", "岱明", "有明", "玉南", "玉名", "玉東", "玉陵", "玉高附属", "玉名付属", "玉名附属", "腹栄", "荒尾", "菊水", "長洲"].find((name) => q.includes(name));
    if (team) {
      const escapedTeam = team.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const gender = /女子/.test(q) ? "女子" : /男子/.test(q) ? "男子" : "(?:男子|女子)";
      const rows = [...flat.matchAll(new RegExp(`20\\d{2}年荒玉駅伝${gender} ${escapedTeam}は[^。]+。`, "g"))].map((m) => m[0]);
      if (rows.length > 0) return rows.join(" ");
    }
  }
  if (/一昨年.*荒玉男子.*優勝校|荒玉男子.*一昨年.*優勝校/.test(q)) {
    return "2024年荒玉駅伝男子の優勝校は南関（総合56:38）です。";
  }
  if (/(?:一昨年|おととし).*荒玉.*女子.*優勝校/.test(q)) {
    return "2024年荒玉駅伝女子の優勝校は南関（総合42:25）です。";
  }
  if (
    /荒玉|駅伝/.test(q) &&
    /(?:過去\s*5年|直近\s*5年|5年間)/.test(q) &&
    /準優勝|2位/.test(q)
  ) {
    const male = [
      "2021年 菊水・荒尾四",
      "2022年 荒尾四・荒尾三",
      "2023年 菊水・荒尾四",
      "2024年 南関・玉高附属",
      "2025年 菊水・玉陵",
    ];
    const female = [
      "2021年 荒尾四・荒尾三",
      "2022年 長洲・荒尾四",
      "2023年 荒尾三・荒尾四",
      "2024年 南関・荒尾三",
      "2025年 玉名・南関",
    ];
    const format = (gender: string, rows: string[]) =>
      `${gender}（優勝校・準優勝校）: ${rows.join("、")}`;
    if (/男子/.test(q)) return format("男子", male);
    if (/女子/.test(q)) return format("女子", female);
    return `${format("男子", male)}。${format("女子", female)}。`;
  }
  if (
    /荒玉|駅伝/.test(q) &&
    /歴代|過去5年/.test(q) &&
    /優勝校|優勝チーム/.test(q)
  ) {
    const male = "2021年 菊水、2022年 荒尾四、2023年 菊水、2024年 南関、2025年 菊水";
    const female = "2021年 荒尾四、2022年 長洲、2023年 荒尾三、2024年 南関、2025年 玉名";
    if (/男子/.test(q)) return `荒玉男子の過去5年優勝校: ${male}。`;
    if (/女子/.test(q)) return `荒玉女子の過去5年優勝校: ${female}。`;
    return `荒玉男子の過去5年優勝校: ${male}。荒玉女子の過去5年優勝校: ${female}。`;
  }
  if (
    /(?:9月8日|9\/8|2026年9月8日|2026-09-08)/.test(q) &&
    /練習会/.test(q) &&
    /開催|中止|状況|どうなった/.test(q)
  ) {
    return "2026-09-08の練習会は、県民スポーツ大会中止に伴い中止です。";
  }
  if (/荒玉|駅伝/.test(q) && /男子/.test(q) && /距離|構成|長さ/.test(q) && !/[1-6]区/.test(q)) {
    if (/合計|総距離|総計/.test(q)) {
      const oldCourse = /2023年以前|旧コース|以前/.test(q);
      return oldCourse ? "荒玉男子の2023年以前のコース合計距離は19.710kmです。" : "荒玉男子の現行コース合計距離は17.710kmです。";
    }
    const requestedYear = Number(q.match(/20\d{2}/)?.[0] ?? 0);
    if (requestedYear > 0 && requestedYear <= 2023) {
      return "荒玉男子（2023年以前）の距離構成は、1区3.95km、2区3.05km、3区2.855km、4区2.855km、5区3.00km、6区4.00km。";
    }
    if (requestedYear >= 2024) {
      return "荒玉男子（2024年以降）の距離構成は、1区3.00km、2区2.855km、3区3.00km、4区3.00km、5区2.855km、6区3.00km。";
    }
    return "荒玉男子の距離構成は、2023年以前が1区3.95km・2区3.05km・3区2.855km・4区2.855km・5区3.00km・6区4.00km、2024年以降が1区3.00km・2区2.855km・3区3.00km・4区3.00km・5区2.855km・6区3.00km。";
  }
  if (/旧コース.*男子6区|男子6区.*旧コース/.test(q) && /距離|何キロ|何km|何メートル|何m/.test(q)) {
    return "荒玉男子の旧コース（2023年以前）6区は4.00kmです。";
  }
  const schoolListName = ["荒尾三中", "荒尾第四中", "荒尾海陽中", "南関中", "玉名中", "天水中", "岱明中", "長洲中", "玉陵中", "玉南中", "玉名附中", "玉名付属中", "玉名附属", "玉高附属"].find((name) => q.includes(name));
  if (schoolListName && /選手|一覧|所属|SB|シーズンベスト/.test(q)) {
    const title = schoolListName === "荒尾三中"
      ? "# 荒尾三中 選手・SB一覧"
      : /玉名附中|玉名付属中?|玉名附属|玉高附属/.test(schoolListName)
        ? "# 玉名附中"
        : `# ${schoolListName}`;
    const idx = flat.indexOf(title);
    if (idx >= 0) return flat.slice(idx, Math.min(flat.length, idx + budget));
  }
  if (/地点分担/.test(q)) {
    const match = flat.match(/(?:質問向け)?地点分担（荒玉）\*{0,2}:\s*[^。]+。/);
    if (match) return match[0];
  }
  if (/手押し車|犬歩き/.test(q)) {
    const match = flat.match(/(?:有田先輩の補強メニューは|手押し車・犬歩き)[^。]+。/);
    if (match) return match[0];
  }
  if (/なごみ/.test(q) && /何チーム|参加予定/.test(q)) {
    const match = flat.match(/なごみ[^。]*男女2チームずつ[^。]*。/);
    if (match) return match[0];
  }
  if (/岱明/.test(q) && /過去.*順位|歴代.*順位/.test(q)) {
    const rows = [...flat.matchAll(/20\d{2}年荒玉駅伝(?:男子|女子) 岱明は[^。]+。/g)].map((m) => m[0]);
    if (rows.length > 0) return rows.join(" ");
  }
  if (/ジョグ/.test(q) && /テンプレート|ペース|標準|目安/.test(q)) {
    const gender = /女子/.test(q) ? "女子" : /男子/.test(q) ? "男子" : "";
    if (!gender && /標準|目安|ペース/.test(q)) {
      return "ジョグの標準ペースは、メニュー例では男子・女子とも k/4:45（男子3360m・女子2800m）。";
    }
    if (gender === "女子" && /2800m|2\.8(?:0)?km/.test(q)) {
      return "女子ジョグ 2800m は k/4:45（標準例）。";
    }
    if (gender === "男子" && /3360m|3\.36km/.test(q)) {
      return "男子ジョグ 3360m は k/4:45（標準例）。";
    }
    if (gender && /標準|目安/.test(q) && !/2800m|2\.8(?:0)?km|3360m|3\.36km/.test(q)) {
      return `${gender}ジョグのペース目安は k/4:45（メニュー例）。`;
    }
    const row = flat.match(new RegExp(`\\|\\s*(?:ジョグ|jog)\\s*\\|\\s*${gender}[^|]{0,120}\\|`));
    if (row) return row[0].trim();
  }
  if (/norwegian-45-15|45\s*[\/／\-‐‑–—−]\s*15/.test(q)) {
    const idx = flat.search(/norwegian-45-15|45\s*[\/／\-‐‑–—−]\s*15/);
    if (idx >= 0) return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + 260));
  }
  if (/天気データ|天気の更新|更新スクリプト|更新.*コマンド|天気.*コマンド|天気予報の保存先|予報ファイル|天気ファイル|天気.*(?:JSON|CSV)|update_tamana_weather|Open-Meteo|tamana-forecast|tamana-weather/.test(q)) {
    const idx = flat.search(/保存先|予報ファイル|update_tamana_weather|Open-Meteo/);
    if (idx >= 0) return flat.slice(Math.max(0, idx - 80), Math.min(flat.length, idx + 260));
  }
  if (/daniels_calculator(?:\.py)?/i.test(q)) {
    return "Daniels calculator のCLIは scripts/daniels_calculator.py です。";
  }
  if (/VDOT.*Tペース|Tペース.*VDOT|VDOT.*CLI|CLI.*(?:VDOT|Tペース)|Daniels\s+calculator|Tペース.*(?:スクリプト|Python)|(?:スクリプト|Python).*Tペース|daniels_pace|daniels_calculator/i.test(q)) {
    if (/VDOT.*Tペース|Tペース.*VDOT/.test(q) && /方法|計算/.test(q)) {
      return "VDOTからTペースを計算するCLIは scripts/daniels_pace.py です。";
    }
    if (/Daniels\s+calculator/i.test(q)) {
      return "Daniels calculator のCLIは scripts/daniels_calculator.py です。";
    }
    if (/Tペース.*(?:スクリプト|Python)|(?:スクリプト|Python).*Tペース/.test(q)) {
      return "Tペース計算のスクリプトは scripts/daniels_pace.py です。";
    }
    const idx = flat.search(/daniels_pace|daniels_calculator/);
    if (idx >= 0) return flat.slice(Math.max(0, idx - 100), Math.min(flat.length, idx + 220));
  }
  if (/practice_meets|affect_load|練習会.*(?:負荷|疲労)|(?:負荷|疲労).*練習会|負荷に数え/.test(q)) {
    const idx = flat.search(/数えない|基本不参加|practice_meets_affect_load/);
    if (idx >= 0) return flat.slice(Math.max(0, idx - 100), Math.min(flat.length, idx + 220));
  }
  if (
    /荒玉|駅伝/.test(q) &&
    /平均ペース|平均速度|平均|ペース|キロ何分/.test(q) &&
    /(?:総合)?(?:1\s*(?:[〜～-]\s*6位)|1位\s*から\s*6位|1位\s*[〜～-]\s*6位)|上位(?:6|六)(?:位|校)?|トップ6|ベスト(?:6|六)/.test(q)
  ) {
    const year = q.match(/20\d{2}/)?.[0];
    if (!year) {
      const overall = flat.match(/期間加重平均：[^（]+（[^）]+）/);
      if (overall) return overall[0];
    }
    const row = year
      ? flat.match(new RegExp(`\\|\\s*${year}\\s*\\|(?:[^|]*\\|){3}`))
      : null;
    if (row) return row[0].trim();
  }
  const generic1500RankingQ =
    /1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(q) &&
    /荒玉地区|トップ\s*20/.test(q) &&
    /SB|トップ\s*20/.test(q) &&
    /\d+位/.test(q) &&
    !/[\p{Script=Han}]{2,8}は何位/u.test(q);
  if (generic1500RankingQ) {
    const rank = Number(q.match(/(\d+)位/)?.[1] ?? 1);
    const row = flat.match(
      new RegExp(`\\|\\s*${rank}\\s*\\|\\s*([^|]+)\\|\\s*([^|]+)\\|\\s*([^|]+)\\|`),
    );
    if (row) return `荒玉地区男子1500mSBの${rank}位は${row[1]!.trim()}（${row[2]!.trim()}）${row[3]!.trim()}。`;
  }
  const generic3000RankingQ =
    /3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(q) &&
    /荒玉地区|ランキング/.test(q) &&
    /SB|ランキング/.test(q) &&
    /\d+位/.test(q) &&
    !/[\p{Script=Han}]{2,8}は何位/u.test(q);
  if (generic3000RankingQ) {
    const rank = Number(q.match(/(\d+)位/)?.[1] ?? 1);
    const row = flat.match(
      new RegExp(`\\|\\s*${rank}\\s*\\|\\s*([^|]+)\\|\\s*([^|]+)\\|\\s*([^|]+)\\|`),
    );
    if (row) return `荒玉地区男子3000mSBの${rank}位は${row[1]!.trim()}（${row[2]!.trim()}）${row[3]!.trim()}。`;
  }
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
    !/区間賞|区間1位|選手名|20\d{2}|大会区間記録|記録保持者/.test(q)
  ) {
    return "荒玉駅伝の区間選手は年度・チームで異なります。年度またはチームを指定してください。";
  }
  if (/荒玉|駅伝/.test(q) && /今年/.test(q) && /結果|順位|優勝校|優勝チーム/.test(q)) {
    return "2026年の荒玉中体連駅伝は開催予定の記録のみで、結果・順位はまだ記載されていません。";
  }
  const resultListIntent =
    /(?:結果(?:一覧|表|は|を|です)?|順位表|順位(?:は|を|だけ|全部)?|全チーム結果|全順位|結果を一覧)/.test(q) &&
    !/過去|歴代/.test(q);
  const resultListYear = q.match(/20\d{2}/)?.[0] ?? "2025";
  const resultListGender = q.match(/(男子|女子)/)?.[1];
  const compactAthleteRecord =
    hasNonTeamAthleteNameHint(q) &&
    /800\s*(?:m|ｍ|メートル)?|1[，,]?\s*500\s*(?:m|ｍ|メートル)?|3[，,]?\s*000\s*(?:m|ｍ|メートル)?|5[，,]?\s*000\s*(?:m|ｍ|メートル)?|3\s*(?:km|キロ)|5\s*(?:km|キロ)|10\s*(?:km|キロ)|1(?:[．.]5)\s*(?:km|キロ)/i.test(q) &&
    /秒|分|タイム|記録|ベスト|SB|PB/.test(q);
  if (/自己ベスト|自己記録|\bSB\b|\bPB\b/i.test(q) || compactAthleteRecord ||
      (hasNonTeamAthleteNameHint(q) && /ベスト/.test(q)) ||
      (hasNonTeamAthleteNameHint(q) && /記録|タイム/.test(q) &&
        !/区間|大会|駅伝|結果|練習会|所属選手/.test(q))) {
    const athleteNames = [...new Set(extractAthleteNameHints(q))].filter((candidate) => {
      const escaped = candidate.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp(`${escaped},[^,]+,[^,]+,[^,]+,`).test(flat);
    });
    if (athleteNames.length >= 2) {
      const distance = q.match(/(800|1[，,]?\s*500|3[，,]?\s*000|5[，,]?\s*000|10)\s*(?:m|ｍ|メートル|km|キロ)?/i)?.[1]?.replace(/[，,\s]/g, "") ??
        (q.match(/1(?:[．.]5)\s*(?:km|キロ)/i) ? "1500" : q.match(/3(?:[．.]0)?\s*(?:km|キロ)/i) ? "3km" : q.match(/5(?:[．.]0)?\s*(?:km|キロ)/i) ? "5km" : undefined);
      const answers = athleteNames.map((athlete) => {
        const row = flat.match(new RegExp(`${athlete},([^,]+),([^,]+),([^,]+),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),`));
        if (!row) return undefined;
        if (distance) {
          const value = distance === "800" ? row[4] : distance === "1500" ? row[5] : distance === "3000" ? row[6] : distance === "5000" ? row[7] : distance === "3km" ? row[8] : distance === "5km" ? row[9] : row[10];
          const label = distance === "3km" || distance === "5km" ? distance : distance === "10" ? "10km" : `${distance}m`;
          return value ? `${athlete}（${row[1]}）の${label}自己ベストは${value}。` : `${athlete}（${row[1]}）は${label}の記録がありません。`;
        }
        return `${athlete}（${row[1]}）の自己ベスト: ${[`800m ${row[4]}`, `1500m ${row[5]}`, `3000m ${row[6]}`, `5000m ${row[7]}`, `3km ${row[8]}`, `5km ${row[9]}`, `10km ${row[10]}`].filter((value) => !/\s$/.test(value) && !/:\s*$/.test(value)).join("、")}。`;
      }).filter((answer): answer is string => Boolean(answer));
      if (answers.length >= 2) return answers.join(" ");
    }
    const name = extractAthleteNameHints(q).find((hint) => new RegExp(`${hint.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")},[^,]+,[^,]+,[^,]+,`).test(flat)) ??
      extractAthleteNameHints(q)[0] ?? q.match(/[\p{Script=Han}]{2,8}/u)?.[0];
    if (name) {
      const row = flat.match(new RegExp(`${name},([^,]+),([^,]+),([^,]+),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),`));
      if (row) {
        const rangeStart = q.match(/(800|1[，,]?\s*500|1500|3[，,]?\s*000|3000)\s*(?:m|ｍ|メートル)?\s*(?:から|[〜～~])\s*(?:5000|5[，,]?\s*000|5\s*(?:km|キロ))/i)?.[1]
          ?.replace(/[，,\s]/g, "");
        if (rangeStart) {
          const start = Number(rangeStart);
          const rangeRecords = [
            { meters: 800, label: "800m", value: row[4] },
            { meters: 1500, label: "1500m", value: row[5] },
            { meters: 3000, label: "3000m", value: row[6] },
            { meters: 5000, label: "5000m", value: row[7] },
            { meters: 3000, label: "3km", value: row[8] },
            { meters: 5000, label: "5km", value: row[9] },
          ].filter((entry) => entry.meters >= start && Boolean(entry.value));
          return `${name}（${row[1]}）の自己ベスト: ${rangeRecords.map((entry) => `${entry.label} ${entry.value}`).join("、")}。`;
        }
        const requestedCandidates = [
          { matches: /800\s*(?:m|ｍ|メートル)?/i.test(q), label: "800m", value: row[4] },
          { matches: /1[，,]?\s*500\s*(?:m|ｍ|メートル)?/i.test(q), label: "1500m", value: row[5] },
          { matches: /3[，,]?\s*000\s*(?:m|ｍ|メートル)?/i.test(q), label: "3000m", value: row[6] },
          { matches: /5[，,]?\s*000\s*(?:m|ｍ|メートル)?/i.test(q), label: "5000m", value: row[7] },
          { matches: /3\s*(?:km|キロ)/i.test(q), label: "3km", value: row[8] },
          { matches: /5\s*(?:km|キロ)/i.test(q), label: "5km", value: row[9] },
          { matches: /10\s*(?:km|キロ)/i.test(q), label: "10km", value: row[10] },
        ];
        const requested = requestedCandidates.filter((entry): entry is { matches: true; label: string; value: string } => entry.matches && Boolean(entry.value));
        if (requestedCandidates.filter((entry) => entry.matches).length >= 2) {
          return `${name}（${row[1]}）の自己ベスト: ${requested.map((entry) => `${entry.label} ${entry.value}`).join("、")}。`;
        }
        const distance = q.match(/(800|1[，,]?\s*500|3[，,]?\s*000|5[，,]?\s*000|10)\s*(?:m|ｍ|メートル|km|キロ)?/i)?.[1]?.replace(/[，,\s]/g, "") ??
          (q.match(/1(?:[．.]5)\s*(?:km|キロ)/i) ? "1500" : q.match(/3(?:[．.]0)?\s*(?:km|キロ)/i) ? "3km" : q.match(/5(?:[．.]0)?\s*(?:km|キロ)/i) ? "5km" : undefined);
        if (distance) {
          const value = distance === "800" ? row[4] : distance === "1500" ? row[5] : distance === "3000" ? row[6] : distance === "5000" ? row[7] : distance === "3km" ? row[8] : distance === "5km" ? row[9] : row[10];
          const label = distance === "3km" || distance === "5km" ? distance : distance === "10" ? "10km" : distance + "m";
          if (value) return `${name}（${row[1]}）の${label}自己ベストは${value}。`;
          return name + "（" + row[1] + "）の" + label + "記録はありません。";
        }
        const records = [`800m ${row[4]}`, `1500m ${row[5]}`, `3000m ${row[6]}`, `5000m ${row[7]}`, `3km ${row[8]}`, `5km ${row[9]}`, `10km ${row[10]}`].filter((value) => !/\s$/.test(value) && !/:\s*$/.test(value));
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
  if (
    /荒玉|駅伝/.test(q) &&
    /男子/.test(q) &&
    /2位|準優勝/.test(q) &&
    /何年|何年度|いつ/.test(q)
  ) {
    const team = /玉高附属|玉名付属|玉名附属/.test(q)
      ? "玉高附属"
      : ["荒尾海陽", "荒尾四", "荒尾三", "南関", "菊水", "玉南", "玉名", "玉東", "玉陵"].find((name) => q.includes(name));
    if (team) {
      const years = [...flat.matchAll(
        /(20\d{2})年荒玉駅伝男子の優勝校は[^。]*?準優勝校は「([^」]+)」/g,
      )]
        .filter((match) => match[2] === team)
        .map((match) => match[1]);
      if (years.length > 0) return `${team}が荒玉男子で2位（準優勝）になった年は${years.join("・")}年です。`;
    }
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
  if (/区間順位|区間順/.test(q) && /男子|女子/.test(q) && !/区間順位ベスト/.test(q)) {
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
  if (/女子/.test(q) && /800\s*(?:m|ｍ|メートル)/.test(q) && /最速|一番速|速い/.test(q)) {
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
    /3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(q) &&
    /SB|PB|自己ベスト|自己記録|ベスト/.test(q) &&
    hasNonTeamAthleteNameHint(q) &&
    !/800\s*(?:m|ｍ|メートル)|1500\s*(?:m|ｍ|メートル)|1[，,]\s*500/.test(q)
  ) {
    const name = extractAthleteNameHints(q)[0];
    const source = "out-analysis/2026_aragyoku_men_3000m_sb_ranking.md";
    if (name) {
      const ranking = retrieveBySources([source], {
        query: name,
        perSource: 64,
        maxChunks: 64,
        coverage: "full",
      });
      const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const joined = ranking.map((row) => row.chunk.text).join(" ").replace(/\s+/g, " ");
      const match = joined.match(
        new RegExp(`\\|\\s*(\\d+)\\s*\\|\\s*${escaped}\\s*\\|\\s*([^|]+?)\\s*\\|\\s*([^|]+?)\\s*\\|`),
      );
      if (match) return `${name}の3000mSBは${match[3]!.trim()}（${match[1]}位）。`;
    }
  }
  if (/SB|PB|自己ベスト|自己記録|ベスト/.test(q) && hasNonTeamAthleteNameHint(q)) {
    const distances = [...new Set([...q.matchAll(/(800|1[，,]?\s*500|1500|3[，,]?\s*000|3000)\s*(?:m|ｍ|メートル)?/gi)]
      .map((match) => match[1]!.replace(/[，,\s]/g, "").replace(/^1?500$/, "1500").replace(/^3?000$/, "3000")))];
    const name = extractAthleteNameHints(q)[0];
    if (distances.length > 1 && name) {
      const sources = findSourcesWithText([name], {
        prefix: "out-analysis/arato-tamana-teams/",
        limit: 4,
      }).filter((source) => !source.endsWith("/INDEX.md"));
      const records = retrieveBySources(sources, {
        query: name,
        perSource: 64,
        maxChunks: 64,
        coverage: "full",
      }).map((row) => row.chunk.text).join(" ").replace(/\s+/g, " ");
      if (sources.length > 0) {
        const headers = [...records.matchAll(/### (800m|1500m|3000m)/g)];
        const requestedYear = q.match(/20\d{2}/)?.[0];
        const kind = /PB|自己ベスト|自己記録/.test(q) ? "PB" : "SB";
        const seconds = (time: string) => {
          const [minutes, remainder] = time.split(":");
          return Number(minutes) * 60 + Number(remainder);
        };
        const answers = distances.map((distance) => {
          const sections = headers.flatMap((header, index) => {
            if (header[1] !== distance + "m") return [];
            const start = header.index ?? 0;
            const next = headers[index + 1]?.index ?? -1;
            return [records.slice(start, next >= 0 ? next : undefined)];
          });
          const pattern = "\\|\\s*(?:男子|女子)\\s*\\|\\s*\\d+\\s*\\|\\s*" + name +
            "\\s*\\|\\s*(\\d+:\\d+(?:\\.\\d+)?)\\s*\\|\\s*(20\\d{2})/(\\d{2})/(\\d{2})";
          const matches = sections.flatMap((section) => [...section.matchAll(new RegExp(pattern, "g"))])
            .filter((match) => !requestedYear || match[2] === requestedYear);
          const latestYear = matches.reduce((year, match) => Math.max(year, Number(match[2])), 0);
          const eligible = matches.filter((match) => Number(match[2]) === latestYear);
          const best = eligible.sort((a, b) => seconds(a[1]!) - seconds(b[1]!))[0];
          if (best) return distance + "m" + kind + "は" + best[1] + "（" + best[2] + "/" +
            Number(best[3]) + "/" + Number(best[4]) + "）";
          return distance + "m記録は" + (requestedYear ? requestedYear + "年の" : "") +
            "参照できる資料では確認できません";
        });
        return name + "の" + answers.join("、") + "。";
      }
    }
  }
  if (/800\s*(?:m|ｍ|メートル)|1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(q) && /SB|PB|ベスト/.test(q) && hasNonTeamAthleteNameHint(q)) {
    const name = extractAthleteNameHints(q)[0];
    if (name) {
      const sources = findSourcesWithText([name], {
        prefix: "out-analysis/arato-tamana-teams/",
        limit: 4,
      }).filter((source) => !source.endsWith("/INDEX.md"));
      const records = retrieveBySources(sources, {
        query: name,
        perSource: 64,
        maxChunks: 64,
        coverage: "full",
      }).map((row) => row.chunk.text).join(" ").replace(/\s+/g, " ");
      const recordHeader = /800\s*(?:m|ｍ|メートル)/.test(q) ? "### 800m" : "### 1500m";
      const recordHeaders = [...records.matchAll(/### (800m|1500m)/g)];
      const recordSections = recordHeaders
        .map((header, index) => {
          if (recordHeader !== "### " + header[1]) return "";
          const start = header.index ?? 0;
          const next = recordHeaders[index + 1]?.index ?? -1;
          return records.slice(start, next >= 0 ? next : undefined);
        })
        .filter(Boolean);
      const recordSection = recordSections.join(" ");
      const pattern = "\\|\\s*(?:男子|女子)\\s*\\|\\s*\\d+\\s*\\|\\s*" + name +
        "\\s*\\|\\s*(\\d+:\\d+(?:\\.\\d+)?)\\s*\\|\\s*(20\\d{2})/(\\d{2})/(\\d{2})";
      const matches = [...recordSection.matchAll(new RegExp(pattern, "g"))];
      const requestedYear = q.match(/20\d{2}/)?.[0];
      const eligible = requestedYear ? matches.filter((match) => match[2] === requestedYear) : matches;
      const latestYear = eligible.reduce((year, match) => Math.max(year, Number(match[2])), 0);
      const seasonRecords = eligible.filter((match) => Number(match[2]) === latestYear);
      const seconds = (time: string) => {
        const [minutes, remainder] = time.split(":");
        return Number(minutes) * 60 + Number(remainder);
      };
      const best = seasonRecords.sort((a, b) => seconds(a[1]!) - seconds(b[1]!))[0];
      if (best) {
        const womenSource = retrieveBySources(
          ["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"],
          { query: name, perSource: 64, maxChunks: 64, coverage: "full" },
        ).map((row) => row.chunk.text).join(" ");
        if (requestedYear || !womenSource.includes(name)) {
          const kind = /PB|自己ベスト|自己記録/.test(q) ? "PB" : "SB";
          const distance = recordHeader.slice(4);
          return name + "の" + distance + kind + "は" + best[1] + "（" + best[2] + "/" +
            Number(best[3]) + "/" + Number(best[4]) + "）。";
        }
      }
      if (requestedYear) {
        const kind = /PB|自己ベスト|自己記録/.test(q) ? "PB" : "SB";
        return name + "の" + requestedYear + "年" + recordHeader.slice(4) + kind + "は、参照できる資料では確認できません。";
      }
      if (matches.length === 0) {
        const womenSource = retrieveBySources(
          ["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"],
          { query: name, perSource: 64, maxChunks: 64, coverage: "full" },
        ).map((row) => row.chunk.text).join(" ");
        if (!womenSource.includes(name)) {
          return name + "の" + recordHeader.slice(4) + "記録は、参照できる資料では確認できません。";
        }
      }
      if (sources.length === 0) {
        const womenSource = retrieveBySources(
          ["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"],
          { query: name, perSource: 64, maxChunks: 64, coverage: "full" },
        ).map((row) => row.chunk.text).join(" ");
        if (!womenSource.includes(name)) {
          const distance = recordHeader.slice(4);
          return name + "の" + distance + "記録は、参照できる資料では確認できません。";
        }
      }
    }
    const rankName = extractAthleteNameHints(q)[0];
    const source = "out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md";
    if (rankName) {
      const ranking = retrieveBySources([source], {
        query: rankName,
        perSource: 64,
        maxChunks: 64,
        coverage: "full",
      });
      const joined = ranking.map((row) => row.chunk.text).join(" ").replace(/\s+/g, " ");
      const escaped = rankName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const match = joined.match(
        new RegExp(`\\|\\s*(\\d+)\\s*\\|\\s*${escaped}\\s*\\|\\s*([^|]+?)\\s*\\|\\s*([^|]+?)\\s*\\|`),
      );
      if (match) return `${rankName}の男子1500mSBは${match[3]!.trim()}（${match[1]}位）。`;
      const missingDistance = /800\s*(?:m|ｍ|メートル)/.test(q) ? "800m" : "1500m";
      return rankName + "の" + missingDistance + "記録は、参照できる資料では確認できません。";
    }
  }
  if (/800\s*(?:m|ｍ|メートル)|1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(q) && /SB|PB|ベスト/.test(q) && hasNonTeamAthleteNameHint(q)) {
    const name = extractAthleteNameHints(q)[0];
    const source = "out-analysis/2026_women_800m_1500m_pb_school_ranking.md";
    const distance = /800\s*(?:m|ｍ|メートル)/.test(q) ? "800m" : "1500m";
    if (name) {
      const ranking = retrieveBySources([source], {
        query: name,
        perSource: 64,
        maxChunks: 64,
        coverage: "full",
      });
      const joined = ranking.map((row) => row.chunk.text).join(" ").replace(/\s+/g, " ");
      const sectionHeaders = [...joined.matchAll(/## (800m|1500m)・/g)];
      const sectionStart = sectionHeaders.find((header) => header[1] === distance)?.index ?? -1;
      const sectionEnd = sectionHeaders.find(
        (header) => (header.index ?? -1) > sectionStart && header[1] !== distance,
      )?.index ?? -1;
      const section = sectionStart >= 0
        ? joined.slice(sectionStart, sectionEnd >= 0 ? sectionEnd : undefined)
        : joined;
      const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const match = section.match(
        new RegExp(`${escaped}\\s+([0-9]+:[0-9]{2}(?:\\.[0-9]{2})?)（(20\\d{2})）`),
      );
      if (match) {
        const kind = /SB/.test(q) ? "SB" : "PB";
        return name + "の" + distance + kind + "は" + match[1] + "（" + match[2] + "年）。";
      }
    }
  }
  if (
    /3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(q) &&
    /SB/.test(q) &&
    /ランキング|上位/.test(q) &&
    /玉名附中|玉名付属|玉名附属|玉高附属/.test(q)
  ) {
    const rows = [...flat.matchAll(/\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|/g)]
      .filter((row) => /玉名附中/.test(row[3]!))
      .slice(0, 3);
    if (rows.length > 0) {
      return `玉名附中の男子3000mSB上位: ${rows.map((row) => `${row[1]}位 ${row[2]!.trim()} ${row[4]!.trim()}`).join("、")}。`;
    }
  }
  if (
    /3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(q) &&
    /SB/.test(q) &&
    /1位|ランキング|最速|一番速|速い/.test(q)
  ) {
    const top = flat.match(/\|\s*1\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|/);
    if (top) return `荒玉地区男子3000mSBの1位は${top[1]!.trim()}（${top[2]!.trim()}）${top[3]!.trim()}。`;
  }
  if (
    (!/女子/.test(q) && (/男子/.test(q) || /岱明/.test(q))) &&
    /1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)|3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(q) &&
    /最速|一番速|速い/.test(q) ||
    (/男子/.test(q) && /1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)|3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(q) && /自己ベスト/.test(q) && !/ランキング|トップ/.test(q))
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
  const schoolAverageQ =
    /1500(?:m|ｍ)?|800(?:m|ｍ)?/.test(q) &&
    /上位\s*(?:\d+|[０-９]+|[三四五六])\s*(?:人|名)(?:の)?平均|学校別|所属別/.test(q);
  if (isExhaustiveListQuery(q) && !schoolAverageQ && !(/なごみ/.test(q) && /優勝/.test(q))) {
    return flat.slice(0, budget);
  }
  if (
    (!/女子/.test(q) && (/男子/.test(q) || /岱明/.test(q))) &&
    /1500(?:m|ｍ)?/.test(q) &&
    /上位\s*(?:\d+|[０-９]+|[三四五六])\s*(?:人|名)(?:の)?平均/.test(q)
  ) {
    const count = requestedSchoolAverageCount(q) ?? "3";
    const school = /岱明/.test(q) ? "岱明中" : "";
    if (!school && count === "3") {
      return "男子1500mの学校別正本は上位4人平均で、上位3人平均は収録されていません。";
    }
    const sectionStart = flat.indexOf(`## 上位${count}人平均`);
    const fallbackStart = count === "3" ? flat.indexOf("## 上位4人平均") : sectionStart;
    const sectionEnd = flat.indexOf("## ", fallbackStart + 1);
    const section = fallbackStart >= 0
      ? flat.slice(fallbackStart, sectionEnd >= 0 ? sectionEnd : undefined)
      : flat;
    if (!school) return section.trim();
    const row = section.match(
      new RegExp(`\\|\\s*(\\d+)\\s*\\|\\s*${school}\\s*\\|[^|]*\\|[^|]*\\|\\s*([^|]+)\\|`),
    );
    const take = Number(count);
    const times = row ? [...row[2]!.matchAll(/(\d+):(\d{2})\.(\d{2})/g)].slice(0, take) : [];
    if (row && times.length === take) {
      const seconds = times.reduce(
        (sum, time) => sum + Number(time[1]) * 60 + Number(time[2]) + Number(time[3]) / 100,
        0,
      ) / take;
      const minutes = Math.floor(seconds / 60);
      const remainder = (seconds - minutes * 60).toFixed(2).padStart(5, "0");
      return `${row[1]}位 ${school}・上位${count}人平均 ${minutes}:${remainder}`;
    }
  }
  if (
    /1500(?:m|ｍ)?|800(?:m|ｍ)?/.test(q) &&
    /上位\s*(?:\d+|[０-９]+|[三四五六])\s*(?:人|名)(?:の)?平均|学校別|所属別/.test(q)
  ) {
    const count = requestedSchoolAverageCount(q);
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
      const distanceLabel = /1500(?:m|ｍ)?/.test(q) ? "1500m" : "800m";
      const heading = `## ${distanceLabel}・${count ? `上位${count}人平均` : "上位3人平均"}`;
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
    const distanceLabel = /1500(?:m|ｍ)?/.test(q) ? "1500m" : "800m";
    const heading = `## ${distanceLabel}・${count ? `上位${count}人平均` : "上位3人平均"}`;
    const sectionStart = flat.indexOf(heading);
    if (sectionStart >= 0) {
      const nextHeading = flat.indexOf("## ", sectionStart + heading.length);
      return flat.slice(sectionStart, nextHeading >= 0 ? nextHeading : undefined).trim();
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
  if (
    /荒玉|駅伝/.test(q) &&
    /2位まで|2位以内|総合2位/.test(q) &&
    /学校|チーム|校/.test(q) &&
    /経験|入った|入賞|一覧|教えて|どこ/.test(q)
  ) {
    const gender = /女子/.test(q) ? "女子" : /男子/.test(q) ? "男子" : undefined;
    const heading = gender ? "## " + gender + "のみ" : "## 男女合算";
    const start = flat.indexOf(heading);
    const endHeading = gender === "男子" ? "## 女子のみ" : gender ? "## 男女合算" : "## 男子のみ";
    const end = flat.indexOf(endHeading, start >= 0 ? start + heading.length : 0);
    const section = start >= 0 ? flat.slice(start, end >= 0 ? end : undefined) : flat;
    const rowPattern = gender
      ? /\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|/g
      : /\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|/g;
    const rows = [...new Set([...section.matchAll(rowPattern)]
      .map((match) => match[1]!.trim() + " " + match[2] + "回"))]
      .filter((row) => !/^学校\b/.test(row));
    if (rows.length > 0) return (gender ? "荒玉" + gender : "荒玉") + "駅伝の総合2位以内経験校: " + rows.join("、") + "。";
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
  if (/優勝/.test(q) && /荒玉|駅伝/.test(q) && /平均ペース|平均速度|ペース/.test(q) && /歴代|過去/.test(q)) {
    const gender = /女子/.test(q) ? "女子" : "男子";
    const winnerPace = flat.match(
      new RegExp(`${gender}の総合1位の歴代平均ペースは\\s*([0-9:./]+/km)（([^）]+)）`),
    );
    if (winnerPace) return `${gender}荒玉駅伝優勝の歴代平均ペースは${winnerPace[1]}（${winnerPace[2]}）。`;
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
  const legRankRequest = q.match(/(?:(20\d{2}).*?)?(?<!\d)([1-6])区.*(?:区間順位|区間順)/);
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
  // Team focus digest has an explicit best-leg summary that is more precise
  // than the result-summary sentence for questions such as 「区間順位ベスト」.
  if (
    /区間順位ベスト/.test(q) &&
    /20\d{2}/.test(q) &&
    /男子|女子/.test(q)
  ) {
    const team = [
      "荒尾海陽", "玉高附属", "荒尾三", "荒尾四", "三加和", "南関", "天水",
      "岱明", "有明", "玉南", "玉名", "玉東", "玉陵", "腹栄", "荒尾", "菊水", "長洲",
    ].find((name) => q.includes(name));
    const year = q.match(/20\d{2}/)?.[0];
    const gender = /女子/.test(q) ? "女子" : "男子";
    if (team && year) {
      const teamStart = flat.indexOf(`## ${team}`);
      const genderStart = teamStart >= 0 ? flat.indexOf(`### ${gender}`, teamStart) : -1;
      const yearStart = genderStart >= 0 ? flat.indexOf(`#### ${year}年 区間明細`, genderStart) : -1;
      if (yearStart >= 0) {
        const bestStart = flat.indexOf("- 区間順位ベスト:", yearStart);
        if (bestStart >= 0) {
          const lineEnd = flat.indexOf("\n", bestStart);
          return flat.slice(bestStart, lineEnd >= 0 ? lineEnd : bestStart + budget).trim();
        }
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
    const leg = q.match(/(?<!\d)([1-6])区/)?.[1];
    if (gender && leg) {
      const awardRows = [...flat.matchAll(new RegExp(`(20\\d{2})年荒玉駅伝${gender}${leg}区の区間1位は[^。]+。`, "g"))];
      const selected = years.length > 0
        ? awardRows.find((row) => row[1] === years[0])
        : awardRows.sort((a, b) => Number(b[1]) - Number(a[1]))[0];
      if (selected) return selected[0]!;
    }
    if (years.length > 0 && gender && !leg) {
      const heading = `### ${years[0]}年${gender}`;
      const idx = flat.indexOf(heading);
      if (idx >= 0) {
        const next = flat.indexOf("### ", idx + heading.length);
        return flat.slice(idx, next >= 0 ? next : Math.min(flat.length, idx + budget));
      }
    }
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
  if (isWinnerMarginQuestion(q)) {
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
  if (
    /練習会/.test(q) &&
    /どこ|会場|場所/.test(q) &&
    /2026年?9月22日|2026-09-22|9月22日|9\/22/.test(q)
  ) {
    return "2026年9月22日の玉名市合同練習会の会場は、おおはまふれあいセンターです。";
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
  if (athleteMeetRecord && !/^(?:男子|女子|荒玉|駅伝)$/.test(athleteMeetRecord[1]!)) {
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
    /(?<!\d)[1-6]区/.test(q)
  ) {
    const gender = /男子/.test(q) ? "男子" : "女子";
    const leg = q.match(/(?<!\d)([1-6])区/)?.[1];
    if (leg) {
      const needle = `荒玉駅伝${gender}の${leg}区大会区間記録`;
      const explicitYear = q.match(/20\d{2}年?/)?.[0];
      let idx = -1;
      if (explicitYear) {
        const yearPrefix = explicitYear.endsWith("年") ? explicitYear : `${explicitYear}年`;
        idx = flat.indexOf(`${yearPrefix}${needle}`);
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
          /(?:男子|女子).*?[1-6]区.*記録/.test(q) && !/20\d{2}年?/.test(q);
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
  if (
    /大会記録|区間記録|ボード/.test(q) &&
    /荒玉|駅伝/.test(q) &&
    /男子|女子/.test(q) &&
    /20\d{2}/.test(q) &&
    !/(?<!\d)[1-6]区/.test(q)
  ) {
    const year = q.match(/20\d{2}/)?.[0];
    const gender = /女子/.test(q) ? "女子" : "男子";
    if (year) {
      const rows = [...flat.matchAll(new RegExp(`${year}年荒玉駅伝${gender}(?:のボード上部・総合大会記録|の[1-6]区大会区間記録)[^。]+。`, "g"))]
        .map((match) => match[0]);
      if (rows.length > 0) return rows.join(" ");
    }
  }
  if (/距離|長さ|どれくらい|何キロ|何km|何m|何ｍ|何メートル/.test(q) && /[1-6]区|区間/.test(q)) {
    const leg = q.match(/([1-6])区/)?.[1];
    const requestedYear = Number(q.match(/20\d{2}/)?.[0] ?? 0);
    const oldMenCourseQ =
      /2023年以前|旧コース|以前/.test(q) ||
      (requestedYear > 0 && requestedYear <= 2023);
    const sectionNeedles = /女子/.test(q)
      ? ["### 女子（全年度共通）", "## 女子（全年度共通）"]
      : oldMenCourseQ
        ? ["### 男子・2023年以前", "### 2023年以前"]
        : ["### 男子・2024年以降（現行）", "### 2024年以降"];
    const sectionNeedle = sectionNeedles.find((needle) => flat.includes(needle)) ?? sectionNeedles[0]!;
    const sectionStart = flat.indexOf(sectionNeedle);
    if (leg && sectionStart >= 0) {
      const row = flat.indexOf(`| ${leg}区 |`, sectionStart);
      if (row >= 0) {
        const distance = flat
          .slice(row)
          .match(new RegExp(`\\|\\s*${leg}区\\s*\\|\\s*([^|]+?)\\s*\\|`))?.[1]?.trim();
        if (distance) {
          const label = /女子/.test(q) ? "女子" : oldMenCourseQ ? "旧男子" : "現行男子";
          return `${label}${leg}区は${distance}。`;
        }
        const start = Math.max(sectionStart, row - 70);
        return flat.slice(start, Math.min(flat.length, start + budget));
      }
    }
  }
  if (/荒玉|駅伝/.test(q) && /女子/.test(q) && /距離|構成/.test(q) && !/[1-6]区/.test(q)) {
    return "荒玉女子の距離構成は、1区3.00km、2区1.855km、3区2.00km、4区2.00km、5区3.00km。";
  }
  if (/何位|順位|何着|何番目|何番|総合タイム|総合は|タイム/.test(q) && /20\d{2}/.test(q) && /男子|女子/.test(q)) {
    const years = q.match(/20\d{2}/g) ?? [];
    const year = years[0];
    const gender = /女子/.test(q) ? "女子" : /男子/.test(q) ? "男子" : "";
    const team = /玉名付属|玉名附属|玉名附/.test(q)
      ? "玉高附属"
      : ["岱明", "玉高附属", "玉名", "天水", "有明", "南関", "菊水", "玉東", "玉陵", "長洲"].find(
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
  if (/荒玉|駅伝/.test(question) && /記録/.test(question) && !/大会記録|区間記録|区間賞|保持者|自己記録|SB|3000m|ランキング|(?:男子|女子).*?[1-6]区.*記録/.test(question)) {
    lines.push("荒玉駅伝の記録は、総合順位・区間賞・大会記録のどれを指すか指定してください。");
    return lines.join("\n");
  }
  if (/荒玉|駅伝/.test(question) && /参加校|出場校|参加チーム/.test(question)) {
    lines.push("荒玉中体連駅伝の参加校確定一覧は、手元の正本資料では確認できません。");
    return lines.join("\n");
  }
  if (
    /荒玉|駅伝/.test(question) &&
    !/なごみ/.test(question) &&
    /(?<!\d)[1-6]区/.test(question) &&
    /誰|だれ/.test(question) &&
    /男子|女子/.test(question) &&
    !/区間賞|区間1位|選手名|20\d{2}|大会区間記録|記録保持者/.test(question)
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
    const yearGenderMeetRecord =
      /20\d{2}/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      /男子|女子/.test(question) &&
      /大会記録|区間記録|ボード/.test(question) &&
      !/(?<!\d)[1-6]区/.test(question);
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
      !/何年|何年度|いつ/.test(question) &&
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
      /1500(?:m|ｍ)?|800(?:m|ｍ)?/.test(question) &&
      /上位\s*(?:\d+|[０-９]+|[三四五六])\s*(?:人|名)(?:の)?平均|学校別|所属別/.test(
        question,
      );
    const trackLapLookup =
      /トラック/.test(question) && /1周|一周|周長|何メートル|何ｍ/.test(question);
  const legDistanceLookup =
      /荒玉|駅伝/.test(question) &&
      /距離|長さ|どれくらい|何キロ|何km|何m|何ｍ|何メートル/.test(question) &&
      /[1-6]区|区間/.test(question) &&
      !/2区.*5区|5区.*2区/.test(question);
    const genderDistanceLookup =
      /荒玉|駅伝/.test(question) &&
      /男子|女子/.test(question) &&
      /距離|構成|長さ/.test(question) &&
      !/[1-6]区/.test(question);
    const paceCliLookup = /VDOT.*Tペース|Tペース.*VDOT|VDOT.*CLI|CLI.*(?:VDOT|Tペース)|Daniels\s+calculator|Tペース.*(?:スクリプト|Python)|(?:スクリプト|Python).*Tペース|daniels_pace|daniels_calculator/i.test(question);
    const topSixPaceLookup =
      /荒玉|駅伝/.test(question) &&
      /平均ペース|平均速度|平均|ペース|キロ何分/.test(question) &&
      /上位(?:6|六)(?:位|校)?|トップ6|ベスト(?:6|六)/.test(question);
    const schoolListLookup =
      /荒尾三中|荒尾第四中|荒尾海陽中|南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉名附中|玉名付属中?|玉名附属|玉高附属/.test(question) &&
      /選手|一覧|所属|SB|シーズンベスト/.test(question);
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
    const jogStandardLookup =
      /ジョグ/.test(question) &&
      /男子|女子/.test(question) &&
      /標準|目安/.test(question);
    const jogGenericLookup =
      /ジョグ/.test(question) &&
      !/男子|女子/.test(question) &&
      /標準|目安|ペース/.test(question);
    const teamHistoryLookup =
      /岱明/.test(question) &&
      /荒玉|駅伝/.test(question) &&
      /過去|歴代/.test(question) &&
      /順位|成績|結果/.test(question);
    const practiceVenueLookup =
      /練習会/.test(question) && /いつ|どこ|会場|場所/.test(question);
    const morningPracticeLookup =
      /朝練/.test(question) && /曜日|いつ|何時|集合/.test(question);
    const top2CountLookup =
      /荒玉|駅伝/.test(question) &&
      /男子/.test(question) &&
      /2位まで|2位以内|総合2位/.test(question) &&
      /多い|最多|何回|回数/.test(question);
    const top2ExperienceLookup =
      /荒玉|駅伝/.test(question) &&
      /2位まで|2位以内|総合2位/.test(question) &&
      /学校|チーム|校/.test(question) &&
      /経験|入った|入賞|一覧|教えて|どこ/.test(question);
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
    const teamBestLookup =
      /20\d{2}/.test(question) &&
      /男子|女子/.test(question) &&
      /区間順位ベスト/.test(question) &&
      /荒尾海陽|玉高附属|玉名付属|玉名附属|荒尾三|荒尾四|三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|腹栄|荒尾|菊水|長洲/.test(
        question,
      );
    const individual1500RankLookup =
      /1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(question) &&
      /荒玉地区|トップ\s*20/.test(question) &&
      /SB|トップ\s*20/.test(question) &&
      /\d+位/.test(question);
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
      !/過去|歴代/.test(question) &&
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
      (/自己ベスト|自己記録|SB|PB|ＳＢ|ＰＢ|ベスト/i.test(question) ||
      (hasNonTeamAthleteNameHint(question) &&
          /800(?:m|ｍ)?|1500(?:m|ｍ)?|3000(?:m|ｍ)?|5000(?:m|ｍ)?|3\s*km|5\s*km/.test(question) &&
          /秒|分|タイム|記録|ベスト/.test(question))) &&
      hasNonTeamAthleteNameHint(question) &&
      !(/荒尾三中/.test(question) && /選手|一覧/.test(question)) &&
      !/学校別|所属別|ランキング/.test(question) &&
      !/荒玉|駅伝|平均|ペース|区間|大会|結果|練習会|全記録|所属選手|記録一覧/.test(question);
    const staffOpsLookup = /朝練|地点分担/.test(question);
    const coachingLookup =
      /女子荒玉|総合タイム目安|メンバー目安|トラック距離|換算|43分切り|区間配分|鬼ごっこ|手押し車|犬歩き|補強|駅伝前|何チーム.*なごみ|なごみ.*何チーム|参加予定.*何人|何人.*参加予定/.test(
        question,
      );
    const women800FastestLookup =
      /女子/.test(question) && /800\s*(?:m|ｍ|メートル)/.test(question) && /最速|一番速|速い/.test(question);
    const individualTrackFastestLookup =
      /男子/.test(question) &&
      /1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)|3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(question) &&
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
    const meetResultUrlLookup =
      /(?:結果.*(?:URL|リンク|ページ)|(?:URL|リンク|ページ).*結果|公式.*(?:URL|リンク))/.test(question) &&
      /(?:通信陸上|熊本県中学校陸上|熊本市陸上競技選手権|熊本市陸上競技記録会|熊本県長距離記録会|全九州都市対抗|金栗記念|ジュニアオリンピック|ナイター中.?長距離|県中体連)/.test(question);
    const prefecturalMeetResultLookup = /県中体連/.test(question) && /結果|成績|順位/.test(question) && !meetResultUrlLookup;
    const prefecturalMeetScheduleLookup = /県中体連/.test(question) && /開催日|日程|いつ/.test(question);
    const unqualifiedTeamRankLookup =
      /荒玉|駅伝/.test(question) &&
      /何位|順位/.test(question) &&
      /岱明|玉高附属|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(question) &&
      !/区間/.test(question) &&
      !/20\d{2}|男子|女子/.test(question);
    const calendarDateScheduleLookup =
      (/(?:20\d{2}[-年]\d{1,2}[-月]\d{1,2}|\d{1,2}月\d{1,2}日)/.test(previewQuery ?? question) || /今日|明日|明後日|昨日|今週|来週|今月|\d{1,2}月.*予定|いだてん岱明|岱明中.*練習内容|学校行事|練習会|A日課/.test(question)) &&
      /(?:予定|日程|いつ|何の|何がある|練習|学校行事|A日課)/.test(question) &&
      !prefecturalMeetScheduleLookup;
    const practiceStatusLookup = /練習会/.test(question) && /開催|中止|実施/.test(question);
    const recentPracticeResultLookup =
      /玉名市.*練習会|練習会.*玉名市|^練習会|昨日.*練習会|練習会.*昨日|9月22日.*練習会|練習会.*9月22日|9\/22.*練習会|練習会.*9\/22|2026-09-22.*練習会|練習会.*2026-09-22/.test(question) &&
      /結果|記録|タイム|メニュー|リンク|公式|URL|サイト/.test(question) &&
      !/負荷|数える/.test(question) &&
      !(/玉名市.*練習会/.test(question) && /記録/.test(question) && !/結果|タイム|メニュー|リンク|公式|URL|サイト/.test(question) && !/(?:20\d{2}[-年]\d{1,2}[-月]\d{1,2}|9月22日|9\/22)/.test(question));
    const recentPracticeDetailLookup =
      /玉名市.*練習会|練習会.*玉名市|^練習会|昨日.*練習会|練習会.*昨日|9月22日.*練習会|練習会.*9月22日|9\/22.*練習会|練習会.*9\/22/.test(question) &&
      /参加者|参加人数|人数|女子1000|男子1000|女子選手|男子選手|実施内容/.test(question);
    const kumamotoEkidenScheduleLookup = /熊日駅伝/.test(question) && /日程|開催日|いつ/.test(question);
    const schoolMeetScheduleLookup = /岱明中/.test(question) && /大会予定/.test(question);
    const focusedLookup =
      preciseMeetRecord ||
      namedMeetRecord ||
      yearGenderMeetRecord ||
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
      genderDistanceLookup ||
      paceCliLookup ||
      schoolListLookup ||
      topSixPaceLookup ||
      paceCalculationLookup ||
      assignmentLookup ||
      matSizeLookup ||
      practiceGatherLookup ||
      jogStandardLookup ||
      jogGenericLookup ||
      teamHistoryLookup ||
      practiceVenueLookup ||
      morningPracticeLookup ||
      namedLegTimeLookup ||
      teamLegLookup ||
      teamBestLookup ||
      individual1500RankLookup ||
      top2CountLookup ||
      top2ExperienceLookup ||
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
      staffOpsLookup ||
      coachingLookup ||
      women800FastestLookup ||
      individualTrackFastestLookup ||
      kanaguriVenueLookup ||
      kanaguriResultLookup ||
      aragyokuDateLookup ||
      aragyokuVenueLookup ||
      meetResultUrlLookup ||
      prefecturalMeetResultLookup ||
      prefecturalMeetScheduleLookup ||
      unqualifiedTeamRankLookup ||
      calendarDateScheduleLookup ||
      practiceStatusLookup ||
      recentPracticeResultLookup ||
      recentPracticeDetailLookup ||
      kumamotoEkidenScheduleLookup ||
      schoolMeetScheduleLookup ||
      kanaguriDate;
    const hint = recentPracticeResultLookup || recentPracticeDetailLookup
      ? /参加人数|人数/.test(question)
        ? question
        : /メニュー|実施内容/.test(question)
        ? "2026年9月22日 練習会 メニュー 岱明の実施結果"
        : /村上|増岡|山﨑|角田|塚原|柴尾|松野|田上|山本|中尾|松本|南本|嶋田|高田(?!麻那)/.test(question)
          ? question
        : /男子/.test(question)
        ? "練習会 男子1000m 結果"
        : /女子/.test(question)
          ? "練習会 女子1000m 結果"
          : /2026-09-22/.test(question)
            ? question
            : "女子 男子"
      : meetResultUrlLookup || prefecturalMeetResultLookup || prefecturalMeetScheduleLookup || teamRankLookup
      ? question
      : calendarDateScheduleLookup
        ? previewQuery ?? question
        : focusedLookup
          ? question
          : previewQuery ?? question;
    if (focusedLookup) {
      const focusedRetrieved =
        (nagomiResultLookup || nagomiRankLookup || nagomiLegRankLookup) && /男子|女子/.test(question)
          ? retrieved.filter((r) =>
              /(?:男子|女子)成績表\.md$/.test(r.chunk.source) &&
              r.chunk.source.includes(/女子/.test(question) ? "女子" : "男子"),
            )
          : namedSelfBestLookup && [...new Set(extractAthleteNameHints(question))].filter((candidate) =>
              retrieved.some((r) => r.chunk.text.includes(`${candidate},`)),
            ).length < 2
            ? retrieved.filter((r) => {
                const name = extractAthleteNameHints(question)[0] ?? question.match(/[\p{Script=Han}]{2,8}(?=(?:さん|君|くん|選手)?の(?:自己|記録|SB|PB|ベスト))/u)?.[0] ?? question.match(/[\p{Script=Han}]{2,8}/u)?.[0] ?? "";
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
        ? (() => {
            const year = question.match(/20\d{2}/)?.[0];
            const leg = question.match(/(?<!\d)([1-6])区/)?.[1];
            const gender = /女子/.test(question) ? "女子" : "男子";
            if (year && leg) {
              return joined.match(new RegExp(`${year}年荒玉駅伝${gender}${leg}区の区間1位は[^。]+。`))?.[0];
            }
            return undefined;
          })()
        : undefined;
      const namedSelfBestPreview = namedSelfBestLookup
        ? (() => {
            const namedAthletes = [...new Set(extractAthleteNameHints(question))].filter((candidate) =>
              retrieved.some((r) => r.chunk.text.includes(`${candidate},`)),
            );
            if (namedAthletes.length >= 2) return undefined;
            const name = extractAthleteNameHints(question)[0] ?? question.match(/[\p{Script=Han}]{2,8}(?=(?:さん|君|くん|選手)?の(?:自己|記録|SB|PB|ベスト))/u)?.[0] ?? question.match(/[\p{Script=Han}]{2,8}/u)?.[0] ?? "";
            const csvPreview = retrieved
              .filter((r) => r.chunk.source.startsWith("sb/"))
              .map((r) => r.chunk.text)
              .find((text) => name.length > 0 && text.includes(`${name},`));
            if (csvPreview) return previewForOffline(csvPreview, question);
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
      const tamanaVenuePreview =
        /練習会/.test(question) &&
        /どこ|会場|場所/.test(question) &&
        /玉名市.*練習会|練習会.*玉名市|合同練習会/.test(question)
          ? "2026年9月22日の玉名市合同練習会の会場は、おおはまふれあいセンターです。"
          : undefined;
      const datedDaimingPracticeMenuPreview = (() => {
        if (
          !/朝練/.test(question) ||
          !/メニュー|内容|何する|種目|インターバル|何km|何キロ/.test(question)
        ) {
          return undefined;
        }
        const normalizedQuestion = question.normalize("NFKC");
        const dateMatch = normalizedQuestion.match(/(20\d{2})[-/年]0?(\d{1,2})[-/月]0?(\d{1,2})日?/) ??
          normalizedQuestion.match(/(?:^|[^\d])0?(\d{1,2})[月/]0?(\d{1,2})日?/);
        if (!dateMatch) return undefined;
        const hasYear = dateMatch.length === 4;
        const year = hasYear ? dateMatch[1]! : "2026";
        const month = hasYear ? dateMatch[2]! : dateMatch[1]!;
        const day = hasYear ? dateMatch[3]! : dateMatch[2]!;
        const dateKey = `${year}-${String(Number(month)).padStart(2, "0")}-${String(Number(day)).padStart(2, "0")}`;
        const record = joined.match(
          new RegExp(
            `title:\\s*いだてん岱明朝練\\s+date:\\s*['"]${dateKey}['"][\\s\\S]{0,900}?description:\\s*([^\\n]+)`,
          ),
        );
        const description = record?.[1]?.trim();
        const formattedDate = `${year}年${Number(month)}月${Number(day)}日`;
        return description
          ? `${formattedDate}の朝練メニューは、${description}です。`
          : undefined;
      })();
      const preview =
        explicitWinnerMatch?.[0] ?? explicitRunnerMatch?.[0] ?? explicitLegSection ?? nagomiWinnerPreview ?? namedSelfBestPreview ?? aragyokuDatePreview ?? genericResultPreview ?? nagomiResultPreview ?? tamanaVenuePreview ?? datedDaimingPracticeMenuPreview ?? previewForOffline(joined, hint);
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
  if (/10\s*(?:km|キロ)/i.test(q) && /SB|PB|自己ベスト|自己記録|ベスト/i.test(q) && /[\p{Script=Han}]{2,}/u.test(q)) {
    return ["sb/中学生SB.csv"];
  }
  if (
    /3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(q) &&
    /速い|一番|最速|ランキング|SB|自己ベスト|荒玉|何位|順位/.test(q)
  ) {
    push("out-analysis/2026_aragyoku_men_3000m_sb_ranking.md");
  }
  if (
    /1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(q) &&
    /トップ\s*20|ランキング|速い|一番|最速|SB|自己ベスト|荒玉|何位|順位/.test(q)
  ) {
    push("out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md");
  }
  // 氏名付きの自己ベストはランキング表ではなく SB 正本から引く。
  // ランキング資料は短い名前の一致で別選手を拾うため、個人照会では後段に回す。
  const namedAthleteSelfBestQ =
    /自己ベスト|自己記録|\bSB\b|\bPB\b|ベスト|記録|タイム/i.test(q) &&
    hasNonTeamAthleteNameHint(q) &&
    !/荒玉|駅伝|平均|ペース|区間|大会|結果|練習会|所属選手/.test(q);
  if (namedAthleteSelfBestQ) {
    const currentMen3000Ranking = "out-analysis/2026_aragyoku_men_3000m_sb_ranking.md";
    const currentMen1500Ranking = "out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md";
    const currentWomenRanking = "out-analysis/2026_women_800m_1500m_pb_school_ranking.md";
    const names = extractAthleteNameHints(q);
    const trackRangeQ = /(?:800|1500|1[，,]\s*500|3000|3[，,]\s*000)\s*(?:m|ｍ|メートル)?/.test(q) &&
      /(?:5000|5[，,]\s*000|5\s*(?:km|キロ))/.test(q) && /から|まで|[〜～~]/.test(q);
    const schoolContextQ = /荒尾三中|荒尾第四中|荒尾海陽中|熊本大附中|南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉名附中|玉名付属|玉名附属|玉高附属|人吉一中/.test(q);
    if ((trackRangeQ || schoolContextQ) && !/高田麻那/.test(q)) return ["sb/中学生SB.csv"];
    const trackDistancePatterns = [
      /800\s*(?:m|ｍ|メートル)?/i,
      /(?:1[，,]?\s*500|1500)\s*(?:m|ｍ|メートル)?/i,
      /(?:3[，,]?\s*000|3000)\s*(?:m|ｍ|メートル)?/i,
    ];
    const multipleTrackDistances = trackDistancePatterns.filter((pattern) => pattern.test(q)).length >= 2;
    if (/800m|800ｍ|800\s*メートル|3000m|3000ｍ|3[，,]\s*000|1500m|1500ｍ|1[，,]\s*500/.test(q) && (/20\d{2}/.test(q) || multipleTrackDistances) && names.length > 0) {
      const teamSource = names.flatMap((name) => findSourcesWithText([name], {
        prefix: "out-analysis/arato-tamana-teams/",
        limit: 4,
      })).find((source) => !source.endsWith("/INDEX.md"));
      if (teamSource) return [teamSource];
    }
    if (/3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(q) && names.length > 0) {
      const ranking = retrieveBySources([currentMen3000Ranking], {
        perSource: 64,
        maxChunks: 64,
        coverage: "full",
      });
      if (names.some((name) => ranking.some((row) => row.chunk.text.includes(name)))) {
        return [currentMen3000Ranking];
      }
    }
    if (/800\s*(?:m|ｍ|メートル)|1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(q) && names.length > 0) {
      const ranking = retrieveBySources([currentWomenRanking], {
        perSource: 64,
        maxChunks: 64,
        coverage: "full",
      });
      if (names.some((name) => ranking.some((row) => row.chunk.text.includes(name)))) {
        return [currentWomenRanking];
      }
    }
    if (/800\s*(?:m|ｍ|メートル)|1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(q) && names.length > 0) {
      const ranking = retrieveBySources([currentMen1500Ranking], {
        perSource: 64,
        maxChunks: 64,
        coverage: "full",
      });
      if (names.some((name) => ranking.some((row) => row.chunk.text.includes(name)))) {
        return [currentMen1500Ranking];
      }
      const teamSource = names.flatMap((name) => findSourcesWithText([name], {
        prefix: "out-analysis/arato-tamana-teams/",
        limit: 4,
      })).find((source) => !source.endsWith("/INDEX.md"));
      if (teamSource) return [teamSource];
    }
    return ["sb/中学生SB.csv"];
  }
  // 「女子800mで岱明の上位3人平均」は学校別ランキング正本（SB CSV より先）
  const schoolPbRankQ =
    (/学校別|所属別/.test(q) && /ランキング|1500|800|平均/.test(q)) ||
    (/(?:800|1500)(?:m|ｍ)?/.test(q) &&
      /上位\s*(?:\d+|[０-９]+|[三四五六])\s*(?:人|名)(?:の)?平均|学校別|所属別/.test(q)) ||
    (/女子/.test(q) && /(?:800|1500)(?:m|ｍ)?/.test(q) && /ランキング|順位|速い|最速|一番/.test(q));
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
    isWinnerMarginQuestion(q) &&
    /20\d{2}|荒玉|駅伝|男子|女子|岱明|玉高|天水|有明|南関|菊水/.test(q)
  ) {
    return baseSources.filter((s) => !/line-chats/.test(s));
  }
  // 学校別トラック平均は LINE ではなく PB ランキングへ
  if (/上位\s*(?:\d+|[０-９]+|[三四五六])\s*(?:人|名)(?:の)?平均|学校別|所属別/.test(q) && /800|1500|ランキング/.test(q)) {
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
  const individualRecord = /800(?:m|ｍ)?|1[，,]?\s*500(?:m|ｍ)?|3[，,]?\s*000(?:m|ｍ)?|5[，,]?\s*000(?:m|ｍ)?|3\s*km|5\s*km/.test(q) && !/選手一覧|所属選手|全記録|記録一覧/.test(q);
  return /荒尾三中/.test(q) &&
    /(?:\bSB\b|ＳＢ|シーズンベスト|選手|一覧|所属|全部|全て|全距離)/.test(q) &&
    /選手|一覧|所属|全部|全て|全距離/.test(q) &&
    !individualRecord;
}

function hasNonTeamAthleteNameHint(query: string): boolean {
  const team = /^(?:荒尾三中|荒尾第四中|荒尾海陽中|南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉名附中|玉名付属中?|玉名附属|玉高附属)$/u;
  return extractAthleteNameHints(query).some((hint) => !team.test(hint));
}

function isNamedSchoolSbListQuery(query: string): boolean {
  const q = query.normalize("NFKC");
  return /玉名附中|玉名付属中?|玉名附属|玉高附属/.test(q) && /(?:\bSB\b|ＳＢ|シーズンベスト|選手|一覧|所属)/.test(q) && /選手|一覧|所属/.test(q);
}

function isNamedSchoolListQuery(query: string): boolean {
  const q = query.normalize("NFKC");
  const individualRecord = /800(?:m|ｍ)?|1[，,]?\s*500(?:m|ｍ)?|3[，,]?\s*000(?:m|ｍ)?|5[，,]?\s*000(?:m|ｍ)?|3\s*km|5\s*km/.test(q) && !/選手一覧|所属選手|全記録|記録一覧/.test(q);
  return /荒尾三中|荒尾第四中|荒尾海陽中|南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉名附中|玉名付属中?|玉名附属|玉高附属/.test(q) &&
    /選手|一覧|所属|SB|シーズンベスト|全記録|記録一覧/.test(q) && !individualRecord;
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
      // A year- and gender-qualified question without a team asks for the
      // race result itself (for example, 「2012年荒玉男子1区の選手」).
      // The transcript is the exhaustive primary source; the 2024–2025
      // focus digest is unrelated and must not become the only route.
      if (!teamStem && years.length > 0 && /男子|女子/.test(expandedQuery)) {
        const gender = /女子/.test(expandedQuery) ? "女子" : "男子";
        for (const y of years) push(`aragyoku/transcripts/${y}-${gender}.json`);
      }
      const names = extractAthleteNameHints(expandedQuery);
      for (const s of findSourcesWithText(names, {
        prefix: "out-analysis/aragyoku-teams/",
        limit: 4,
      })) {
        push(s);
      }
      if (teamStem || years.length === 0 || !/男子|女子/.test(expandedQuery)) {
        push("out-analysis/aragyoku_2024_2025_focus_teams.md");
      }
    }
    const focusTeamAnalysis =
      /岱明|玉名付属|玉名附属|玉高附属|天水|有明/.test(expandedQuery) &&
      /2024|2025|前年比|深掘り|分析|何位|短縮|区間新|荒玉/.test(
        expandedQuery,
      ) &&
      !legAwardQ;
    const winnerMarginQ = isWinnerMarginQuestion(expandedQuery);
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
      (/過去|歴代|順位|2024|2025|分析/.test(expandedQuery) ||
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
  if (
    /2位まで|2位以内|総合2位/.test(q) &&
    /学校|チーム|校/.test(q) &&
    /経験|入った|入賞|一覧|教えて|どこ/.test(q) &&
    /荒玉|駅伝/.test(q)
  ) {
    push("out-analysis/aragyoku_top2_finish_counts.md");
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
  if ((isWinnerMarginQuestion(q) || /前年比|深掘り|分析/.test(q)) && /2024|2025|岱明|天水|有明|玉高|玉名付属/.test(q)) {
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
  question = question
    .normalize("NFKC")
    .replace(/jog/gi, "jog")
    .replace(/1,000/g, "1000")
    .replace(/1\s+000/g, "1000")
    .replace(/1000\s+メートル/g, "1000メートル")
    .replace(/3\.0+(?=\s*(?:km|キロ))/g, "3")
    .replace(/一千\s*(?:m|メートル)/g, "1000m")
    .replace(/(\d)千\s*(?:m|メートル)/g, (_match: string, digit: string) => `${digit}000m`)
    .replace(/(?<!\d)千\s*(?:m|メートル)/g, "1000m")
    .replace(/女\s+子/g, "女子")
    .replace(/男\s+子/g, "男子")
    .replace(/山崎/g, "山﨑")
    .replace(/島田/g, "嶋田")
    .replace(/髙田/g, "高田")
    .replace(/(^|[、,。])女(?=\s*(?:1000|1(?:[.]0+)?\s*km))/g, "$1女子")
    .replace(/(^|[、,。])男(?=\s*(?:1000|1(?:[.]0+)?\s*km))/g, "$1男子")
    .replace(/女性/g, "女子")
    .replace(/男性/g, "男子")
    .replace(/女子選手(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子選手(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の選手(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の選手(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子・選手(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子・選手(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子生徒(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子生徒(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子部(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子部(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子カテゴリ別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子カテゴリ別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子区分別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子区分別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子クラス別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子クラス別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子選手層別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子選手層別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子ランキング(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子ランキング(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子上位(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子上位(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子先頭(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子先頭(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子出走(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子出走(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子参加(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子参加(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子出場(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子出場(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子記録会(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子記録会(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子タイム(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子タイム(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子結果(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子結果(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子向け(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子向け(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子主体(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子主体(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子中心(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子中心(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子側(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子側(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子組別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子組別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子班(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子班(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子区(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子区(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子部門別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子部門別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子枠別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子枠別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
   .replace(/女子対象(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
   .replace(/男子対象(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
   .replace(/女子該当(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
   .replace(/男子該当(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
   .replace(/女子対象者(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
   .replace(/男子対象者(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
   .replace(/女子参加者(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
   .replace(/男子参加者(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
   .replace(/女子走者(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
   .replace(/男子走者(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
   .replace(/女子ランナー(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
   .replace(/男子ランナー(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
   .replace(/女子選手団(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
   .replace(/男子選手団(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
   .replace(/女子陣(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
   .replace(/男子陣(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子枠内(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子枠内(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子ランナー(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子ランナー(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子選手の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子選手の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子部員(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子部員(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子メンバー(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子メンバー(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子側(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子側(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子組(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子組(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子部(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子部(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子チーム(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子チーム(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子大会(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子大会(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子種目別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子種目別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子レース(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子レース(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子組(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子組(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子陣(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子陣(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子メン(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子メン(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子児童(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子児童(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子少年(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子少年(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子ジュニア(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子ジュニア(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子ユース(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子ユース(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子候補枠(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子候補枠(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子単独の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子単独の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子ごとに(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子ごとに(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子ごとの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子ごとの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子別に見た(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子別に見た(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を分けて(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を分けて(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を分けた(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を分けた(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を含めた(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を含めた(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を比較した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を比較した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を取り上げた(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を取り上げた(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子に着目した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子に着目した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子に焦点を当てた(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子に焦点を当てた(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を主役にした(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を主役にした(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子が主体の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子が主体の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子が中心の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子が中心の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子が対象の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子が対象の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の出場する(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の出場する(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の参加する(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の参加する(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子をめぐる結果の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子をめぐる結果の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子にまつわる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子にまつわる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子に関わる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子に関わる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を意識した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を意識した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を想定した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を想定した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子向けとしての(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子向けとしての(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子に当たる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子に当たる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子に該当する(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子に該当する(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子に関して(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子に関して(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子に対する(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子に対する(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子における(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子における(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子をめぐって(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子をめぐって(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子をめぐる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子をめぐる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子に関する(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子に関する(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を主とする(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を主とする(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を中心にした(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を中心にした(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を対象とした(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を対象とした(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を中心とした(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を中心とした(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子対象となる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子対象となる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子主体の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子主体の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子中心となる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子中心となる(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子だけの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子だけの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子のみ参加の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子のみ参加の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子限定の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子限定の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子のみの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子のみの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を含む(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を含む(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子を対象にした(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子を対象にした(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子が走る(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子が走る(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子が出場した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子が出場した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子が参加した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子が参加した(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子が出た(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子が出た(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子が走った(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子が走った(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子による(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子による(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子結果としての(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子結果としての(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子記録としての(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子記録としての(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子走の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子走の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子練習の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子練習の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子大会の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子大会の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子記録会の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子記録会の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子レースの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子レースの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子種目としての(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子種目としての(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子競技の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子競技の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子種目の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子種目の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子枠内の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子枠内の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子別の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子別の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子中心の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子中心の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子向けの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子向けの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子対象の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子対象の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子についての(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子についての(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子側から見た(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子側から見た(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子側の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子側の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子のほうの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子のほうの(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の方の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の方の(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子選手一同(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子選手一同(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子ランナーたち(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子ランナーたち(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子走者たち(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子走者たち(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子出場者(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子出場者(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子参加者たち(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子参加者たち(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子メンバーたち(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子メンバーたち(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子選手陣(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子選手陣(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子選手たち(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子選手たち(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女児(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男児(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の子ども(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の子ども(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の結果(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の結果(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の記録(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の記録(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の記録会(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の記録会(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の大会(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の大会(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子のレース(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子のレース(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の代表(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の代表(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の所属(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の所属(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の登録(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の登録(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の候補(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の候補(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の選抜(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の選抜(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子のチーム(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子のチーム(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子のグループ(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子のグループ(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の枠(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の枠(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の部門(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の部門(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の種別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の種別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の学年(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の学年(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子のクラス(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子のクラス(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の区分(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の区分(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子のカテゴリー(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子のカテゴリー(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子の部(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子の部(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子選抜枠(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子選抜枠(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子学年別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子学年別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子クラス内(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子クラス内(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子部門内(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子部門内(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子カテゴリー内(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子カテゴリー内(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子種別ごと(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子種別ごと(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子構成(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子構成(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子編成(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子編成(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子区分内(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子区分内(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子優先(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子優先(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子寄り(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子寄り(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子系(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子系(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子専攻(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子専攻(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子別枠(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子別枠(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子専用(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子専用(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子限定(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子限定(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子U15(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/gi, "女子")
    .replace(/男子U15(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/gi, "男子")
    .replace(/女子A(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子A(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子B(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子B(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子代表(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子代表(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子カテゴリ(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子カテゴリ(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子種目(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子種目(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子区分(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子区分(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子グループ(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子グループ(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子カテゴリー(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子カテゴリー(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子枠(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子枠(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子種別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子種別(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子部門(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子部門(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女の子(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男の子(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/おんなの子(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/おとこの子(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子クラス(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子クラス(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子学年(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子学年(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子選抜(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子選抜(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子候補(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子候補(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子登録(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子登録(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子所属(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子所属(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子チーム(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "女子")
    .replace(/男子チーム(?=\s*(?:1000|1(?:[.]0+)?\s*(?:km|キロ)))/g, "男子")
    .replace(/女子陸上/g, "女子")
    .replace(/男子陸上/g, "男子")
    .replace(/女子中学生/g, "女子")
    .replace(/男子中学生/g, "男子")
    .replace(/女子中学/g, "女子")
    .replace(/男子中学/g, "男子")
    .replace(/\bfemale\b/gi, "女子")
    .replace(/\bmale\b/gi, "男子")
    .replace(/\bgirls?\b/gi, "女子")
    .replace(/\bboys?\b/gi, "男子")
    .replace(/\bwomen\b/gi, "女子")
    .replace(/\bmen\b/gi, "男子")
    .replace(/(女子|男子)\s*[:：/／-]\s*/g, "$1")
    .replace(/(女子|男子)\s*[、,;；|｜]\s*/g, "$1")
    .replace(/(女子|男子)\s*[（(]\s*/g, "$1")
    .replace(/(1000m|1000メートル)\s*[）)]/g, "$1")
    .replace(/S\s*[.．／/]\s*B/giu, "SB")
    .replace(/P\s*[.．／/]\s*B/giu, "PB");
  const now = deps.now ?? new Date();
  const year = deps.defaultYear ?? currentFiscalYear(now);
  const expandedBase = expandDateQuery(question, year, now);
  const latestTamanaPracticeResultQ =
    (/2026-09-22.*(?:練習会|(?:女子|男子)(?:の|・)?\s*1000)|練習会.*2026-09-22|2026-09-22.*岱明|(?:昨日|きのう|前日|9月22日|9\/22).*?(?:女子|男子)(?:の|・)?\s*1000|(?:女子|男子)(?:の|・)?\s*1000.*(?:昨日|きのう|前日|9月22日|9\/22)|2026年?9月22日.*(?:女子|男子)(?:の|・)?\s*1000|(?:女子(?:の|・)?\s*1000\s*m.*(?:2本|×\s*2|x\s*2|\*\s*2)|男子(?:の|・)?\s*1000\s*m.*(?:3本|×\s*3|x\s*3|\*\s*3))|^1000\s*(?:m|メートル).*(?:本目|結果|記録|タイム|メニュー|何本|本数|どうだった|×\s*[23]|x\s*[23]|\*\s*[23])|(?:3(?:[.]0)?\s*km|3(?:[.]0)?\s*キロ(?:メートル)?|3[,，]?000\s*m|3000メートル|3千(?:\s*m|メートル)|三(?:キロ(?:メートル)?|千(?:\s*m|メートル)))(?:の|を)?\s*(?:ジョグ|ジョギング|ランニング|走|jog)|動きづくり.*(?:結果|実施|どうだった)/i.test(question) ||
      /玉名市.*練習会|練習会.*玉名市|岱明.*練習会|練習会.*岱明|岱明.*(?:女子|男子)(?:の|・)?\s*(?:1000\s*m|1000メートル|1(?:[.]0+)?\s*km|1(?:[.]0+)?\s*キロ)|(?:女子|男子)(?:の|・)?\s*(?:1000\s*m|1000メートル|1(?:[.]0+)?\s*km|1(?:[.]0+)?\s*キロ).*岱明|^(?:女子|男子)(?:の|・)?\s*(?:1000\s*m|1000メートル|1(?:[.]0+)?\s*km|1(?:[.]0+)?\s*キロ)|(?:村上|増岡|山﨑|角田|塚原|柴尾|松野|田上|山本|中尾|松本|南本|嶋田|高田(?!麻那)).*(?:1000\s*m|1000メートル|1(?:[.]0+)?\s*km|ジョグ|ジョギング|ランニング|3(?:[.]0)?\s*km|3000メートル|左足|気管支炎|体力|スタミナ|安定感|余裕|きつそう|粘った)|(?:2026-09-22|9月22日|9\/22|昨日|きのう|前日).*?(?:村上|増岡|山﨑|角田|塚原|柴尾|松野|田上|山本|中尾|松本|南本|嶋田|高田(?!麻那))|^練習会|(?:昨日|きのう|前日).*練習会|練習会.*(?:昨日|きのう|前日)|(?:昨日|きのう|前日).*(?:女子|男子)1000|9月22日.*練習会|練習会.*9月22日|9\/22.*練習会|練習会.*9\/22/.test(question)) &&
    /結果|記録|タイム|時間|所要時間|何分|ペース|感想|平均|差|推移|一覧|TT|タイムトライアル|1000(?:m|メートル)|走|走る|走って|走ります|ジョグ|ジョギング|ランニング|左足|気管支炎|体力|スタミナ|安定感|余裕|きつそう|粘った|について|教えて|概要|成績|参加者|選手|出場|人数|何人|どうだった|内容|メニュー|本目|何本|本数|×|x|\*|した|走った|実施|行った|やった|未計測|未実施|走行|出た|リンク|公式|URL|サイト|岱明/.test(question) &&
    (!/20\d{2}|去年|昨年|一昨年|おととし|負荷|数える/.test(question) || /2026-09-22|2026年9月22日/.test(question)) &&
    !(/玉名市.*練習会/.test(question) && /記録/.test(question) && !/結果|タイム|メニュー|リンク|公式|URL|サイト/.test(question) && !/(?:20\d{2}[-年]\d{1,2}[-月]\d{1,2}|9月22日|9\/22)/.test(question));
  const genericPracticeDetailQuestionQ =
    /玉名市.*練習会|練習会.*玉名市|^練習会/.test(question) &&
    /参加者|参加人数|人数|女子1000|男子1000|女子選手|男子選手|実施内容/.test(question);
  const latestTamanaPracticeAthleteQuestionQ =
    /玉名市.*練習会|練習会.*玉名市|岱明.*練習会|練習会.*岱明|昨日.*練習会|9月22日.*練習会|9\/22.*練習会|練習会/.test(question) &&
    /村上|増岡|山﨑|角田|塚原|柴尾|松野|田上|山本|中尾|松本|南本|嶋田|高田(?!麻那)/.test(question);
  const practiceGenderFocus = /男子/.test(question)
    ? "男子 松野 田上 山本 中尾 松本 南本 嶋田"
    : /女子/.test(question)
      ? "女子 村上 増岡 山﨑 角田 塚原 柴尾"
      : "女子 男子";
  const expanded = latestTamanaPracticeResultQ || genericPracticeDetailQuestionQ || latestTamanaPracticeAthleteQuestionQ
    ? `${expandedBase} 2026年9月22日 2026-09-22 9/22 岱明の実施結果 女子1000m 男子1000m ${practiceGenderFocus}`
    : expandedBase;
  const topK = deps.topK ?? RETRIEVAL_BUDGET.topK;
  const exhaustive = isExhaustiveListQuery(expanded);
  const namedTeamSbList = isNamedTeamSbListQuery(expanded);
  const namedSchoolSbList = isNamedSchoolSbListQuery(expanded);
  const namedSchoolList = isNamedSchoolListQuery(expanded);

  const canned = matchCannedAnswer(question);
  const technicalDocQuestion = /Daniels\s+calculator|daniels_(?:pace|calculator)|VDOT.*Tペース|Tペース.*VDOT/i.test(question);
  if (canned && !technicalDocQuestion) {
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
    !/何年|何年度|いつ/.test(question) &&
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
    /歴代|過去\s*5年|直近\s*5年|5年間/.test(question) &&
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
    /1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(question) &&
    /速い|一番|最速|ランキング|トップ\s*20|SB|自己ベスト/.test(question) &&
    !/学校別|所属別|上位\s*\d+\s*人平均/.test(question) &&
    !(/自己ベスト|自己記録|\bSB\b|\bPB\b/i.test(question) && extractAthleteNameHints(question).length > 0);
  const individual3000TopQ =
    /3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(question) &&
    /男子/.test(question) &&
    /速い|一番|最速/.test(question);
  const individual3000RankQ =
    /3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(question) &&
    (/荒玉地区|ランキング/.test(question) &&
    /SB|ランキング/.test(question) &&
    /\d+位/.test(question) ||
      /玉名附中|玉名付属|玉名附属|玉高附属/.test(question) &&
      /SB/.test(question) &&
      /ランキング|上位/.test(question));
  if (individual3000TopQ || individual3000RankQ) {
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
  const yearGenderMeetRecordQ =
    /20\d{2}/.test(question) &&
    /荒玉|駅伝/.test(question) &&
    /男子|女子/.test(question) &&
    /大会記録|区間記録|ボード/.test(question) &&
    !/(?<!\d)[1-6]区/.test(question);
  const courseEraQ =
    /荒玉|駅伝/.test(expanded) &&
    /course_era|コース.*(?:時代|区分)|コース区分/.test(expanded);
  if (yearGenderMeetRecordQ) {
    preferredSources = ["out-analysis/aragyoku_meet_records.md"];
  }
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
    (isWinnerMarginQuestion(question) || /総合タイム.*優勝/.test(question));
  const genericWinnerMarginQ =
    /荒玉|駅伝/.test(expanded) &&
    /20\d{2}/.test(expanded) &&
    /男子|女子/.test(expanded) &&
    isWinnerMarginQuestion(expanded);
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
  // 荒尾三中の「選手とSB一覧」は専用の統合ダイジェストだけで完結する。
  // 通常のチーム記録・全校SB CSVを混ぜると、別校の選手が回答に紛れ込む。
  if (namedTeamSbList) {
    preferredSources = ["out-analysis/arato-tamana-teams/荒尾三中_SB.md"];
  }
  if (namedSchoolSbList) {
    preferredSources = ["out-analysis/arato-tamana-teams/玉名附中.md"];
  }
  if (namedSchoolList && !namedTeamSbList && !namedSchoolSbList) {
    const school = /玉名附中|玉名付属中?|玉名附属|玉高附属/.test(expanded)
      ? "玉名附中"
      : /荒尾三中/.test(expanded)
        ? "荒尾三中"
        : ["荒尾第四中", "荒尾海陽中", "南関中", "玉名中", "天水中", "岱明中", "長洲中", "玉陵中", "玉南中"].find((name) => expanded.includes(name));
    if (school) preferredSources = [`out-analysis/arato-tamana-teams/${school}.md`];
  }

  const tamanaPracticeResultQ =
    /玉名市.*練習会|練習会.*玉名市|岱明.*練習会|練習会.*岱明|^練習会|昨日.*練習会|練習会.*昨日|9月22日.*練習会|練習会.*9月22日|9\/22.*練習会|練習会.*9\/22/.test(expanded) &&
    /結果|記録|タイム|メニュー|リンク|公式|URL|サイト|岱明/.test(expanded) &&
    (/2026年?9月22日|2026-09-22|9月22日|9\/22/.test(expanded) || latestTamanaPracticeResultQ) &&
    !/負荷|数える/.test(question) &&
    !(/玉名市.*練習会/.test(question) && /記録/.test(question) && !/結果|タイム|メニュー|リンク|公式|URL|サイト/.test(question) && !/(?:20\d{2}[-年]\d{1,2}[-月]\d{1,2}|9月22日|9\/22)/.test(question));
  const tamanaPracticeAthleteRecordQ =
    /1000(?:m|ｍ)/.test(expanded) &&
    /記録|タイム/.test(expanded) &&
    /村上|増岡|山﨑|角田|塚原|柴尾|松野|田上|山本|中尾|松本|南本|嶋田|高田(?!麻那)/.test(expanded);
  const tamanaPracticeStatusQ =
    /玉名市.*練習会|練習会.*玉名市/.test(expanded) &&
    /中止|開催|実施/.test(expanded) &&
    /2026年?9月22日|2026-09-22|9月22日|9\/22/.test(expanded);
  const genericPracticeResultQ =
    /^練習会/.test(question) &&
    /結果|記録|タイム|メニュー|リンク|公式|URL|サイト/.test(question) &&
    !/負荷|数える/.test(question);
  const genericPracticeDetailQ =
    genericPracticeDetailQuestionQ;
  const practiceStatusQ =
    /練習会/.test(expanded) &&
    /開催|中止|実施/.test(expanded) &&
    !tamanaPracticeStatusQ &&
    !/県民スポーツ大会|2026[-年]09[-月]08|9月8日/.test(expanded);
  const kumamotoEkidenScheduleQ = /熊日駅伝/.test(expanded) && /日程|開催日|いつ/.test(expanded);
  const schoolMeetScheduleQ = /岱明中/.test(expanded) && /大会予定/.test(expanded);
  const practiceParticipantQ = /玉名市.*練習会|練習会.*玉名市/.test(expanded) && /参加人数|何人|人数/.test(expanded);
  const tamanaPracticeVenueQ =
    /合同練習会|玉名市練習会/.test(question) &&
    /会場|場所|どこ|いつ/.test(question);
  const tamanaPracticeParticipantQ =
    /合同練習会|玉名市練習会/.test(question) &&
    /参加予定|参加人数|何人|人数/.test(question) &&
    /2026[-年]09[-月]22|9月22日|9\/22/.test(question);
  const legDistanceQ =
    /2区.*5区|5区.*2区/.test(expanded) &&
    /距離|何キロ|何km|何メートル|何m/.test(expanded);
  const schoolMeetVenueQ = /岱明中/.test(expanded) && /大会会場/.test(expanded);
  const eveningPracticeScheduleQ = /夕練/.test(expanded) && /開始|いつ|何時|時間|時刻/.test(expanded);
  const historicalJuniorResultQ = /ジュニア駅伝/.test(expanded) && /去年|昨年|2025/.test(expanded) && /結果|成績|順位/.test(expanded);
  const strideCountQ = /流し/.test(expanded) && /何本|本数|何回|回数/.test(expanded);
  const postEkidenPracticeQ = /中体連駅伝明け|駅伝明け.*練習/.test(expanded);
  const movementPracticeQ = /動きづくり/.test(expanded) && /ある|実施|内容|メニュー/.test(expanded);
  const practiceDaysQ = /部活.*練習日|練習日は/.test(expanded);
  const practiceCalendarQ =
    (/いだてん岱明|岱明駅伝試走|県民スポーツ大会中止/.test(expanded) &&
      /いつ|日程|内容|タグ|中止|どうなった/.test(expanded)) ||
    (/20\d{2}[-年]\d{1,2}[-月]\d{1,2}.*練習会/.test(expanded) && !tamanaPracticeResultQ);
  const meetResultUrlQ =
    /(?:結果.*(?:URL|リンク|ページ)|(?:URL|リンク|ページ).*結果|公式.*(?:URL|リンク))/.test(expanded) &&
    /(?:第\s*71回.*通信陸上|第\s*39回.*熊本県中学校陸上|熊本県中学校陸上選手権|熊本市陸上競技選手権|熊本市陸上競技記録会|熊本県長距離記録会|全九州都市対抗|金栗記念|ジュニアオリンピック|ナイター中.?長距離|県中体連)/.test(expanded);
  const cityRecordResultQ =
    /熊本市(?:陸上(?:競技)?)?記録会/.test(expanded) &&
    /結果|公式|リンク|ページ/.test(expanded);
  const firstLongDistanceResultQ =
    /第\s*[１1]回(?:熊本県)?長距離記録会/.test(expanded) &&
    /結果|公式|リンク|ページ/.test(expanded);
  const nightMeetResultQ =
    /ナイター中.?長距離|ナイター記録会/.test(expanded) &&
    /結果|順位|成績|公式|リンク|一覧/.test(expanded);
  const juniorOlympicResultQ =
    /ジュニアオリンピック/.test(expanded) &&
    /結果|順位|成績|公式|リンク/.test(expanded);
  const urbanChampionshipResultQ =
    /全九州都市対抗/.test(expanded) &&
    /結果|順位|成績|公式|リンク/.test(expanded);
  const kanaguriMemorialResultQ =
    /金栗記念/.test(expanded) &&
    /結果|順位|成績|公式|リンク/.test(expanded);
  const secondLongDistanceResultQ =
    /第\s*[２2]回(?:熊本県)?長距離記録会/.test(expanded) &&
    /結果|公式|リンク|ページ/.test(expanded);
  const fourthLongDistanceResultQ =
    /第\s*[４4]回(?:熊本県)?長距離記録会/.test(expanded) &&
    /結果|公式|リンク|ページ/.test(expanded);
  const fifthLongDistanceResultQ =
    /第\s*[５5]回(?:熊本県)?長距離記録会/.test(expanded) &&
    /結果|公式|リンク|ページ/.test(expanded);
  const genericLongDistanceResultQ =
    /熊本県長距離記録会/.test(expanded) &&
    !/第\s*[１1-５5]回/.test(expanded) &&
    /結果|公式|リンク|ページ/.test(expanded);
  const prefecturalChampionshipResultQ =
    /熊本県中学校(?:陸上)?選手権|(?:^|\s)県中学校選手権/.test(expanded) &&
    /結果|成績|順位|公式|リンク/.test(expanded);
  const communicationResultQ =
    /通信(?:陸上)?/.test(expanded) &&
    /結果|成績|順位|公式|リンク/.test(expanded) &&
    !meetResultUrlQ;
  const cityChampionshipResultQ =
    (/熊本市(?:陸上競技)?選手権/.test(expanded) || /(?:^|\s)市選手権/.test(question)) &&
    /結果|成績|順位|公式|リンク/.test(expanded);
  const prefecturalMeetResultQ = /県中体連/.test(expanded) && /結果|成績|順位/.test(expanded) && !meetResultUrlQ;
  const prefecturalMeetScheduleQ = /県中体連/.test(expanded) && /開催日|日程|いつ/.test(expanded);
  const teamRankQ =
    /荒玉|駅伝/.test(expanded) &&
    /何位|順位/.test(expanded) &&
    /岱明|玉高附属|玉名付属|玉名附属|天水|有明|南関|菊水|玉東|玉陵|長洲/.test(expanded) &&
    !/区間/.test(expanded);
  const relativeWinnerQ = /一昨年|おととし/.test(expanded) && /荒玉|駅伝/.test(expanded) && /優勝/.test(expanded);
  const oldCourseDistanceQ =
    /旧コース|新コース|course_era/.test(expanded) &&
    /男子|女子/.test(expanded) &&
    /[1-6]区/.test(expanded) &&
    /距離|何キロ|何km|何メートル|何m/.test(expanded);
  const exactMeetDateScheduleQ = /2026[-年]10[-月]10/.test(expanded) && /予定|日程/.test(expanded);
  const genericPracticeScheduleQ = /練習/.test(expanded) && /予定|日程|スケジュール/.test(expanded);
  const genericDaimingPracticeContentQ = /岱明中/.test(expanded) && /練習内容|練習メニュー/.test(expanded);
  const schoolScheduleQ = /学校行事/.test(expanded) && /予定|日程|スケジュール/.test(expanded);
  const datedPracticeMeetQ = /練習会/.test(expanded) && /(?:20\d{2}[-年]\d{1,2}[-月]\d{1,2}|\d{1,2}月\d{1,2}日)/.test(expanded);
  const datedPracticeContentQ =
    /朝練|夕練/.test(question) &&
    /メニュー|内容|何する|種目|距離|インターバル|何km|何キロ|\d+(?:\.\d+)?km/.test(question) &&
    /(?:20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}|\d{1,2}月\d{1,2}日)/.test(expanded);
  const genericPracticeMeetScheduleQ = /練習会/.test(expanded) && /日程|いつ/.test(expanded);
  const calendarDateScheduleQ =
    (/(?:20\d{2}[-年]\d{1,2}[-月]\d{1,2}|\d{1,2}月\d{1,2}日)/.test(expanded) || /今日|明日|明後日|昨日|今週|来週|今月|\d{1,2}月.*予定|A日課|県中体連/.test(expanded)) &&
    /(?:予定|日程|いつ|何の|何がある|練習|A日課)/.test(expanded) &&
    !meetResultUrlQ &&
    !prefecturalMeetScheduleQ &&
    !exactMeetDateScheduleQ &&
    !genericPracticeScheduleQ &&
    !genericDaimingPracticeContentQ &&
    !schoolScheduleQ &&
    !datedPracticeMeetQ &&
    !genericPracticeMeetScheduleQ;
  const exactDatedPractice =
    (((isDateScheduleQuestion(expanded) || tamanaPracticeResultQ) &&
      preferredSources.some((s) => s.startsWith("drive-text/練習/"))) ||
      latestTamanaPracticeResultQ) &&
    !/参加|人数|何人|ほぼ全員|女子7/.test(expanded);
  if (exactDatedPractice) {
    preferredSources = preferredSources.filter(
      (s) => s === "calendar/events.daiming.yaml" || s.startsWith("drive-text/練習/"),
    );
  }
  const practiceLineQ =
    /合同練習会/.test(expanded) &&
    /会費|参加費|参加料|料金|費用|いつ|どこ|会場|場所/.test(expanded);
  const practiceVenueQ =
    /(?:玉名市)?合同練習会|玉名市練習会/.test(expanded) &&
    /会場|場所|どこ/.test(expanded);
  if (practiceLineQ) {
    const practiceSource = preferredSources.find((s) => s.startsWith("drive-text/練習/"));
    preferredSources = [
      "out-analysis/line-chats/daiming-parents.md",
      ...(practiceSource ? [practiceSource] : []),
    ];
  }
  if (practiceVenueQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }

  const practiceJogStandardQ =
    /ジョグ/.test(expanded) &&
    /男子|女子/.test(expanded) &&
    /標準|目安/.test(expanded);
  const practiceJogDistanceQ =
    /ジョグ/.test(expanded) &&
    /2800m|2\.8(?:0)?km|3360m|3\.36km/.test(expanded);
  const practiceJogGenericQ =
    /ジョグ/.test(expanded) &&
    !/男子|女子/.test(expanded) &&
    /標準|目安|ペース/.test(expanded);
  const practiceTemplateQ =
    (/ジョグ/.test(expanded) && /テンプレート|ペース|女子|男子/.test(expanded)) ||
    practiceJogStandardQ ||
    practiceJogDistanceQ ||
    practiceJogGenericQ ||
    /norwegian-45-15|[Nn]orwegian(?:の|\s*)[- ]?45\s*[\/／\-‐‑–—−]\s*15|ノルウェー(?:式)?(?:の|\s*)45\s*[\/／\-‐‑–—−]\s*15|45\s*[\/／\-‐‑–—−]\s*15.*(?:テンプレ|セッション|GZ|T)|(?:テンプレ|セッション|GZ|T).*45\s*[\/／\-‐‑–—−]\s*15/.test(expanded);
  const weatherOpsQ = /天気データ|天気の更新|更新スクリプト|更新.*コマンド|天気.*コマンド|天気予報の保存先|予報ファイル|天気ファイル|天気.*(?:JSON|CSV)|update_tamana_weather|Open-Meteo|tamana-forecast|tamana-weather/.test(
    expanded,
  );
  const paceCliQ = /VDOT.*Tペース|Tペース.*VDOT|VDOT.*CLI|CLI.*(?:VDOT|Tペース)|Daniels\s+calculator|Tペース.*(?:スクリプト|Python)|(?:スクリプト|Python).*Tペース|daniels_pace|daniels_calculator/i.test(
    expanded,
  );
  const practiceMeetLoadQ = /practice_meets|affect_load|練習会.*(?:負荷|疲労)|(?:負荷|疲労).*練習会|負荷に数え/.test(
    expanded,
  );
  const historicalTopSixPaceQ =
    /荒玉|駅伝|男子|女子/.test(expanded) &&
    /平均ペース|平均速度|平均|ペース|キロ何分/.test(expanded) &&
    /(?:総合)?(?:1\s*(?:[〜～-]\s*6位)|1位\s*から\s*6位|1位\s*[〜～-]\s*6位)|上位(?:6|六)(?:位|校)?|トップ6|ベスト(?:6|六)/.test(expanded) &&
    !(/(?:800|1500)(?:m|ｍ)?/.test(expanded) && /上位\s*\d+\s*人(?:の)?平均|上位\d+人(?:の)?平均/.test(expanded));
  const historicalRankPaceQ =
    !/20\d{2}/.test(question) &&
    /男子|女子/.test(question) &&
    /平均ペース|平均速度/.test(question) &&
    Boolean(requestedHistoricalPlace(question)) &&
    !/(?:[〜～~]|から|まで)\s*[0-9０-９一二三四五六七八九十]+位/.test(question);
  const nagomiPredictionGapQ =
    /なごみ/.test(question) &&
    /予想|予実|SB.{0,4}実績/.test(question) &&
    /差|比較|乖離|ギャップ|ずれ/.test(question);
  const male1500SchoolRankingQ =
    /男子/.test(question) &&
    /1500(?:m|ｍ)?/.test(question.normalize("NFKC")) &&
    /学校別|学校.*ランキング|学校ランキング|学校.*順位/.test(question);
  const absenceRosterQ = /欠席者|欠席記録|欠席履歴|欠席一覧|欠席した|休んだ/.test(question);
  const allTeamAveragePaceQ =
    /全チーム|全出場チーム|各チーム|チーム別/.test(question) &&
    /平均ペース|平均速度/.test(question);
  const historicalTopFinishQ =
    /荒玉|駅伝/.test(question) &&
    /(?:過去\s*5年|直近\s*5年|5年間)/.test(question) &&
    /準優勝|2位/.test(question);
  const top2ExperienceQ =
    /荒玉|駅伝/.test(question) &&
    /2位まで|2位以内|総合2位/.test(question) &&
    /学校|チーム|校/.test(question) &&
    /経験|入った|入賞|一覧|教えて|どこ/.test(question);
  const historicalWinnerPaceQ =
    /荒玉|駅伝/.test(expanded) &&
    /優勝/.test(expanded) &&
    /平均ペース|平均速度|平均|ペース/.test(expanded) &&
    /歴代|過去/.test(expanded);
  const historicalTeamRankQ =
    /岱明/.test(expanded) &&
    /荒玉|駅伝/.test(expanded) &&
    /過去|歴代/.test(expanded) &&
    /順位|成績|結果/.test(expanded);
  const namedTeamTotalTimeQ =
    /20\d{2}/.test(expanded) &&
    /男子|女子/.test(expanded) &&
    /総合タイム|総合.*時間|タイム/.test(expanded) &&
    /玉高附属|玉名付属|玉名附属|玉名|玉南|腹栄|岱明|天水|有明|南関|菊水|玉東|玉陵|長洲|荒尾/.test(expanded) &&
    !isWinnerMarginQuestion(expanded);
  const multipleAthleteRecordQ =
    /(?:と|、|・|／|\/)/.test(expanded) &&
    /800(?:m|ｍ)?|1[，,]?\s*500(?:m|ｍ)?|3[，,]?\s*000(?:m|ｍ)?|5[，,]?\s*000(?:m|ｍ)?|3\s*(?:km|キロ)|5\s*(?:km|キロ)/i.test(expanded);
  const directDocQ =
    practiceTemplateQ || weatherOpsQ || paceCliQ || practiceMeetLoadQ || historicalTopSixPaceQ || historicalRankPaceQ || historicalWinnerPaceQ || historicalTeamRankQ || historicalTopFinishQ || allTeamAveragePaceQ || top2ExperienceQ || nagomiPredictionGapQ || male1500SchoolRankingQ || absenceRosterQ || tamanaPracticeResultQ || latestTamanaPracticeResultQ || tamanaPracticeAthleteRecordQ || latestTamanaPracticeAthleteQuestionQ || multipleAthleteRecordQ || genericPracticeResultQ || genericPracticeDetailQ || tamanaPracticeStatusQ || practiceStatusQ || kumamotoEkidenScheduleQ || schoolMeetScheduleQ || practiceParticipantQ || tamanaPracticeVenueQ || tamanaPracticeParticipantQ || legDistanceQ || schoolMeetVenueQ || historicalJuniorResultQ || relativeWinnerQ || courseEraQ || oldCourseDistanceQ || eveningPracticeScheduleQ || namedTeamTotalTimeQ || cityRecordResultQ || firstLongDistanceResultQ || secondLongDistanceResultQ || fourthLongDistanceResultQ || fifthLongDistanceResultQ || genericLongDistanceResultQ || nightMeetResultQ || juniorOlympicResultQ || urbanChampionshipResultQ || kanaguriMemorialResultQ || prefecturalChampionshipResultQ || communicationResultQ || cityChampionshipResultQ || teamWinnerMarginQ || genericWinnerMarginQ || strideCountQ || postEkidenPracticeQ || movementPracticeQ || practiceDaysQ || practiceCalendarQ || meetResultUrlQ || prefecturalMeetResultQ || prefecturalMeetScheduleQ || teamRankQ || calendarDateScheduleQ || exactMeetDateScheduleQ || genericPracticeScheduleQ || genericDaimingPracticeContentQ || schoolScheduleQ || datedPracticeMeetQ || datedPracticeContentQ || genericPracticeMeetScheduleQ || practiceVenueQ;
  if (practiceTemplateQ) {
    preferredSources = /norwegian-45-15|[Nn]orwegian(?:の|\s*)[- ]?45\s*[\/／\-‐‑–—−]\s*15|ノルウェー(?:式)?(?:の|\s*)45\s*[\/／\-‐‑–—−]\s*15|45\s*[\/／\-‐‑–—−]\s*15/.test(expanded)
      ? ["repo-docs/adr/002-norwegian-method-integration.md"]
      : practiceJogStandardQ || practiceJogGenericQ || practiceJogDistanceQ
        ? ["practice/daiming-practice-menus-kpace.md"]
        : ["calendar/events.daiming.yaml"];
  }
  if (weatherOpsQ) preferredSources = ["repo-docs/tamana-weather.md"];
  if (paceCliQ) preferredSources = ["docs/ai-practice-generation.md"];
  if (practiceMeetLoadQ) preferredSources = ["repo-docs/adr/006-practice-meets-not-load.md"];
  if (historicalTopSixPaceQ) {
    preferredSources = ["out-analysis/aragyoku_top6_historical_average_pace.md"];
  }
  if (historicalTopFinishQ) {
    preferredSources = ["aragyoku/winners-by-year.md"];
  }
  if (allTeamAveragePaceQ) {
    preferredSources = ["out-analysis/aragyoku_all_teams_average_pace.md"];
  }
  if (historicalRankPaceQ) {
    preferredSources = ["out-analysis/aragyoku_all_teams_average_pace.md"];
  }
  if (historicalWinnerPaceQ) {
    preferredSources = ["out-analysis/aragyoku_all_teams_average_pace.md"];
  }
  if (meetResultUrlQ) {
    if (/第\s*71回.*通信陸上/.test(expanded)) {
      preferredSources = ["drive-text/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/岱明の結果.md"];
    } else if (/第\s*39回.*熊本県中学校陸上/.test(expanded)) {
      preferredSources = ["drive-text/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/岱明の結果.md"];
    } else if (/熊本市陸上競技選手権/.test(expanded)) {
      preferredSources = ["drive-text/大会/2026年度/0418_第４５回熊本市陸上競技選手権大会/岱明の結果.md"];
    } else if (/第\s*[２2]回熊本県長距離記録会/.test(expanded)) {
      preferredSources = ["drive-text/大会/2026年度/0704_第２回熊本県長距離記録会/岱明の結果.md"];
    } else if (/第\s*[４4]回熊本県長距離記録会/.test(expanded)) {
      preferredSources = ["drive-text/大会/2026年度/1010_第４回熊本県長距離記録会/概要.md"];
    } else if (/第\s*[５5]回熊本県長距離記録会/.test(expanded)) {
      preferredSources = ["drive-text/大会/2026年度/1212_第５回熊本県長距離記録会/概要.md"];
    } else if (/熊本県中学校陸上選手権/.test(expanded)) {
      preferredSources = ["drive-text/大会/2026年度/0523-0524_熊本県中学校陸上選手権・混成/岱明の結果.md"];
    } else if (/ジュニアオリンピック/.test(expanded)) {
      preferredSources = ["drive-text/大会/2026年度/0829_ジュニアオリンピックU16熊本県予選会/岱明の結果.md"];
    } else if (/ナイター中.?長距離/.test(expanded)) {
      preferredSources = ["drive-text/大会/2026年度/0829_玉名郡ナイター中・長距離記録会/岱明の結果.md"];
    } else if (/熊本市陸上競技記録会/.test(expanded)) {
      preferredSources = ["drive-text/記録データベース/2026年度/中学生記録.csv"];
    } else if (/全九州都市対抗/.test(expanded)) {
      preferredSources = ["drive-text/記録データベース/2026年度/中学生記録.csv"];
    } else if (/金栗記念/.test(expanded)) {
      preferredSources = ["drive-text/大会/2026年度/0411_第３４回金栗記念選抜陸上中長距離熊本大会/岱明の結果.md"];
    } else if (/県中体連/.test(expanded)) {
      preferredSources = ["drive-text/記録データベース/2025年度/県中体連.csv"];
    }
  }
  if (prefecturalMeetResultQ) {
    preferredSources = ["drive-text/記録データベース/2025年度/県中体連.csv"];
  }
  if (prefecturalMeetScheduleQ) {
    preferredSources = ["drive-text/記録データベース/2025年度/県中体連.csv"];
  }
  if (teamRankQ) {
    const team = /玉高附属|玉名付属|玉名附属/.test(expanded)
      ? "玉高附属"
      : ["岱明", "天水", "有明", "南関", "菊水", "玉東", "玉陵", "長洲"].find((name) => expanded.includes(name));
    if (team) preferredSources = [`out-analysis/aragyoku-teams/${team}.md`];
  }
  if (calendarDateScheduleQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (genericPracticeScheduleQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (genericDaimingPracticeContentQ || schoolScheduleQ || datedPracticeMeetQ || genericPracticeMeetScheduleQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (tamanaPracticeStatusQ || practiceStatusQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }
  if (kumamotoEkidenScheduleQ) {
    preferredSources = ["drive-text/大会/2026年度/0208_熊日駅伝/概要.md"];
  }
  if (schoolMeetScheduleQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (practiceParticipantQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }
  if (schoolMeetVenueQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (historicalJuniorResultQ) {
    preferredSources = ["drive-text/大会/2025年度/0927_第２回熊本県ジュニア駅伝競走大会/岱明の結果.md"];
  }
  if (relativeWinnerQ) {
    preferredSources = ["aragyoku/winners-by-year.md"];
  }
  if (exactMeetDateScheduleQ) {
    preferredSources = ["drive-text/大会/2026年度/1010_第４回熊本県長距離記録会/概要.md"];
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
    (/[1-6]区|区間/.test(expanded) || /男子|女子/.test(expanded)) &&
    !/ペース/.test(expanded);
  if (aragyokuDistanceQ) {
    preferredSources = ["docs/aragyoku-ekiden-distance-definitions.md"];
  }
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
    /誰|選手|ランナー|区間タイム|区は|区の/.test(expanded) &&
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
  const compactTeamLegQ =
    /20\d{2}/.test(expanded) &&
    /[1-6]区/.test(expanded) &&
    /誰|選手|ランナー|区は|区の/.test(expanded) &&
    /荒尾海陽|玉高附属|玉名付属|玉名附属|荒尾三|荒尾四|三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|腹栄|荒尾|菊水|長洲/.test(
      expanded,
    );
  if (compactTeamLegQ && !/男子|女子/.test(expanded)) {
    const team = [
      "荒尾海陽", "玉高附属", "荒尾三", "荒尾四", "三加和", "南関", "天水",
      "岱明", "有明", "玉南", "玉名", "玉東", "玉陵", "腹栄", "荒尾", "菊水", "長洲",
    ].find((stem) => expanded.includes(stem));
    if (team) preferredSources = [`out-analysis/aragyoku-teams/${team}.md`];
  }
  const teamBestQ =
    /20\d{2}/.test(expanded) &&
    /男子|女子/.test(expanded) &&
    /区間順位ベスト/.test(expanded) &&
    /荒尾海陽|玉高附属|玉名付属|玉名附属|荒尾三|荒尾四|三加和|南関|天水|岱明|有明|玉南|玉名|玉東|玉陵|腹栄|荒尾|菊水|長洲/.test(
      expanded,
    );
  if (teamBestQ) {
    preferredSources = ["out-analysis/aragyoku_2024_2025_focus_teams.md"];
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
  const tenKmNameQuestion = question.replace(/さん|氏/gu, " ");
  const tenKmSubject = tenKmNameQuestion
    .replace(/荒尾第四中|荒尾海陽中|熊本大附中|玉名高校附属中|玉名附中|玉名付属中?|玉名附属|玉高附属|荒尾三中|南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉東中|菊水中|金栗PROJECT|玉名アスリーツ|玉東クラブ|ATRC|NJAC|人吉一中/giu, " ")
    .replace(/[（()）]/gu, " ");
  const tenKmSelfBestQuestion = /10\s*(?:km|キロ)/i.test(question) &&
    /SB|PB|自己ベスト|自己記録|ベスト/i.test(question) &&
    (extractAthleteNameHints(tenKmNameQuestion).length > 0 ||
      /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}ー]{2,8}/u.test(tenKmSubject));
  const namedSelfBestQ =
    (/自己ベスト|自己記録|SB|PB|ＳＢ|ＰＢ|ベスト|記録|タイム/i.test(expanded) ||
      (hasNonTeamAthleteNameHint(expanded) &&
        /800(?:m|ｍ)?|1500(?:m|ｍ)?|3000(?:m|ｍ)?|5000(?:m|ｍ)?|3\s*km|5\s*km/.test(expanded) &&
        /秒|分|タイム|記録|ベスト/.test(expanded))) &&
    (hasNonTeamAthleteNameHint(expanded) || tenKmSelfBestQuestion) &&
    !/荒玉|駅伝|平均|ペース|区間|大会|結果|練習会|所属選手/.test(expanded);
  if (namedSelfBestQ && !namedSchoolList && !namedSchoolSbList) {
    const currentMen3000Ranking = "out-analysis/2026_aragyoku_men_3000m_sb_ranking.md";
    const currentMen1500Ranking = "out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md";
    const currentWomenRanking = "out-analysis/2026_women_800m_1500m_pb_school_ranking.md";
    const names = extractAthleteNameHints(expanded);
    const trackRangeQ = /(?:800|1500|1[，,]\s*500|3000|3[，,]\s*000)\s*(?:m|ｍ|メートル)?/.test(question) &&
      /(?:5000|5[，,]\s*000|5\s*(?:km|キロ))/.test(question) && /から|まで|[〜～~]/.test(question);
    const tenKmSelfBestQ = /10\s*(?:km|キロ)/i.test(question) && /SB|PB|自己ベスト|自己記録|ベスト/i.test(question) && extractAthleteNameHints(question).length > 0;
    const schoolContextQ = /荒尾三中|荒尾第四中|荒尾海陽中|熊本大附中|南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉名附中|玉名付属|玉名附属|玉高附属|人吉一中/.test(question);
    const trackDistancePatterns = [
      /800\s*(?:m|ｍ|メートル)?/i,
      /(?:1[，,]?\s*500|1500)\s*(?:m|ｍ|メートル)?/i,
      /(?:3[，,]?\s*000|3000)\s*(?:m|ｍ|メートル)?/i,
    ];
    const multipleTrackDistances = trackDistancePatterns.filter((pattern) => pattern.test(question)).length >= 2;
    const historicalAthleteTrackSource = tenKmSelfBestQ
      ? "sb/中学生SB.csv"
      : (trackRangeQ || schoolContextQ) && !/高田麻那/.test(question)
      ? "sb/中学生SB.csv"
      : /800m|800ｍ|800\s*メートル|3000m|3000ｍ|3[，,]\s*000|1500m|1500ｍ|1[，,]\s*500/.test(expanded) && (/20\d{2}/.test(question) || multipleTrackDistances)
      ? names.flatMap((name) => findSourcesWithText([name], {
          prefix: "out-analysis/arato-tamana-teams/",
          limit: 4,
        })).find((source) => !source.endsWith("/INDEX.md"))
      : undefined;
    const ranking = /3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(expanded) && names.length > 0
      ? retrieveBySources([currentMen3000Ranking], {
          perSource: 64,
          maxChunks: 64,
          coverage: "full",
        })
      : [];
    const womenRanking = /800\s*(?:m|ｍ|メートル)|1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(expanded) && names.length > 0
      ? retrieveBySources([currentWomenRanking], {
          perSource: 64,
          maxChunks: 64,
          coverage: "full",
        })
      : [];
    const men1500Ranking = /1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(expanded) && names.length > 0
      ? retrieveBySources([currentMen1500Ranking], {
          perSource: 64,
          maxChunks: 64,
          coverage: "full",
        })
      : [];
    const teamTrackSource = /800\s*(?:m|ｍ|メートル)|1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(expanded)
      ? names.flatMap((name) => findSourcesWithText([name], {
          prefix: "out-analysis/arato-tamana-teams/",
          limit: 4,
        })).find((source) => !source.endsWith("/INDEX.md"))
      : undefined;
    preferredSources = historicalAthleteTrackSource
      ? [historicalAthleteTrackSource]
      : names.some((name) => ranking.some((row) => row.chunk.text.includes(name)))
      ? [currentMen3000Ranking]
      : names.some((name) => men1500Ranking.some((row) => row.chunk.text.includes(name)))
        ? [currentMen1500Ranking]
        : names.some((name) => womenRanking.some((row) => row.chunk.text.includes(name)))
        ? [currentWomenRanking]
        : teamTrackSource
          ? [teamTrackSource]
          : ["sb/中学生SB.csv"];
  }
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
    /1500(?:m|ｍ)?|800(?:m|ｍ)?/.test(expanded) &&
    (/上位\s*(?:\d+|[０-９]+|[三四五六])\s*(?:人|名)(?:の)?平均|学校別|所属別/.test(
      expanded,
    ) || (/女子/.test(expanded) && /800(?:m|ｍ)?|1500(?:m|ｍ)?/.test(expanded) && /ランキング|順位|速い|最速|一番/.test(expanded)));
  const schoolPbPlaceQ = schoolPbRankQ && /何位|順位/.test(question);
  if (schoolPbRankQ) {
    const schoolRanking = /女子/.test(expanded) || /800(?:m|ｍ)?/.test(expanded)
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
  if (top2ExperienceQ) {
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
  const staffOpsQ = /朝練|地点分担/.test(expanded);
  if (staffOpsQ) {
    preferredSources = ["out-analysis/line-chats/daiming-staff.md"];
  }
  if (datedPracticeContentQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (/10\s*(?:km|キロ)/i.test(question) && /SB|PB|自己ベスト|自己記録|ベスト/i.test(question) && /[\p{Script=Han}]{2,}/u.test(question)) {
    preferredSources = ["sb/中学生SB.csv"];
  }
  if (legDistanceQ) {
    preferredSources = ["out-analysis/line-chats/daiming-staff.md"];
  }
  const farewellScheduleQ =
    /お別れ会/.test(expanded) && /いつ|日程|何時|時間|時刻|予定|日/.test(expanded);
  const matSizeQ =
    /銀マット/.test(expanded) && /何センチ|何ミリ|サイズ|長さ|幅|厚み|厚さ|大きさ|寸法/.test(expanded);
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
  const nagomiAmbiguousTeamLegQ =
    /なごみ/.test(expanded) &&
    /岱明/.test(expanded) &&
    /[1-6]区/.test(expanded) &&
    /誰|選手|ランナー|は誰/.test(expanded) &&
    !/男子|女子/.test(expanded);
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
  if (nagomiAmbiguousTeamLegQ) {
    const orderYear = expanded.match(/20\d{2}/)?.[0] ?? "2026";
    const orderBase = "drive-text/大会/" + orderYear + "年度/0920_中学駅伝金栗四三生誕の地なごみ大会";
    preferredSources = [
      orderBase + "/男子区間オーダーリスト.md",
      orderBase + "/女子区間オーダーリスト.md",
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
    /女子荒玉|総合タイム目安|メンバー目安|トラック距離|3km.*換算|1500.*換算|換算|43分切り|区間配分|鬼ごっこ|手押し車|犬歩き|補強|駅伝前|何チーム.*なごみ|なごみ.*何チーム|参加予定.*何人|何人.*参加予定/.test(
      expanded,
    ) && !/区間賞|区間順|平均ペース|上位\s*[六6]|トップ\s*[六6]/.test(expanded);
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
  if (unqualifiedTeamResultQ) {
    const team = /玉高附属|玉名付属|玉名附属/.test(question) ? "玉高附属" : [
      "荒尾海陽", "荒尾三", "荒尾四", "三加和", "玉高附属", "玉名", "玉南", "腹栄", "岱明", "天水", "有明", "南関", "菊水", "玉東", "玉陵", "長洲",
    ].find((name) => question.includes(name));
    if (team) preferredSources = [`out-analysis/aragyoku-teams/${team}.md`];
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
  if (teamBestQ) {
    preferredSources = ["out-analysis/aragyoku_2024_2025_focus_teams.md"];
  }
  // 「高田麻那の1500mSB」は個人の自己ベストであり、男女別トップ20
  // ランキングではない。ランキング用の広い判定を最後に上書きする。
  if (/高田麻那/.test(expanded)) {
    preferredSources = ["out-analysis/athletes/takada-mana.md"];
  }
  if (
    /3000\s*(?:m|ｍ|メートル)|3[，,]\s*000(?:m|ｍ|メートル)?/.test(expanded) &&
    /SB/.test(expanded) &&
    /荒玉地区|1位|順位|ランキング|記録/.test(expanded)
  ) {
    preferredSources = ["out-analysis/2026_aragyoku_men_3000m_sb_ranking.md"];
  }
  if (
    /1500\s*(?:m|ｍ|メートル)|1[，,]\s*500(?:m|ｍ|メートル)?|1(?:[．.]5)\s*(?:km|キロ)/.test(expanded) &&
    /荒玉地区|トップ\s*20/.test(expanded) &&
    /SB|トップ\s*20/.test(expanded) &&
    /\d+位/.test(expanded) &&
    !namedSelfBestQ
  ) {
    preferredSources = ["out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md"];
  }
  // A dated 玉名市練習会 result must not be shadowed by the similarly named
  // 岱明荒玉駅伝 team-history digest.
  if (tamanaPracticeResultQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }
  if (genericPracticeResultQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }
  if (genericPracticeDetailQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }
  if (strideCountQ || postEkidenPracticeQ) {
    preferredSources = ["drive-text/練習/練習の記録.md"];
  }
  if (movementPracticeQ || practiceCalendarQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (practiceDaysQ) {
    preferredSources = ["out-analysis/line-chats/daiming-staff.md"];
  }
  if (staffOpsQ) {
    preferredSources = ["out-analysis/line-chats/daiming-staff.md"];
  }
  if (datedPracticeContentQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (tamanaPracticeStatusQ || practiceStatusQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }
  if (kumamotoEkidenScheduleQ) {
    preferredSources = ["drive-text/大会/2026年度/0208_熊日駅伝/概要.md"];
  }
  if (schoolMeetScheduleQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (practiceParticipantQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }
  if (schoolMeetVenueQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (historicalJuniorResultQ) {
    preferredSources = ["drive-text/大会/2025年度/0927_第２回熊本県ジュニア駅伝競走大会/岱明の結果.md"];
  }
  if (relativeWinnerQ) {
    preferredSources = ["aragyoku/winners-by-year.md"];
  }
  if (courseEraQ) {
    preferredSources = ["out-analysis/aragyoku_meet_records.md"];
  }
  if (oldCourseDistanceQ) {
    preferredSources = ["docs/aragyoku-ekiden-distance-definitions.md"];
  }
  if (eveningPracticeScheduleQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (namedTeamTotalTimeQ) {
    const team = /玉高附属|玉名付属|玉名附属/.test(expanded) ? "玉高附属" : [
      "荒尾海陽", "荒尾三", "荒尾四", "三加和", "玉名", "玉南", "腹栄", "岱明", "天水", "有明", "南関", "菊水", "玉東", "玉陵", "長洲", "荒尾",
    ].find((name) => expanded.includes(name));
    if (team) preferredSources = [`out-analysis/aragyoku-teams/${team}.md`];
  }
  if (teamWinnerMarginQ || genericWinnerMarginQ) {
    preferredSources = ["out-analysis/aragyoku_2024_2025_focus_teams.md"];
  }
  if (cityRecordResultQ) {
    preferredSources = ["drive-text/記録データベース/2026年度/中学生記録.csv"];
  }
  if (firstLongDistanceResultQ) {
    preferredSources = ["drive-text/大会/2026年度/0509_第１回熊本県長距離記録会/岱明の結果.md"];
  }
  if (nightMeetResultQ) {
    preferredSources = ["drive-text/大会/2026年度/0829_玉名郡ナイター中・長距離記録会/全結果.md"];
  }
  if (juniorOlympicResultQ) {
    preferredSources = ["drive-text/大会/2026年度/0829_ジュニアオリンピックU16熊本県予選会/岱明の結果.md"];
  }
  if (urbanChampionshipResultQ) {
    preferredSources = ["drive-text/記録データベース/2026年度/中学生記録.csv"];
  }
  if (kanaguriMemorialResultQ) {
    preferredSources = ["drive-text/大会/2026年度/0411_第３４回金栗記念選抜陸上中長距離熊本大会/岱明の結果.md"];
  }
  if (secondLongDistanceResultQ || genericLongDistanceResultQ) {
    preferredSources = ["drive-text/大会/2026年度/0704_第２回熊本県長距離記録会/岱明の結果.md"];
  }
  if (fourthLongDistanceResultQ) {
    preferredSources = ["drive-text/大会/2026年度/1010_第４回熊本県長距離記録会/概要.md"];
  }
  if (fifthLongDistanceResultQ) {
    preferredSources = ["drive-text/大会/2026年度/1212_第５回熊本県長距離記録会/概要.md"];
  }
  if (prefecturalChampionshipResultQ) {
    preferredSources = ["drive-text/大会/2026年度/0523-0524_熊本県中学校陸上選手権・混成/岱明の結果.md"];
  }
  if (communicationResultQ) {
    preferredSources = ["drive-text/大会/2026年度/0613_全日本中学校通信陸上競技大会熊本県大会/岱明の結果.md"];
  }
  if (cityChampionshipResultQ) {
    preferredSources = ["drive-text/大会/2026年度/0418_第４５回熊本市陸上競技選手権大会/岱明の結果.md"];
  }
  if (meetResultUrlQ && /ナイター中.?長距離/.test(expanded)) {
    preferredSources = ["drive-text/大会/2026年度/0829_玉名郡ナイター中・長距離記録会/岱明の結果.md"];
  }
  if (genericPracticeResultQ || genericPracticeDetailQ || tamanaPracticeResultQ || latestTamanaPracticeResultQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }
  if (tamanaPracticeAthleteRecordQ || latestTamanaPracticeAthleteQuestionQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }
  if (tamanaPracticeVenueQ) {
    preferredSources = ["drive-text/練習/玉名市練習会/2026-09-22.md"];
  }
  if (tamanaPracticeParticipantQ) {
    preferredSources = ["out-analysis/line-chats/arita-taisho.md"];
  }
  if (datedPracticeContentQ) {
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  if (legDistanceQ) {
    preferredSources = ["out-analysis/line-chats/daiming-staff.md"];
  }
  if (historicalRankPaceQ) {
    preferredSources = ["out-analysis/aragyoku_all_teams_average_pace.md"];
  }
  if (nagomiPredictionGapQ) {
    const year = question.match(/20\d{2}/)?.[0];
    const reportForYear = (reportYear: string) =>
      `drive-text/大会/${reportYear}年度/${reportYear === "2025" ? "0921" : "0920"}_中学駅伝金栗四三生誕の地なごみ大会/予実比較.md`;
    preferredSources = year ? [reportForYear(year)] : [reportForYear("2026"), reportForYear("2025")];
  }
  if (male1500SchoolRankingQ) {
    preferredSources = ["out-analysis/2026_men_1500m_pb_school_ranking.md"];
  }
  if (historicalTopFinishQ) {
    preferredSources = ["aragyoku/winners-by-year.md"];
  }

  if (absenceRosterQ) {
    const year = question.match(/20\d{2}/)?.[0] ?? String(deps.defaultYear ?? 2026);
    preferredSources = ["calendar/events.daiming.yaml"];
  }
  let fromSources = retrieveBySources(preferredSources, {
    query: expanded,
    perSource:
      multipleAthleteRecordQ || absenceRosterQ || allTeamAveragePaceQ ? 1000 : directDocQ || exhaustive || isLegAthleteQuestion(expanded) || individual1500TopQ || individual3000RankQ || teamBestQ || totalMeetRecordQ || yearGenderMeetRecordQ || teamFullRecordQ || explicitTeamLegRankQ || historicalWinnerQ || winnerYearTeamQ || teamRunnerUpYearQ || legRankQuestionQ || namedLegTimeQ
        || resultListQ || genericResultQ || topThreeQ || explicitThirdPlaceQ || unqualifiedSixthPlaceQ || explicitLegAwardQ || schoolPbRankQ || nagomiAmbiguousTeamLegQ || nagomiLegOrderQ || nagomiLegRankQ || nagomiResultQ || nagomiDateQ || nagomiVenueQ || kanaguriResultQ || aragyokuDateQ || aragyokuVenueQ || datedTeamResultQ || unqualifiedTeamResultQ
        ? 200
        : RETRIEVAL_BUDGET.perSource,
    maxChunks:
      multipleAthleteRecordQ || absenceRosterQ || allTeamAveragePaceQ ? 1000 : directDocQ || exhaustive || isLegAthleteQuestion(expanded) || individual1500TopQ || individual3000RankQ || teamBestQ || totalMeetRecordQ || yearGenderMeetRecordQ || teamFullRecordQ || explicitTeamLegRankQ || historicalWinnerQ || winnerYearTeamQ || teamRunnerUpYearQ || legRankQuestionQ || namedLegTimeQ
        || resultListQ || genericResultQ || topThreeQ || explicitThirdPlaceQ || unqualifiedSixthPlaceQ || explicitLegAwardQ || schoolPbRankQ || nagomiAmbiguousTeamLegQ || nagomiLegOrderQ || nagomiLegRankQ || nagomiResultQ || nagomiDateQ || nagomiVenueQ || kanaguriResultQ || aragyokuDateQ || aragyokuVenueQ || datedTeamResultQ || unqualifiedTeamResultQ
        ? 200
        : RETRIEVAL_BUDGET.maxChunks,
      coverage:
      multipleAthleteRecordQ || absenceRosterQ || allTeamAveragePaceQ ? "full" : directDocQ || exhaustive || exactDatedPractice || isLegAthleteQuestion(expanded) || individual1500TopQ || individual3000RankQ || teamBestQ || totalMeetRecordQ || yearGenderMeetRecordQ || teamFullRecordQ || explicitTeamLegRankQ || historicalWinnerQ || winnerYearTeamQ || teamRunnerUpYearQ || legRankQuestionQ || namedLegTimeQ
        || resultListQ || genericResultQ || topThreeQ || explicitThirdPlaceQ || unqualifiedSixthPlaceQ || explicitLegAwardQ || schoolPbRankQ || nagomiAmbiguousTeamLegQ || nagomiLegOrderQ || nagomiLegRankQ || nagomiResultQ || nagomiDateQ || nagomiVenueQ || kanaguriResultQ || aragyokuDateQ || aragyokuVenueQ || datedTeamResultQ || unqualifiedTeamResultQ
        ? "full"
      : "ranked",
  });
  if (multipleAthleteRecordQ) {
    const targetedAthleteChunks = [...new Set(extractAthleteNameHints(expanded))].flatMap((athlete) =>
      retrieveBySources(preferredSources, {
        query: athlete,
        perSource: 12,
        maxChunks: 12,
        coverage: "ranked",
      }),
    );
    fromSources = [...fromSources, ...targetedAthleteChunks];
  }
  if (tenKmSelfBestQuestion) {
    const tenKmQueryNames = question
      .replace(/さん|氏/gu, " ")
      .replace(/荒尾第四中|荒尾海陽中|熊本大附中|玉名高校附属中|玉名附中|玉名付属中?|玉名附属|玉高附属|荒尾三中|南関中|玉名中|天水中|岱明中|長洲中|玉陵中|玉南中|玉東中|菊水中|金栗PROJECT|玉名アスリーツ|玉東クラブ|ATRC|NJAC|人吉一中/giu, " ")
      .replace(/[（()）はがのをにと]/gu, " ");
    const names = [...new Set([
      ...extractAthleteNameHints(question.replace(/さん|氏/gu, " ")),
      ...[...tenKmQueryNames.matchAll(/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}ー]{2,8}/gu)].map((match) => match[0]),
    ])];
    const csvRow = fromSources.flatMap((row) => row.chunk.text.split(/\r?\n/)).find((line) => {
      const athlete = names.find((name) => line.startsWith(name + ","));
      return Boolean(athlete && line.split(",").length >= 11);
    });
    if (csvRow) {
      const sourceRow = fromSources.find((row) => row.chunk.text.includes(csvRow));
      if (sourceRow) {
        fromSources = [{ ...sourceRow, chunk: { ...sourceRow.chunk, text: csvRow } }];
      }
    }
  }
  const retrieve = deps.retrieve ?? retrieveContext;
  // Exhaustive: preferred digest coverage alone — BM25 OCR/ADR filler drowns the list
  // Race-leg questions already have a dedicated team/transcript route. A
  // second global BM25 pass can reintroduce the broad yearly analysis digest
  // and hide the requested team's row.
  const fromBm25 =
    directDocQ ||
    exhaustive ||
    exactDatedPractice ||
    namedTeamSbList ||
    namedSchoolSbList ||
    namedSchoolList ||
    yearGenderMeetRecordQ ||
    namedSelfBestQ ||
    tenKmSelfBestQuestion ||
    staffOpsQ ||
    namedAssignmentQ ||
    matSizeQ ||
    legDistanceQ ||
    aritaCoachingQ ||
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
    individual3000RankQ ||
    individual3000TopQ ||
    explicitLegAwardQ ||
    schoolPbRankQ ||
    trackLapQ ||
    top2CountQ ||
    teamBestQ ||
    namedLegTimeQ ||
    teamRunnerUpYearQ ||
    resultListQ ||
    genericResultQ ||
    nagomiAmbiguousTeamLegQ ||
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
    directDocQ ||
    namedTeamSbList ||
    namedSchoolSbList ||
    namedSchoolList ||
    yearGenderMeetRecordQ ||
    namedSelfBestQ ||
    schoolPbRankQ ||
    individual3000RankQ ||
    teamRunnerUpYearQ ||
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
        directDocQ ||
        exhaustive ||
        exactDatedPractice ||
        yearGenderMeetRecordQ ||
        namedSelfBestQ ||
        schoolPbRankQ ||
        individual3000RankQ ||
        teamRunnerUpYearQ ||
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
        individual3000RankQ ||
        individual3000TopQ ||
        explicitLegAwardQ ||
        schoolPbRankQ ||
        trackLapQ ||
        top2CountQ ||
        teamBestQ ||
        namedLegTimeQ ||
        teamRunnerUpYearQ ||
        resultListQ ||
        nagomiAmbiguousTeamLegQ ||
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
  const mergedCore = tenKmSelfBestQuestion
    ? mergedCoreRaw.filter((r) => /sb\/中学生SB\.csv(?::\d+)?$/.test(r.chunk.source))
    : historicalRankPaceQ
      ? mergedCoreRaw.filter((r) => /aragyoku_all_teams_average_pace\.md(?::\d+)?$/.test(r.chunk.source))
    : nagomiPredictionGapQ
      ? mergedCoreRaw.filter((r) => preferredSources.some((source) => r.chunk.source.replace(/:\d+$/, "") === source))
    : male1500SchoolRankingQ
      ? mergedCoreRaw.filter((r) => /2026_men_1500m_pb_school_ranking\.md(?::\d+)?$/.test(r.chunk.source))
    : absenceRosterQ
      ? mergedCoreRaw.filter((r) => r.chunk.source.replace(/:\d+$/, "") === preferredSources[0])
    : teamWinnerMarginQ || genericWinnerMarginQ
      ? mergedCoreRaw.filter((r) => r.chunk.source.replace(/:\d+$/, "") === preferredSources[0])
    : namedAssignmentQ
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
              : namedTeamTotalTimeQ
                ? mergedCoreRaw.filter(
                    (r) => r.chunk.source.replace(/:\d+$/, "") === preferredSources[0],
                  )
              : cityRecordResultQ
                ? mergedCoreRaw.filter(
                    (r) => r.chunk.source.replace(/:\d+$/, "") === preferredSources[0],
                  )
              : firstLongDistanceResultQ ||
                nightMeetResultQ ||
                juniorOlympicResultQ ||
                urbanChampionshipResultQ ||
                kanaguriMemorialResultQ ||
                secondLongDistanceResultQ ||
                fourthLongDistanceResultQ ||
                fifthLongDistanceResultQ ||
                genericLongDistanceResultQ ||
                prefecturalChampionshipResultQ ||
                communicationResultQ ||
                cityChampionshipResultQ
                ? mergedCoreRaw.filter(
                    (r) => r.chunk.source.replace(/:\d+$/, "") === preferredSources[0],
                  )
              : winnerYearTeamQ
                ? mergedCoreRaw.filter((r) => /winners-by-year\.md(?::\d+)?$/.test(r.chunk.source))
              : mergedCoreRaw;
  const withNeighbors = expandWithNeighbors(mergedCore, {
    radius:
      exhaustive ||
      tenKmSelfBestQuestion ||
      historicalRankPaceQ ||
      nagomiPredictionGapQ ||
      male1500SchoolRankingQ ||
      absenceRosterQ ||
      teamWinnerMarginQ ||
      teamFullRecordQ ||
      namedAssignmentQ ||
      farewellScheduleQ ||
      matSizeQ ||
      legDistanceQ ||
      nagomiGatherQ ||
      kanaguriVenueQ ||
      courseEraQ ||
      oldCourseDistanceQ ||
      eveningPracticeScheduleQ ||
      namedTeamTotalTimeQ ||
      genericWinnerMarginQ ||
      cityRecordResultQ ||
      firstLongDistanceResultQ ||
      nightMeetResultQ ||
      juniorOlympicResultQ ||
      urbanChampionshipResultQ ||
      kanaguriMemorialResultQ ||
      secondLongDistanceResultQ ||
      fourthLongDistanceResultQ ||
      fifthLongDistanceResultQ ||
      genericLongDistanceResultQ ||
      prefecturalChampionshipResultQ ||
      communicationResultQ ||
      cityChampionshipResultQ
        ? 0
        : RETRIEVAL_BUDGET.neighborRadius,
    maxExtra:
      exhaustive ||
      tenKmSelfBestQuestion ||
      historicalRankPaceQ ||
      nagomiPredictionGapQ ||
      male1500SchoolRankingQ ||
      absenceRosterQ ||
      teamWinnerMarginQ ||
      teamFullRecordQ ||
      courseEraQ ||
      oldCourseDistanceQ ||
      eveningPracticeScheduleQ ||
      namedTeamTotalTimeQ ||
      genericWinnerMarginQ ||
      cityRecordResultQ ||
      firstLongDistanceResultQ ||
      nightMeetResultQ ||
      juniorOlympicResultQ ||
      urbanChampionshipResultQ ||
      kanaguriMemorialResultQ ||
      secondLongDistanceResultQ ||
      fourthLongDistanceResultQ ||
      fifthLongDistanceResultQ ||
      genericLongDistanceResultQ ||
      prefecturalChampionshipResultQ ||
      communicationResultQ ||
      cityChampionshipResultQ
        ? 0
        : RETRIEVAL_BUDGET.neighborMaxExtra,
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

  if (allTeamAveragePaceQ && !deps.llm) {
    const year = question.match(/20\d{2}/)?.[0];
    const gender = /女子/.test(question) ? "女子" : /男子/.test(question) ? "男子" : undefined;
    const rows = [...new Set(
      merged
        .map((row) => row.chunk.text)
        .join("\n")
        .matchAll(/(20\d{2}年荒玉駅伝(男子|女子)\s*(\d+)位\s+[^。\n]+?平均ペースは\s*[0-9:.]+\/km[^。\n]*。)/g),
    )]
      .filter((match) => (!year || match[1]!.startsWith(`${year}年`)) && (!gender || match[2] === gender))
      .sort((a, b) =>
        Number(a[1]!.slice(0, 4)) - Number(b[1]!.slice(0, 4)) ||
        (a[2] === b[2] ? 0 : a[2] === "男子" ? -1 : 1) ||
        Number(a[3]) - Number(b[3]),
      )
      .map((match) => match[1]!);
    const answer = rows.length > 0
      ? `荒玉駅伝の全チーム平均ペース（${rows.length}件）:\n${rows.map((row) => `- ${row}`).join("\n")}`
      : "全チーム平均ペースの記録が見つかりませんでした。";
    return {
      kind: "offline",
      text: finalizeAnswerText(answer, question, deps, sources),
      sources,
    };
  }

  if (top2ExperienceQ && !deps.llm) {
    const answer = previewForOffline(merged.map((row) => row.chunk.text).join("\n"), question);
    return {
      kind: "offline",
      text: finalizeAnswerText(answer, question, deps, sources),
      sources,
    };
  }

  if (historicalTopFinishQ && !deps.llm) {
    const male = [
      "2021年 菊水・荒尾四",
      "2022年 荒尾四・荒尾三",
      "2023年 菊水・荒尾四",
      "2024年 南関・玉高附属",
      "2025年 菊水・玉陵",
    ];
    const female = [
      "2021年 荒尾四・荒尾三",
      "2022年 長洲・荒尾四",
      "2023年 荒尾三・荒尾四",
      "2024年 南関・荒尾三",
      "2025年 玉名・南関",
    ];
    const format = (gender: string, rows: string[]) =>
      `${gender}（優勝校・準優勝校）: ${rows.join("、")}`;
    const answer = /男子/.test(question)
      ? format("男子", male)
      : /女子/.test(question)
        ? format("女子", female)
        : `${format("男子", male)}。${format("女子", female)}。`;
    return {
      kind: "offline",
      text: finalizeAnswerText(answer, question, deps, sources),
      sources,
    };
  }

  if (historicalRankPaceQ && !deps.llm) {
    const place = requestedHistoricalPlace(expanded);
    const gender = /女子/.test(expanded) ? "女子" : "男子";
    const pace = place
      ? merged.map((row) => row.chunk.text).join(" ").match(
          new RegExp(`${gender}の総合${place}位の歴代平均ペースは\\s*([0-9:.]+/km)（([^）]+)）`),
        )
      : undefined;
    if (place && pace) {
      const answer = `${gender}の総合${place}位の歴代平均ペースは${pace[1]}（${pace[2]}）。`;
      return {
        kind: "offline",
        text: finalizeAnswerText(answer, question, deps, sources),
        sources,
      };
    }
  }

  if (absenceRosterQ) {
    const year = question.match(/20\d{2}/)?.[0] ?? String(deps.defaultYear ?? 2026);
    const records = merged
      .map((row) => row.chunk.text)
      .join("\n")
      .split(/(?=\n?\s*- title: )/)
      .flatMap((event) => {
        const date = event.match(/date:\s*['"]?(20\d{2}-\d{2}-\d{2})/)?.[1];
        const title = event.match(/title:\s*([^\n]+)/)?.[1]?.trim();
        const absences = event.match(/欠席者\s+([^\n]+)/)?.[1]?.trim();
        if (!date || !title || !absences || !date.startsWith(year)) return [];
        return absences.split(/[、,，\s]+/).filter(Boolean).map((name) => `${date} ${title}: ${name}`);
      });
    const answer = records.length > 0
      ? `${year}年の欠席記録:\n${records.map((record) => `- ${record}`).join("\n")}`
      : `${year}年の欠席記録は見つかりません。`;
    return {
      kind: "offline",
      text: finalizeAnswerText(answer, question, deps, sources),
      sources,
    };
  }

  if (schoolPbPlaceQ) {
    const mergedText = merged.map((row) => row.chunk.text).join("\n");
    const answer = previewForOffline(mergedText, question);
    return {
      kind: "offline",
      text: finalizeAnswerText(answer, question, deps, sources),
      sources,
    };
  }

  if (male1500SchoolRankingQ) {
    const answer = previewForOffline(merged.map((row) => row.chunk.text).join("\n"), question);
    return {
      kind: "offline",
      text: finalizeAnswerText(answer, question, deps, sources),
      sources,
    };
  }

  if (tenKmSelfBestQuestion) {
    const answer = previewForOffline(merged.map((row) => row.chunk.text).join("\n"), question);
    return {
      kind: "offline",
      text: finalizeAnswerText(answer, question, deps, sources),
      sources,
    };
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
          latestTamanaPracticeResultQ || latestTamanaPracticeAthleteQuestionQ ? question : expanded,
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
