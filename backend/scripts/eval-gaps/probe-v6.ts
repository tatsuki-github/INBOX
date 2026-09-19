/** Probe questions outside crush100-v4 / probe-v5 — discover real gaps. */
import { answerQuestion } from "../../src/domain/answer.js";
import { resetRetrieverCache } from "../../src/rag/retrieve.js";
import { resetKgCache } from "../../src/kg/query.js";

type Case = { q: string; all_of: string[]; any_of?: string[] };

const cases: Case[] = [
  // top2 finish counts
  { q: "荒玉で総合2位以内が最多の学校は？何回？", all_of: ["玉名", "15"] },
  { q: "荒玉男子で総合2位以内回数が多い学校は？", all_of: ["玉名"] },
  { q: "岱明が荒玉で総合2位以内に入ったのは何回？", all_of: ["1"] },
  { q: "玉高附属が荒玉男子で2位になったのは何年？", all_of: ["2024"] },
  // historical pace
  { q: "荒玉男子トップ6の歴代平均ペースは？", all_of: ["3:18"] },
  { q: "2023年荒玉男子総合1〜6位の平均ペースは？", all_of: ["3:15"] },
  { q: "荒玉男子優勝の歴代平均ペースは？", all_of: ["3:13"] },
  // historical meet records (pre-focus)
  { q: "2012年荒玉男子の総合大会記録は？", all_of: ["63:28", "荒尾海陽"] },
  { q: "2017年荒玉男子の総合大会記録の保持校は？", all_of: ["62:53", "菊水"] },
  { q: "2013年荒玉男子1区の大会区間記録保持者は？", all_of: ["田上建", "12:12"] },
  { q: "女子2区の大会区間記録の保持者は？", all_of: ["井上智世", "6:08"] },
  { q: "2024年荒玉男子総合の大会記録は？", all_of: ["56:38", "南関"] },
  { q: "2025年荒玉男子3区の大会区間記録は誰？", all_of: ["亀井遼希", "9:24"] },
  { q: "2015年荒玉男子の総合大会記録は？", all_of: ["63:03", "玉名"] },
  // historical winners / results outside 2024-25 focus
  { q: "2023年荒玉男子の優勝校は？", all_of: ["菊水"] },
  { q: "2022年荒玉女子の優勝校は？", all_of: ["長洲"] },
  { q: "2021年荒玉女子の優勝校は？", all_of: ["荒尾四"] },
  { q: "2020年荒玉男子の優勝校は？", all_of: ["玉南"] },
  { q: "2019年荒玉男子2位は？", all_of: ["玉東"] },
  { q: "2016年荒玉女子の優勝校は？", all_of: ["荒尾三"] },
  // SB exact
  { q: "荒玉地区3000mSBの1位の記録は？", all_of: ["8:54"] },
  { q: "松浦眞大の3000mSBは？", all_of: ["9:08"] },
  { q: "石川隼の3000mSBは？", all_of: ["9:10"] },
  { q: "草野瑠唯の3000mSBは？", all_of: ["9:28"] },
  { q: "松野凛空の3000mSBは？", all_of: ["9:37"] },
  // LINE staff
  { q: "荒玉の地点分担で土山はどこ？", all_of: ["D地点"] },
  { q: "荒玉の地点分担で柴尾はどこ？", all_of: ["A地点"] },
  { q: "岱明の朝練は何曜日？集合は？", all_of: ["7:20"] },
  { q: "金栗駅伝はいつ？", all_of: ["2026-03-15", "3/15"] },
  { q: "荒玉男子2区と5区の距離は？", all_of: ["2.855"] },
  // athlete disambiguation
  { q: "高田麻那の1500mSBは？", all_of: ["5:21"] },
  { q: "高田麻那の5000mSBは？", all_of: ["11:05"] },
  // focus deep facts not in v4 phrasing
  { q: "2025年岱明男子5区は誰で区間順は？", all_of: ["山本哲瑠", "2"] },
  { q: "2024年岱明男子4区の区間タイムは？", all_of: ["田上侑蕾", "14:55"] },
  { q: "有明女子は2024から2025で何秒速くなった？", all_of: ["33"] },
  { q: "天水男子の2024と2025の総合タイム差は？", all_of: ["1"] },
  // non-focus team MD
  { q: "2025年菊水男子の総合タイムは？", all_of: ["56:17"] },
  { q: "2024年南関女子の総合タイムは？", all_of: ["42:25"] },
  { q: "2025年玉東女子は何位？", all_of: ["3位", "44:24"] },
  // course distance
  { q: "現行コースの荒玉男子合計距離は？", all_of: ["17.71"] },
  { q: "旧コースの荒玉男子合計距離は？", all_of: ["19.71"] },
  // board vs split_record confusion
  { q: "井上智世の荒玉女子2区大会区間記録は？", all_of: ["6:08"] },
  { q: "西川侑里の女子1区大会区間記録は？", all_of: ["9:46"] },
  { q: "一瀬弘樹の男子1区大会区間記録は何年ボード？", all_of: ["12:28"] },
  // arato school digests
  { q: "金栗PROJECTの3000mで一番速いのは誰？", all_of: ["隈部"] },
  { q: "玉名附中の3000mSBランキング上位は？", all_of: ["小倉"] },
];

function check(text: string, c: Case): string[] {
  const reasons: string[] = [];
  if (text.includes("コーチに直接")) reasons.push("coach-handoff");
  for (const t of c.all_of) {
    if (!text.includes(t)) reasons.push(`missing all_of: ${t}`);
  }
  if (c.any_of && !c.any_of.some((t) => text.includes(t))) {
    reasons.push(`missing any_of: ${c.any_of.join("|")}`);
  }
  return reasons;
}

async function main() {
  let fail = 0;
  for (const c of cases) {
    resetRetrieverCache();
    resetKgCache();
    const r = await answerQuestion(c.q, { skipRouter: true, defaultYear: 2026 });
    const text = (r.text || "").replace(/\n/g, " ");
    const reasons = check(text, c);
    const hit = reasons.length === 0;
    if (!hit) fail++;
    const src =
      r.kind === "answered" || r.kind === "offline" ? r.sources.slice(0, 3).join(",") : "";
    console.log(`${hit ? "OK  " : "FAIL"} | ${c.q}`);
    if (!hit) {
      console.log(`     ${reasons.join("; ")}`);
      console.log(`     ${r.kind} | ${src}`);
      console.log(`     ${text.slice(0, 220)}`);
    }
  }
  console.log(`\nFAIL ${fail}/${cases.length}`);
}

main();
