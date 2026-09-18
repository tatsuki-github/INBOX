import type { RetrievedChunk } from "./retrieve.js";

/** User-facing text when the corpus has no answer (LLM + offline paths). */
export const MISSING_INFO_MESSAGE = "コーチに直接聞いてください。";

export function buildSystemPrompt(): string {
  return [
    "あなたはこのリポジトリの知識コーパス（練習・駅伝・記録・分析・ドキュメント等）に基づくアシスタントです。",
    "与えられたコーパス抜粋だけを根拠に日本語で答えてください。推測や一般知識での補完は禁止です。",
    "抜粋に書かれている事実は漏らさず使い、複数抜粋が矛盾する場合は日付・大会名が質問に近いものを優先してください。",
    "「去年」「今年」などは抜粋内の西暦と対応づけて答えてください（例: 去年＝抜粋の該当年の結果）。",
    "優勝校・順位の質問で男女が指定されていない場合は、男子と女子の両方を抜粋にあれば答えてください。",
    `コーパス抜粋に無いこと・不明なことは「${MISSING_INFO_MESSAGE}」とだけ答えてください（「コーパス」等の内部用語は出さない）。`,
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
