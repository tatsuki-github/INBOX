/** Probe questions outside crush100-v4 coverage. */
import { answerQuestion } from "../../src/domain/answer.js";
import { resetRetrieverCache } from "../../src/rag/retrieve.js";
import { resetKgCache } from "../../src/kg/query.js";

const qs = [
  // athlete name without school
  "草野瑠唯は荒玉で何区を走った？",
  "山本悠斗の荒玉区間タイムは？",
  "米村和真の区間新は何年何区？",
  // meet records without year (current/latest)
  "荒玉男子2区の大会区間記録の保持者は？",
  "荒玉女子総合の大会記録は？",
  // course era / reset
  "男子の大会記録がリセットされたのはいつ？",
  "荒玉男子のcourse_eraは？",
  // winners phrasing
  "去年の荒玉女子優勝タイムは？",
  "一昨年の荒玉男子優勝校は？",
  // team digests other schools
  "長洲の2025男子2区は誰？",
  "玉陵の2025男子総合タイムは？",
  "荒尾三の2024女子順位は？",
  // focus YoY deltas
  "岱明男子は前年比何分速くなった？",
  "玉高附属女子は前年比何分遅くなった？",
  // distance edge
  "女子5区の距離は？",
  "旧コース男子6区の距離は？",
  // SB / ranking
  "荒玉地区3000mSBの2位は誰？",
  "隈部侑成の3000mSBは？",
  // LINE / practice
  "銀マットのサイズは？",
  "夕練の開始時刻は？",
  // track
  "岱明のトラック1周は何メートル？",
  // weather ops
  "玉名の天気データはどう更新する？",
  // junior disambiguation
  "去年のジュニア駅伝の岱明の結果は？",
  // alias
  "玉名附属中の2025男子は何位？",
  "付属の草野瑠唯は何区？",
];

function hasAnchor(text: string, anchors: string[]): boolean {
  return anchors.some((a) => text.includes(a));
}

const expect: Record<string, string[]> = {
  "草野瑠唯は荒玉で何区を走った？": ["3区", "草野瑠唯"],
  "山本悠斗の荒玉区間タイムは？": ["8:37", "山本悠斗"],
  "米村和真の区間新は何年何区？": ["米村和真", "1区"],
  "荒玉男子2区の大会区間記録の保持者は？": ["荒木琉偉", "8:41"],
  "荒玉女子総合の大会記録は？": ["40:58", "玉名"],
  "男子の大会記録がリセットされたのはいつ？": ["2024"],
  "荒玉男子のcourse_eraは？": ["men_2024plus", "men_pre2024"],
  "去年の荒玉女子優勝タイムは？": ["41:58", "玉名"],
  "一昨年の荒玉男子優勝校は？": ["南関", "56:38"],
  "長洲の2025男子2区は誰？": ["長洲"],
  "玉陵の2025男子総合タイムは？": ["58:02", "玉陵"],
  "荒尾三の2024女子順位は？": ["2位", "42:36"],
  "岱明男子は前年比何分速くなった？": ["6:07", "-6:07"],
  "玉高附属女子は前年比何分遅くなった？": ["3:05", "+3:05"],
  "女子5区の距離は？": ["3km", "3.00", "3.0"],
  "旧コース男子6区の距離は？": ["4km", "4.00", "4.0"],
  "荒玉地区3000mSBの2位は誰？": ["2"],
  "隈部侑成の3000mSBは？": ["隈部"],
  "銀マットのサイズは？": ["180", "60"],
  "夕練の開始時刻は？": ["18:00", "18時"],
  "岱明のトラック1周は何メートル？": ["400", "300"],
  "玉名の天気データはどう更新する？": ["Open-Meteo", "weather", "天気"],
  "去年のジュニア駅伝の岱明の結果は？": ["ジュニア"],
  "玉名附属中の2025男子は何位？": ["3位", "58:37"],
  "付属の草野瑠唯は何区？": ["3区", "草野瑠唯"],
};

async function main() {
  let fail = 0;
  for (const q of qs) {
    resetRetrieverCache();
    resetKgCache();
    const r = await answerQuestion(q, { skipRouter: true, defaultYear: 2026 });
    const text = (r.text || "").replace(/\n/g, " ");
    const coach = text.includes("コーチに直接");
    const anchors = expect[q] ?? [];
    const hit = !coach && (anchors.length === 0 || hasAnchor(text, anchors));
    if (!hit) fail++;
    const src =
      r.kind === "answered" || r.kind === "offline" ? r.sources.slice(0, 3).join(",") : "";
    console.log(`${hit ? "OK  " : "FAIL"} | ${q}`);
    if (!hit) {
      console.log(`     want any ${anchors.join("|")}`);
      console.log(`     ${r.kind} | ${src}`);
      console.log(`     ${text.slice(0, 180)}`);
    }
  }
  console.log(`\nFAIL ${fail}/${qs.length}`);
}

main();
