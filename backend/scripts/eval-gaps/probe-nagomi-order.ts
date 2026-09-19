/** Probe なごみ 2026 order vs 金栗駅伝 / 金栗記念 collisions. */
import { answerQuestion } from "../../src/domain/answer.js";
import { resetRetrieverCache } from "../../src/rag/retrieve.js";
import { resetKgCache } from "../../src/kg/query.js";

type Case = { q: string; all_of: string[]; forbid?: string[]; sources_any?: string[]; sources_none?: string[] };

const cases: Case[] = [
  {
    q: "なごみ駅伝の岱明男子1区は誰？",
    all_of: ["哲瑠"],
    sources_any: ["区間オーダーリスト"],
    sources_none: ["金栗駅伝", "金栗記念", ".meta.json"],
  },
  {
    q: "なごみ駅伝2026 岱明A 1区は誰？",
    all_of: ["哲瑠"],
    sources_any: ["区間オーダーリスト"],
  },
  {
    q: "なごみ駅伝のオーダーを教えて。岱明男子A",
    all_of: ["哲瑠"],
    sources_any: ["区間オーダーリスト"],
  },
  {
    q: "金栗駅伝の日付は？",
    all_of: [],
    sources_any: ["金栗駅伝"],
  },
];

async function main() {
  let fail = 0;
  for (const c of cases) {
    resetRetrieverCache();
    resetKgCache();
    const r = await answerQuestion(c.q, { skipRouter: true, defaultYear: 2026 });
    const text = (r.text || "").replace(/\n/g, " ");
    const src =
      r.kind === "answered" || r.kind === "offline" ? r.sources.slice(0, 6).join(" | ") : "";
    const miss = c.all_of.filter((t) => !text.includes(t));
    const srcMiss =
      c.sources_any && c.sources_any.length > 0
        ? !c.sources_any.some((t) => src.includes(t))
        : false;
    const srcBad = (c.sources_none ?? []).filter((t) => src.includes(t));
    const coach = text.includes("コーチに直接");
    const hit = !coach && miss.length === 0 && !srcMiss && srcBad.length === 0;
    if (!hit) fail++;
    console.log(`${hit ? "OK  " : "FAIL"} | ${c.q}`);
    if (!hit) {
      console.log(`     miss=${miss.join("|") || "-"} srcMiss=${srcMiss} srcBad=${srcBad.join("|") || "-"}`);
      console.log(`     src=${src}`);
      console.log(`     ${text.slice(0, 200)}`);
    }
  }
  console.log(`FAIL ${fail}/${cases.length}`);
}

main();
