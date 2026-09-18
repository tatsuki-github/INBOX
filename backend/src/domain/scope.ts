/** Scope guard: only いだてん岱明 topics. */

import { looksLikeDateQuestion, parseDateMentions } from "./dates.js";

export type ScopeDecision =
  | { kind: "in_scope"; reason: string }
  | { kind: "out_of_scope"; message: string; hard?: boolean };

const IN_SCOPE_KEYWORDS = [
  "いだてん",
  "岱明",
  "たいめい",
  "タイメイ",
  "荒玉",
  "駅伝",
  "ekiden",
  "aragyoku",
  "daiming",
  "練習",
  "朝練",
  "夕練",
  "記録",
  "sb",
  "名簿",
  "生徒",
  "部員",
  "区間",
  "オーダー",
  "中体連",
  "gz",
  "サブ閾値",
  "norwegian",
  // Schedule / meet vocabulary (dedicated LINE bot)
  "予定",
  "カレンダー",
  "大会",
  "なごみ",
  "ジュニア",
  "部活",
  "メニュー",
  "開催要項",
  "試合",
] as const;

const OUT_OF_SCOPE_PATTERNS = [
  /天気/,
  /ニュース/,
  /株価/,
  /レシピ/,
  /プログラミング(?!.*(岱明|いだてん|荒玉))/,
  /chatgpt/i,
  /あなたは誰/,
] as const;

export const OUT_OF_SCOPE_MESSAGE =
  "いだてん岱明（練習・駅伝・記録・名簿）に関することだけ答えられます。例: 「2024年男子の荒玉駅伝で岱明は何位？」";

export function classifyScope(question: string): ScopeDecision {
  const q = question.trim();
  if (!q) {
    return { kind: "out_of_scope", message: OUT_OF_SCOPE_MESSAGE };
  }

  for (const pat of OUT_OF_SCOPE_PATTERNS) {
    if (pat.test(q) && !IN_SCOPE_KEYWORDS.some((k) => q.toLowerCase().includes(k.toLowerCase()))) {
      return { kind: "out_of_scope", message: OUT_OF_SCOPE_MESSAGE, hard: true };
    }
  }

  const lower = q.toLowerCase();
  const hit = IN_SCOPE_KEYWORDS.find((k) => lower.includes(k.toLowerCase()));
  if (hit) {
    return { kind: "in_scope", reason: `keyword:${hit}` };
  }

  // Date-like questions → calendar / meet lookup for this dedicated bot
  if (parseDateMentions(q).length > 0 || looksLikeDateQuestion(q)) {
    return { kind: "in_scope", reason: "date_question" };
  }

  // Ambiguous short questions: treat as out of scope (refuse rather than hallucinate)
  return { kind: "out_of_scope", message: OUT_OF_SCOPE_MESSAGE };
}
