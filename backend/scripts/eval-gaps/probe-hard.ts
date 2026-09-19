/** Quick probe for hard phrasings. */
import { answerQuestion } from "../../src/domain/answer.js";
import { resetRetrieverCache } from "../../src/rag/retrieve.js";
import { resetKgCache } from "../../src/kg/query.js";

const qs = [
  "2025年荒玉駅伝男子の岱明は何位？",
  "玉名付属中の女子は2025年荒玉で何位？",
  "天水の山本悠斗の区間タイムは？",
  "荒玉駅伝男子2区の大会記録は誰？",
  "2025年ボードの男子総合大会記録は？",
  "有明中の荒玉2024男子1区は誰？",
  "岱明男子は2024から2025で何分短縮した？",
  "玉高附属の草野瑠唯は何区？",
  "2024年荒玉男子の優勝は南関でタイムは？",
  "荒玉の現行男子4区の距離は？",
  "2025女子優勝の玉名の総合タイムは？",
  "天水女子は2025何位？",
  "有明女子は前年比でどうなった？",
  "菊水の2025男子1区は誰？",
  "2025年荒玉男子3区の大会区間記録保持者は？",
];

async function main() {
  for (const q of qs) {
    resetRetrieverCache();
    resetKgCache();
    const r = await answerQuestion(q, { skipRouter: true, defaultYear: 2026 });
    const text = (r.text || "").replace(/\n/g, " ");
    const coach = text.includes("コーチに直接");
    const src =
      r.kind === "answered" || r.kind === "offline" ? r.sources.slice(0, 4).join(",") : "";
    console.log(`${coach ? "FAIL" : "OK  "} | ${q}`);
    console.log(`     ${r.kind} | ${src}`);
    console.log(`     ${text.slice(0, 160)}`);
  }
}

main();
