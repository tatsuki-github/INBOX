import { classifyScope, OUT_OF_SCOPE_MESSAGE } from "./scope.js";
import type { LlmClient } from "./llm.js";
import { buildSystemPrompt, buildUserPrompt } from "../rag/prompt.js";
import { retrieveContext, type RetrievedChunk } from "../rag/retrieve.js";

export type AnswerResult =
  | { kind: "refused"; text: string }
  | { kind: "answered"; text: string; sources: string[] }
  | { kind: "offline"; text: string; sources: string[] }
  | { kind: "error"; text: string };

export type AnswerDeps = {
  retrieve?: (question: string, topK?: number) => RetrievedChunk[];
  llm?: LlmClient | null;
  topK?: number;
};

function offlineAnswer(question: string, retrieved: RetrievedChunk[]): string {
  const lines = [
    "（オフライン回答 — LLM 未設定）",
    "",
    `Q: ${question}`,
    "",
    "関連コーパス:",
  ];
  for (const [i, r] of retrieved.entries()) {
    const preview = r.chunk.text.replace(/\s+/g, " ").slice(0, 280);
    lines.push(`${i + 1}. [${r.chunk.source}] ${preview}`);
  }
  if (retrieved.length === 0) {
    lines.push("(ヒットなし)");
  }
  return lines.join("\n");
}

export async function answerQuestion(
  question: string,
  deps: AnswerDeps = {},
): Promise<AnswerResult> {
  const scope = classifyScope(question);
  if (scope.kind === "out_of_scope") {
    return { kind: "refused", text: scope.message || OUT_OF_SCOPE_MESSAGE };
  }

  const retrieve = deps.retrieve ?? retrieveContext;
  const topK = deps.topK ?? 5;
  const retrieved = retrieve(question, topK);
  const sources = [...new Set(retrieved.map((r) => r.chunk.source))];

  if (!deps.llm) {
    return { kind: "offline", text: offlineAnswer(question, retrieved), sources };
  }

  try {
    const text = await deps.llm.complete(
      buildSystemPrompt(),
      buildUserPrompt(question, retrieved),
    );
    return { kind: "answered", text, sources };
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error("answerQuestion llm failed:", msg.slice(0, 300));
    return {
      kind: "error",
      text: "回答生成中にエラーが起きました。しばらくしてから、もう一度短い質問で試してください。",
    };
  }
}
