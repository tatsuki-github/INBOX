/** Probe around the two v7 failures + nearby school-rank / margin gaps. */
import { answerQuestion } from "../../src/domain/answer.js";
import { resetRetrieverCache } from "../../src/rag/retrieve.js";
import { resetKgCache } from "../../src/kg/query.js";

const qs: { q: string; need: string[] }[] = [
  { q: "女子800mで岱明の上位3人平均は？", need: ["2:28"] },
  { q: "女子800m学校別ランキングで岱明は何位？", need: ["3"] },
  { q: "女子800m上位3人平均1位の学校は？", need: ["長洲", "2:27"] },
  { q: "女子1500m学校別ランキング1位は？", need: [] },
  { q: "男子1500m上位4人平均で菊水は何位？", need: ["2"] },
  { q: "男子1500m学校別で玉名附中の平均は？", need: ["4:28"] },
  { q: "2025年岱明男子の優勝との差は？", need: ["2:51"] },
  { q: "2024年岱明男子の優勝差は？", need: ["8:37"] },
  { q: "2025年玉高附属男子の優勝との差は？", need: [] },
  { q: "岱明男子2025は優勝から何分離れている？", need: ["2:51"] },
  { q: "2025年天水男子の優勝との差は？", need: [] },
  { q: "2024年有明女子の優勝との差は？", need: [] },
  { q: "女子800mPB学校別で荒尾三は何位？", need: ["2"] },
  { q: "800m学校別ランキングの岱明の平均タイムは？", need: ["2:28"] },
  { q: "村上咲稀の800mは学校別でどう？", need: ["2:20"] },
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
      r.kind === "answered" || r.kind === "offline" ? r.sources.slice(0, 4).join(" | ") : "";
    console.log(`${hit ? "OK  " : "FAIL"} | ${q}`);
    if (!hit) {
      console.log(`     miss=${miss.join("|") || "coach"} | ${src}`);
      console.log(`     ${text.slice(0, 200)}`);
    }
  }
  console.log(`\nFAIL ${fail}/${qs.length}`);
}

main();
