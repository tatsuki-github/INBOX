/** Probe gaps outside crush100-v5 coverage. */
import { answerQuestion } from "../../src/domain/answer.js";
import { resetRetrieverCache } from "../../src/rag/retrieve.js";
import { resetKgCache } from "../../src/kg/query.js";

type Case = { q: string; all_of: string[]; any_of?: string[] };

const cases: Case[] = [
  // arita coaching
  { q: "有田先輩のメンタルの考え方は？", all_of: ["楽しさ", "本気度"] },
  { q: "有田先輩の補強メニューは？", all_of: ["手押し車", "犬歩き"] },
  { q: "女子荒玉のタイム目安は？", all_of: ["43分"] },
  { q: "夏のメニューでペーランより何がいい？", all_of: ["ビルド"] },
  { q: "厚底シューズについて有田先輩はどう言ってる？", all_of: ["故障"] },
  // parents LINE
  { q: "銀マットの厚みは？", all_of: ["15"] },
  { q: "玉名市合同練習会はいつどこ？", all_of: ["おおはま", "9月22"] },
  { q: "合同練習会の集合時刻は？", all_of: [], any_of: ["8時", "8:00", "午前8"] },
  { q: "なごみ駅伝の集合場所は？", all_of: ["和水"] },
  { q: "合同練習会の会費は？", all_of: ["1000"] },
  // 1500m SB ranking
  { q: "荒玉地区1500mSBの1位は誰？", all_of: ["隈部", "4:11"] },
  { q: "荒玉地区1500mトップ20の2位は？", all_of: ["石川", "4:15"] },
  { q: "松野凛空の1500mSBは？", all_of: ["4:22"] },
  { q: "山本哲瑠の1500mSBは？", all_of: ["4:30"] },
  { q: "草野瑠唯の1500mSBは？", all_of: ["4:21"] },
  // school rankings
  { q: "男子1500m学校別ランキング1位は？", all_of: ["玉陵"] },
  { q: "男子1500m上位4人平均で岱明は何位？", all_of: ["5"] },
  { q: "女子800m学校別で1位は？", all_of: ["長洲"] },
  { q: "女子800mで岱明の上位3人平均は？", all_of: ["2:28"] },
  { q: "村上咲稀の800mPBは？", all_of: ["2:20"] },
  // junior / nagomi meets (not aragyoku)
  { q: "去年のジュニア駅伝の岱明の結果は？", all_of: ["ジュニア"] },
  { q: "なごみ駅伝はいつ？", all_of: ["なごみ"] },
  { q: "金栗駅伝の日付は？", all_of: [], any_of: ["3/15", "2026-03-15", "3月15"] },
  // older historical team results
  { q: "2018年荒玉男子の優勝校は？", all_of: ["南関"] },
  { q: "2015年荒玉男子の優勝校は？", all_of: ["玉名"] },
  { q: "2012年荒玉女子2位は？", all_of: ["岱明"] },
  { q: "2021年荒玉男子の優勝校は？", all_of: ["菊水"] },
  { q: "2023年荒玉女子の優勝校は？", all_of: ["荒尾三"] },
  // meet records obscure
  { q: "女子4区の大会区間記録の保持者は？", all_of: ["浦浜"] },
  { q: "永尾海斗の大会区間記録は？", all_of: ["9:38"] },
  { q: "高木悠人の大会区間記録は？", all_of: ["9:11"] },
  // practice / calendar
  { q: "夕練は何時から？", all_of: ["18"] },
  { q: "朝練の集合は何時？", all_of: ["7:20"] },
  { q: "岱明のトラック1周は？", all_of: [], any_of: ["400", "300"] },
  // relative / ambiguous phrasing
  { q: "一昨年の荒玉女子優勝校は？", all_of: ["南関"] },
  { q: "去年の荒玉男子優勝タイムは？", all_of: ["56:17"] },
  { q: "付属中の2025男子総合は？", all_of: ["58:37"] },
  { q: "玉名付属の2024男子は何位？", all_of: ["2位", "58:13"] },
  // arato team digests
  { q: "ATRCの選手の全記録を見せて", all_of: ["ATRC"] },
  { q: "金栗PROJECT所属選手の全記録", all_of: ["金栗"] },
  { q: "南関中の所属選手の記録一覧", all_of: ["南関"] },
  // focus deep
  { q: "2025年岱明男子の優勝との差は？", all_of: ["2:51"] },
  { q: "天水の区間新は誰？", all_of: ["山本悠斗", "8:37"] },
  { q: "有明男子は2024から2025で何秒遅くなった？", all_of: ["42"] },
  // women track / cross
  { q: "菊水男子が荒玉で2位以内に入った回数は？", all_of: ["6"] },
  // staff LINE remaining
  { q: "地点分担で熊澤先生はどこ？", all_of: ["C地点"] },
  { q: "地点分担で土本先生はどこ？", all_of: ["B地点"] },
  { q: "お別れ会はいつ？", all_of: [], any_of: ["3/15", "12:30", "お別れ会"] },
];

function check(text: string, c: Case): string[] {
  const reasons: string[] = [];
  if (text.includes("コーチに直接")) reasons.push("coach-handoff");
  for (const t of c.all_of) {
    if (!text.includes(t)) reasons.push(`missing:${t}`);
  }
  if (c.any_of && c.any_of.length > 0 && !c.any_of.some((t) => text.includes(t))) {
    reasons.push(`any_of:${c.any_of.join("|")}`);
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
      console.log(`     ${text.slice(0, 200)}`);
    }
  }
  console.log(`\nFAIL ${fail}/${cases.length}`);
}

main();
