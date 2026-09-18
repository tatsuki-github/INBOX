/** Scope guard: refuse only clearly external topics; otherwise answer from repo corpus. */

export type ScopeDecision =
  | { kind: "in_scope"; reason: string }
  | { kind: "out_of_scope"; message: string; hard?: boolean };

/** Hard refuse — external live data / unrelated chat, even if other tokens appear. */
const HARD_OUT_OF_SCOPE_PATTERNS = [
  /天気/,
  /ニュース/,
  /株価/,
  /レシピ/,
  /chatgpt/i,
  /あなたは誰/,
] as const;

export const OUT_OF_SCOPE_MESSAGE =
  "このボットはリポジトリに書いてある内容（練習・駅伝・記録・分析・ドキュメント等）について答えます。天気・ニュースなど外部の話題は対象外です。";

/**
 * Classify whether to attempt a corpus-backed answer.
 * Default is in_scope for any non-empty question — grounding and refusals for
 * missing facts happen at retrieval / LLM time. Hard patterns always refuse.
 */
export function classifyScope(question: string): ScopeDecision {
  const q = question.trim();
  if (!q) {
    return { kind: "out_of_scope", message: OUT_OF_SCOPE_MESSAGE };
  }

  for (const pat of HARD_OUT_OF_SCOPE_PATTERNS) {
    if (pat.test(q)) {
      return { kind: "out_of_scope", message: OUT_OF_SCOPE_MESSAGE, hard: true };
    }
  }

  return { kind: "in_scope", reason: "repo_corpus" };
}
