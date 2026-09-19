/** Broader leg/athlete probes around the daimyo LINE-drown gap. */
import { answerQuestion } from "../../src/domain/answer.js";
import { resetRetrieverCache } from "../../src/rag/retrieve.js";
import { resetKgCache } from "../../src/kg/query.js";

const qs: { q: string; need: string[] }[] = [
  { q: "2025年岱明男子5区は誰？", need: ["山本哲瑠"] },
  { q: "2025年岱明男子5区の選手は？", need: ["山本哲瑠"] },
  { q: "岱明の2025男子5区は誰でタイムは？", need: ["山本哲瑠", "9:37"] },
  { q: "2025荒玉 岱明 5区", need: ["山本哲瑠"] },
  { q: "2025年玉高附属男子1区は誰？", need: ["草野瑠唯"] },
  { q: "2025年天水女子3区は誰？", need: [] },
  { q: "2024年有明男子1区は誰？", need: ["米村和真"] },
  { q: "2025年南関男子4区は誰？", need: [] },
  { q: "2025年菊水男子6区は誰？", need: [] },
  { q: "今村昇磨は2025年荒玉で何区？", need: ["3区", "今村昇磨"] },
  { q: "倉田裕斗は2025年何区？", need: ["1区", "倉田裕斗"] },
  { q: "山本哲瑠の2025荒玉区間タイムは？", need: ["山本哲瑠", "9:37"] },
  { q: "案浦竜士は何区を走った？", need: ["案浦竜士", "6区"] },
  { q: "2025年岱明男子の区間順位ベストは誰？", need: ["山本哲瑠"] },
  { q: "2024年岱明男子のボトルネック区間は？", need: ["4区"] },
  { q: "村上咲稀は荒玉女子の何区？", need: ["村上咲稀"] },
  { q: "2025年玉高附属女子の総合タイムは？", need: ["46:55"] },
  { q: "有明の米村和真は何区で区間新？", need: ["米村和真", "1区"] },
  { q: "2025年岱明男子通過順の推移は？", need: ["岱明"] },
  { q: "土山の地点分担は？", need: ["D地点"] },
  { q: "2025年岱明男子総合タイムと優勝差は？", need: ["59:08"] },
  { q: "松野凛空は2025荒玉何区？", need: ["2区", "松野凛空"] },
  { q: "佐藤央琉は何区？", need: ["佐藤央琉", "4区"] },
  { q: "2024年岱明男子1区は誰？", need: ["根本和樹"] },
  { q: "2025年有明男子総合は？", need: ["62:31"] },
  { q: "2025年天水男子総合は？", need: ["63:39"] },
  { q: "2024年天水女子総合は？", need: ["49:41"] },
  { q: "2025年有明女子総合は？", need: ["47:24"] },
  { q: "亀井遼希は何区で大会区間記録？", need: ["亀井遼希", "3区"] },
  { q: "田崎空汰の大会区間記録は？", need: ["田崎空汰", "9:13"] },
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
    const hit = !coach && miss.length === 0;
    if (!hit) fail++;
    const src =
      r.kind === "answered" || r.kind === "offline" ? r.sources.slice(0, 4).join(" | ") : r.kind;
    console.log(`${hit ? "OK  " : "FAIL"} | ${q}`);
    if (!hit) {
      console.log(`     miss=${miss.join("|") || "coach"} | ${src}`);
      console.log(`     ${text.slice(0, 200)}`);
    }
  }
  console.log(`\nFAIL ${fail}/${qs.length}`);
}

main();
