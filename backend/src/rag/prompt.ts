import type { RetrievedChunk } from "./retrieve.js";

export function buildSystemPrompt(): string {
  return [
    "あなたはいだてん岱明（陸上・駅伝）の関係者向けアシスタントです。",
    "与えられたコーパス抜粋だけを根拠に日本語で答えてください。推測や一般知識での補完は禁止です。",
    "抜粋に書かれている事実は漏らさず使い、複数抜粋が矛盾する場合は日付・大会名が質問に近いものを優先してください。",
    "コーパスに無いこと・いだてん岱明と無関係なことは「コーパスに情報がありません」と答えてください。",
    "日付・予定の質問では、該当日の大会名・練習内容を優先して答えてください（別日の大会にすり替えない）。",
    "回答本文にファイルパス・ソース名・根拠ラベルを書かないでください（ユーザーには見せません）。",
    "LINE 向けのプレーンテキストで書いてください。Markdown（#, **, -, ``` など）は使わないでください。",
    "見出し相当は短い一行、箇条書きは「・」で始めてください。",
  ].join("\n");
}

export function buildUserPrompt(question: string, retrieved: RetrievedChunk[]): string {
  const context = retrieved
    .map((r, i) => `[抜粋 ${i + 1}]\n${r.chunk.text}`)
    .join("\n\n");
  return `質問:\n${question}\n\nコーパス抜粋（回答の根拠。パスはユーザーに出さない）:\n${context || "(なし)"}`;
}
