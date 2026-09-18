import type { RetrievedChunk } from "./retrieve.js";

export function buildSystemPrompt(): string {
  return [
    "あなたはいだてん岱明（陸上・駅伝）の関係者向けアシスタントです。",
    "与えられたコーパス抜粋だけを根拠に日本語で簡潔に答えてください。",
    "コーパスに無いこと・いだてん岱明と無関係なことは推測せず「コーパスに情報がありません」と答えてください。",
    "可能なら根拠ソースパスを末尾に短く書いてください。",
  ].join("\n");
}

export function buildUserPrompt(question: string, retrieved: RetrievedChunk[]): string {
  const context = retrieved
    .map((r, i) => `[${i + 1}] source=${r.chunk.source}\n${r.chunk.text}`)
    .join("\n\n");
  return `質問:\n${question}\n\nコーパス抜粋:\n${context || "(なし)"}`;
}
