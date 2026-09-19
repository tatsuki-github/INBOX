/** Discover more 「誰？」phrasing failures for school+leg. */
import { answerQuestion } from "../../src/domain/answer.js";
import { resetRetrieverCache } from "../../src/rag/retrieve.js";
import { resetKgCache } from "../../src/kg/query.js";

const qs: { q: string; need: string[] }[] = [
  { q: "2025年岱明男子5区は誰？", need: ["山本哲瑠"] },
  { q: "2025年岱明男子2区は誰？", need: ["松野凛空"] },
  { q: "2025年岱明男子1区は誰？", need: ["倉田裕斗"] },
  { q: "2025年岱明男子3区は誰？", need: ["今村昇磨"] },
  { q: "2025年岱明男子4区は誰？", need: ["佐藤央琉"] },
  { q: "2025年岱明男子6区は誰？", need: ["案浦竜士"] },
  { q: "2024年岱明男子5区は誰？", need: ["松野凛空"] },
  { q: "2024年岱明男子2区は誰？", need: ["満田樹生"] },
  { q: "2025年岱明女子1区は誰？", need: ["村上咲稀"] },
  { q: "2025年岱明女子2区は誰？", need: ["増岡里俐"] },
  { q: "2024年岱明女子5区は誰？", need: [] },
  { q: "2025年玉高附属男子2区は誰？", need: [] },
  { q: "2025年玉高附属男子5区は誰？", need: [] },
  { q: "2024年有明男子5区は誰？", need: [] },
  { q: "2025年天水男子2区は誰？", need: ["山本悠斗"] },
  { q: "岱明男子5区は誰？（2025）", need: ["山本哲瑠"] },
  { q: "荒玉2025 岱明 男子 5区 誰", need: ["山本哲瑠"] },
  { q: "2025岱明5区誰", need: ["山本哲瑠"] },
  { q: "岱明の5区は誰が走った2025", need: ["山本哲瑠"] },
  { q: "2025年荒玉駅伝岱明男子5区ランナーは？", need: ["山本哲瑠"] },
];

async function main() {
  let fail = 0;
  for (const { q, need } of qs) {
    resetRetrieverCache();
    resetKgCache();
    const r = await answerQuestion(q, { skipRouter: true, defaultYear: 2026 });
    const text = (r.text || "").replace(/\n/g, " ");
    const coach = text.includes("コーチに直接");
    const miss = need.filter((n) => !text.includes(n));
    const hit = !coach && (need.length === 0 || miss.length === 0);
    if (!hit) fail++;
    const src =
      r.kind === "answered" || r.kind === "offline" ? r.sources.slice(0, 3).join(" | ") : r.kind;
    console.log(`${hit ? "OK  " : "FAIL"} | ${q}`);
    if (!hit) {
      console.log(`     miss=${miss.join("|") || "coach"} | ${src}`);
      console.log(`     ${text.slice(0, 180)}`);
    }
  }
  console.log(`\nFAIL ${fail}/${qs.length}`);
}

main();
