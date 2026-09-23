import { describe, expect, it } from "vitest";
import { answerQuestion } from "../src/domain/answer.js";
import { resetKgCache } from "../src/kg/query.js";
import { resetRetrieverCache } from "../src/rag/retrieve.js";

async function ask(question: string) {
  resetKgCache();
  resetRetrieverCache();
  const result = await answerQuestion(question, {
    defaultYear: 2026,
    llm: null,
    skipRouter: true,
  });
  expect(result.kind).toBe("offline");
  if (result.kind !== "offline") throw new Error("expected offline result");
  return result;
}

async function askAt(question: string, now: string) {
  resetKgCache();
  resetRetrieverCache();
  const result = await answerQuestion(question, {
    defaultYear: 2026,
    now: new Date(now),
    llm: null,
    skipRouter: true,
  });
  expect(result.kind).toBe("offline");
  if (result.kind !== "offline") throw new Error("expected offline result");
  return result;
}

describe("QA precision regressions", () => {
  it("keeps 荒尾三中 player/SB lists on the dedicated digest", async () => {
    const result = await ask("荒尾三中の選手とSB一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("田中羚弥");
    expect(result.text).toContain("福島志帆");
    expect(result.text).not.toContain("熊本西原中");
  });

  it("answers the female jog template from the practice template table", async () => {
    const result = await ask("女子ジョグのテンプレートペースは？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toMatch(/4:20|4:30/);
  });

  it("answers a year-specific top-six pace from the historical pace table", async () => {
    const result = await ask("荒玉男子2023年の総合1〜6位の平均ペースは？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("3:15.4");
  });

  it("treats 平均速度 as a pace alias for year-specific top-six questions", async () => {
    const result = await ask("荒玉男子2023年1位から6位までの平均速度は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("3:15.4");
  });

  it("answers weather update questions from the weather operations document", async () => {
    const result = await ask("玉名の天気データはどう更新する？");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("Open-Meteo");
  });

  it("answers the weather forecast output path from the same document", async () => {
    const result = await ask("天気予報の保存先ファイルは？");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("weather/tamana-forecast.json");
  });

  it("answers the VDOT CLI question from the practice generation guide", async () => {
    const result = await ask("VDOTからTペースを出すCLIは？");
    expect(result.sources).toEqual(["docs/ai-practice-generation.md"]);
    expect(result.text).toContain("scripts/daniels_pace.py");
  });

  it("answers that practice meets do not count toward Daiming load", async () => {
    const result = await ask("練習会は岱明の負荷に数える？");
    expect(result.sources).toEqual(["repo-docs/adr/006-practice-meets-not-load.md"]);
    expect(result.text).toContain("基本不参加");
  });

  it("answers a dated 玉名市練習会 result from the practice record", async () => {
    const result = await ask("2026年9月22日の玉名市練習会で岱明の結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
    expect(result.text).toContain("村上");
    expect(result.text).toContain("3:30 - 3:23");
    expect(result.text).toContain("男子1000m×3本");
  });

  it("answers stride-count questions from practice records", async () => {
    const result = await ask("流しは何本やる？");
    expect(result.sources).toEqual(["drive-text/練習/練習の記録.md"]);
    expect(result.text).toContain("流し2本");
    expect(result.text).toContain("日によって本数は異なります");
  });

  it("answers post-ekiden practice questions from practice records", async () => {
    const result = await ask("中体連駅伝明けの練習はどんな感じ？");
    expect(result.sources).toEqual(["drive-text/練習/練習の記録.md"]);
    expect(result.text).toContain("中体連駅伝明け最初の練習");
    expect(result.text).toContain("流し2本");
  });

  it("answers movement-drill questions from the Daiming calendar", async () => {
    const result = await ask("動きづくりはある？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり");
  });

  it("answers club practice-day questions from the staff memo", async () => {
    const result = await ask("部活の練習日はいつ？");
    expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
    expect(result.text).toContain("月・火・木・金");
  });

  it("answers evening-practice schedule questions from the Daiming calendar", async () => {
    const result = await ask("いだてん岱明夕練の日程を教えて");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("いだてん岱明夕練");
  });

  it("answers dated practice-content questions from the Daiming calendar", async () => {
    const result = await ask("2025-10-20のいだてん岱明練習の内容は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2025-10-20");
  });

  it("answers trial-run date questions from the Daiming calendar", async () => {
    const result = await ask("岱明駅伝試走はいつ？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("岱明駅伝試走");
  });

  it("answers Daiming practice-tag questions from the Daiming calendar", async () => {
    const result = await ask("いだてん岱明練習のタグについて教えて");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("practice:daiming");
  });

  it("answers the cancelled prefectural-sports practice question from the calendar", async () => {
    const result = await ask("県民スポーツ大会中止に伴う練習会について教えて");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("県民スポーツ大会中止");
  });

  it("answers a dated practice-meet question from the Daiming calendar", async () => {
    const result = await ask("2026-08-20の練習会はどうなった？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-08-20");
  });

  it("keeps the 2025 communication meet URL on the matching result note", async () => {
    const result = await ask("第71回全日本中学校通信陸上競技大会の結果リンク教えて（2025）");
    expect(result.sources).toEqual([
      "drive-text/大会/2025年度/0628-0629_全日本中学校通信陸上競技大会熊本県大会/岱明の結果.md",
    ]);
    expect(result.text).toContain("rel101.html");
  });

  it("routes the 2025 prefectural meet URL to its database", async () => {
    const result = await ask("県中体連の結果URLほしい");
    expect(result.sources).toEqual(["drive-text/記録データベース/2025年度/県中体連.csv"]);
    expect(result.text).toContain("chugaku/rel");
  });

  it("keeps the 2026 Kumamoto City championship URL on its result note", async () => {
    const result = await ask("第４５回 熊本市陸上競技選手権大会の結果リンク教えて（2026）");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0418_第４５回熊本市陸上競技選手権大会/岱明の結果.md",
    ]);
    expect(result.text).toContain("sisen_i/450418");
  });

  it("keeps the second long-distance meet URL on its result note", async () => {
    const result = await ask("2026年度第２回熊本県長距離記録会の結果リンク教えて（2026）");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0704_第２回熊本県長距離記録会/岱明の結果.md",
    ]);
    expect(result.text).toContain("26,7,4long/kyougi.html");
  });

  it("routes the urban championship URL to the matching record database", async () => {
    const result = await ask("第79回 全九州都市対抗陸上競技大会の結果リンク教えて（2026）");
    expect(result.sources).toEqual(["drive-text/記録データベース/2026年度/中学生記録.csv"]);
    expect(result.text).toContain("omuta.meet7.org");
  });

  it("answers the A-day schedule from the Daiming calendar", async () => {
    const result = await ask("岱明中 A日課（6時間）はいつ？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("岱明中 A日課（6時間）");
  });

  it("answers an unqualified May 8 schedule question from the calendar", async () => {
    const result = await ask("5月8日の予定は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2025-05-08");
  });

  it("keeps a dated July 20 schedule question on the calendar only", async () => {
    const result = await ask("2026-07-20は何の予定？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-07-20");
  });

  it("narrows a dated A-day lookup to the requested calendar date", async () => {
    const result = await ask("2026-09-08のA日課は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-08");
    expect(result.text).toContain("岱明中 A日課（6時間）");
  });

  it("keeps the 2025 39th prefectural championship URL on its result note", async () => {
    const result = await ask("第39回熊本県中学校陸上競技選手権大会の結果URLは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2025年度/0607-0608_熊本県中学生陸上競技選手権/岱明の結果.md",
    ]);
    expect(result.text).toContain("kumariku.org/25");
  });

  it("routes the fourth long-distance meet URL question to its scheduled overview", async () => {
    const result = await ask("2026年度第4回熊本県長距離記録会の結果リンク教えて");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/1010_第４回熊本県長距離記録会/概要.md"]);
    expect(result.text).toContain("第 ４回 熊本県長距離記録会");
  });

  it("routes the fifth long-distance meet URL question to its scheduled overview", async () => {
    const result = await ask("2026年度第5回熊本県長距離記録会の結果リンク教えて");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/1212_第５回熊本県長距離記録会/概要.md"]);
    expect(result.text).toContain("第 ５回 熊本県長距離記録会");
  });

  it("keeps the Kanakuri result URL on the matching result note", async () => {
    const result = await ask("金栗記念の結果URLを教えて（2026）");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0411_第３４回金栗記念選抜陸上中長距離熊本大会/岱明の結果.md",
    ]);
    expect(result.text).toContain("kanaguri");
  });

  it("routes a prefectural meet result question to the prefectural database", async () => {
    const result = await ask("県中体連の結果は？");
    expect(result.sources).toEqual(["drive-text/記録データベース/2025年度/県中体連.csv"]);
    expect(result.text).toContain("県中体連");
  });

  it("routes a prefectural meet date question to its timetable", async () => {
    const result = await ask("県中体連の開催日は？");
    expect(result.sources).toEqual(["drive-text/記録データベース/2025年度/県中体連.csv"]);
    expect(result.text).toMatch(/2025-07-19|2025-07-20/);
  });

  it("uses the injected current date for 今日の予定", async () => {
    const result = await askAt("今日の予定は？", "2026-09-08T00:00:00+09:00");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-08");
  });

  it("uses the injected current date for 明日の予定", async () => {
    const result = await askAt("明日の予定は？", "2026-09-07T00:00:00+09:00");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-08");
  });

  it("routes an unqualified Daiming rank question to the team digest", async () => {
    const result = await ask("荒玉駅伝で岱明は何位？");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/岱明.md"]);
    expect(result.text).toContain("2025年荒玉駅伝男子 岱明は6位");
  });

  it("keeps a combined practice venue question on the dated practice note", async () => {
    const result = await ask("玉名市合同練習会の会場は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("おおはまふれあいセンター");
  });

  it("keeps a dated A-day question focused on the requested date", async () => {
    const result = await ask("2026年9月8日の予定は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-08");
    expect(result.text).toContain("岱明中 A日課（6時間）");
  });

  it("routes the prefectural championship URL to the 2026 result note", async () => {
    const result = await ask("熊本県中学校陸上選手権の結果URLは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0523-0524_熊本県中学校陸上選手権・混成/岱明の結果.md",
    ]);
    expect(result.text).toContain("kumariku.com/competition");
  });

  it("routes the junior Olympic URL to its result note", async () => {
    const result = await ask("ジュニアオリンピックU16熊本県予選会の結果リンクは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0829_ジュニアオリンピックU16熊本県予選会/岱明の結果.md",
    ]);
    expect(result.text).toContain("ジュニアオリンピックU１６");
  });

  it("routes the night meet URL to the night meet result note", async () => {
    const result = await ask("玉名郡ナイター中長距離記録会の結果URLは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0829_玉名郡ナイター中・長距離記録会/岱明の結果.md",
    ]);
    expect(result.text).toContain("玉名郡ナイター中・長距離記録会");
  });

  it("routes the Kumamoto city record-meet URL to the record database", async () => {
    const result = await ask("熊本市陸上競技記録会の結果リンクは？");
    expect(result.sources).toEqual(["drive-text/記録データベース/2026年度/中学生記録.csv"]);
    expect(result.text).toContain("kcrk.jp/i-mode/kiroku/272");
  });

  it("keeps this-week schedule retrieval on the calendar", async () => {
    const result = await ask("今週の予定は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09");
  });

  it("keeps next-week schedule retrieval on the calendar", async () => {
    const result = await ask("来週の予定は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09");
  });

  it("keeps a month schedule query on the calendar", async () => {
    const result = await ask("9月の予定を教えて");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09");
  });

  it("keeps generic practice schedule retrieval on the calendar", async () => {
    const result = await ask("練習の予定は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("practice:daiming");
  });

  it("routes the October 10 schedule to the fourth long-distance meet overview", async () => {
    const result = await ask("2026年10月10日の予定は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/1010_第４回熊本県長距離記録会/概要.md",
    ]);
    expect(result.text).toContain("2026-10-10");
  });

  it("keeps the city-record result URL attached to its matching database", async () => {
    const result = await ask("2026年の熊本市陸上競技記録会の結果URLは？");
    expect(result.sources).toEqual(["drive-text/記録データベース/2026年度/中学生記録.csv"]);
    expect(result.text).toContain("kcrk.jp/i-mode/kiroku/272");
  });

  it("routes generic Daiming practice content to the calendar", async () => {
    const result = await ask("岱明中の練習内容は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("practice:daiming");
  });

  it("keeps 今日の練習 on the calendar", async () => {
    const result = await askAt("今日の練習は？", "2026-09-24T00:00:00+09:00");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-24");
  });

  it("keeps 明日の練習 on the calendar", async () => {
    const result = await askAt("明日の練習は？", "2026-09-23T00:00:00+09:00");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-24");
  });

  it("answers the morning-practice schedule from the staff memo", async () => {
    const result = await ask("いだてん岱明の朝練はいつ？");
    expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
    expect(result.text).toContain("月・火・木・金");
  });

  it("focuses the evening-practice schedule on the matching calendar entries", async () => {
    const result = await ask("いだてん岱明の夕練はいつ？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("いだてん岱明夕練");
  });

  it("answers school-event schedule questions from the calendar", async () => {
    const result = await ask("学校行事予定を教えて");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("学校行事");
  });

  it("focuses a dated practice-meet question on the requested date", async () => {
    const result = await ask("9月8日の練習会は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-08");
    expect(result.text).toContain("練習会（岱明）（県民スポーツ大会中止に伴い中止）");
  });

  it("focuses a dated Tamana practice-meet question on the calendar", async () => {
    const result = await ask("2026-09-08の玉名市練習会は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-08");
  });

  it("answers the morning-practice meeting-time alias from the staff memo", async () => {
    const result = await ask("いだてん岱明朝練の集合時間は？");
    expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
    expect(result.text).toContain("7:20");
  });

  it("focuses a generic practice-meet schedule query on the calendar", async () => {
    const result = await ask("練習会の日程は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("練習会");
  });

  it("answers the dated Tamana practice status from the practice note", async () => {
    const result = await ask("2026年9月22日の玉名市練習会は中止？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("2026-09-22");
  });

  it("keeps the September school schedule on the calendar", async () => {
    const result = await ask("岱明中の9月行事予定は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-01");
  });

  it("does not claim October school details from the September calendar head", async () => {
    const result = await ask("10月の学校行事予定は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-10");
  });

  it("keeps the Kumamoto Nichi Ekiden date on its overview", async () => {
    const result = await ask("熊日駅伝の日程は？");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/0208_熊日駅伝/概要.md"]);
    expect(result.text).toContain("2026-02-08");
  });

  it("answers generic practice-meet status from the dated practice note", async () => {
    const result = await ask("練習会は開催された？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("おおはまふれあいセンター");
  });

  it("keeps Daiming competition schedules on the calendar", async () => {
    const result = await ask("岱明中の大会予定は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("大会");
    expect(result.text).toContain("2026-10-14");
  });

  it("keeps the 2025 Aragyoku result link query on both gender transcripts", async () => {
    const result = await ask("荒玉駅伝2025の結果リンクは？");
    expect(result.sources).toEqual([
      "aragyoku/transcripts/2025-男子.json",
      "aragyoku/transcripts/2025-女子.json",
    ]);
    expect(result.text).toContain("2025年荒玉駅伝の結果");
  });

  it("keeps Nagomi result links on the two gender result sheets", async () => {
    const result = await ask("なごみ駅伝の結果リンクは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/男子成績表.md",
      "drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/女子成績表.md",
    ]);
    expect(result.text).toContain("2026年なごみ駅伝の結果");
  });

  it("keeps the Kanakuri Ekiden date on its overview", async () => {
    const result = await ask("金栗駅伝の開催日は？");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/0315_金栗駅伝/概要.md"]);
    expect(result.text).toContain("2026-03-15");
  });

  it("keeps the practice-record query on the 2026 practice note", async () => {
    const result = await ask("玉名市練習会の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("玉名市練習会＆BBQ");
  });

  it("reports when the practice note lacks a participant count", async () => {
    const result = await ask("玉名市練習会の参加人数は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("確定値の記載がありません");
  });

  it("keeps the Daiming meet-venue query on the calendar", async () => {
    const result = await ask("岱明中の大会会場は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("大会");
  });

  it("preserves the out-of-scope answer for live weather", async () => {
    const result = await answerQuestion("今日の玉名の天気は？", {
      defaultYear: 2026,
      llm: null,
      skipRouter: true,
    });
    expect(result.kind).toBe("refused");
  });

  it("keeps Takada Mana's 1500m SB on the dedicated athlete file", async () => {
    const result = await ask("高田麻那の1500mSBは？");
    expect(result.sources).toEqual(["out-analysis/athletes/takada-mana.md"]);
    expect(result.text).toContain("高田麻那");
  });

  it("keeps the full Daiming record lookup on the team digest", async () => {
    const result = await ask("岱明中の全記録を見せて");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/岱明中.md"]);
    expect(result.text).toContain("岱明中 記録一覧");
  });

  it("keeps the practice-deadline answer on the practice note", async () => {
    const result = await ask("玉名市練習会の申込締切は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("2026年9月10日");
  });

  it("keeps the Aragyoku venue clarification concise", async () => {
    const result = await ask("荒玉駅伝の会場は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("正本資料では確認できません");
  });

  it("keeps the Nagomi venue answer on the Nagomi documents", async () => {
    const result = await ask("2026年なごみ駅伝の会場は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/プログラム.pdf.md",
      "drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/開催要項.md",
      "drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/当日スケジュール.md",
    ]);
    expect(result.text).toContain("和水町三加和公民館");
  });

  it("keeps the monthly practice-meet query on the calendar", async () => {
    const result = await ask("今月の練習会予定は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09");
  });

  it("keeps the dated practice record concise for a result lookup", async () => {
    const result = await ask("2026年9月22日の玉名市練習会の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("resolves 一昨年 to the 2024 male winner", async () => {
    const result = await ask("一昨年の荒玉男子優勝校は？");
    expect(result.sources).toEqual(["aragyoku/winners-by-year.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子の優勝校は南関");
    expect(result.text).toContain("56:38");
  });

  it("routes last-year junior Ekiden results to the 2025 result note", async () => {
    const result = await ask("去年のジュニア駅伝の岱明の結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2025年度/0927_第２回熊本県ジュニア駅伝競走大会/岱明の結果.md",
    ]);
    expect(result.text).toContain("ジュニア駅伝");
  });

  it("keeps the 2025 junior result note focused for a dated alias", async () => {
    const result = await ask("2025年ジュニア駅伝の岱明結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2025年度/0927_第２回熊本県ジュニア駅伝競走大会/岱明の結果.md",
    ]);
  });

  it("keeps the male course-era question on meet records", async () => {
    const result = await ask("荒玉男子のcourse_eraは？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toMatch(/men_2024plus|men_pre2024/);
  });

  it("keeps the old-course distance question on distance definitions", async () => {
    const result = await ask("旧コース男子6区の距離は？");
    expect(result.sources).toEqual(["docs/aragyoku-ekiden-distance-definitions.md"]);
    expect(result.text).toContain("4.00");
  });

  it("keeps the male board-record reset question on meet records", async () => {
    const result = await ask("男子の大会記録がリセットされたのはいつ？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024");
  });

  it("keeps the silver-mat size question on the parent memo", async () => {
    const result = await ask("銀マットのサイズは？");
    expect(result.sources).toEqual(["out-analysis/line-chats/daiming-parents.md"]);
    expect(result.text).toMatch(/180|60/);
  });

  it("keeps the evening start-time question on the calendar", async () => {
    const result = await ask("夕練の開始時刻は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toMatch(/18:00|18時/);
  });

  it("keeps the 2025 玉陵 total-time question on the team digest", async () => {
    const result = await ask("玉陵の2025男子総合タイムは？");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/玉陵.md"]);
    expect(result.text).toContain("58:02");
  });

  it("keeps the 2024 荒尾三女子 rank question on the team digest", async () => {
    const result = await ask("荒尾三の2024女子順位は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/荒尾三.md"]);
    expect(result.text).toContain("2位");
  });

  it("resolves おととし to the 2024 female winner", async () => {
    const result = await ask("おととしの荒玉女子優勝校は？");
    expect(result.sources).toEqual(["aragyoku/winners-by-year.md"]);
    expect(result.text).toContain("2024年荒玉駅伝女子の優勝校は南関");
    expect(result.text).toContain("42:25");
  });

  it("resolves 一昨年 to the 2024 female winner", async () => {
    const result = await ask("一昨年の荒玉女子優勝校は？");
    expect(result.sources).toEqual(["aragyoku/winners-by-year.md"]);
    expect(result.text).toContain("2024年荒玉駅伝女子の優勝校は南関");
  });

  it("answers a bare evening-practice start-time alias", async () => {
    const result = await ask("夕練は何時から？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("18:00");
  });

  it("answers a compact evening-practice start-time alias", async () => {
    const result = await ask("いだてん岱明夕練開始時間は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("18:00");
  });

  it("keeps a Japanese dated practice lookup on the exact calendar date", async () => {
    const result = await ask("2026年9月8日の練習は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-08");
  });

  it("keeps a slash-formatted May schedule lookup on the calendar", async () => {
    const result = await ask("5/8の予定は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2025-05-08");
  });

  it("answers the 2025 female winner from the winner digest", async () => {
    const result = await ask("2025年荒玉女子の総合優勝校は？");
    expect(result.sources).toEqual(["aragyoku/winners-by-year.md"]);
    expect(result.text).toContain("玉名");
    expect(result.text).toContain("41:58");
  });

  it("answers the 2025 玉陵 female total time from the team digest", async () => {
    const result = await ask("玉陵の2025女子総合タイムは？");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/玉陵.md"]);
    expect(result.text).toContain("49:36");
  });

  it("keeps the 2025 junior result alias on the junior result note", async () => {
    const result = await ask("2025ジュニア駅伝の岱明結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2025年度/0927_第２回熊本県ジュニア駅伝競走大会/岱明の結果.md",
    ]);
  });

  it("keeps a course-era distance alias on the distance definitions", async () => {
    const result = await ask("新コース男子6区の距離は？");
    expect(result.sources).toEqual(["docs/aragyoku-ekiden-distance-definitions.md"]);
    expect(result.text).toContain("3.00");
  });

  it("keeps an unqualified 2024 winner-margin question on the focus digest", async () => {
    const result = await ask("荒玉男子2024の優勝差は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_2024_2025_focus_teams.md"]);
    expect(result.text).toContain("優勝との差");
  });

  it("keeps an unqualified 2025 winner-margin question on the focus digest", async () => {
    const result = await ask("荒玉男子2025の優勝差は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_2024_2025_focus_teams.md"]);
    expect(result.text).toContain("優勝との差");
  });

  it("keeps a female winner-margin question on the focus digest", async () => {
    const result = await ask("荒玉女子2024の優勝差は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_2024_2025_focus_teams.md"]);
    expect(result.text).toContain("優勝との差");
  });

  it("keeps a winner-gap wording on the focus digest", async () => {
    const result = await ask("荒玉2024男子は優勝から何分離れていた？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_2024_2025_focus_teams.md"]);
    expect(result.text).toContain("優勝との差");
  });

  it("routes an official Kumamoto City record-meet result lookup to the database", async () => {
    const result = await ask("熊本市陸上競技記録会の公式結果は？");
    expect(result.sources).toEqual(["drive-text/記録データベース/2026年度/中学生記録.csv"]);
  });

  it("routes a short Kumamoto City record-meet result lookup to the database", async () => {
    const result = await ask("熊本市陸上競技記録会の結果は？");
    expect(result.sources).toEqual(["drive-text/記録データベース/2026年度/中学生記録.csv"]);
  });

  it("focuses a September 8 cancellation question on the calendar", async () => {
    const result = await ask("9月8日の練習会は中止？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-08");
  });

  it("focuses a dated September 8 status question on the calendar", async () => {
    const result = await ask("2026年9月8日練習会の開催状況は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-08");
  });

  it("routes the 274th Kumamoto City record-meet result link to the database", async () => {
    const result = await ask("第274回熊本市陸上競技記録会の結果リンクは？");
    expect(result.sources).toEqual(["drive-text/記録データベース/2026年度/中学生記録.csv"]);
  });

  it("focuses the dated September 8 practice status on the calendar", async () => {
    const result = await ask("2026-09-08の練習会はどうなった？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2026-09-08");
  });

  it("summarizes all recent male winners for a historical query", async () => {
    const result = await ask("荒玉男子の歴代優勝校は？");
    expect(result.sources).toEqual(["aragyoku/winners-by-year.md"]);
    expect(result.text).toContain("2021年");
    expect(result.text).toContain("2025年");
  });

  it("summarizes all recent female winners for a historical query", async () => {
    const result = await ask("荒玉女子の歴代優勝校は？");
    expect(result.sources).toEqual(["aragyoku/winners-by-year.md"]);
    expect(result.text).toContain("2021年");
    expect(result.text).toContain("2025年");
  });

  it("summarizes both genders for an unqualified historical winner query", async () => {
    const result = await ask("荒玉の歴代優勝校は？");
    expect(result.sources).toEqual(["aragyoku/winners-by-year.md"]);
    expect(result.text).toContain("男子");
    expect(result.text).toContain("女子");
    expect(result.text).toContain("2021年");
    expect(result.text).toContain("2025年");
  });

  it("summarizes the recent five-year male winner table", async () => {
    const result = await ask("荒玉男子の過去5年の優勝校は？");
    expect(result.sources).toEqual(["aragyoku/winners-by-year.md"]);
    expect(result.text).toContain("2021年");
    expect(result.text).toContain("2025年");
  });

  it("summarizes the recent five-year female winner table", async () => {
    const result = await ask("荒玉女子の過去5年の優勝校は？");
    expect(result.sources).toEqual(["aragyoku/winners-by-year.md"]);
    expect(result.text).toContain("2021年");
    expect(result.text).toContain("2025年");
  });

  it("answers an unqualified September 8 practice cancellation", async () => {
    const result = await ask("9月8日の練習会は開催？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("中止");
  });

  it("answers the September 8 practice cancellation with a date", async () => {
    const result = await ask("2026年9月8日練習会は開催？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("中止");
  });

  it("answers a slash-formatted September practice cancellation", async () => {
    const result = await ask("9/8の練習会は中止？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("中止");
  });

  it("keeps the September 8 practice status on the calendar", async () => {
    const result = await ask("2026-09-08練習会の開催状況は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("中止");
  });

  it("keeps a dated cancellation lookup on the calendar", async () => {
    const result = await ask("2026-09-08の練習会は中止になった？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("中止");
  });

  it("routes the first long-distance meet result to its result note", async () => {
    const result = await ask("第1回熊本県長距離記録会の結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0509_第１回熊本県長距離記録会/岱明の結果.md",
    ]);
  });

  it("routes the first long-distance meet result link to its result note", async () => {
    const result = await ask("第1回熊本県長距離記録会の結果リンクは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0509_第１回熊本県長距離記録会/岱明の結果.md",
    ]);
  });

  it("routes an unqualified night-meet result to the full result sheet", async () => {
    const result = await ask("玉名郡ナイター中長距離の結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0829_玉名郡ナイター中・長距離記録会/全結果.md",
    ]);
  });

  it("keeps a night-meet result lookup on the full result sheet", async () => {
    const result = await ask("ナイター中長距離記録会の結果一覧は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0829_玉名郡ナイター中・長距離記録会/全結果.md",
    ]);
  });

  it("routes a generic junior Olympic result to its result note", async () => {
    const result = await ask("ジュニアオリンピック熊本県予選の結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0829_ジュニアオリンピックU16熊本県予選会/岱明の結果.md",
    ]);
  });

  it("routes an urban championship result to the record database", async () => {
    const result = await ask("全九州都市対抗の結果は？");
    expect(result.sources).toEqual(["drive-text/記録データベース/2026年度/中学生記録.csv"]);
  });

  it("routes a Kanakuri Memorial result to its result note", async () => {
    const result = await ask("金栗記念の岱明結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0411_第３４回金栗記念選抜陸上中長距離熊本大会/岱明の結果.md",
    ]);
  });

  it("routes the first long-distance meet official result to its result note", async () => {
    const result = await ask("第1回熊本県長距離記録会の公式結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0509_第１回熊本県長距離記録会/岱明の結果.md",
    ]);
  });

  it("routes a junior Olympic result link to its result note", async () => {
    const result = await ask("ジュニアオリンピック熊本県予選の結果リンクは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0829_ジュニアオリンピックU16熊本県予選会/岱明の結果.md",
    ]);
  });

  it("routes a city championship result link to the record database", async () => {
    const result = await ask("全九州都市対抗の結果リンクは？");
    expect(result.sources).toEqual(["drive-text/記録データベース/2026年度/中学生記録.csv"]);
  });

  it("routes the second long-distance meet result to its result note", async () => {
    const result = await ask("第2回熊本県長距離記録会の結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0704_第２回熊本県長距離記録会/岱明の結果.md",
    ]);
  });

  it("routes the second long-distance official result to its result note", async () => {
    const result = await ask("第2回熊本県長距離記録会の公式結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0704_第２回熊本県長距離記録会/岱明の結果.md",
    ]);
  });

  it("routes an unqualified long-distance result link to the latest completed meet", async () => {
    const result = await ask("熊本県長距離記録会の結果リンクは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0704_第２回熊本県長距離記録会/岱明の結果.md",
    ]);
  });

  it("routes the prefectural middle-school championship result to its 2026 note", async () => {
    const result = await ask("熊本県中学校陸上選手権の結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0523-0524_熊本県中学校陸上選手権・混成/岱明の結果.md",
    ]);
  });

  it("routes the communication-meet result to its 2026 note", async () => {
    const result = await ask("通信陸上の結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0613_全日本中学校通信陸上競技大会熊本県大会/岱明の結果.md",
    ]);
  });

  it("routes the city championship result to its 2026 note", async () => {
    const result = await ask("熊本市陸上競技選手権の結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0418_第４５回熊本市陸上競技選手権大会/岱明の結果.md",
    ]);
  });

  it("routes the prefectural championship result link to its 2026 note", async () => {
    const result = await ask("熊本県中学校陸上選手権の結果リンクは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0523-0524_熊本県中学校陸上選手権・混成/岱明の結果.md",
    ]);
  });

  it("routes the communication-meet result link to its 2026 note", async () => {
    const result = await ask("通信陸上の結果リンクは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0613_全日本中学校通信陸上競技大会熊本県大会/岱明の結果.md",
    ]);
  });

  it("routes the city championship result link to its 2026 note", async () => {
    const result = await ask("熊本市陸上競技選手権の結果リンクは？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0418_第４５回熊本市陸上競技選手権大会/岱明の結果.md",
    ]);
  });

  it("routes the unqualified long-distance result to a completed result note", async () => {
    const result = await ask("熊本県長距離記録会の結果は？");
    expect(result.sources).toEqual([
      "drive-text/大会/2026年度/0704_第２回熊本県長距離記録会/岱明の結果.md",
    ]);
  });

  it("answers Norwegian 45/15 template questions from the method ADR", async () => {
    const result = await ask("norwegian-45-15テンプレは何のセッション？");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/Norwegian|ノルウェー|norwegian-45-15|GZ|Tセッション/);
  });

  it("routes year-and-gender leg-athlete lookups to the requested transcript", async () => {
    const result = await ask("2012年荒玉男子1区の選手は？");
    expect(result.sources).toEqual(["aragyoku/transcripts/2012-男子.json"]);
    expect(result.text).toMatch(/田上|12:12/);
  });

  it("answers the forecast file alias from the weather operations document", async () => {
    const result = await ask("玉名の予報ファイルはどこに保存する？");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("tamana-forecast");
  });

  it("answers the weather updater script alias from the weather operations document", async () => {
    const result = await ask("天気更新スクリプト名は？");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("update_tamana_weather.py");
  });

  it("recognizes a shorthand top-six average question", async () => {
    const result = await ask("荒玉男子2024年の上位6平均は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toMatch(/3:1[5-9]/);
  });

  it("routes fatigue questions about practice meets to the load ADR", async () => {
    const result = await ask("練習会を疲労計算に入れる？");
    expect(result.sources).toEqual(["repo-docs/adr/006-practice-meets-not-load.md"]);
    expect(result.text).toContain("基本不参加");
  });

  it("answers the female 2800m jog standard from the practice menu table", async () => {
    const result = await ask("女子ジョグ2800mの標準は？");
    expect(result.sources).toEqual(["practice/daiming-practice-menus-kpace.md"]);
    expect(result.text).toMatch(/2800m|2\.8km/);
    expect(result.text).toMatch(/4:45|5:00/);
  });

  it("routes GZ/T classification of 45/15 to the Norwegian ADR", async () => {
    const result = await ask("45/15はGZとTのどちら？");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/GZ\/T|GZ|T/);
  });

  it("routes a Norwegian 45/15 shorthand to the Norwegian ADR", async () => {
    const result = await ask("norwegianの45/15は何？");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/45-15|45\/15|GZ\/T/);
  });

  it("treats a plain top-six average as the historical pace question", async () => {
    const result = await ask("荒玉男子2024年1位から6位までの平均は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toMatch(/3:1[5-9]/);
  });

  it("accepts spaced and capitalized Norwegian 45-15 wording", async () => {
    const result = await ask("Norwegian 45-15はどのセッション？");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/GZ\/T|45-15|セッション/);
  });

  it("answers the female jog pace alias instead of returning a table fragment", async () => {
    const result = await ask("女子ジョグのペース目安は？");
    expect(result.sources).toEqual(["practice/daiming-practice-menus-kpace.md"]);
    expect(result.text).toContain("k/4:45");
  });

  it("answers the male jog pace alias instead of returning a table fragment", async () => {
    const result = await ask("男子ジョグのペース目安は？");
    expect(result.sources).toEqual(["practice/daiming-practice-menus-kpace.md"]);
    expect(result.text).toContain("k/4:45");
  });

  it("answers an unqualified jog standard from the practice menu", async () => {
    const result = await ask("ジョグの標準ペースは？");
    expect(result.sources).toEqual(["practice/daiming-practice-menus-kpace.md"]);
    expect(result.text).toMatch(/男子.*女子|女子.*男子/);
    expect(result.text).toContain("k/4:45");
  });

  it("keeps weather JSON path questions in repo scope", async () => {
    const result = await ask("天気JSONの保存場所は？");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("tamana-forecast.json");
  });

  it("keeps weather CSV path questions in repo scope", async () => {
    const result = await ask("天気CSVの保存場所は？");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("tamana-forecast.csv");
  });

  it("answers the weather update command alias", async () => {
    const result = await ask("天気更新コマンドを教えて");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("update_tamana_weather.py");
  });

  it("accepts kanji top-six wording", async () => {
    const result = await ask("2024年荒玉男子上位六校の平均ペースは？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("3:19.3");
  });

  it("accepts best-six wording for the historical pace table", async () => {
    const result = await ask("2024年荒玉男子ベスト6平均ペースは？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("3:19.3");
  });

  it("accepts an explicit 1位〜6位 range for top-six pace", async () => {
    const result = await ask("荒玉男子2024年1位〜6位平均ペースは？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("3:19.3");
  });

  it("accepts a Unicode hyphen in 45-15 wording", async () => {
    const result = await ask("Norwegian 45‐15は？");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/GZ\/T|45-15|セッション/);
  });

  it("accepts weather JSON wording with a forecast qualifier", async () => {
    const result = await ask("天気予報JSONはどこ？");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("tamana-forecast.json");
  });

  it("accepts a location-prefixed weather JSON question", async () => {
    const result = await ask("玉名天気のJSONファイルは？");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("tamana-forecast.json");
  });

  it("accepts a weather CSV output question without the word 保存先", async () => {
    const result = await ask("天気のCSVはどこに出る？");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("tamana-forecast.csv");
  });

  it("accepts a forecast CSV filename question", async () => {
    const result = await ask("天気予報CSVファイルは？");
    expect(result.sources).toEqual(["repo-docs/tamana-weather.md"]);
    expect(result.text).toContain("tamana-forecast.csv");
  });

  it("routes Japanese Norwegian 45-15 wording to the method ADR", async () => {
    const result = await ask("ノルウェー式の45‐15は？");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/45-15|GZ\/T|セッション/);
  });

  it("routes a Japanese Norwegian 45-15 template question to the method ADR", async () => {
    const result = await ask("ノルウェー式45‐15テンプレは？");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/45-15|GZ\/T|テンプレ/);
  });

  it("answers a male 3360m jog alias", async () => {
    const result = await ask("男子3360mジョグ目安");
    expect(result.sources).toEqual(["practice/daiming-practice-menus-kpace.md"]);
    expect(result.text).toContain("k/4:45");
  });

  it("accepts best-six kanji wording", async () => {
    const result = await ask("2024年荒玉男子ベスト六の平均");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("3:19.3");
  });

  it("routes gendered top-six pace questions without the 荒玉 token", async () => {
    const result = await ask("2024年男子上位6校の平均kmペースは？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("3:19.3");
  });

  it("accepts a best-six pace alias with the 荒玉 token", async () => {
    const result = await ask("2024年荒玉男子ベスト六平均ペースは？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("3:19.3");
  });

  it("answers the VDOT calculation method alias", async () => {
    const result = await ask("VDOTでTペースを計算する方法は？");
    expect(result.sources).toEqual(["docs/ai-practice-generation.md"]);
    expect(result.text).toContain("daniels_pace.py");
  });

  it("answers a standalone T-pace script question", async () => {
    const result = await ask("Tペース計算のスクリプトは？");
    expect(result.sources).toEqual(["docs/ai-practice-generation.md"]);
    expect(result.text).toContain("daniels_pace.py");
  });

  it("answers the spaced Daniels calculator CLI alias", async () => {
    const result = await ask("Daniels calculator CLIは？");
    expect(result.sources).toEqual(["docs/ai-practice-generation.md"]);
    expect(result.text).toContain("daniels_calculator.py");
  });

  it("answers a Python T-pace script question", async () => {
    const result = await ask("Tペースを出すPythonスクリプトは？");
    expect(result.sources).toEqual(["docs/ai-practice-generation.md"]);
    expect(result.text).toContain("daniels_pace.py");
  });

  it("routes Japanese Norwegian 45-15 shorthand with a Unicode hyphen", async () => {
    const result = await ask("ノルウェー式の45‐15は？");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/45-15|GZ\/T|セッション/);
  });

  it("routes Japanese Norwegian template wording with a Unicode hyphen", async () => {
    const result = await ask("ノルウェー式45‐15テンプレは？");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/45-15|GZ\/T|テンプレ/);
  });

  it("keeps a team-specific fifth-leg question on the team digest", async () => {
    const result = await ask("2025年荒玉女子玉名の5区は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/玉名.md"]);
    expect(result.text).toMatch(/5区|水本星夏|11:04/);
  });

  it("keeps a team-specific first-leg question on the team digest", async () => {
    const result = await ask("2024年荒玉男子の南関1区は誰？");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/南関.md"]);
    expect(result.text).toMatch(/坂梨天飛|9:16/);
  });

  it("routes a female jog distance pace question to the practice menu", async () => {
    const result = await ask("女子ジョグ2800mペース");
    expect(result.sources).toEqual(["practice/daiming-practice-menus-kpace.md"]);
    expect(result.text).toContain("k/4:45");
  });

  it("routes a male jog distance pace question to the practice menu", async () => {
    const result = await ask("男子3360mジョグペース");
    expect(result.sources).toEqual(["practice/daiming-practice-menus-kpace.md"]);
    expect(result.text).toContain("k/4:45");
  });

  it("selects the requested year for a meet leg record without 年 after the year", async () => {
    const result = await ask("荒玉駅伝2024男子1区の大会記録は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子の1区大会区間記録は9:01");
    expect(result.text).not.toContain("2025年荒玉駅伝男子");
  });

  it("selects the old-course distance for a 2023 leg question", async () => {
    const result = await ask("荒玉男子2023年1区は何km？");
    expect(result.sources).toContain("docs/aragyoku-ekiden-distance-definitions.md");
    expect(result.text).toContain("旧男子1区は3.95km");
  });

  it("answers the generic women distance composition concisely", async () => {
    const result = await ask("荒玉女子の距離構成は？");
    expect(result.sources).toContain("docs/aragyoku-ekiden-distance-definitions.md");
    expect(result.text).toContain("1区3.00km");
    expect(result.text).toContain("5区3.00km");
  });

  it("returns the full historical ranking summary for 岱明", async () => {
    const result = await ask("岱明の荒玉過去順位");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/岱明.md"]);
    expect(result.text).toContain("2012年荒玉駅伝男子");
    expect(result.text).toContain("2025年荒玉駅伝男子");
  });

  it("narrows 玉名附中 SB list wording to its team record digest", async () => {
    const result = await ask("玉名附中の選手とSB一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("玉名附中");
  });

  it("selects the old-course distance when the year is written first", async () => {
    const result = await ask("2023年荒玉男子1区の距離は？");
    expect(result.sources).toContain("docs/aragyoku-ekiden-distance-definitions.md");
    expect(result.text).toContain("旧男子1区は3.95km");
  });

  it("selects the requested year for a compact meet-record wording", async () => {
    const result = await ask("2024年荒玉男子1区の大会記録は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子の1区大会区間記録は9:01");
  });

  it("answers a compact year-first meet-record alias", async () => {
    const result = await ask("2024年荒玉男子1区大会記録は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子の1区大会区間記録は9:01");
  });

  it("answers a women distance composition question with all five legs", async () => {
    const result = await ask("荒玉駅伝女子の距離構成");
    expect(result.sources).toContain("docs/aragyoku-ekiden-distance-definitions.md");
    expect(result.text).toContain("2区1.855km");
    expect(result.text).toContain("4区2.00km");
  });

  it("keeps the historical ranking query on the 岱明 digest", async () => {
    const result = await ask("岱明の荒玉駅伝過去順位は？");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/岱明.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子");
  });

  it("treats historical 成績 wording as a full 岱明 digest request", async () => {
    const result = await ask("岱明の荒玉歴代成績");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/岱明.md"]);
    expect(result.text).toContain("2012年荒玉駅伝男子");
    expect(result.text).toContain("2025年荒玉駅伝女子");
  });

  it("keeps a generic women distance question on the distance definitions", async () => {
    const result = await ask("荒玉駅伝女子の距離");
    expect(result.sources).toEqual(["docs/aragyoku-ekiden-distance-definitions.md"]);
    expect(result.text).toContain("1区3.00km");
    expect(result.text).toContain("5区3.00km");
  });

  it("answers a compact year-gender-leg record wording", async () => {
    const result = await ask("2024年荒玉駅伝男子1区記録");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子の1区大会区間記録は9:01");
  });

  it("routes a 玉名附中 player list to the school record digest", async () => {
    const result = await ask("玉名附中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("accepts the 玉名付属中 alias for the school SB digest", async () => {
    const result = await ask("玉名付属中の選手とSB一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("accepts 玉高附属 wording for the school SB digest", async () => {
    const result = await ask("玉高附属の選手とSB一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("accepts a fullwidth slash in the Norwegian 45/15 alias", async () => {
    const result = await ask("ノルウェー式45／15");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/GZ|T|45/);
  });

  it("accepts spaces around an English Norwegian dash alias", async () => {
    const result = await ask("Norwegian 45 – 15");
    expect(result.sources).toEqual(["repo-docs/adr/002-norwegian-method-integration.md"]);
    expect(result.text).toMatch(/GZ|T|45/);
  });

  it("routes Daniels calculator wording to the practice generation guide", async () => {
    const result = await ask("Daniels calculatorの使い方");
    expect(result.sources).toEqual(["docs/ai-practice-generation.md"]);
    expect(result.text).toContain("scripts/daniels_calculator.py");
  });

  it("answers the generic men distance composition from both course eras", async () => {
    const result = await ask("荒玉男子の距離構成");
    expect(result.sources).toEqual(["docs/aragyoku-ekiden-distance-definitions.md"]);
    expect(result.text).toContain("2023年以前");
    expect(result.text).toContain("2024年以降");
  });

  it("answers a 2023 men distance composition without a leg number", async () => {
    const result = await ask("荒玉男子2023年距離構成");
    expect(result.sources).toEqual(["docs/aragyoku-ekiden-distance-definitions.md"]);
    expect(result.text).toContain("3.95km");
    expect(result.text).toContain("4.00km");
  });

  it("filters a historical ranking digest to women when requested", async () => {
    const result = await ask("岱明の荒玉過去順位女子");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/岱明.md"]);
    expect(result.text).toContain("2025年荒玉駅伝女子");
    expect(result.text).not.toContain("2025年荒玉駅伝男子");
  });

  it("returns the full historical digest for 三加和", async () => {
    const result = await ask("三加和の荒玉歴代成績");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/三加和.md"]);
    expect(result.text).toContain("2012年荒玉駅伝男子");
    expect(result.text).toContain("2025年荒玉駅伝女子");
  });

  it("routes 玉名付属 SB wording to the school record digest", async () => {
    const result = await ask("玉名付属のSB一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("routes 玉名附属 wording to the school record digest", async () => {
    const result = await ask("玉名附属の選手とSB一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("keeps 玉名付属 player lists on the school record digest", async () => {
    const result = await ask("玉名付属の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("answers a daniels_calculator.py question directly", async () => {
    const result = await ask("daniels_calculator.pyは何？");
    expect(result.sources).toEqual(["docs/ai-practice-generation.md"]);
    expect(result.text).toContain("scripts/daniels_calculator.py");
  });

  it("does not duplicate a VDOT T-pace answer", async () => {
    const result = await ask("TペースをVDOTから計算する方法");
    expect(result.sources).toEqual(["docs/ai-practice-generation.md"]);
    expect(result.text.match(/scripts\/daniels_pace\.py/g)?.length).toBe(1);
  });

  it("answers a current-course men distance composition", async () => {
    const result = await ask("荒玉男子2024年の距離構成");
    expect(result.sources).toEqual(["docs/aragyoku-ekiden-distance-definitions.md"]);
    expect(result.text).toContain("1区3.00km");
    expect(result.text).toContain("6区3.00km");
  });

  it("routes a generic 荒尾三中 player list to the SB digest", async () => {
    const result = await ask("荒尾三中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps a year-specific top-six pace answer to one table row", async () => {
    const result = await ask("荒玉男子2024年上位6校平均ペース");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("| 2024 | 6 | 17.71km | 3:19.3/km |");
    expect(result.text).not.toContain("| 2025 | 6 |");
  });

  it("accepts the compact year-first top-six pace alias", async () => {
    const result = await ask("荒玉2024男子上位6平均ペース");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("| 2024 | 6 | 17.71km | 3:19.3/km |");
    expect(result.text).not.toContain("| 2025 | 6 |");
  });

  it("answers an explicit 2024 first-leg award concisely", async () => {
    const result = await ask("2024年荒玉男子1区区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子1区の区間1位は米村和真");
    expect(result.text).not.toContain("2024年荒玉駅伝男子2区");
  });

  it("answers a compact year-first first-leg award alias", async () => {
    const result = await ask("2024荒玉男子1区区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子1区の区間1位は米村和真");
  });

  it("answers the latest men first-leg award alias", async () => {
    const result = await ask("荒玉男子1区区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("2025年荒玉駅伝男子1区の区間1位は江口大尊");
  });

  it("accepts an 駅伝-prefixed latest first-leg award alias", async () => {
    const result = await ask("荒玉駅伝男子1区区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("2025年荒玉駅伝男子1区の区間1位は江口大尊");
  });

  it("answers the polite first-leg award wording", async () => {
    const result = await ask("2024年荒玉男子1区の区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子1区の区間1位は米村和真");
  });

  it("summarizes an unqualified top-six pace question", async () => {
    const result = await ask("荒玉駅伝男子上位6校の平均ペース");
    expect(result.sources).toContain("out-analysis/aragyoku_top6_historical_average_pace.md");
    expect(result.text).toContain("期間加重平均：3:18.1/km");
    expect(result.text).not.toContain("順位別の歴代平均ペース");
  });

  it("keeps the full 2024 men section for an all-leg ranking question", async () => {
    const result = await ask("2024年荒玉駅伝男子の区間順位");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("2024年男子・区間別上位");
    expect(result.text).toContain("2024年荒玉駅伝男子1区の区間1位");
  });

  it("routes 南関中 player lists to the school digest", async () => {
    const result = await ask("南関中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/南関中.md"]);
    expect(result.text).toContain("# 南関中 記録一覧");
  });

  it("routes 南関中 SB aliases to the school digest", async () => {
    const result = await ask("南関中SB一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/南関中.md"]);
    expect(result.text).toContain("# 南関中 記録一覧");
  });

  it("routes 天水中 player lists to the school digest", async () => {
    const result = await ask("天水中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/天水中.md"]);
    expect(result.text).toContain("# 天水中 記録一覧");
  });

  it("routes 玉名中 player lists to the school digest", async () => {
    const result = await ask("玉名中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名中.md"]);
    expect(result.text).toContain("# 玉名中 記録一覧");
  });

  it("routes 岱明中 player lists away from LINE transcripts", async () => {
    const result = await ask("岱明中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/岱明中.md"]);
    expect(result.text).toContain("# 岱明中 記録一覧");
    expect(result.text).not.toContain("保護者");
  });

  it("routes 玉陵中 player lists to the school digest", async () => {
    const result = await ask("玉陵中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉陵中.md"]);
    expect(result.text).toContain("# 玉陵中 記録一覧");
  });

  it("routes 荒尾第四中 player lists to the school digest", async () => {
    const result = await ask("荒尾第四中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾第四中.md"]);
    expect(result.text).toContain("# 荒尾第四中 記録一覧");
  });

  it("starts a year-and-gender award summary at the requested section", async () => {
    const result = await ask("荒玉駅伝2024女子区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("### 2024年女子");
    expect(result.text).not.toContain("内野遥翔");
  });

  it("does not route a female leg-award query to coaching notes", async () => {
    const result = await ask("女子荒玉1区区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("2025年荒玉駅伝女子1区の区間1位は坂井優花");
  });

  it("keeps a compact female 2024 first-leg award alias exact", async () => {
    const result = await ask("2024荒玉女子1区区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("2024年荒玉駅伝女子1区の区間1位");
    expect(result.text).not.toContain("2024年荒玉駅伝女子2区");
  });

  it("routes 長洲中 player lists to the school digest", async () => {
    const result = await ask("長洲中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/長洲中.md"]);
    expect(result.text).toContain("# 長洲中 記録一覧");
  });

  it("routes 玉南中 player lists to the school digest", async () => {
    const result = await ask("玉南中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉南中.md"]);
    expect(result.text).toContain("# 玉南中 記録一覧");
  });

  it("routes 荒尾海陽中 player lists to the school digest", async () => {
    const result = await ask("荒尾海陽中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾海陽中.md"]);
    expect(result.text).toContain("# 荒尾海陽中 記録一覧");
  });

  it("routes 玉名附属中 aliases to the canonical school digest", async () => {
    const result = await ask("玉名附属中の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("routes 玉高附属 aliases to the canonical school digest", async () => {
    const result = await ask("玉高附属の選手一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("does not mistake the year suffix for a race leg in female awards", async () => {
    const result = await ask("荒玉女子2025区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("### 2025年女子");
    expect(result.text).not.toContain("2025年荒玉駅伝女子5区");
  });

  it("does not mistake the year suffix for a race leg in male awards", async () => {
    const result = await ask("荒玉男子2025区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("### 2025年男子");
    expect(result.text).not.toContain("2025年荒玉駅伝男子5区");
  });

  it("keeps the explicit year-first female award section focused", async () => {
    const result = await ask("2025年女子荒玉駅伝区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("### 2025年女子");
  });

  it("keeps the station-prefixed male award section focused", async () => {
    const result = await ask("荒玉駅伝2025男子区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("### 2025年男子");
  });

  it("keeps an explicit 2025 female first-leg award exact", async () => {
    const result = await ask("荒玉駅伝2025女子1区区間賞");
    expect(result.sources).toEqual(["out-analysis/aragyoku_leg_awards.md"]);
    expect(result.text).toContain("2025年荒玉駅伝女子1区の区間1位は坂井優花");
  });

  it("keeps female top-six pace queries out of coaching notes", async () => {
    const result = await ask("女子荒玉2025上位6平均ペース");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("| 2025 | 6 |");
    expect(result.text).not.toContain("女子荒玉は43分切り");
  });

  it("summarizes a compact-year female meet-record query", async () => {
    const result = await ask("2024荒玉女子の大会記録");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝女子のボード上部・総合大会記録");
    expect(result.text).not.toContain("2012年荒玉駅伝女子");
  });

  it("summarizes a year-suffix female meet-record query", async () => {
    const result = await ask("荒玉女子2024大会記録");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝女子のボード上部・総合大会記録");
    expect(result.text).not.toContain("2012年荒玉駅伝女子");
  });

  it("summarizes a compact-year male leg-record query", async () => {
    const result = await ask("2024荒玉男子区間記録");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子の1区大会区間記録");
    expect(result.text).not.toContain("2012年荒玉駅伝男子");
  });

  it("summarizes a year-suffix male leg-record query", async () => {
    const result = await ask("荒玉男子2024区間記録");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子の1区大会区間記録");
    expect(result.text).not.toContain("2012年荒玉駅伝男子");
  });

  it("keeps an explicit-year female station-record query focused", async () => {
    const result = await ask("2024年荒玉女子の大会記録");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝女子の1区大会区間記録");
  });

  it("keeps an explicit-year male station-record query focused", async () => {
    const result = await ask("2024年荒玉男子の区間記録");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子の1区大会区間記録");
  });

  it("keeps the station-prefixed female record query focused", async () => {
    const result = await ask("荒玉駅伝2024女子の大会記録");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝女子のボード上部・総合大会記録");
  });

  it("keeps the station-prefixed male record query focused", async () => {
    const result = await ask("荒玉駅伝2024男子の区間記録");
    expect(result.sources).toEqual(["out-analysis/aragyoku_meet_records.md"]);
    expect(result.text).toContain("2024年荒玉駅伝男子の1区大会区間記録");
  });

  it("keeps a female top-six pace query with year suffix exact", async () => {
    const result = await ask("荒玉女子2025上位6校平均ペース");
    expect(result.sources).toEqual(["out-analysis/aragyoku_top6_historical_average_pace.md"]);
    expect(result.text).toContain("| 2025 | 6 |");
  });

  it("answers compact 佐藤央琉 800m questions from the SB source", async () => {
    const result = await ask("佐藤央琉800m何秒");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("佐藤央琉（岱明中）の800m自己ベストは2:21.61");
  });

  it("answers compact 佐藤央琉 wording with a no-何 prefix", async () => {
    const result = await ask("佐藤央琉800m何分");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m自己ベストは2:21.61");
  });

  it("answers compact 角田亜美 1500m questions from the SB source", async () => {
    const result = await ask("角田亜美1500mは何分");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("角田亜美（岱明）の1500m自己ベストは5:45.56");
  });

  it("answers compact 村上咲稀 800m questions from the SB source", async () => {
    const result = await ask("村上咲稀800m何秒");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上咲稀（岱明中）の800m自己ベストは2:23.45");
  });

  it("answers compact 案浦竜士 1500m questions from the SB source", async () => {
    const result = await ask("案浦竜士1500m秒");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("案浦竜士（岱明中）の1500m自己ベストは4:49.63");
  });

  it("answers compact 松野凛空 1500m questions from the SB source", async () => {
    const result = await ask("松野凛空1500m何秒");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("松野凛空");
  });

  it("answers compact 田上颯人 1500m questions from the SB source", async () => {
    const result = await ask("田上颯人1500m何分");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("田上颯人");
  });

  it("answers compact 西優翔 1500m questions from the SB source", async () => {
    const result = await ask("西優翔1500m何秒");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("西優翔");
  });

  it("answers compact 木下紗那 1500m questions from the SB source", async () => {
    const result = await ask("木下紗那1500m何分");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("木下紗那");
  });

  it("answers compact 三鶴創一朗 1500m questions from the SB source", async () => {
    const result = await ask("三鶴創一朗1500m秒");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("三鶴創一朗");
  });

  it("answers unitless 佐藤央琉 800m questions from the SB source", async () => {
    const result = await ask("佐藤央琉800タイム");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m自己ベストは2:21.61");
  });

  it("answers unitless 佐藤央琉 800m best wording from the SB source", async () => {
    const result = await ask("佐藤央琉800ベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m自己ベストは2:21.61");
  });

  it("answers unitless 角田亜美 1500m best wording from the SB source", async () => {
    const result = await ask("角田亜美1500ベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m自己ベストは5:45.56");
  });

  it("answers unitless 松野凛空 1500m wording from the SB source", async () => {
    const result = await ask("松野凛空1500何分");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("松野凛空");
  });

  it("answers unitless 西優翔 1500m wording from the SB source", async () => {
    const result = await ask("西優翔1500ベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("西優翔");
  });

  it("answers unitless 木下紗那 1500m wording from the SB source", async () => {
    const result = await ask("木下紗那1500タイム");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("木下紗那");
  });

  it("answers unitless 三鶴創一朗 1500m wording from the SB source", async () => {
    const result = await ask("三鶴創一朗1500ベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("三鶴創一朗");
  });

  it("answers unitless 坂本春翔 1500m wording from the SB source", async () => {
    const result = await ask("坂本春翔1500何秒");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("坂本春翔");
  });

  it("selects the 1500m section for a female school average", async () => {
    const result = await ask("女子1500m岱明上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位3人平均 5:10.77");
    expect(result.text).not.toContain("2:28.81");
  });

  it("keeps a female 800m school average on the 800m section", async () => {
    const result = await ask("女子800m岱明上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位3人平均 2:28.81");
  });

  it("defaults an unqualified 岱明 800m average to the 800m ranking", async () => {
    const result = await ask("岱明800m上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位3人平均 2:28.81");
    expect(result.text).not.toContain("4:30.05");
  });

  it("keeps 岱明中 800m averages on the female ranking", async () => {
    const result = await ask("岱明中800m上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("2:28.81");
  });

  it("keeps school-qualified 岱明 800m averages focused", async () => {
    const result = await ask("学校別800m岱明上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("2:28.81");
  });

  it("keeps an 800m-first 岱明 average focused", async () => {
    const result = await ask("800m岱明上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("2:28.81");
  });

  it("keeps a gender-after-school 800m average focused", async () => {
    const result = await ask("岱明の女子800m上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("2:28.81");
  });

  it("keeps a gender-before-school 800m average focused", async () => {
    const result = await ask("女子岱明800m上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("2:28.81");
  });

  it("keeps a school-average 800m alias focused", async () => {
    const result = await ask("岱明800m学校別平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("学校別平均 2:28.81");
  });

  it("keeps a female school-average 800m alias focused", async () => {
    const result = await ask("女子800m岱明学校別平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("学校別平均 2:28.81");
  });

  it("keeps the full female 800m school-average wording focused", async () => {
    const result = await ask("女子800m岱明上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位3人平均 2:28.81");
  });

  it("routes 朝練 time questions to the staff memo", async () => {
    const result = await ask("朝練は何時");
    expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
    expect(result.text).toContain("集合7:20");
  });

  it("routes 朝練 weekday questions to the staff memo", async () => {
    const result = await ask("朝練の曜日は？");
    expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
    expect(result.text).toContain("月・火・木・金");
  });

  it("answers generic 地点分担 from the staff memo summary", async () => {
    const result = await ask("地点分担は何地点");
    expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
    expect(result.text).toContain("地点分担（荒玉）");
    expect(result.text).toContain("土山=D地点");
  });

  it("routes 朝練集合時間 to the staff memo", async () => {
    const result = await ask("朝練の集合時間");
    expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
    expect(result.text).toContain("集合7:20");
  });

  it("routes 手押し車 questions to the coaching memo only", async () => {
    const result = await ask("手押し車の補強メニュー");
    expect(result.sources).toEqual(["out-analysis/line-chats/arita-taisho.md"]);
    expect(result.text).toContain("手押し車・犬歩き");
  });

  it("routes 犬歩き questions to the coaching memo only", async () => {
    const result = await ask("犬歩きの補強");
    expect(result.sources).toEqual(["out-analysis/line-chats/arita-taisho.md"]);
    expect(result.text).toContain("手押し車・犬歩き");
  });

  it("keeps female 荒玉 member guidance on the coaching memo", async () => {
    const result = await ask("女子荒玉のメンバー目安");
    expect(result.sources).toEqual(["out-analysis/line-chats/arita-taisho.md"]);
    expect(result.text).toContain("女子荒玉は43分切り目安");
  });

  it("answers the planned なごみ team count concisely", async () => {
    const result = await ask("なごみは何チーム参加予定");
    expect(result.sources).toEqual(["out-analysis/line-chats/arita-taisho.md"]);
    expect(result.text).toContain("なごみは男女2チームずつ");
  });

  it("keeps 荒玉 leg allocation on the coaching memo", async () => {
    const result = await ask("荒玉駅伝の区間配分");
    expect(result.sources).toEqual(["out-analysis/line-chats/arita-taisho.md"]);
    expect(result.text).toContain("区");
  });

  it("keeps the shared 2区・5区 distance on the staff memo", async () => {
    const result = await ask("2区と5区の距離");
    expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
    expect(result.text).toContain("2.855km");
  });

  it("answers unitless 岱明 800m school averages", async () => {
    const result = await ask("岱明800上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位3人平均 2:28.81");
  });

  it("answers a generic female 800 school-average table", async () => {
    const result = await ask("女子800上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 800m・上位3人平均");
  });

  it("answers a generic female 1500 school-average table", async () => {
    const result = await ask("女子1500上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 1500m・上位3人平均");
    expect(result.text).toContain("5:10.77");
  });

  it("keeps a gender-before-school unitless 800m average focused", async () => {
    const result = await ask("岱明女子800上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("2:28.81");
  });

  it("keeps an 800-first unitless 岱明 average focused", async () => {
    const result = await ask("800岱明上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("2:28.81");
  });

  it("answers school-qualified female 800 averages", async () => {
    const result = await ask("学校別女子800上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 800m・上位3人平均");
  });

  it("answers the female 800 school-average alias without m", async () => {
    const result = await ask("女子800学校別平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 800m・上位3人平均");
  });

  it("answers the female 1500 school-average alias without m", async () => {
    const result = await ask("女子1500学校別平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 1500m・上位3人平均");
  });

  it("keeps school-qualified female 1500 averages on the 1500m section", async () => {
    const result = await ask("学校別女子1500上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 1500m・上位3人平均");
    expect(result.text).toContain("5:10.77");
  });

  it("answers unitless 岱明女子 1500m averages", async () => {
    const result = await ask("岱明女子1500上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位3人平均 5:10.77");
    expect(result.text).not.toContain("2:28.81");
  });

  it("calculates the requested top-three male 1500m average", async () => {
    const result = await ask("岱明男子1500上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位3人平均 4:28.69");
    expect(result.text).not.toContain("4:30.05");
  });

  it("keeps the male-before-school 1500m average focused", async () => {
    const result = await ask("男子1500岱明上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("4:28.69");
  });

  it("handles the school-suffixed male 1500m query", async () => {
    const result = await ask("岱明中男子1500上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("4:28.69");
  });

  it("handles the unit-suffixed male 1500m query", async () => {
    const result = await ask("男子1500m岱明上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("4:28.69");
  });

  it("handles a gender-before-school male 1500m query", async () => {
    const result = await ask("男子岱明1500上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("4:28.69");
  });

  it("defaults a named 1500m average to the male source when gender is omitted", async () => {
    const result = await ask("1500岱明上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("4:28.69");
  });

  it("handles a unit-suffixed genderless 1500m average", async () => {
    const result = await ask("1500m岱明上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("4:28.69");
  });

  it("explains when the male source lacks a top-three table", async () => {
    const result = await ask("学校別男子1500上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位3人平均は収録されていません");
    expect(result.text).not.toContain("上位4人平均 |");
  });

  it("explains the generic male top-three limitation", async () => {
    const result = await ask("男子1500上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("正本は上位4人平均");
  });

  it("handles a named 1500m average without an explicit gender", async () => {
    const result = await ask("岱明1500上位3人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位3人平均 4:28.69");
  });

  it("selects the male top-four 1500m section", async () => {
    const result = await ask("男子1500上位4人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 上位4人平均");
    expect(result.text).toContain("4:23.09");
  });

  it("selects the unit-suffixed male top-four section", async () => {
    const result = await ask("男子1500m上位4人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 上位4人平均");
  });

  it("selects the male top-six 1500m section", async () => {
    const result = await ask("男子1500上位6人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 上位6人平均");
    expect(result.text).toContain("4:26.62");
  });

  it("selects the unit-suffixed male top-six section", async () => {
    const result = await ask("男子1500m上位6人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 上位6人平均");
  });

  it("keeps a named male top-four average on the correct table", async () => {
    const result = await ask("岱明男子1500上位4人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位4人平均 4:30.05");
  });

  it("keeps a named male top-six average on the correct table", async () => {
    const result = await ask("男子1500岱明上位6人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位6人平均 4:42.49");
  });

  it("focuses the school-qualified male top-four query", async () => {
    const result = await ask("学校別男子1500上位4人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 上位4人平均");
  });

  it("accepts kanji top-four wording for male 1500m", async () => {
    const result = await ask("男子1500上位四人平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 上位4人平均");
  });

  it("accepts the no-space top-six wording with の", async () => {
    const result = await ask("男子1500上位6人の平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 上位6人平均");
  });

  it("accepts kanji top-six wording for male 1500m", async () => {
    const result = await ask("男子1500上位六人の平均");
    expect(result.sources).toEqual(["out-analysis/2026_men_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 上位6人平均");
  });

  it("accepts kanji top-five wording for female 800m", async () => {
    const result = await ask("女子800上位五人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 800m・上位5人平均");
    expect(result.text).toContain("2:32.96");
  });

  it("accepts kanji top-five wording for female 1500m", async () => {
    const result = await ask("女子1500上位五人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 1500m・上位5人平均");
    expect(result.text).toContain("5:19.61");
  });

  it("accepts fullwidth top-five wording for female 800m", async () => {
    const result = await ask("女子800上位５人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 800m・上位5人平均");
  });

  it("accepts fullwidth top-five wording for female 1500m", async () => {
    const result = await ask("女子1500上位５人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 1500m・上位5人平均");
  });

  it("accepts の平均 wording for female 800m", async () => {
    const result = await ask("女子800上位5人の平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 800m・上位5人平均");
  });

  it("accepts の平均 wording for female 1500m", async () => {
    const result = await ask("女子1500上位5人の平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 1500m・上位5人平均");
  });

  it("keeps a school-qualified female 1500 top-five query focused", async () => {
    const result = await ask("学校別女子1500上位5人の平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 1500m・上位5人平均");
  });

  it("answers a named female 800 top-five average in kanji wording", async () => {
    const result = await ask("女子800岱明上位五人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位5人平均 2:32.96");
  });

  it("answers a named female 1500 top-five average in fullwidth wording", async () => {
    const result = await ask("女子1500岱明上位５人平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("上位5人平均 5:19.61");
  });

  it("accepts kanji and の平均 together for female 800m", async () => {
    const result = await ask("女子800上位五人の平均");
    expect(result.sources).toEqual(["out-analysis/2026_women_800m_1500m_pb_school_ranking.md"]);
    expect(result.text).toContain("## 800m・上位5人平均");
  });

  it("routes an undated 玉名市練習会 result to the latest practice record", async () => {
    const result = await ask("玉名市練習会の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes the abbreviated first long-distance meet result to its result note", async () => {
    const result = await ask("第1回長距離記録会の結果");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/0509_第１回熊本県長距離記録会/岱明の結果.md"]);
    expect(result.text).toContain("第１回熊本県長距離記録会");
  });

  it("routes the abbreviated second long-distance meet result to its result note", async () => {
    const result = await ask("第2回長距離記録会の結果");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/0704_第２回熊本県長距離記録会/岱明の結果.md"]);
    expect(result.text).toContain("第２回熊本県長距離記録会");
  });

  it("routes the short city-championship result query to the current result note", async () => {
    const result = await ask("市選手権の結果");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/0418_第４５回熊本市陸上競技選手権大会/岱明の結果.md"]);
    expect(result.text).toContain("第４５回熊本市陸上競技選手権大会");
  });

  it("routes the abbreviated Kumamoto city championship result to its result note", async () => {
    const result = await ask("熊本市選手権の結果");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/0418_第４５回熊本市陸上競技選手権大会/岱明の結果.md"]);
    expect(result.text).toContain("第４５回熊本市陸上競技選手権大会");
  });

  it("routes the short nighter-meet result query to the full result note", async () => {
    const result = await ask("ナイター記録会の結果");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/0829_玉名郡ナイター中・長距離記録会/全結果.md"]);
    expect(result.text).toContain("第25回玉名郡ナイター中・長距離記録会");
  });

  it("routes the short prefectural championship result to the 2026 result note", async () => {
    const result = await ask("県中学校選手権の結果");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/0523-0524_熊本県中学校陸上選手権・混成/岱明の結果.md"]);
    expect(result.text).toContain("第40回熊本県中学校陸上競技選手権大会");
  });

  it("routes the short communication-meet result to its 2026 result note", async () => {
    const result = await ask("通信の結果");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/0613_全日本中学校通信陸上競技大会熊本県大会/岱明の結果.md"]);
    expect(result.text).toContain("第72回全日本中学校通信陸上競技大会熊本県大会");
  });

  it("routes the abbreviated first long-distance result-link query to its result note", async () => {
    const result = await ask("第1回長距離記録会の結果リンク");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/0509_第１回熊本県長距離記録会/岱明の結果.md"]);
    expect(result.text).toContain("第１回熊本県長距離記録会");
  });

  it("routes the abbreviated fourth long-distance result query to its scheduled overview", async () => {
    const result = await ask("第4回長距離記録会の結果");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/1010_第４回熊本県長距離記録会/概要.md"]);
    expect(result.text).toContain("熊本県長距離記録会");
  });

  it("routes the abbreviated fifth long-distance result query to its scheduled overview", async () => {
    const result = await ask("第5回長距離記録会の結果");
    expect(result.sources).toEqual(["drive-text/大会/2026年度/1212_第５回熊本県長距離記録会/概要.md"]);
    expect(result.text).toContain("熊本県長距離記録会");
  });

  it("routes the short Kumamoto city record-meet result to the record database", async () => {
    const result = await ask("熊本市記録会の結果");
    expect(result.sources).toEqual(["drive-text/記録データベース/2026年度/中学生記録.csv"]);
  });

  it("routes the partially abbreviated Kumamoto city record-meet result to the database", async () => {
    const result = await ask("熊本市陸上記録会の結果");
    expect(result.sources).toEqual(["drive-text/記録データベース/2026年度/中学生記録.csv"]);
  });

  it("routes a relative-date practice-meet result to the latest practice note", async () => {
    const result = await askAt("昨日の練習会の結果", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("keeps an unqualified Daiming Aragyoku result on the team digest", async () => {
    const result = await ask("岱明の荒玉駅伝の結果");
    expect(result.sources).toEqual(["out-analysis/aragyoku-teams/岱明.md"]);
    expect(result.text).toContain("2025年荒玉駅伝");
  });

  it("routes a dated but venue-omitted practice-meet result to the practice note", async () => {
    const result = await ask("9月22日の練習会の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes an unqualified practice-meet result link to the practice note", async () => {
    const result = await ask("玉名市練習会の結果リンク");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes an unqualified practice-meet official link to the practice note", async () => {
    const result = await ask("玉名市練習会の公式リンク");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("sites.google.com/view/tamariku");
  });

  it("routes a relative-date practice-meet site query to the practice note", async () => {
    const result = await askAt("昨日の練習会のサイト", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("sites.google.com/view/tamariku");
  });

  it("routes a generic practice-meet official link to the latest practice note", async () => {
    const result = await ask("練習会の公式リンク");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("sites.google.com/view/tamariku");
  });

  it("routes a generic practice-meet record query to the latest practice note", async () => {
    const result = await ask("練習会の記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a short practice-meet time query to the latest practice note", async () => {
    const result = await ask("練習会のタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a generic practice-meet participant query to the latest practice note", async () => {
    const result = await ask("練習会の参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
  });

  it("routes a generic practice-meet participant-count query to the latest practice note", async () => {
    const result = await ask("練習会の参加人数");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
  });

  it("routes a generic female 1000m practice query to the latest practice note", async () => {
    const result = await ask("練習会の女子1000m");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes a generic male 1000m practice query to the latest practice note", async () => {
    const result = await ask("練習会の男子1000m");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes a dated practice-meet menu query to the latest practice note", async () => {
    const result = await ask("9月22日の練習会メニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a relative-date practice-meet menu query to the latest practice note", async () => {
    const result = await askAt("昨日の練習会メニュー", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a generic female practice result query to the latest practice note", async () => {
    const result = await ask("練習会の女子結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes a generic male practice result query to the latest practice note", async () => {
    const result = await ask("練習会の男子結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes a female 1000m practice-time query to the latest practice note", async () => {
    const result = await ask("玉名市練習会の女子1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a male 1000m practice-time query to the latest practice note", async () => {
    const result = await ask("玉名市練習会の男子1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - 3:20 - 3:09");
  });

  it("routes a generic practice-meet implementation-content query to the latest practice note", async () => {
    const result = await ask("練習会の実施内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a generic female practice-record query to the latest practice note", async () => {
    const result = await ask("練習会の女子記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes a generic male practice-record query to the latest practice note", async () => {
    const result = await ask("練習会の男子記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes a female 1000m practice-result query to the latest practice note", async () => {
    const result = await ask("玉名市練習会の女子1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a male 1000m practice-result query to the latest practice note", async () => {
    const result = await ask("玉名市練習会の男子1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - 3:20 - 3:09");
  });

  it("routes a relative-date female practice-time query to the latest practice note", async () => {
    const result = await askAt("昨日の練習会の女子タイム", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a relative-date male practice-time query to the latest practice note", async () => {
    const result = await askAt("昨日の練習会の男子タイム", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - 3:20 - 3:09");
  });

  it("routes a dated practice implementation query to the latest practice note", async () => {
    const result = await ask("9月22日の練習会の実施内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes a generic practice-meet roster query to the latest practice note", async () => {
    const result = await ask("練習会の参加者名簿");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
  });

  it("routes a dated practice-meet record-list query to the latest practice note", async () => {
    const result = await ask("9月22日の練習会の記録一覧");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes a generic female practice-menu query to the latest practice note", async () => {
    const result = await ask("練習会の女子メニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a generic male practice-menu query to the latest practice note", async () => {
    const result = await ask("練習会の男子メニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes a female 1000m practice-record query to the latest practice note", async () => {
    const result = await ask("練習会の女子1000m記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a male 1000m practice-record query to the latest practice note", async () => {
    const result = await ask("練習会の男子1000m記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - 3:20 - 3:09");
  });

  it("routes a generic female practice-player query to the latest practice note", async () => {
    const result = await ask("練習会の女子選手");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes a generic male practice-player query to the latest practice note", async () => {
    const result = await ask("練習会の男子選手");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes a practice implementation-result query to the latest practice note", async () => {
    const result = await ask("玉名市練習会の実施結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a generic practice-result-table query to the latest practice note", async () => {
    const result = await ask("練習会の結果表");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes a slash-dated practice-time query to the latest practice note", async () => {
    const result = await ask("9/22練習会のタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a relative-date practice-result-list query to the latest practice note", async () => {
    const result = await askAt("昨日の練習会の結果一覧", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a unitless female 1000m practice query to the latest practice note", async () => {
    const result = await ask("練習会の女子1000");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a unitless male 1000m practice query to the latest practice note", async () => {
    const result = await ask("練習会の男子1000");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - 3:20 - 3:09");
  });

  it("routes a unitless female practice-time query to the latest practice note", async () => {
    const result = await ask("練習会の女子1000タイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a unitless male practice-time query to the latest practice note", async () => {
    const result = await ask("練習会の男子1000タイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - 3:20 - 3:09");
  });

  it("routes a female practice-player-list query to the latest practice note", async () => {
    const result = await ask("練習会の女子選手一覧");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes a male practice-player-list query to the latest practice note", async () => {
    const result = await ask("練習会の男子選手一覧");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes a named female practice-record query to the latest practice note", async () => {
    const result = await ask("玉名市練習会の女子記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a named male practice-record query to the latest practice note", async () => {
    const result = await ask("玉名市練習会の男子記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - 3:20 - 3:09");
  });

  it("routes a compact Japanese-date practice-result query to the latest practice note", async () => {
    const result = await ask("9月22日練習会結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a compact slash-date practice-result query to the latest practice note", async () => {
    const result = await ask("9/22練習会結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a female 1000m participant-description query to the latest practice note", async () => {
    const result = await ask("練習会で女子1000mを走った人");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes a male 1000m participant-description query to the latest practice note", async () => {
    const result = await ask("練習会で男子1000mを走った人");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes a female practice-participant query to the latest practice note", async () => {
    const result = await ask("練習会の女子参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes a male practice-participant query to the latest practice note", async () => {
    const result = await ask("練習会の男子参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes a female practice-record-table query to the latest practice note", async () => {
    const result = await ask("練習会の女子記録表");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a male practice-record-table query to the latest practice note", async () => {
    const result = await ask("練習会の男子記録表");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - 3:20 - 3:09");
  });

  it("routes a fullwidth-year practice-result query to the latest practice note", async () => {
    const result = await ask("2026年9月22日練習会結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes an ISO-date practice-result query to the latest practice note", async () => {
    const result = await ask("2026-09-22練習会結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a compact relative practice-time query to the latest practice note", async () => {
    const result = await askAt("昨日の玉名市練習会タイム", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a compact dated practice-time query to the latest practice note", async () => {
    const result = await ask("9月22日の玉名市練習会タイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("answers the current male course total distance", async () => {
    const result = await ask("荒玉男子の現行コース合計距離は？");
    expect(result.sources).toEqual(["docs/aragyoku-ekiden-distance-definitions.md"]);
    expect(result.text).toContain("17.710km");
  });

  it("answers the pre-2024 male course total distance", async () => {
    const result = await ask("荒玉男子の2023年以前の合計距離は？");
    expect(result.sources).toEqual(["docs/aragyoku-ekiden-distance-definitions.md"]);
    expect(result.text).toContain("19.710km");
  });

  it("answers a dated male morning-practice interval distance", async () => {
    const result = await ask("2026年7月21日朝練の男子インターバル距離は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2.5km");
  });

  it("answers the dated joint-practice venue from the practice note", async () => {
    const result = await ask("9月22日の玉名市合同練習会の集合場所は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("おおはまふれあいセンター");
  });

  it("answers the combined second-and-fifth-leg distance from the staff memo", async () => {
    const result = await ask("荒玉の2区と5区の距離は？");
    expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
    expect(result.text).toContain("2.855km");
  });

  it("answers the planned joint-practice attendance from the coaching memo", async () => {
    const result = await ask("9/22合同練習会に岱明は何人くらい参加予定？");
    expect(result.sources).toEqual(["out-analysis/line-chats/arita-taisho.md"]);
    expect(result.text).toContain("女子7名");
  });

  it("answers the current course total with a current-course alias", async () => {
    const result = await ask("荒玉男子現行コースの総距離は？");
    expect(result.sources).toEqual(["docs/aragyoku-ekiden-distance-definitions.md"]);
    expect(result.text).toContain("17.710km");
  });

  it("answers the old course total with an old-course alias", async () => {
    const result = await ask("荒玉男子旧コースの総距離は？");
    expect(result.sources).toEqual(["docs/aragyoku-ekiden-distance-definitions.md"]);
    expect(result.text).toContain("19.710km");
  });

  it("answers an ISO-dated male morning-practice interval distance", async () => {
    const result = await ask("2026-07-21朝練の男子2.5kmは？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("2.5km");
  });

  it("answers a slash-dated joint-practice venue", async () => {
    const result = await ask("9/22玉名市合同練習会の場所は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("おおはまふれあいセンター");
  });

  it("answers a dated morning menu for July 21", async () => {
    const result = await ask("2026年7月21日の朝練メニューは？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり、男子2.5km×2、女子2km×2");
  });

  it("answers a dated morning menu for July 23", async () => {
    const result = await ask("2026年7月23日の朝練メニューは？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり、男子2.5km×2、女子2km×2");
  });

  it("answers a dated morning menu for July 24", async () => {
    const result = await ask("2026年7月24日の朝練メニューは？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり、男子2.5km×2、女子2km×2");
  });

  it("answers an ISO-dated morning menu", async () => {
    const result = await ask("2026-07-23朝練のメニュー");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり、男子2.5km×2、女子2km×2");
  });

  it("answers a month-day morning-practice content query", async () => {
    const result = await ask("7月23日の朝練内容");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり、男子2.5km×2、女子2km×2");
  });

  it("answers what to do in a dated morning practice", async () => {
    const result = await ask("2026年7月23日朝練は何する？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり、男子2.5km×2、女子2km×2");
  });

  it("answers a slash-dated interval query", async () => {
    const result = await ask("7/23朝練のインターバルは？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり、男子2.5km×2、女子2km×2");
  });

  it("answers a dated morning distance query", async () => {
    const result = await ask("2026年7月23日の朝練は何km？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり、男子2.5km×2、女子2km×2");
  });

  it("answers a month-day morning content query without a year", async () => {
    const result = await ask("7月24日朝練の内容は？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり、男子2.5km×2、女子2km×2");
  });

  it("answers a slash-formatted dated morning menu", async () => {
    const result = await ask("2026/07/23朝練メニューは？");
    expect(result.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(result.text).toContain("動きづくり、男子2.5km×2、女子2km×2");
  });

  it("answers an athlete SB query with a school in parentheses", async () => {
    const result = await ask("江口大尊（荒尾三中）の3000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a compact athlete-school SB query", async () => {
    const result = await ask("江口大尊 荒尾三中 3000mSB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a school-first athlete personal-best query", async () => {
    const result = await ask("荒尾三中の江口大尊3000m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers an athlete-first school-attached SB query", async () => {
    const result = await ask("江口大尊の荒尾三中3000mSB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a 3000m best query with school context", async () => {
    const result = await ask("江口大尊（荒尾三中）の3000mベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a school-context 3000m record query", async () => {
    const result = await ask("江口大尊 荒尾三中 3000mの記録");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a school-first compact SB query", async () => {
    const result = await ask("荒尾三中 江口大尊 3000m SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("accepts the honorific in an athlete SB query", async () => {
    const result = await ask("江口大尊さん（荒尾三中）の3000m SBを教えて");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers an athlete SB query with trailing school context", async () => {
    const result = await ask("江口大尊の3000m SB（荒尾三中）");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a spaced athlete-school SB query", async () => {
    const result = await ask("荒尾三中 江口大尊 3000mSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a school-context 1500m SB query", async () => {
    const result = await ask("稗島葵音（南関中）の1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("5:02.49");
  });

  it("answers a school-context 5000m SB query", async () => {
    const result = await ask("稗島葵音（南関中）の5000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("11:18.46");
  });

  it("answers a compact 1500m SB query for the athlete", async () => {
    const result = await ask("稗島葵音 南関中 1500mSB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("5:02.49");
  });

  it("answers a school-first 1500m personal-best query", async () => {
    const result = await ask("南関中の稗島葵音1500m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("5:02.49");
  });

  it("answers an athlete-first 1500m SB query", async () => {
    const result = await ask("稗島葵音の南関中1500mSB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("5:02.49");
  });

  it("answers a school-first spaced 1500m SB query", async () => {
    const result = await ask("南関中 稗島葵音 1500m SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("5:02.49");
  });

  it("answers an honorific 1500m SB query", async () => {
    const result = await ask("稗島葵音さん（南関中）の1500m SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("5:02.49");
  });

  it("answers a trailing-school 1500m SB query", async () => {
    const result = await ask("稗島葵音の1500m SB（南関中）");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("5:02.49");
  });

  it("answers a compact 5000m SB query", async () => {
    const result = await ask("稗島葵音 南関中 5000mSB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("11:18.46");
  });

  it("answers a school-first 5000m best query", async () => {
    const result = await ask("南関中の稗島葵音5000mベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("11:18.46");
  });

  it("answers a hiragana-name personal-best query", async () => {
    const result = await ask("原田はなの1500m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a hiragana-name school-context SB query", async () => {
    const result = await ask("原田はな（Star Light AC）の1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a spaced hiragana-name personal-best query", async () => {
    const result = await ask("原田はな 1500m自己ベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a hiragana-name honorific SB query", async () => {
    const result = await ask("原田はなさんの1500m SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a hiragana-name compact SB query", async () => {
    const result = await ask("原田はなの1500m SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a second hiragana-name personal-best query", async () => {
    const result = await ask("小脇あかりの1500m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:41.70");
  });

  it("answers a second hiragana-name school-context SB query", async () => {
    const result = await ask("小脇あかり（TTC）の1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:41.70");
  });

  it("answers a second spaced hiragana-name query", async () => {
    const result = await ask("小脇あかり1500m自己ベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:41.70");
  });

  it("answers a second hiragana-name honorific query", async () => {
    const result = await ask("小脇あかりさんの1500m SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:41.70");
  });

  it("answers a school-context hiragana-name best query", async () => {
    const result = await ask("原田はな（Star Light AC）の1500mベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a 5km school-context SB query", async () => {
    const result = await ask("村上葉侑（南関中）の5km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a compact 5km school-context query", async () => {
    const result = await ask("村上葉侑 南関中 5kmSB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a school-first 5km personal-best query", async () => {
    const result = await ask("南関中の村上葉侑5km自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers an athlete-first 5km SB query", async () => {
    const result = await ask("村上葉侑の南関中5kmSB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a 5km honorific SB query", async () => {
    const result = await ask("村上葉侑さん（南関中）の5km SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a trailing-school 5km SB query", async () => {
    const result = await ask("村上葉侑の5km SB（南関中）");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a school-first spaced 5km SB query", async () => {
    const result = await ask("南関中 村上葉侑 5km SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a 5km best query with school context", async () => {
    const result = await ask("村上葉侑（南関中）の5kmベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a 5km record query with school context", async () => {
    const result = await ask("村上葉侑 南関中 5kmの記録");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a 5km time query with school context", async () => {
    const result = await ask("村上葉侑は南関中で5km何分？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a 3km school-context SB query", async () => {
    const result = await ask("原田はな（Star Light AC）の3km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a 3km personal-best query", async () => {
    const result = await ask("原田はなの3km自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a compact 3km SB query", async () => {
    const result = await ask("原田はな 3kmSB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers an honorific 3km SB query", async () => {
    const result = await ask("原田はなさんの3km SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a trailing-team 3km SB query", async () => {
    const result = await ask("原田はなの3km SB（Star Light AC）");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a second 3km school-context SB query", async () => {
    const result = await ask("税所由羽（人吉一中）の3km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:57.00");
  });

  it("answers a second 3km personal-best query", async () => {
    const result = await ask("税所由羽の3km自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:57.00");
  });

  it("answers a second compact 3km SB query", async () => {
    const result = await ask("税所由羽 3kmSB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:57.00");
  });

  it("answers a second honorific 3km SB query", async () => {
    const result = await ask("税所由羽さんの3km SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:57.00");
  });

  it("answers a second trailing-school 3km SB query", async () => {
    const result = await ask("税所由羽の3km SB（人吉一中）");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:57.00");
  });

  it("answers an unqualified named best query from the SB CSV", async () => {
    const result = await ask("原田はなのベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
  });

  it("answers a second unqualified named best query from the SB CSV", async () => {
    const result = await ask("小脇あかりのベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:41.70");
  });

  it("answers a named best query with school context", async () => {
    const result = await ask("村上葉侑（南関中）のベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3000m 9:44.02");
  });

  it("answers a named best query with club context", async () => {
    const result = await ask("原田はな（Star Light AC）のベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3km 10:39.00");
  });

  it("answers a named best query without a question mark", async () => {
    const result = await ask("江口大尊のベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3000m 9:04.46");
  });

  it("answers a named best-time query", async () => {
    const result = await ask("税所由羽のベストタイムは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:25.75");
  });

  it("answers a named best query with honorific", async () => {
    const result = await ask("原田はなさんのベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:40.44");
  });

  it("answers a named best query with trailing school", async () => {
    const result = await ask("江口大尊 荒尾三中 ベスト");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3000m 9:04.46");
  });

  it("answers a named best-record query", async () => {
    const result = await ask("村上葉侑のベスト記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("5km 17:18.00");
  });

  it("answers a second named best-time query", async () => {
    const result = await ask("小脇あかりのベストタイム");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:41.70");
  });

  it("answers an unqualified named record query", async () => {
    const result = await ask("原田はなの記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:40.44");
  });

  it("answers an unqualified named time query", async () => {
    const result = await ask("原田はなのタイムは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3km 10:39.00");
  });

  it("answers a second named record query", async () => {
    const result = await ask("小脇あかりの記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:41.70");
  });

  it("answers a named record query for a male athlete", async () => {
    const result = await ask("江口大尊の記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3000m 9:04.46");
  });

  it("answers a named time query for a female athlete", async () => {
    const result = await ask("税所由羽のタイムは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:25.75");
  });

  it("answers a named record query with honorific", async () => {
    const result = await ask("原田はなさんの記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
  });

  it("answers a named record query with school context", async () => {
    const result = await ask("江口大尊 荒尾三中 記録");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3000m 9:04.46");
  });

  it("answers a named record query with five-kilometre data", async () => {
    const result = await ask("村上葉侑の記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("5km 17:18.00");
  });

  it("answers a second named time query", async () => {
    const result = await ask("小脇あかりのタイム");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:41.70");
  });

  it("answers a second named record-time query", async () => {
    const result = await ask("村上葉侑のタイムは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3000m 9:44.02");
  });

  it("routes a female 1000m practice record for 村上", async () => {
    const result = await ask("女子1000mの村上の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:23");
  });

  it("routes a female 1000m practice record for 増岡", async () => {
    const result = await ask("女子1000mの増岡の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:46 - 3:41");
  });

  it("routes a female 1000m practice record for 山﨑", async () => {
    const result = await ask("女子1000mの山﨑の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:46 - 3:37");
  });

  it("routes a female 1000m practice record for 角田", async () => {
    const result = await ask("女子1000mの角田の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:49 - 3:45");
  });

  it("routes a female 1000m practice record for 塚原", async () => {
    const result = await ask("女子1000mの塚原の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("4:00 - 4:00");
  });

  it("routes a male 1000m practice record for 松野", async () => {
    const result = await ask("男子1000mの松野の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - ? - ?");
  });

  it("routes a male 1000m practice record for 田上", async () => {
    const result = await ask("男子1000mの田上の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - 3:20 - 3:09");
  });

  it("routes a male 1000m practice record for 山本", async () => {
    const result = await ask("男子1000mの山本の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10 - ? - ?");
  });

  it("routes a male 1000m practice record for 中尾", async () => {
    const result = await ask("男子1000mの中尾の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:30 - 3:19");
  });

  it("routes a male 1000m practice record for 松本", async () => {
    const result = await ask("男子1000mの松本の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30 - 3:30 - 3:21");
  });

  it("answers a comma-separated 3000m SB query", async () => {
    const result = await ask("江口大尊（荒尾三中）の3,000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a fullwidth comma 3000m SB query", async () => {
    const result = await ask("江口大尊（荒尾三中）の3，000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a comma-separated 3000m query with a space", async () => {
    const result = await ask("江口大尊（荒尾三中）の3,000 m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a comma-separated 1500m SB query", async () => {
    const result = await ask("原田はなの1,500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a fullwidth comma 1500m SB query", async () => {
    const result = await ask("原田はなの1，500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a comma-separated 5000m SB query", async () => {
    const result = await ask("正木好の5,000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("12:37.91");
  });

  it("answers a fullwidth comma 5000m SB query", async () => {
    const result = await ask("正木好の5，000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("12:37.91");
  });

  it("answers a school-context comma-separated 3000m query", async () => {
    const result = await ask("荒尾三中 江口大尊 3,000m SB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a compact comma-separated 3000m query", async () => {
    const result = await ask("江口大尊 荒尾三中 3,000mSB");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a comma-separated 3000m personal-best query", async () => {
    const result = await ask("江口大尊の3,000m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers an uppercase 3KM query", async () => {
    const result = await ask("原田はなの3KM SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a fullwidth uppercase 3KM query", async () => {
    const result = await ask("原田はなの３ＫＭ SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a mixed-case 3Km query", async () => {
    const result = await ask("原田はなの3Km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a spaced uppercase 3 KM query", async () => {
    const result = await ask("原田はなの3 KM SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers an uppercase 5KM query", async () => {
    const result = await ask("村上葉侑の5KM SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a fullwidth 5km query", async () => {
    const result = await ask("村上葉侑の５km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a mixed-case 5Km query", async () => {
    const result = await ask("村上葉侑の5Km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a spaced uppercase 5 KM query", async () => {
    const result = await ask("村上葉侑の5 KM SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers an uppercase 3KM personal-best query", async () => {
    const result = await ask("原田はなの3KM自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers an uppercase 5KM personal-best query", async () => {
    const result = await ask("村上葉侑の5KM自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a spaced 1500m query", async () => {
    const result = await ask("原田はなの1 500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a fullwidth-spaced 1500m query", async () => {
    const result = await ask("原田はなの1　500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a spaced 3000m query", async () => {
    const result = await ask("江口大尊の3 000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a fullwidth-spaced 3000m query", async () => {
    const result = await ask("江口大尊の3　000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a spaced 5000m query", async () => {
    const result = await ask("村上葉侑の5 000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a fullwidth-spaced 5000m query", async () => {
    const result = await ask("村上葉侑の5　000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a spaced 1500m personal-best query", async () => {
    const result = await ask("原田はなの1 500m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a spaced 3000m personal-best query", async () => {
    const result = await ask("江口大尊の3 000m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a spaced 5000m personal-best query", async () => {
    const result = await ask("村上葉侑の5 000m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a comma-and-space 3000m query", async () => {
    const result = await ask("江口大尊の3, 000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a 1.5km SB query", async () => {
    const result = await ask("原田はなの1.5km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a fullwidth-decimal 1.5km SB query", async () => {
    const result = await ask("原田はなの1．5km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a two-decimal 1.50km SB query", async () => {
    const result = await ask("原田はなの1.50km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a spaced 1.5 KM SB query", async () => {
    const result = await ask("原田はなの1.5 KM SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a fullwidth 1.5km personal-best query", async () => {
    const result = await ask("原田はなの１．５ｋｍ自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a 3.0km SB query", async () => {
    const result = await ask("原田はなの3.0km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a fullwidth-decimal 3.0km SB query", async () => {
    const result = await ask("原田はなの3．0km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a spaced 3.0 KM SB query", async () => {
    const result = await ask("原田はなの3.0 KM SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a 5.0km SB query", async () => {
    const result = await ask("村上葉侑の5.0km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a spaced 5.0 KM SB query", async () => {
    const result = await ask("村上葉侑の5.0 KM SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a spaced 800 m SB query", async () => {
    const result = await ask("原田はなの800 m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("2:20.81");
  });

  it("answers a fullwidth-unit 800m SB query", async () => {
    const result = await ask("原田はなの800 ｍ SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("2:20.81");
  });

  it("answers a spaced 1500 m SB query", async () => {
    const result = await ask("原田はなの1500 m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a fullwidth-unit 1500m SB query", async () => {
    const result = await ask("原田はなの1500 ｍ SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a spaced 3000 m SB query", async () => {
    const result = await ask("江口大尊の3000 m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a fullwidth-unit 3000m SB query", async () => {
    const result = await ask("江口大尊の3000 ｍ SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a spaced 5000 m SB query", async () => {
    const result = await ask("寺田向希の5000 m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("14:37.39");
  });

  it("answers a fullwidth-unit 5000m SB query", async () => {
    const result = await ask("寺田向希の5000 ｍ SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("14:37.39");
  });

  it("answers a spaced 3000 m personal-best query", async () => {
    const result = await ask("江口大尊の3000 m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a spaced 1500 m personal-best query", async () => {
    const result = await ask("原田はなの1500 m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a fullwidth SB query", async () => {
    const result = await ask("原田はなの1500m ＳＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers an attached fullwidth SB query", async () => {
    const result = await ask("原田はなの1500mＳＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a fullwidth PB query", async () => {
    const result = await ask("江口大尊の3000m ＰＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers an attached fullwidth PB query", async () => {
    const result = await ask("江口大尊の3000mＰＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a season-best alias query", async () => {
    const result = await ask("村上葉侑の5km シーズンベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a season-best alias without a distance unit", async () => {
    const result = await ask("村上葉侑のシーズンベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a fullwidth SB query with a fullwidth distance unit", async () => {
    const result = await ask("原田はなの１５００ｍ ＳＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a fullwidth PB query with a fullwidth distance unit", async () => {
    const result = await ask("江口大尊の３０００ｍ ＰＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers a season-best alias with a spaced distance", async () => {
    const result = await ask("村上葉侑の5 000m シーズンベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a season-best alias with a fullwidth space", async () => {
    const result = await ask("村上葉侑の5　000m シーズンベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a 3-kilometer Japanese-unit query", async () => {
    const result = await ask("原田はなの3キロSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a 5-kilometer Japanese-unit query", async () => {
    const result = await ask("村上葉侑の5キロ自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a 1.5-kilometer Japanese-unit query", async () => {
    const result = await ask("原田はなの1.5キロSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a 3.0-kilometer Japanese-unit query", async () => {
    const result = await ask("原田はなの3.0キロSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a 5.0-kilometer Japanese-unit query", async () => {
    const result = await ask("村上葉侑の5.0キロSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("17:18.00");
  });

  it("answers a 1500-meter Japanese-unit query", async () => {
    const result = await ask("原田はなの1500メートルSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers a 3000-meter Japanese-unit query", async () => {
    const result = await ask("江口大尊の3000メートル自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("9:04.46");
  });

  it("answers an 800-meter Japanese-unit query", async () => {
    const result = await ask("原田はなの800メートルSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("2:20.81");
  });

  it("answers a spaced 3-kilometer Japanese-unit query", async () => {
    const result = await ask("原田はなの3 キロSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("10:39.00");
  });

  it("answers a fullwidth-decimal 1.5-kilometer Japanese-unit query", async () => {
    const result = await ask("原田はなの１．５キロSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("4:40.44");
  });

  it("answers an athlete-suffixed 1500m query", async () => {
    const result = await ask("原田はな選手の1500mSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers an athlete-suffixed 3000m query", async () => {
    const result = await ask("江口大尊選手の3000m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers an athlete-suffixed 5km query", async () => {
    const result = await ask("村上葉侑選手の5kmSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers an athlete-suffixed fullwidth-unit query", async () => {
    const result = await ask("原田はな選手の１５００ｍ ＳＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers an athlete-suffixed Japanese-unit query", async () => {
    const result = await ask("江口大尊選手の3000メートルSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a spaced athlete-suffixed query", async () => {
    const result = await ask("原田はな選手の1 500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers an athlete-suffixed 800m query", async () => {
    const result = await ask("原田はな選手の800mSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("2:20.81");
  });

  it("answers an athlete-suffixed season-best query", async () => {
    const result = await ask("村上葉侑選手の5kmシーズンベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers an athlete-suffixed PB query", async () => {
    const result = await ask("江口大尊選手の3000mＰＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers an athlete-suffixed query without a distance", async () => {
    const result = await ask("村上葉侑選手のシーズンベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers a halfwidth-spaced surname query", async () => {
    const result = await ask("原田 はなの1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a fullwidth-spaced surname query", async () => {
    const result = await ask("原田　はなの1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a halfwidth-spaced male name query", async () => {
    const result = await ask("江口 大尊の3000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a fullwidth-spaced male name query", async () => {
    const result = await ask("江口　大尊の3000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a halfwidth-spaced five-kilometer query", async () => {
    const result = await ask("村上 葉侑の5km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers a fullwidth-spaced five-kilometer query", async () => {
    const result = await ask("村上　葉侑の5km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers a spaced name with a season-best alias", async () => {
    const result = await ask("原田 はなの1500m シーズンベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a spaced name with an athlete suffix", async () => {
    const result = await ask("原田 はな選手の1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a spaced name with a fullwidth unit", async () => {
    const result = await ask("江口 大尊の３０００ｍ ＰＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a spaced name without a distance", async () => {
    const result = await ask("村上 葉侑のシーズンベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers a colon-separated athlete query", async () => {
    const result = await ask("原田はな：1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a comma-separated athlete query", async () => {
    const result = await ask("原田はな、1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a slash-separated athlete query", async () => {
    const result = await ask("原田はな／1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a hyphen-separated athlete query", async () => {
    const result = await ask("原田はな-1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a fullwidth-colon athlete query", async () => {
    const result = await ask("江口大尊：3000m PBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a reverse-order 1500m query", async () => {
    const result = await ask("1500m SBは原田はな？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a reverse-order 3000m query", async () => {
    const result = await ask("3000m PBは江口大尊？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a reverse-order five-kilometer query", async () => {
    const result = await ask("5km SBは村上葉侑？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers a reverse-order Japanese-unit query", async () => {
    const result = await ask("1500メートルSBは原田はな？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a reverse-order query with a fullwidth unit", async () => {
    const result = await ask("３０００ｍ ＰＢは江口大尊？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a lowercase sb query", async () => {
    const result = await ask("原田はなの1500m sbは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a lowercase pb query", async () => {
    const result = await ask("江口大尊の3000m pbは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a mixed-case sb query", async () => {
    const result = await ask("村上葉侑の5km Sbは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers a mixed-case pb query", async () => {
    const result = await ask("江口大尊の3000m Pbは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a lowercase sb query with a Japanese unit", async () => {
    const result = await ask("村上葉侑の5キロ sbは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers a lowercase pb query with a fullwidth unit", async () => {
    const result = await ask("江口大尊の３０００ｍ ｐｂは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a lowercase sb query with a fullwidth distance", async () => {
    const result = await ask("原田はなの１５００ｍ ｓｂは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a lowercase sb query without a distance", async () => {
    const result = await ask("村上葉侑のsbは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers a lowercase pb query without a distance", async () => {
    const result = await ask("江口大尊のpbは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a lowercase sb query with an athlete suffix", async () => {
    const result = await ask("原田はな選手の1500m sbは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a dotted SB query", async () => {
    const result = await ask("原田はなの1500m S.B.は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a dotted PB query", async () => {
    const result = await ask("江口大尊の3000m P.B.は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a fullwidth-dotted SB query", async () => {
    const result = await ask("原田はなの1500m Ｓ.Ｂ.は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a slash-separated SB query", async () => {
    const result = await ask("原田はなの1500m S／Bは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a slash-separated PB query", async () => {
    const result = await ask("江口大尊の3000m P／Bは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a spaced dotted SB query", async () => {
    const result = await ask("原田はなの1500m S. B.は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a lowercase dotted SB query", async () => {
    const result = await ask("原田はなの1500m s.b.は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a dotted SB query with a Japanese unit", async () => {
    const result = await ask("村上葉侑の5キロ S.B.は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers a dotted PB query with a fullwidth unit", async () => {
    const result = await ask("江口大尊の３０００ｍ Ｐ.Ｂ.は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a dotted SB query without a distance", async () => {
    const result = await ask("村上葉侑のS.B.は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("answers a dated Daiming practice result query", async () => {
    const result = await ask("2026-09-22 岱明 女子1000m");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("answers a Daiming practice result query without the city name", async () => {
    const result = await ask("岱明の練習会の結果を教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("answers yesterday's practice athlete query", async () => {
    const result = await askAt("昨日の玉名市練習会で松野は？", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
    expect(result.text).toContain("3:10");
  });

  it("answers a dated female practice result query", async () => {
    const result = await ask("9月22日の岱明練習会の女子1000m結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("answers a dated male practice result query", async () => {
    const result = await ask("2026年9月22日の男子1000m結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("answers a Daiming practice athlete record query", async () => {
    const result = await ask("岱明練習会の村上の記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
    expect(result.text).toContain("3:30");
  });

  it("answers a yesterday practice query for a male athlete", async () => {
    const result = await askAt("昨日の練習会で田上は？", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
    expect(result.text).toContain("3:20");
  });

  it("answers a September 22 practice query for a female athlete", async () => {
    const result = await ask("9/22の練習会で増岡は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
    expect(result.text).toContain("3:46");
  });

  it("answers a Daiming practice query for a runner with unknown splits", async () => {
    const result = await ask("岱明練習会の山本のタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
    expect(result.text).toContain("3:10");
  });

  it("answers a dated practice query for the women's second runner", async () => {
    const result = await ask("2026-09-22の岱明練習会で山﨑は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
    expect(result.text).toContain("3:37");
  });

  it("answers a generic female 1000m practice result query", async () => {
    const result = await ask("女子1000m2本の結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
    expect(result.text).toContain("3:46");
  });

  it("answers a generic male 1000m practice result query", async () => {
    const result = await ask("男子1000m3本の結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
    expect(result.text).toContain("3:20");
  });

  it("answers a female practice athlete time without a date", async () => {
    const result = await ask("増岡の練習会タイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
    expect(result.text).toContain("3:46");
  });

  it("answers a male practice athlete time without a date", async () => {
    const result = await ask("松本の練習会タイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松本");
    expect(result.text).toContain("3:30");
  });

  it("answers a female practice result by gender and event", async () => {
    const result = await ask("岱明練習会の女子1000mは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
    expect(result.text).toContain("3:49");
  });

  it("answers a male practice result by gender and event", async () => {
    const result = await ask("玉名市練習会の男子1000mは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
    expect(result.text).toContain("3:19");
  });

  it("answers a female practice participant query", async () => {
    const result = await ask("練習会で女子1000mを走った人は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
    expect(result.text).toContain("柴尾");
  });

  it("answers a male practice participant query", async () => {
    const result = await ask("練習会で男子1000mを走った人は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
    expect(result.text).toContain("嶋田");
  });

  it("answers a female two-repetition result query", async () => {
    const result = await ask("女子1000mを2本走った結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
    expect(result.text).toContain("3:41");
  });

  it("answers a male three-repetition result query", async () => {
    const result = await ask("男子1000mを3本走った結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
    expect(result.text).toContain("3:09");
  });

  it("answers Takada's practice record query", async () => {
    const result = await ask("高田の練習会記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("高田");
    expect(result.text).toContain("ジョグのみ");
  });

  it("answers Takada's practice query without the word record", async () => {
    const result = await ask("高田の練習会は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("answers Takada's practice status query", async () => {
    const result = await ask("高田は練習会で何をした？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("answers a fullwidth-space Takada practice query", async () => {
    const result = await ask("高田　の練習会記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("answers a dated Takada practice query", async () => {
    const result = await ask("9/22の練習会で高田は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("answers Takada's 1000m participation query", async () => {
    const result = await ask("高田は練習会で女子1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("1000mは実施せず");
  });

  it("answers Takada's practice time query", async () => {
    const result = await ask("高田の練習会タイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("keeps Takada Mana on the athlete corpus", async () => {
    const result = await ask("高田麻那の練習会タイムは？");
    expect(result.sources).not.toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.sources).toContain("out-analysis/athletes/takada-mana.md");
  });

  it("answers Takada's practice note query", async () => {
    const result = await ask("高田の練習会の所感は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("answers Takada's practice participation query", async () => {
    const result = await ask("練習会で高田は走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("answers two requested distances for one athlete", async () => {
    const result = await ask("原田はなの800mと1500mのSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("1500m 4:40.44");
  });

  it("answers two distances separated by a middle dot", async () => {
    const result = await ask("原田はなの800m・1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("1500m 4:40.44");
  });

  it("answers two male distances", async () => {
    const result = await ask("江口大尊の1500mと3000m自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3000m 9:04.46");
  });

  it("answers three requested distances", async () => {
    const result = await ask("村上葉侑の1500m、3000m、5km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:30.83");
    expect(result.text).toContain("3000m 9:44.02");
    expect(result.text).toContain("5km 17:18.00");
  });

  it("answers slash-separated distances", async () => {
    const result = await ask("原田はなの800m/1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("1500m 4:40.44");
  });

  it("answers 1500m and 3km together", async () => {
    const result = await ask("原田はなの1500mと3kmのSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:40.44");
    expect(result.text).toContain("3km 10:39.00");
  });

  it("answers a range-like multi-distance query", async () => {
    const result = await ask("原田はなの800mから1500mのSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("1500m 4:40.44");
  });

  it("answers fullwidth multi-distance notation", async () => {
    const result = await ask("原田はなの８００ｍと１５００ｍのＳＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("1500m 4:40.44");
  });

  it("answers spaced multi-distance notation", async () => {
    const result = await ask("村上葉侑の1 500mと3 000m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:30.83");
    expect(result.text).toContain("3000m 9:44.02");
  });

  it("answers Japanese-unit multi-distance notation", async () => {
    const result = await ask("村上葉侑の1500メートルと5キロSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:30.83");
    expect(result.text).toContain("5km 17:18.00");
  });

  it("answers two athletes separated by と", async () => {
    const result = await ask("原田はなと村上葉侑の1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）の1500m自己ベストは4:40.44");
    expect(result.text).toContain("村上葉侑（南関中）の1500m自己ベストは4:30.83");
  });

  it("answers two athletes separated by a comma", async () => {
    const result = await ask("原田はな、村上葉侑の1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）の1500m自己ベストは4:40.44");
    expect(result.text).toContain("村上葉侑（南関中）の1500m自己ベストは4:30.83");
  });

  it("answers three athletes separated by commas", async () => {
    const result = await ask("原田はな、江口大尊、村上葉侑の1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）の1500m自己ベストは4:40.44");
    expect(result.text).toContain("江口大尊（荒尾三中）は1500の記録がありません");
    expect(result.text).toContain("村上葉侑（南関中）の1500m自己ベストは4:30.83");
  });

  it("answers two athletes separated by a middle dot", async () => {
    const result = await ask("村上葉侑・原田はなの5km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）の5km自己ベストは17:18.00");
    expect(result.text).toContain("原田はな（Star Light AC）は5kmの記録がありません");
  });

  it("answers two athletes separated by a slash", async () => {
    const result = await ask("原田はな／村上葉侑の1500m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）の1500m自己ベストは4:40.44");
    expect(result.text).toContain("村上葉侑（南関中）の1500m自己ベストは4:30.83");
  });

  it("answers two athletes' complete SB request", async () => {
    const result = await ask("原田はなと村上葉侑の自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）の自己ベスト:");
    expect(result.text).toContain("村上葉侑（南関中）の自己ベスト:");
  });

  it("answers a two-athlete 3km request", async () => {
    const result = await ask("原田はなと村上葉侑の3km SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）の3km自己ベストは10:39.00");
    expect(result.text).toContain("村上葉侑（南関中）は3kmの記録がありません");
  });

  it("answers a two-athlete 800m request", async () => {
    const result = await ask("原田はなと村上葉侑の800m SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）の800m自己ベストは2:20.81");
    expect(result.text).toContain("村上葉侑（南関中）は800の記録がありません");
  });

  it("answers two athletes' 5km request with a fullwidth delimiter", async () => {
    const result = await ask("原田はな・村上葉侑の５ｋｍ ＳＢは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）は5kmの記録がありません");
    expect(result.text).toContain("村上葉侑（南関中）の5km自己ベストは17:18.00");
  });

  it("answers two athletes with a Japanese unit", async () => {
    const result = await ask("原田はなと村上葉侑の1500メートルSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）の1500m自己ベストは4:40.44");
    expect(result.text).toContain("村上葉侑（南関中）の1500m自己ベストは4:30.83");
  });

  it("answers an 800m-to-5km range query", async () => {
    const result = await ask("原田はなの800mから5kmまでの記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("1500m 4:40.44");
    expect(result.text).toContain("3km 10:39.00");
  });

  it("answers a range query using 800 meters", async () => {
    const result = await ask("原田はなの800メートルから5キロまでのSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("3km 10:39.00");
  });

  it("answers a fullwidth range query", async () => {
    const result = await ask("原田はなの８００ｍから５ｋｍまでの記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("1500m 4:40.44");
  });

  it("answers a range query with a season-best alias", async () => {
    const result = await ask("原田はなの800mから5kmまでのSBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3000m 10:28.63");
  });

  it("answers a range query for a male athlete", async () => {
    const result = await ask("村上葉侑の1500mから5kmまでの記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:30.83");
    expect(result.text).toContain("5km 17:18.00");
  });

  it("answers a range query with Japanese distance names", async () => {
    const result = await ask("村上葉侑の1500メートルから5キロまでの記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:30.83");
    expect(result.text).toContain("5km 17:18.00");
  });

  it("answers a range query with a spaced start distance", async () => {
    const result = await ask("村上葉侑の1 500mから5kmまでの記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("1500m 4:30.83");
    expect(result.text).toContain("5km 17:18.00");
  });

  it("answers a range query for the full SB set", async () => {
    const result = await ask("原田はなの800mから5kmまでの自己ベストは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("3km 10:39.00");
  });

  it("answers a range query with a fullwidth separator", async () => {
    const result = await ask("原田はなの800m〜5kmまでの記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("3km 10:39.00");
  });

  it("answers a range query for an athlete with missing 5km data", async () => {
    const result = await ask("江口大尊の800mから5kmまでの記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("3000m 9:04.46");
  });

  it("answers an individual record-list query", async () => {
    const result = await ask("原田はなの記録一覧は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな");
    expect(result.text).toContain("4:40.44");
  });

  it("answers an individual full-record query", async () => {
    const result = await ask("原田はなの全記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな");
    expect(result.text).toContain("10:39.00");
  });

  it("answers an individual SB-list query", async () => {
    const result = await ask("原田はなのSB一覧は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("原田はな（Star Light AC）");
    expect(result.text).toContain("4:40.44");
  });

  it("answers a male individual record-list query", async () => {
    const result = await ask("江口大尊の記録一覧は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a female individual full-record query", async () => {
    const result = await ask("村上葉侑の全記録は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑");
    expect(result.text).toContain("17:18.00");
  });

  it("answers an all-distance SB query", async () => {
    const result = await ask("原田はなの全距離SBは？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("3km 10:39.00");
  });

  it("answers a listed SB query", async () => {
    const result = await ask("江口大尊のSBを一覧で教えて");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("江口大尊（荒尾三中）");
    expect(result.text).toContain("9:04.46");
  });

  it("answers a complete SB query", async () => {
    const result = await ask("原田はなのSBを全部教えて");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("800m 2:20.81");
    expect(result.text).toContain("1500m 4:40.44");
  });

  it("answers a personal-best list query", async () => {
    const result = await ask("村上葉侑の自己ベスト一覧は？");
    expect(result.sources).toEqual(["sb/中学生SB.csv"]);
    expect(result.text).toContain("村上葉侑（南関中）");
    expect(result.text).toContain("17:18.00");
  });

  it("keeps a school full-record query on the school digest", async () => {
    const result = await ask("荒尾三中の全記録は？");
    expect(result.sources).toContain("out-analysis/arato-tamana-teams/荒尾三中.md");
    expect(result.sources).not.toEqual(["sb/中学生SB.csv"]);
  });

  it("routes a concise 荒尾三中 SB list to the dedicated digest", async () => {
    const result = await ask("荒尾三中のSB一覧は？");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps 荒尾三中 player lists on the dedicated digest", async () => {
    const result = await ask("荒尾三中の選手一覧は？");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps combined 荒尾三中 player and SB lists dedicated", async () => {
    const result = await ask("荒尾三中の選手とSB一覧は？");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps 所属選手 wording on the 荒尾三中 SB digest", async () => {
    const result = await ask("荒尾三中の所属選手一覧は？");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps シーズンベスト wording on the 荒尾三中 SB digest", async () => {
    const result = await ask("荒尾三中のシーズンベスト一覧は？");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps imperative 荒尾三中 SB list wording dedicated", async () => {
    const result = await ask("荒尾三中のSBを一覧で教えて");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("routes 玉名附中 SB lists to its school digest", async () => {
    const result = await ask("玉名附中のSB一覧は？");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("keeps combined 玉名附中 lists on its school digest", async () => {
    const result = await ask("玉名附中の選手とSB一覧は？");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("accepts 玉名付属 in concise SB list wording", async () => {
    const result = await ask("玉名付属のSB一覧は？");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("accepts 玉高附属 in combined SB list wording", async () => {
    const result = await ask("玉高附属の選手とSB一覧は？");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/玉名附中.md"]);
    expect(result.text).toContain("# 玉名附中 記録一覧");
  });

  it("routes 荒尾三中 SB all wording to the dedicated digest", async () => {
    const result = await ask("荒尾三中のSBを全部見せて");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("accepts 全て wording for 荒尾三中 SB lists", async () => {
    const result = await ask("荒尾三中のSBを全て教えて");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("accepts 全距離 wording for 荒尾三中 SB lists", async () => {
    const result = await ask("荒尾三中の全距離SBは？");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps an SB全一覧 query on the 荒尾三中 digest", async () => {
    const result = await ask("荒尾三中のSB全一覧");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps 全記録のSB wording on the 荒尾三中 digest", async () => {
    const result = await ask("荒尾三中のSB記録を全部");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps player SB all wording on the 荒尾三中 digest", async () => {
    const result = await ask("荒尾三中の選手SBを全部");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("accepts 全距離のSB wording on the 荒尾三中 digest", async () => {
    const result = await ask("荒尾三中の全距離のSBを教えて");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps all 荒尾三中 SB records on the dedicated digest", async () => {
    const result = await ask("荒尾三中のSB記録を全て見せて");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps a complete 荒尾三中 SB request dedicated", async () => {
    const result = await ask("荒尾三中のSBを全部一覧で");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("keeps complete current SB wording on the 荒尾三中 digest", async () => {
    const result = await ask("荒尾三中の現行SBを全部");
    expect(result.sources).toEqual(["out-analysis/arato-tamana-teams/荒尾三中_SB.md"]);
    expect(result.text).toContain("# 荒尾三中 選手・SB一覧");
  });

  it("routes 岱明女子1000m results to the practice note", async () => {
    const result = await ask("岱明の女子1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
    expect(result.text).toContain("村上");
  });

  it("routes 岱明男子1000m results to the practice note", async () => {
    const result = await ask("岱明の男子1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
    expect(result.text).toContain("松野");
  });

  it("routes 岱明女子1000m records to the practice note", async () => {
    const result = await ask("岱明女子1000mの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes 岱明男子1000m records to the practice note", async () => {
    const result = await ask("岱明男子1000mの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes 岱明女子1000m times to the practice note", async () => {
    const result = await ask("岱明の女子1000mタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes 岱明男子1000m times to the practice note", async () => {
    const result = await ask("岱明の男子1000mタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes dated 岱明女子1000m results to the practice note", async () => {
    const result = await ask("9月22日岱明女子1000m結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes dated 岱明男子1000m results to the practice note", async () => {
    const result = await ask("9月22日岱明男子1000m結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes slash-date 岱明女子1000m results to the practice note", async () => {
    const result = await ask("9/22岱明女子1000m結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("村上");
  });

  it("routes slash-date 岱明男子1000m results to the practice note", async () => {
    const result = await ask("9/22岱明男子1000m結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("松野");
  });

  it("routes a generic female 1000m time query to the practice note", async () => {
    const result = await ask("女子1000mのタイムを教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes a generic male 1000m time query to the practice note", async () => {
    const result = await ask("男子1000mのタイムを教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes a female 1000m record query to the practice note", async () => {
    const result = await ask("女子1000mの記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes a male 1000m record query to the practice note", async () => {
    const result = await ask("男子1000mの記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes a female 1000m result query to the practice note", async () => {
    const result = await ask("女子1000mの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes a male 1000m result query to the practice note", async () => {
    const result = await ask("男子1000mの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes a female 1000m result request to the practice note", async () => {
    const result = await ask("女子1000m結果を教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes a male 1000m result request to the practice note", async () => {
    const result = await ask("男子1000m結果を教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes a female 1000m performance query to the practice note", async () => {
    const result = await ask("女子1000mの成績は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes a male 1000m performance query to the practice note", async () => {
    const result = await ask("男子1000mの成績は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("嶋田");
  });

  it("routes 村上 individual 1000m results to the practice note", async () => {
    const result = await ask("村上の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30");
  });

  it("routes 増岡 individual 1000m results to the practice note", async () => {
    const result = await ask("増岡の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:46");
  });

  it("routes 山﨑 individual 1000m results to the practice note", async () => {
    const result = await ask("山﨑の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:46");
  });

  it("routes 角田 individual 1000m results to the practice note", async () => {
    const result = await ask("角田の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:49");
  });

  it("routes 塚原 individual 1000m results to the practice note", async () => {
    const result = await ask("塚原の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("4:00");
  });

  it("routes 柴尾 individual 1000m results to the practice note", async () => {
    const result = await ask("柴尾の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes 松野 individual 1000m results to the practice note", async () => {
    const result = await ask("松野の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10");
  });

  it("routes 田上 individual 1000m results to the practice note", async () => {
    const result = await ask("田上の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:20");
  });

  it("routes 山本 individual 1000m results to the practice note", async () => {
    const result = await ask("山本の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes 中尾 individual 1000m results to the practice note", async () => {
    const result = await ask("中尾の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30");
  });

  it("answers 高田's 1000m participation from the practice note", async () => {
    const result = await ask("高田は1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
    expect(result.text).toContain("実施せず");
  });

  it("answers 村上's 1000m participation from the practice note", async () => {
    const result = await ask("村上は1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:30");
  });

  it("answers 増岡's 1000m participation from the practice note", async () => {
    const result = await ask("増岡は1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:46");
  });

  it("answers 山﨑's 1000m participation from the practice note", async () => {
    const result = await ask("山﨑は1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:46");
  });

  it("answers 角田's 1000m participation from the practice note", async () => {
    const result = await ask("角田は1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:49");
  });

  it("answers 塚原's 1000m participation from the practice note", async () => {
    const result = await ask("塚原は1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("4:00");
  });

  it("answers 柴尾's 1000m participation from the practice note", async () => {
    const result = await ask("柴尾は1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("answers 松野's 1000m participation from the practice note", async () => {
    const result = await ask("松野は1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10");
  });

  it("answers 田上's 1000m participation from the practice note", async () => {
    const result = await ask("田上は1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:10");
  });

  it("answers 嶋田's 1000m participation from the practice note", async () => {
    const result = await ask("嶋田は1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("嶋田");
  });

  it("routes female 1000メートル results to the practice note", async () => {
    const result = await ask("女子1000メートルの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male 1000メートル results to the practice note", async () => {
    const result = await ask("男子1000メートルの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female 1km results to the practice note", async () => {
    const result = await ask("女子1kmの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male 1km results to the practice note", async () => {
    const result = await ask("男子1kmの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female 1キロ results to the practice note", async () => {
    const result = await ask("女子1キロの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male 1キロ results to the practice note", async () => {
    const result = await ask("男子1キロの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes dated female 1000メートル results to the practice note", async () => {
    const result = await ask("9月22日の女子1000メートル結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes dated male 1000メートル results to the practice note", async () => {
    const result = await ask("9月22日の男子1000メートル結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes female 1000メートル records to the practice note", async () => {
    const result = await ask("女子1000メートルの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes male 1000メートル records to the practice note", async () => {
    const result = await ask("男子1000メートルの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes a 3km jog result query to the practice note", async () => {
    const result = await ask("3kmジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes a 3km jog record query to the practice note", async () => {
    const result = await ask("3kmジョグの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes a conversational 3km jog query to the practice note", async () => {
    const result = await ask("3kmジョグはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes a 3km jog content query to the practice note", async () => {
    const result = await ask("3kmジョグの内容は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a dated 3km jog result query to the practice note", async () => {
    const result = await ask("9月22日の3kmジョグ結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes a dated 3km jog record query to the practice note", async () => {
    const result = await ask("9月22日の3kmジョグ記録");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes a slash-date 3km jog result query to the practice note", async () => {
    const result = await ask("9/22の3kmジョグ結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes a 3kmジョグ menu query to the practice note", async () => {
    const result = await ask("3kmジョグのメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes a 3kmジョグ implementation query to the practice note", async () => {
    const result = await ask("3kmジョグの実施内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes a 3km jog time query to the practice note", async () => {
    const result = await ask("3kmジョグのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 動きづくり result wording to the practice note", async () => {
    const result = await ask("動きづくりの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes 動きづくり implementation wording to the practice note", async () => {
    const result = await ask("動きづくりの実施内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes conversational 動きづくり result wording to the practice note", async () => {
    const result = await ask("動きづくりはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes 動きづくり execution wording to the practice note", async () => {
    const result = await ask("動きづくりは実施した？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes dated 動きづくり results to the practice note", async () => {
    const result = await ask("9月22日の動きづくり結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes dated 動きづくり implementation to the practice note", async () => {
    const result = await ask("9月22日の動きづくり実施内容");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes slash-date 動きづくり results to the practice note", async () => {
    const result = await ask("9/22の動きづくり結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("動きづくり");
  });

  it("routes 動きづくり completion questions to the practice note", async () => {
    const result = await ask("動きづくりは実施したの？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 動きづくり performance questions to the practice note", async () => {
    const result = await ask("動きづくりはどう実施した？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes 動きづくり outcome questions to the practice note", async () => {
    const result = await ask("動きづくりの結果を教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes a 3キロ jog result query to the practice note", async () => {
    const result = await ask("3キロジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes a 3キロ jog record query to the practice note", async () => {
    const result = await ask("3キロジョグの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes a 3キロ jog content query to the practice note", async () => {
    const result = await ask("3キロジョグの内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes a 3キロ jog menu query to the practice note", async () => {
    const result = await ask("3キロジョグのメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes a 3キロ jog time query to the practice note", async () => {
    const result = await ask("3キロジョグのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes a dated 3キロ jog result query to the practice note", async () => {
    const result = await ask("9月22日の3キロジョグ結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes a dated 3キロ jog content query to the practice note", async () => {
    const result = await ask("9月22日の3キロジョグ内容");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes a slash-date 3キロ jog result query to the practice note", async () => {
    const result = await ask("9/22の3キロジョグ結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes a conversational 3キロ jog query to the practice note", async () => {
    const result = await ask("3キロジョグはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes a 3キロ jog implementation query to the practice note", async () => {
    const result = await ask("3キロジョグの実施内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes an unqualified 1000m second-repetition query to the practice note", async () => {
    const result = await ask("1000m2本目は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
    expect(result.text).toContain("男子3本");
  });

  it("routes an unqualified 1000m first-repetition query to the practice note", async () => {
    const result = await ask("1000m1本目は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes an unqualified 1000m result query to the practice note", async () => {
    const result = await ask("1000mの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes an unqualified 1000m record query to the practice note", async () => {
    const result = await ask("1000mの記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes an unqualified 1000m time query to the practice note", async () => {
    const result = await ask("1000mのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes an unqualified 1000m menu query to the practice note", async () => {
    const result = await ask("1000mのメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
  });

  it("routes an unqualified Japanese-unit 1000m query to the practice note", async () => {
    const result = await ask("1000メートル2本目は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子3本");
  });

  it("routes an unqualified 1000m count query to the practice note", async () => {
    const result = await ask("1000mは何本？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
  });

  it("routes an unqualified 1000m second-time query to the practice note", async () => {
    const result = await ask("1000mの2本目のタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:20");
  });

  it("routes an unqualified 1000m repetition-count query to the practice note", async () => {
    const result = await ask("1000mの本数と結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子3本");
  });

  it("accepts a space before km in 3 km jog results", async () => {
    const result = await ask("3 kmジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts a space before km in 3 km jog records", async () => {
    const result = await ask("3 kmジョグの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts a space before km in 3 km jog content", async () => {
    const result = await ask("3 kmジョグの内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("accepts a space before km in 3 km jog menus", async () => {
    const result = await ask("3 kmジョグのメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("accepts a space before km in 3 km jog times", async () => {
    const result = await ask("3 kmジョグのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts dated 3 km jog results", async () => {
    const result = await ask("9月22日の3 kmジョグ結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts slash-dated 3 km jog results", async () => {
    const result = await ask("9/22の3 kmジョグ結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts conversational 3 km jog questions", async () => {
    const result = await ask("3 kmジョグはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts 3 km jog implementation questions", async () => {
    const result = await ask("3 kmジョグの実施内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("accepts 3 km jog time questions with spacing", async () => {
    const result = await ask("3 kmジョグのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts a space in 3キロ ジョグ results", async () => {
    const result = await ask("3キロ ジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts a space in 3キロ ジョグ records", async () => {
    const result = await ask("3キロ ジョグの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts a space in 3キロ ジョグ content", async () => {
    const result = await ask("3キロ ジョグの内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("accepts a space in 3キロ ジョグ menus", async () => {
    const result = await ask("3キロ ジョグのメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("accepts a space in 3キロ ジョグ times", async () => {
    const result = await ask("3キロ ジョグのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts dated 3キロ ジョグ results", async () => {
    const result = await ask("9月22日の3キロ ジョグ結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts slash-dated 3キロ ジョグ results", async () => {
    const result = await ask("9/22の3キロ ジョグ結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts conversational 3キロ ジョグ questions", async () => {
    const result = await ask("3キロ ジョグはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts 3キロ ジョグ implementation questions", async () => {
    const result = await ask("3キロ ジョグの実施内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("accepts 3キロ ジョグ time questions", async () => {
    const result = await ask("3キロ ジョグのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts a space in female 1000m results", async () => {
    const result = await ask("女子 1000mの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("accepts a space in male 1000m results", async () => {
    const result = await ask("男子 1000mの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts a space in female 1000m records", async () => {
    const result = await ask("女子 1000mの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("accepts a space in male 1000m records", async () => {
    const result = await ask("男子 1000mの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("accepts a space in female 1000m times", async () => {
    const result = await ask("女子 1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("accepts a space in male 1000m times", async () => {
    const result = await ask("男子 1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("accepts a dated female 1000m query with spacing", async () => {
    const result = await ask("9月22日の女子 1000m結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("女子1000m×2本");
  });

  it("accepts a dated male 1000m query with spacing", async () => {
    const result = await ask("9月22日の男子 1000m結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("男子1000m×3本");
  });

  it("accepts conversational female 1000m spacing", async () => {
    const result = await ask("女子 1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("accepts conversational male 1000m spacing", async () => {
    const result = await ask("男子 1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts a space in unqualified 1000 m results", async () => {
    const result = await ask("1000 mの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts a space in unqualified 1000 m records", async () => {
    const result = await ask("1000 mの記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("accepts a space in unqualified 1000 m times", async () => {
    const result = await ask("1000 mのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("accepts a space in unqualified 1000 m menus", async () => {
    const result = await ask("1000 mのメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
  });

  it("accepts a space in an unqualified 1000 m second repetition", async () => {
    const result = await ask("1000 m 2本目は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子3本");
  });

  it("accepts a space in Japanese-unit 1000 メートル results", async () => {
    const result = await ask("1000 メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("accepts dated 1000 m results", async () => {
    const result = await ask("9月22日の1000 m結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("松野");
  });

  it("accepts slash-dated 1000 m results", async () => {
    const result = await ask("9/22の1000 m結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("田上");
  });

  it("accepts conversational 1000 m questions", async () => {
    const result = await ask("1000 mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
  });

  it("accepts 1000 m count questions", async () => {
    const result = await ask("1000 mは何本？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子3本");
  });

  it("accepts a space in female 1 km results", async () => {
    const result = await ask("女子1 kmの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("accepts a space in male 1 km results", async () => {
    const result = await ask("男子1 kmの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts a space in female 1 キロ results", async () => {
    const result = await ask("女子1 キロの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("accepts a space in male 1 キロ results", async () => {
    const result = await ask("男子1 キロの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("accepts dated female 1 km results", async () => {
    const result = await ask("9月22日の女子1 km結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("女子1000m×2本");
  });

  it("accepts dated male 1 km results", async () => {
    const result = await ask("9月22日の男子1 km結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("男子1000m×3本");
  });

  it("accepts conversational female 1 km questions", async () => {
    const result = await ask("女子1 kmはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("accepts conversational male 1 km questions", async () => {
    const result = await ask("男子1 kmはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts female 1 km record questions with spacing", async () => {
    const result = await ask("女子1 kmの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("accepts male 1 km time questions with spacing", async () => {
    const result = await ask("男子1 kmのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes yesterday's female 1000m results to the practice note", async () => {
    const result = await askAt("昨日の女子1000m結果", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes yesterday's male 1000m results to the practice note", async () => {
    const result = await askAt("昨日の男子1000m結果", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes yesterday's female 1000m records to the practice note", async () => {
    const result = await askAt("昨日の女子1000m記録", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes yesterday's male 1000m records to the practice note", async () => {
    const result = await askAt("昨日の男子1000m記録", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes yesterday's female 1000m times to the practice note", async () => {
    const result = await askAt("昨日の女子1000mタイム", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes yesterday's male 1000m times to the practice note", async () => {
    const result = await askAt("昨日の男子1000mタイム", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes yesterday's female 1000m menu query to the practice note", async () => {
    const result = await askAt("昨日の女子1000mメニュー", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes yesterday's male 1000m menu query to the practice note", async () => {
    const result = await askAt("昨日の男子1000mメニュー", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes yesterday's female 1000m participation query to the practice note", async () => {
    const result = await askAt("昨日の女子1000mはどうだった？", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes yesterday's male 1000m participation query to the practice note", async () => {
    const result = await askAt("昨日の男子1000mはどうだった？", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("keeps ISO-date female 1000m results on the practice note", async () => {
    const result = await ask("2026-09-22女子1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("keeps ISO-date male 1000m results on the practice note", async () => {
    const result = await ask("2026-09-22男子1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("keeps ISO-date female 1000m records on the practice note", async () => {
    const result = await ask("2026-09-22女子1000m記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("keeps ISO-date male 1000m records on the practice note", async () => {
    const result = await ask("2026-09-22男子1000m記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("keeps ISO-date female 1000m times on the practice note", async () => {
    const result = await ask("2026-09-22女子1000mタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("keeps ISO-date male 1000m times on the practice note", async () => {
    const result = await ask("2026-09-22男子1000mタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("keeps ISO-date female 1000m menu queries on the practice note", async () => {
    const result = await ask("2026-09-22女子1000mメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("keeps ISO-date male 1000m menu queries on the practice note", async () => {
    const result = await ask("2026-09-22男子1000mメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("keeps ISO-date female 1000m conversations on the practice note", async () => {
    const result = await ask("2026-09-22女子1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("keeps ISO-date male 1000m conversations on the practice note", async () => {
    const result = await ask("2026-09-22男子1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female 1000m multiplication notation to the practice note", async () => {
    const result = await ask("女子1000m×2の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male 1000m multiplication notation to the practice note", async () => {
    const result = await ask("男子1000m×3の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female 1000m multiplication menu wording to the practice note", async () => {
    const result = await ask("女子1000m×2のメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes male 1000m multiplication menu wording to the practice note", async () => {
    const result = await ask("男子1000m×3のメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("accepts lowercase x for female 1000m repetitions", async () => {
    const result = await ask("女子1000mx2の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("accepts lowercase x for male 1000m repetitions", async () => {
    const result = await ask("男子1000mx3の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes dated female multiplication notation to the practice note", async () => {
    const result = await ask("9月22日女子1000m×2結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes dated male multiplication notation to the practice note", async () => {
    const result = await ask("9月22日男子1000m×3結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes conversational female multiplication notation to the practice note", async () => {
    const result = await ask("女子1000m×2はどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes conversational male multiplication notation to the practice note", async () => {
    const result = await ask("男子1000m×3はどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts spaces around female multiplication notation", async () => {
    const result = await ask("女子1000m × 2の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("accepts spaces around male multiplication notation", async () => {
    const result = await ask("男子1000m × 3の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts spaced lowercase x for female repetitions", async () => {
    const result = await ask("女子1000m x 2の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("accepts spaced lowercase x for male repetitions", async () => {
    const result = await ask("男子1000m x 3の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("accepts spaced female multiplication menus", async () => {
    const result = await ask("女子1000m × 2のメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("accepts spaced male multiplication menus", async () => {
    const result = await ask("男子1000m × 3のメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("accepts dated spaced female multiplication", async () => {
    const result = await ask("9月22日女子1000m × 2結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("女子1000m×2本");
  });

  it("accepts dated spaced male multiplication", async () => {
    const result = await ask("9月22日男子1000m × 3結果");
    expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    expect(result.text).toContain("男子1000m×3本");
  });

  it("accepts conversational spaced female multiplication", async () => {
    const result = await ask("女子1000m × 2はどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("accepts conversational spaced male multiplication", async () => {
    const result = await ask("男子1000m × 3はどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes unqualified 1000m×2 to the practice note", async () => {
    const result = await ask("1000m×2");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
  });

  it("routes unqualified 1000m×3 to the practice note", async () => {
    const result = await ask("1000m×3");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子3本");
  });

  it("routes spaced unqualified 1000m×2 to the practice note", async () => {
    const result = await ask("1000m × 2");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
  });

  it("routes spaced unqualified 1000m×3 to the practice note", async () => {
    const result = await ask("1000m × 3");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子3本");
  });

  it("routes lowercase x2 to the practice note", async () => {
    const result = await ask("1000mx2");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
  });

  it("routes lowercase x3 to the practice note", async () => {
    const result = await ask("1000mx3");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子3本");
  });

  it("routes spaced lowercase x2 to the practice note", async () => {
    const result = await ask("1000m x 2");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
  });

  it("routes spaced lowercase x3 to the practice note", async () => {
    const result = await ask("1000m x 3");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子3本");
  });

  it("routes Japanese-unit 1000メートル×2 to the practice note", async () => {
    const result = await ask("1000メートル×2");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
  });

  it("routes Japanese-unit 1000メートル×3 to the practice note", async () => {
    const result = await ask("1000メートル×3");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子3本");
  });

  it("routes decimal-km jog results to the practice note", async () => {
    const result = await ask("3.0kmジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts a space before the decimal-km jog unit", async () => {
    const result = await ask("3.0 kmジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts Japanese decimal-km jog notation", async () => {
    const result = await ask("3.0キロジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts the full Japanese unit for decimal-km jogs", async () => {
    const result = await ask("3.0キロメートルジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts decimal-km jog detail questions", async () => {
    const result = await ask("3.0kmジョグはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("メニュー");
  });

  it("accepts decimal-km jog menu questions", async () => {
    const result = await ask("3.0 kmジョグのメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("accepts full-unit jog detail questions", async () => {
    const result = await ask("3キロメートルジョグはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts full-unit jog record questions", async () => {
    const result = await ask("3キロメートルジョグの記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts decimal-km jog time questions", async () => {
    const result = await ask("3.0kmジョグのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts decimal-km jog result wording", async () => {
    const result = await ask("3.0kmジョグはどんな結果？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes spaced 1000 m female results to the practice note", async () => {
    const result = await ask("女子1000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes spaced 1000 m male results to the practice note", async () => {
    const result = await ask("男子1000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts spaces around the female distance", async () => {
    const result = await ask("女子 1000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("accepts spaces around the male distance", async () => {
    const result = await ask("男子 1000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts spaced female 1000 m multiplication", async () => {
    const result = await ask("女子 1000 m 2本の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("accepts spaced male 1000 m multiplication", async () => {
    const result = await ask("男子 1000 m 3本の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("accepts female full-unit results with a space before the count", async () => {
    const result = await ask("女子1000メートル 2本の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("accepts male full-unit results with a space before the count", async () => {
    const result = await ask("男子1000メートル 3本の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts a spaced female 1000 m second-repeat question", async () => {
    const result = await ask("女子1000 m×2本目は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("accepts a spaced male 1000 m third-repeat question", async () => {
    const result = await ask("男子1000 m×3本目は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000m×3本");
  });

  it("routes female-of-1000m results to the practice note", async () => {
    const result = await ask("女子の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-of-1000m results to the practice note", async () => {
    const result = await ask("男子の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-of-1000m time questions to the practice note", async () => {
    const result = await ask("女子の1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes male-of-1000m time questions to the practice note", async () => {
    const result = await ask("男子の1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts the middle-dot female separator", async () => {
    const result = await ask("女子・1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("accepts the middle-dot male separator", async () => {
    const result = await ask("男子・1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts the female second-repeat particle wording", async () => {
    const result = await ask("女子の1000mの2本目");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("accepts the male third-repeat particle wording", async () => {
    const result = await ask("男子の1000mの3本目");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts a female run-count phrase", async () => {
    const result = await ask("女子1000mを2本走った結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("accepts a male run-count phrase", async () => {
    const result = await ask("男子1000mを3本走った結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("keeps yesterday's female result on the practice note only", async () => {
    const result = await ask("昨日の女子の1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("keeps yesterday's male result on the practice note only", async () => {
    const result = await ask("昨日の男子の1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("keeps slash-date female results on the practice note only", async () => {
    const result = await ask("9/22女子の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("keeps slash-date male results on the practice note only", async () => {
    const result = await ask("9/22男子の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("keeps Japanese-date female results on the practice note only", async () => {
    const result = await ask("2026年9月22日女子の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("keeps ISO-date male results on the practice note only", async () => {
    const result = await ask("2026-09-22男子の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("keeps female conversational results on the practice note only", async () => {
    const result = await ask("女子の1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("keeps male conversational results on the practice note only", async () => {
    const result = await ask("男子の1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("keeps female spaced-unit results on the practice note only", async () => {
    const result = await ask("昨日の女子1000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("keeps male spaced-unit results on the practice note only", async () => {
    const result = await ask("昨日の男子1000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes 3km-of-jog results to the practice note", async () => {
    const result = await ask("3kmのジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts a spaced 3km-of-jog expression", async () => {
    const result = await ask("3 kmのジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts Japanese 3-kilometer-of-jog wording", async () => {
    const result = await ask("3キロのジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts the full Japanese unit with のジョグ", async () => {
    const result = await ask("3キロメートルのジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts decimal-km-of-jog wording", async () => {
    const result = await ask("3.0kmのジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("keeps yesterday's 3km-of-jog result on the practice note", async () => {
    const result = await ask("昨日の3kmのジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts 3km-of-jog record questions", async () => {
    const result = await ask("3kmのジョグの記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts 3km-of-jog detail questions", async () => {
    const result = await ask("3kmのジョグはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("accepts 3km-of-jog menu questions", async () => {
    const result = await ask("3 kmのジョグのメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("accepts 3km-of-jog time questions", async () => {
    const result = await ask("3キロのジョグのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes whether the 3km jog happened", async () => {
    const result = await ask("3kmジョグをした？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes whether the 3km jog was run", async () => {
    const result = await ask("3kmジョグは走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km jog implementation questions", async () => {
    const result = await ask("3kmジョグは実施した？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes the particle form of whether the jog happened", async () => {
    const result = await ask("3kmのジョグをした？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes Japanese-distance jog action questions", async () => {
    const result = await ask("3キロジョグは行った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes the Japanese particle action form", async () => {
    const result = await ask("3キロのジョグは実施した？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes decimal jog measurement questions", async () => {
    const result = await ask("3.0kmジョグは未計測？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes jog non-implementation questions", async () => {
    const result = await ask("3kmジョグは未実施？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("keeps yesterday's jog action question on the practice note", async () => {
    const result = await ask("昨日の3kmジョグは走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes casual jog action wording", async () => {
    const result = await ask("3kmジョグをやった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km jog duration questions", async () => {
    const result = await ask("3kmジョグの時間は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3km jog elapsed-time questions", async () => {
    const result = await ask("3kmジョグの所要時間は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km jog minute questions", async () => {
    const result = await ask("3kmジョグは何分？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes the spaced 3km jog duration form", async () => {
    const result = await ask("3 kmジョグの時間は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes Japanese-distance jog duration questions", async () => {
    const result = await ask("3キロジョグの時間は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes full-unit jog duration questions", async () => {
    const result = await ask("3キロメートルジョグの時間は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes decimal jog duration questions", async () => {
    const result = await ask("3.0kmジョグの時間は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes yesterday's 3km jog duration question", async () => {
    const result = await ask("昨日の3kmジョグの時間は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3km-of-jog duration questions", async () => {
    const result = await ask("3kmのジョグの所要時間は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km jog measurement-time questions", async () => {
    const result = await ask("3kmジョグの計測時間は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes general 3km jog explanations", async () => {
    const result = await ask("3kmジョグについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes polite 3km jog explanations", async () => {
    const result = await ask("3kmジョグについて教えてください");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes spaced 3km jog explanations", async () => {
    const result = await ask("3 kmジョグについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes Japanese-distance jog explanations", async () => {
    const result = await ask("3キロジョグについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes full-unit jog explanations", async () => {
    const result = await ask("3キロメートルジョグについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes decimal jog explanations", async () => {
    const result = await ask("3.0kmジョグについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes particle-form jog explanations", async () => {
    const result = await ask("3kmのジョグについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes jog overview questions", async () => {
    const result = await ask("3kmジョグの概要を教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes yesterday's jog explanations", async () => {
    const result = await ask("昨日の3kmジョグについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes full-unit particle-form explanations", async () => {
    const result = await ask("3キロメートルのジョグについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes 3000m jog results to the practice note", async () => {
    const result = await ask("3000mジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts the full Japanese 3000m unit", async () => {
    const result = await ask("3000メートルジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts comma-separated 3000m notation", async () => {
    const result = await ask("3,000mジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts fullwidth-comma 3000m notation", async () => {
    const result = await ask("3，000mジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts 3000m jog detail questions", async () => {
    const result = await ask("3000mジョグはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("accepts 3000m jog menu questions", async () => {
    const result = await ask("3000mジョグのメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("accepts 3000m jog timing questions", async () => {
    const result = await ask("3000mジョグのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts 3000m-of-jog wording", async () => {
    const result = await ask("3000mのジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts yesterday's 3000m jog result", async () => {
    const result = await ask("昨日の3000mジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts 3000m jog explanation requests", async () => {
    const result = await ask("3000mジョグについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes kanji-three-kilometer jog results", async () => {
    const result = await ask("三キロジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts kanji-three-kilometer particle wording", async () => {
    const result = await ask("三キロのジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts kanji-three-kilometer full-unit wording", async () => {
    const result = await ask("三キロメートルジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts kanji-three-kilometer full-unit particles", async () => {
    const result = await ask("三キロメートルのジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3千m jog results", async () => {
    const result = await ask("3千mジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts 3千m particle wording", async () => {
    const result = await ask("3千mのジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts 3千メートル wording", async () => {
    const result = await ask("3千メートルジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("keeps yesterday's kanji-distance result on the practice note", async () => {
    const result = await ask("昨日の三キロジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts kanji-distance explanation requests", async () => {
    const result = await ask("三キロジョグについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("accepts kanji-distance duration questions", async () => {
    const result = await ask("三キロジョグは何分？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes female terminology for 1000m results", async () => {
    const result = await ask("女性1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male terminology for 1000m results", async () => {
    const result = await ask("男性1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female terminology for 1km results", async () => {
    const result = await ask("女性1kmの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male terminology for 1km results", async () => {
    const result = await ask("男性1kmの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female terminology with a particle", async () => {
    const result = await ask("女性の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes male terminology with a particle", async () => {
    const result = await ask("男性の1000m結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female terminology for the full unit", async () => {
    const result = await ask("女性1000メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male terminology for the full unit", async () => {
    const result = await ask("男性1000メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes spaced female terminology", async () => {
    const result = await ask("女性 1000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes spaced male terminology", async () => {
    const result = await ask("男性 1000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes decimal female 1km results", async () => {
    const result = await ask("女子1.0kmの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes decimal male 1km results", async () => {
    const result = await ask("男子1.0kmの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes decimal female-kilo results", async () => {
    const result = await ask("女子1.0キロの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes decimal male-kilo results", async () => {
    const result = await ask("男子1.0キロの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("accepts decimal female 1km spacing", async () => {
    const result = await ask("女子1.0 kmの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("accepts decimal male kilo spacing", async () => {
    const result = await ask("男子1.0 キロの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts two-decimal female 1km notation", async () => {
    const result = await ask("女子1.00kmの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("accepts two-decimal male 1km notation", async () => {
    const result = await ask("男子1.00kmの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("accepts decimal female 1km conversational questions", async () => {
    const result = await ask("女子1.0kmはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("accepts decimal male 1km time questions", async () => {
    const result = await ask("男子1.0kmのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes comma-separated female 1000m results", async () => {
    const result = await ask("女子1,000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes comma-separated male 1000m results", async () => {
    const result = await ask("男子1,000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts fullwidth comma female 1000m results", async () => {
    const result = await ask("女子1，000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("accepts fullwidth comma male 1000m results", async () => {
    const result = await ask("男子1，000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes comma-separated female full-unit results", async () => {
    const result = await ask("女子1,000メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes comma-separated male full-unit results", async () => {
    const result = await ask("男子1,000メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts comma-separated female spaced-unit results", async () => {
    const result = await ask("女子1,000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("accepts comma-separated male spaced-unit results", async () => {
    const result = await ask("男子1,000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("accepts comma-separated female conversational results", async () => {
    const result = await ask("女子1,000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("accepts comma-separated male time questions", async () => {
    const result = await ask("男子1,000mのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes 1千m female results", async () => {
    const result = await ask("女子1千mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes 1千m male results", async () => {
    const result = await ask("男子1千mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes bare 千m female results", async () => {
    const result = await ask("女子千mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes bare 千メートル male results", async () => {
    const result = await ask("男子千メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes 1千メートル female results", async () => {
    const result = await ask("女子1千メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes 1千メートル male results", async () => {
    const result = await ask("男子1千メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts spaced 1千m female wording", async () => {
    const result = await ask("女子1千 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("accepts spaced 1千m male wording", async () => {
    const result = await ask("男子1千 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("accepts conversational 千m female wording", async () => {
    const result = await ask("女子千mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("accepts conversational 千m male wording", async () => {
    const result = await ask("男子千mのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes spaced-thousands female results", async () => {
    const result = await ask("女子1 000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes spaced-thousands male results", async () => {
    const result = await ask("男子1 000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts fullwidth-space female results", async () => {
    const result = await ask("女子1　000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("accepts fullwidth-space male results", async () => {
    const result = await ask("男子1　000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("accepts spaces around a female 1000m", async () => {
    const result = await ask("女子 1 000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("accepts spaces around a male 1000m", async () => {
    const result = await ask("男子 1 000 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts spaced-thousands female conversational results", async () => {
    const result = await ask("女子1 000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("accepts spaced-thousands male time questions", async () => {
    const result = await ask("男子1 000mのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("accepts spaced-thousands female full-unit results", async () => {
    const result = await ask("女子1 000メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("accepts spaced-thousands male full-unit results", async () => {
    const result = await ask("男子1 000メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松本");
  });

  it("routes female star-two repeats", async () => {
    const result = await ask("女子1000m*2の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male star-three repeats", async () => {
    const result = await ask("男子1000m*3の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts spaced female star-two repeats", async () => {
    const result = await ask("女子1000m * 2の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("accepts spaced male star-three repeats", async () => {
    const result = await ask("男子1000m * 3の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("accepts female star-two time questions", async () => {
    const result = await ask("女子1000m*2のタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("accepts male star-three time questions", async () => {
    const result = await ask("男子1000m*3のタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts female Japanese-unit star repeats", async () => {
    const result = await ask("女子1000メートル*2の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("accepts male Japanese-unit star repeats", async () => {
    const result = await ask("男子1000メートル*3の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes unqualified star-two repeats", async () => {
    const result = await ask("1000m*2");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子2本");
  });

  it("routes unqualified star-three repeats", async () => {
    const result = await ask("1000m*3");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子3本");
  });

  it("routes colon-separated female results", async () => {
    const result = await ask("女子:1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes colon-separated male results", async () => {
    const result = await ask("男子:1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts fullwidth-colon female results", async () => {
    const result = await ask("女子：1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("accepts fullwidth-colon male results", async () => {
    const result = await ask("男子：1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("accepts hyphen-separated female results", async () => {
    const result = await ask("女子-1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("accepts hyphen-separated male results", async () => {
    const result = await ask("男子-1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts slash-separated female results", async () => {
    const result = await ask("女子／1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("accepts slash-separated male results", async () => {
    const result = await ask("男子／1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("normalizes female terminology with a colon", async () => {
    const result = await ask("女性：1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("normalizes male terminology with a slash", async () => {
    const result = await ask("男性／1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松本");
  });

  it("routes Japanese-comma female results", async () => {
    const result = await ask("女子、1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes Japanese-comma male results", async () => {
    const result = await ask("男子、1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts comma-separated female results", async () => {
    const result = await ask("女子,1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("accepts comma-separated male results", async () => {
    const result = await ask("男子,1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes parenthesized female results", async () => {
    const result = await ask("女子(1000m)の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes parenthesized male results", async () => {
    const result = await ask("男子(1000m)の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes fullwidth-parenthesized female results", async () => {
    const result = await ask("女子（1000m）の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes fullwidth-parenthesized male results", async () => {
    const result = await ask("男子（1000m）の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("accepts parenthesized female conversational results", async () => {
    const result = await ask("女子(1000m)はどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("accepts parenthesized male time questions", async () => {
    const result = await ask("男子(1000m)のタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松本");
  });

  it("routes female repeat-pace questions", async () => {
    const result = await ask("女子1000m2本のペース");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male repeat-pace questions", async () => {
    const result = await ask("男子1000m3本のペース");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female repeat-content questions", async () => {
    const result = await ask("女子1000m2本の内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male repeat-content questions", async () => {
    const result = await ask("男子1000m3本の内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female repeat implementation questions", async () => {
    const result = await ask("女子1000m2本を実施した？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes male repeat implementation questions", async () => {
    const result = await ask("男子1000m3本を実施した？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female repeat-impression questions", async () => {
    const result = await ask("女子1000m2本の感想");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes male repeat-impression questions", async () => {
    const result = await ask("男子1000m3本の感想");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female Japanese-unit repeat pace", async () => {
    const result = await ask("女子1000メートル2本のペース");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male Japanese-unit repeat pace", async () => {
    const result = await ask("男子1000メートル3本のペース");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松本");
  });

  it("routes female repeat averages", async () => {
    const result = await ask("女子1000m2本の平均");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male repeat averages", async () => {
    const result = await ask("男子1000m3本の平均");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female repeat differences", async () => {
    const result = await ask("女子1000m2本の差");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male repeat differences", async () => {
    const result = await ask("男子1000m3本の差");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female repeat trends", async () => {
    const result = await ask("女子1000m2本の推移");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes male repeat trends", async () => {
    const result = await ask("男子1000m3本の推移");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female repeat record lists", async () => {
    const result = await ask("女子1000m2本の記録一覧");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes male repeat record lists", async () => {
    const result = await ask("男子1000m3本の記録一覧");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes dated female repeat averages", async () => {
    const result = await ask("9月22日の女子1000m2本の平均");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes dated male repeat differences", async () => {
    const result = await ask("9月22日の男子1000m3本の差");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松本");
  });

  it("accepts semicolon-separated female results", async () => {
    const result = await ask("女子;1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("accepts semicolon-separated male results", async () => {
    const result = await ask("男子;1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("accepts fullwidth-semicolon female results", async () => {
    const result = await ask("女子；1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("accepts fullwidth-semicolon male results", async () => {
    const result = await ask("男子；1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("accepts vertical-bar female results", async () => {
    const result = await ask("女子|1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("accepts vertical-bar male results", async () => {
    const result = await ask("男子|1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("accepts fullwidth-bar female results", async () => {
    const result = await ask("女子｜1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("accepts fullwidth-bar male results", async () => {
    const result = await ask("男子｜1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("accepts spaced semicolon female results", async () => {
    const result = await ask("女子 ; 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("accepts spaced semicolon male results", async () => {
    const result = await ask("男子 ; 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松本");
  });

  it("routes female TT questions", async () => {
    const result = await ask("女子1000mTTは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male TT questions", async () => {
    const result = await ask("男子1000mTTは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female time-trial questions", async () => {
    const result = await ask("女子1000mタイムトライアルは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male time-trial questions", async () => {
    const result = await ask("男子1000mタイムトライアルは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female TT result questions", async () => {
    const result = await ask("女子1000mTTの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes male TT result questions", async () => {
    const result = await ask("男子1000mTTの結果は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female trial-record questions", async () => {
    const result = await ask("女子1000mタイムトライアルの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes male trial-record questions", async () => {
    const result = await ask("男子1000mタイムトライアルの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female TT time questions", async () => {
    const result = await ask("女子1000mTTのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male TT time questions", async () => {
    const result = await ask("男子1000mTTのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松本");
  });

  it("routes female 1000m-run questions", async () => {
    const result = await ask("女子1000m走は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male 1000m-run questions", async () => {
    const result = await ask("男子1000m走は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female 1000m-run results", async () => {
    const result = await ask("女子1000m走の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male 1000m-run results", async () => {
    const result = await ask("男子1000m走の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female 1000m-run times", async () => {
    const result = await ask("女子1000m走のタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("柴尾");
  });

  it("routes male 1000m-run times", async () => {
    const result = await ask("男子1000m走のタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female full-unit run questions", async () => {
    const result = await ask("女子1000メートル走は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes male full-unit run questions", async () => {
    const result = await ask("男子1000メートル走は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female conversational run questions", async () => {
    const result = await ask("女子1000m走どうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male conversational run questions", async () => {
    const result = await ask("男子1000m走どうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松本");
  });

  it("routes English female jog wording", async () => {
    const result = await ask("3km jogの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes English male jog wording", async () => {
    const result = await ask("3 km jogの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts decimal English jog wording", async () => {
    const result = await ask("3.0km jogの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("accepts particle English jog wording", async () => {
    const result = await ask("3kmのjogの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("accepts Japanese-distance English jog wording", async () => {
    const result = await ask("3キロjogの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes English jog time questions", async () => {
    const result = await ask("3km jogのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes English jog detail questions", async () => {
    const result = await ask("3km jogはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes English jog menu questions", async () => {
    const result = await ask("3km jogのメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes yesterday's English jog result", async () => {
    const result = await ask("昨日の3km jogの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes English jog explanation requests", async () => {
    const result = await ask("3km jogについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes uppercase female JOG wording", async () => {
    const result = await ask("3km JOGの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes uppercase spaced JOG wording", async () => {
    const result = await ask("3 km JOGの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes uppercase decimal JOG wording", async () => {
    const result = await ask("3.0km JOGの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes mixed-case Jog wording", async () => {
    const result = await ask("3km Jogの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes uppercase JOG time questions", async () => {
    const result = await ask("3km JOGのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes uppercase JOG detail questions", async () => {
    const result = await ask("3km JOGはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes uppercase JOG menu questions", async () => {
    const result = await ask("3km JOGのメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes yesterday's uppercase JOG result", async () => {
    const result = await ask("昨日の3km JOGの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes uppercase JOG explanations", async () => {
    const result = await ask("3km JOGについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes uppercase particle JOG wording", async () => {
    const result = await ask("3kmのJOGの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes female jogging results", async () => {
    const result = await ask("3kmジョギングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes spaced jogging results", async () => {
    const result = await ask("3 kmジョギングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes decimal jogging results", async () => {
    const result = await ask("3.0kmジョギングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes particle jogging results", async () => {
    const result = await ask("3kmのジョギングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes jogging time questions", async () => {
    const result = await ask("3kmジョギングのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes jogging detail questions", async () => {
    const result = await ask("3kmジョギングはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes jogging menu questions", async () => {
    const result = await ask("3kmジョギングのメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes jogging explanation requests", async () => {
    const result = await ask("3kmジョギングについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes yesterday's jogging result", async () => {
    const result = await ask("昨日の3kmジョギングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes full-unit jogging results", async () => {
    const result = await ask("3000メートルジョギングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes female running results", async () => {
    const result = await ask("3kmランニングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes spaced running results", async () => {
    const result = await ask("3 kmランニングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes decimal running results", async () => {
    const result = await ask("3.0kmランニングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes particle running results", async () => {
    const result = await ask("3kmのランニングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes running time questions", async () => {
    const result = await ask("3kmランニングのタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes running detail questions", async () => {
    const result = await ask("3kmランニングはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes running menu questions", async () => {
    const result = await ask("3kmランニングのメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes running explanation requests", async () => {
    const result = await ask("3kmランニングについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes yesterday's running result", async () => {
    const result = await ask("昨日の3kmランニングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes full-unit running results", async () => {
    const result = await ask("3000メートルランニングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes short female 3km-run results", async () => {
    const result = await ask("3km走の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes spaced short 3km-run results", async () => {
    const result = await ask("3 km走の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes decimal short 3km-run results", async () => {
    const result = await ask("3.0km走の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes particle short 3km-run results", async () => {
    const result = await ask("3kmの走の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes short-run time questions", async () => {
    const result = await ask("3km走のタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes short-run detail questions", async () => {
    const result = await ask("3km走はどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes short-run menu questions", async () => {
    const result = await ask("3km走のメニューは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes short-run explanation requests", async () => {
    const result = await ask("3km走について教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes yesterday's short-run result", async () => {
    const result = await ask("昨日の3km走の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes full-unit short-run results", async () => {
    const result = await ask("3000メートル走の結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes female 3km ran-result wording", async () => {
    const result = await ask("3kmを走った結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes spaced 3km ran-result wording", async () => {
    const result = await ask("3 kmを走った結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes decimal 3km ran-result wording", async () => {
    const result = await ask("3.0kmを走った結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes Japanese-distance ran-result wording", async () => {
    const result = await ask("3キロを走った結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes full-unit ran-result wording", async () => {
    const result = await ask("3000メートルを走った結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3km run action questions", async () => {
    const result = await ask("3kmを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes 3km run detail questions", async () => {
    const result = await ask("3kmを走った内容は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000m×2本");
  });

  it("routes 3km run time questions", async () => {
    const result = await ask("3kmを走ったタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes yesterday's 3km run result", async () => {
    const result = await ask("昨日の3kmを走った結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3km run explanation requests", async () => {
    const result = await ask("3kmを走ったことについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes 3km run dictionary form", async () => {
    const result = await ask("3kmを走る結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes polite 3km run form", async () => {
    const result = await ask("3kmを走りますか？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km run te-form", async () => {
    const result = await ask("3kmを走ってどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes spaced 3km run dictionary form", async () => {
    const result = await ask("3 kmを走る結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes decimal 3km run dictionary form", async () => {
    const result = await ask("3.0kmを走る結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes Japanese-distance run dictionary form", async () => {
    const result = await ask("3キロを走る結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes full-unit run dictionary form", async () => {
    const result = await ask("3000メートルを走る結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km run plan questions", async () => {
    const result = await ask("3kmを走ってください");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes yesterday's 3km run dictionary form", async () => {
    const result = await ask("昨日の3kmを走る結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3km run te-form time questions", async () => {
    const result = await ask("3kmを走ってタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3km run average questions", async () => {
    const result = await ask("3km走の平均は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3km run difference questions", async () => {
    const result = await ask("3km走の差は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km run trend questions", async () => {
    const result = await ask("3km走の推移は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3km run impression questions", async () => {
    const result = await ask("3km走の感想は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km run list questions", async () => {
    const result = await ask("3km走の一覧は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km run pace questions", async () => {
    const result = await ask("3km走のペースは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3km run record questions", async () => {
    const result = await ask("3km走の成績は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km run TT questions", async () => {
    const result = await ask("3km走のTTは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3km run time-trial questions", async () => {
    const result = await ask("3km走のタイムトライアルは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3km run average-time questions", async () => {
    const result = await ask("3km走の平均タイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes polite-past 3km run results", async () => {
    const result = await ask("3kmを走りました");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes polite-past 3km run result questions", async () => {
    const result = await ask("3kmを走りましたか？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes spaced polite-past 3km runs", async () => {
    const result = await ask("3 kmを走りました");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes decimal polite-past 3km runs", async () => {
    const result = await ask("3.0kmを走りました");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes Japanese-distance polite-past 3km runs", async () => {
    const result = await ask("3キロを走りました");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes full-unit polite-past 3km runs", async () => {
    const result = await ask("3000メートルを走りました");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes polite-past 3km run time questions", async () => {
    const result = await ask("3kmを走りましたがタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes polite-past 3km run detail questions", async () => {
    const result = await ask("3kmを走りましたが内容は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes yesterday polite-past 3km runs", async () => {
    const result = await ask("昨日3kmを走りましたか？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes polite-past 3km run impressions", async () => {
    const result = await ask("3kmを走りましたがどうでしたか？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes negative 3km run statements", async () => {
    const result = await ask("3kmを走っていない");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes negative 3km run questions", async () => {
    const result = await ask("3kmを走っていない？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes contracted negative 3km run statements", async () => {
    const result = await ask("3kmを走ってない");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes spaced negative 3km runs", async () => {
    const result = await ask("3 kmを走っていない");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes decimal negative 3km runs", async () => {
    const result = await ask("3.0kmを走っていない");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes Japanese-distance negative 3km runs", async () => {
    const result = await ask("3キロを走っていない");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes full-unit negative 3km runs", async () => {
    const result = await ask("3000メートルを走っていない");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes negative 3km run time questions", async () => {
    const result = await ask("3kmを走っていないけどタイムは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes negative 3km run detail questions", async () => {
    const result = await ask("3kmを走っていないが内容は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes yesterday negative 3km run questions", async () => {
    const result = await ask("昨日3kmを走っていない？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes female 1000m participant questions", async () => {
    const result = await ask("女子1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male 1000m participant questions", async () => {
    const result = await ask("男子1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female 1000m athlete questions", async () => {
    const result = await ask("女子1000mの選手");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male 1000m athlete questions", async () => {
    const result = await ask("男子1000mの選手");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female 1000m entry questions", async () => {
    const result = await ask("女子1000mに出場した人");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male 1000m entry questions", async () => {
    const result = await ask("男子1000mに出場した人");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female 1000m participant questions", async () => {
    const result = await ask("9月22日の女子1000m参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male 1000m participant questions", async () => {
    const result = await ask("9月22日の男子1000m参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female 1000m entry records", async () => {
    const result = await ask("女子1000mの出場記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male 1000m entry records", async () => {
    const result = await ask("男子1000mの出場記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female 1000m repetition counts", async () => {
    const result = await ask("女子1000mの本数");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000mの記録");
  });

  it("routes male 1000m repetition counts", async () => {
    const result = await ask("男子1000mの本数");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000mの記録");
  });

  it("routes female second repetition questions", async () => {
    const result = await ask("女子1000mの2本目");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male third repetition questions", async () => {
    const result = await ask("男子1000mの3本目");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female repetition-number questions", async () => {
    const result = await ask("女子1000mは何本？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000mの記録");
  });

  it("routes male repetition-number questions", async () => {
    const result = await ask("男子1000mは何本？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000mの記録");
  });

  it("routes female 1000m menu questions", async () => {
    const result = await ask("女子1000mのメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000mの記録");
  });

  it("routes male 1000m menu questions", async () => {
    const result = await ask("男子1000mのメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000mの記録");
  });

  it("routes female 1000m implementation questions", async () => {
    const result = await ask("女子1000mの実施内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male 1000m implementation questions", async () => {
    const result = await ask("男子1000mの実施内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes Takada jog-only questions", async () => {
    const result = await ask("高田はジョグだけ？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("高田の練習会記録");
  });

  it("routes Takada jog result questions", async () => {
    const result = await ask("高田のジョグ結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes Takada 3km jog questions", async () => {
    const result = await ask("高田の3kmジョグ");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes Takada running-only questions", async () => {
    const result = await ask("高田は3kmだけ走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes Takada jogging questions", async () => {
    const result = await ask("高田のジョギング記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes Takada running questions", async () => {
    const result = await ask("高田のランニング結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes dated Takada jog questions", async () => {
    const result = await ask("9月22日の高田のジョグ");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes yesterday Takada jog questions", async () => {
    const result = await ask("昨日の高田のジョグ結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes Takada 3000m jogging questions", async () => {
    const result = await ask("高田の3000メートルジョギング");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes Takada jog detail questions", async () => {
    const result = await ask("高田のジョグの内容は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes Murakami left-foot questions", async () => {
    const result = await ask("村上の左足について");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("左足の外側");
  });

  it("routes Murakami impression questions", async () => {
    const result = await ask("村上の1000mの感想");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("左足の外側");
  });

  it("routes Matsuno bronchitis questions", async () => {
    const result = await ask("松野の気管支炎と1000m");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("気管支炎");
  });

  it("routes Matsuno fitness questions", async () => {
    const result = await ask("松野の体力について");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("体力を戻す必要");
  });

  it("routes Nakao stamina questions", async () => {
    const result = await ask("中尾のスタミナについて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("スタミナが必要");
  });

  it("routes Matsumoto stamina questions", async () => {
    const result = await ask("松本のスタミナについて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("スタミナが必要");
  });

  it("routes Masuoka stability questions", async () => {
    const result = await ask("増岡の安定感について");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("安定感あり");
  });

  it("routes Yamazaki余裕 questions", async () => {
    const result = await ask("山﨑の余裕について");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("余裕があった");
  });

  it("routes Tsunoda difficult-first-repetition questions", async () => {
    const result = await ask("角田のきつそうだった理由");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("きつそう");
  });

  it("routes Tsunoda persistence questions", async () => {
    const result = await ask("角田はどう粘った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("粘った");
  });

  it("routes female 1000m headcount questions", async () => {
    const result = await ask("女子1000mは何人？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("女子1000mの記録");
  });

  it("routes male 1000m headcount questions", async () => {
    const result = await ask("男子1000mは何人？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("男子1000mの記録");
  });

  it("routes female 1000m participant-count questions", async () => {
    const result = await ask("女子1000mの人数");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male 1000m participant-count questions", async () => {
    const result = await ask("男子1000mの人数");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes dated female 1000m headcounts", async () => {
    const result = await ask("9月22日の女子1000mは何人？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes dated male 1000m headcounts", async () => {
    const result = await ask("9月22日の男子1000mは何人？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female full-unit headcounts", async () => {
    const result = await ask("女子1000メートルの人数");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male full-unit headcounts", async () => {
    const result = await ask("男子1000メートルの人数");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes female 1000m count explanations", async () => {
    const result = await ask("女子1000mの人数を教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes male 1000m count explanations", async () => {
    const result = await ask("男子1000mの人数を教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female spaced full-unit results", async () => {
    const result = await ask("女子1000 メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male spaced full-unit results", async () => {
    const result = await ask("男子1000 メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female spaced full-unit time questions", async () => {
    const result = await ask("女子1000 メートルのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male spaced full-unit time questions", async () => {
    const result = await ask("男子1000 メートルのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes dated female spaced full-unit results", async () => {
    const result = await ask("9月22日の女子1000 メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes dated male spaced full-unit results", async () => {
    const result = await ask("9月22日の男子1000 メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes female spaced full-unit detail questions", async () => {
    const result = await ask("女子1000 メートルはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes male spaced full-unit detail questions", async () => {
    const result = await ask("男子1000 メートルはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female spaced full-unit participant questions", async () => {
    const result = await ask("女子1000 メートルの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male spaced full-unit participant questions", async () => {
    const result = await ask("男子1000 メートルの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes split female gender results", async () => {
    const result = await ask("女 子1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes split male gender results", async () => {
    const result = await ask("男 子1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes split female gender time questions", async () => {
    const result = await ask("女 子1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes split male gender time questions", async () => {
    const result = await ask("男 子1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes split female gender participant questions", async () => {
    const result = await ask("女 子1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes split male gender participant questions", async () => {
    const result = await ask("男 子1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes split female gender detailed questions", async () => {
    const result = await ask("女 子1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes split male gender detailed questions", async () => {
    const result = await ask("男 子1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes split female gender menu questions", async () => {
    const result = await ask("女 子1000mのメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes split male gender menu questions", async () => {
    const result = await ask("男 子1000mのメニュー");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes short female gender results", async () => {
    const result = await ask("女1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes short male gender results", async () => {
    const result = await ask("男1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes spaced short female gender results", async () => {
    const result = await ask("女 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes spaced short male gender results", async () => {
    const result = await ask("男 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes short female gender time questions", async () => {
    const result = await ask("女1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes short male gender time questions", async () => {
    const result = await ask("男1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes short female gender participant questions", async () => {
    const result = await ask("女1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes short male gender participant questions", async () => {
    const result = await ask("男1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes short female gender detail questions", async () => {
    const result = await ask("女1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes short male gender detail questions", async () => {
    const result = await ask("男1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes previous-day female 1000m results", async () => {
    const result = await askAt("前日の女子1000mの結果", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes previous-day male 1000m results", async () => {
    const result = await askAt("前日の男子1000mの結果", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes previous-day female 1000m times", async () => {
    const result = await askAt("前日の女子1000mのタイム", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes previous-day male 1000m times", async () => {
    const result = await askAt("前日の男子1000mのタイム", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes previous-day female 1000m participants", async () => {
    const result = await askAt("前日の女子1000mの参加者", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes previous-day male 1000m participants", async () => {
    const result = await askAt("前日の男子1000mの参加者", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes previous-day female 1000m details", async () => {
    const result = await askAt("前日の女子1000mはどうだった？", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes previous-day male 1000m details", async () => {
    const result = await askAt("前日の男子1000mはどうだった？", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes previous-day female 1000m menus", async () => {
    const result = await askAt("前日の女子1000mのメニュー", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes previous-day male 1000m menus", async () => {
    const result = await askAt("前日の男子1000mのメニュー", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes colloquial-yesterday female results", async () => {
    const result = await askAt("きのうの女子1000mの結果", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes colloquial-yesterday male results", async () => {
    const result = await askAt("きのうの男子1000mの結果", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes colloquial-yesterday female times", async () => {
    const result = await askAt("きのうの女子1000mのタイム", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes colloquial-yesterday male times", async () => {
    const result = await askAt("きのうの男子1000mのタイム", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes colloquial-yesterday female participants", async () => {
    const result = await askAt("きのうの女子1000mの参加者", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes colloquial-yesterday male participants", async () => {
    const result = await askAt("きのうの男子1000mの参加者", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes colloquial-yesterday female details", async () => {
    const result = await askAt("きのうの女子1000mはどうだった？", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes colloquial-yesterday male details", async () => {
    const result = await askAt("きのうの男子1000mはどうだった？", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes colloquial-yesterday female menus", async () => {
    const result = await askAt("きのうの女子1000mのメニュー", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes colloquial-yesterday male menus", async () => {
    const result = await askAt("きのうの男子1000mのメニュー", "2026-09-23T12:00:00+09:00");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes common-font Yamazaki records", async () => {
    const result = await ask("山崎の1000mの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes common-font Yamazaki impression questions", async () => {
    const result = await ask("山崎の1000mの感想");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("余裕があった");
  });

  it("routes common-font Yamazaki time questions", async () => {
    const result = await ask("山崎の1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:46");
  });

  it("routes common-font Yamazaki result questions", async () => {
    const result = await ask("山崎の練習会結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:46 - 3:37");
  });

  it("routes common-font Yamazaki date questions", async () => {
    const result = await ask("9月22日の山崎の記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("余裕があった");
  });

  it("routes common-font Yamazaki pace questions", async () => {
    const result = await ask("山崎の1000mのペースは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:46 - 3:37");
  });

  it("routes common-font Yamazaki stability questions", async () => {
    const result = await ask("山崎は余裕があった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("余裕があった");
  });

  it("routes common-font Yamazaki athlete questions", async () => {
    const result = await ask("山崎は女子1000mの選手？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes common-font Yamazaki detail questions", async () => {
    const result = await ask("山崎の1000mの内容はどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3:46 - 3:37");
  });

  it("routes common-font Yamazaki follow-up questions", async () => {
    const result = await ask("山崎の1000mについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes common-font Shimada records", async () => {
    const result = await ask("島田の1000mの記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("嶋田");
  });

  it("routes common-font Shimada time questions", async () => {
    const result = await ask("島田の1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("嶋田");
  });

  it("routes common-font Shimada result questions", async () => {
    const result = await ask("島田の練習会結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("嶋田");
  });

  it("routes common-font Shimada record questions", async () => {
    const result = await ask("島田の1000mの記録は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("? - ?");
  });

  it("routes common-font Shimada date questions", async () => {
    const result = await ask("9月22日の島田の1000m");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("嶋田");
  });

  it("routes common-font Shimada impression questions", async () => {
    const result = await ask("島田の1000mの感想");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("4分");
  });

  it("routes common-font Shimada participant questions", async () => {
    const result = await ask("島田は男子1000mの参加者？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("嶋田");
  });

  it("routes common-font Shimada detail questions", async () => {
    const result = await ask("島田の1000mの内容は？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("4分");
  });

  it("routes common-font Shimada follow-up questions", async () => {
    const result = await ask("島田の1000mについて教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("嶋田");
  });

  it("routes common-font Shimada dated records", async () => {
    const result = await ask("前日の島田の記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("嶋田");
  });

  it("routes variant-font Takada jog records", async () => {
    const result = await ask("髙田のジョグ記録");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes variant-font Takada 1000m questions", async () => {
    const result = await ask("髙田の1000mは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes variant-font Takada non-entry questions", async () => {
    const result = await ask("髙田は1000mに参加した？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("実施せず");
  });

  it("routes variant-font Takada result questions", async () => {
    const result = await ask("髙田の練習会結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("高田");
  });

  it("routes variant-font Takada jogging questions", async () => {
    const result = await ask("髙田のジョギングは？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes variant-font dated Takada questions", async () => {
    const result = await ask("9月22日の髙田のジョグ");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes variant-font previous-day Takada questions", async () => {
    const result = await ask("前日の髙田の1000m");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes variant-font Takada detail questions", async () => {
    const result = await ask("髙田のジョグの内容");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes variant-font Takada participation questions", async () => {
    const result = await ask("髙田は女子1000mを走った？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes variant-font Takada follow-up questions", async () => {
    const result = await ask("髙田について練習会で教えて");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("ジョグのみ");
  });

  it("routes English female 1000m results", async () => {
    const result = await ask("female 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes English male 1000m results", async () => {
    const result = await ask("male 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes English female 1000m times", async () => {
    const result = await ask("female 1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes English male 1000m times", async () => {
    const result = await ask("male 1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes English female 1000m participants", async () => {
    const result = await ask("female 1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes English male 1000m participants", async () => {
    const result = await ask("male 1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated English female 1000m results", async () => {
    const result = await ask("9月22日のfemale 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated English male 1000m results", async () => {
    const result = await ask("9月22日のmale 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes English female 1000m details", async () => {
    const result = await ask("female 1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes English male 1000m details", async () => {
    const result = await ask("male 1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes girls 1000m results", async () => {
    const result = await ask("girls 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes boys 1000m results", async () => {
    const result = await ask("boys 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes singular girl 1000m results", async () => {
    const result = await ask("girl 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes singular boy 1000m results", async () => {
    const result = await ask("boy 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes girls 1000m times", async () => {
    const result = await ask("girls 1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes boys 1000m times", async () => {
    const result = await ask("boys 1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes girls 1000m participants", async () => {
    const result = await ask("girls 1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes boys 1000m participants", async () => {
    const result = await ask("boys 1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes dated girls 1000m results", async () => {
    const result = await ask("9月22日のgirls 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes dated boys 1000m results", async () => {
    const result = await ask("9月22日のboys 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-athlete 1000m results", async () => {
    const result = await ask("女子選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-athlete 1000m results", async () => {
    const result = await ask("男子選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-athlete 1000m times", async () => {
    const result = await ask("女子選手1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-athlete 1000m times", async () => {
    const result = await ask("男子選手1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-athlete 1000m participants", async () => {
    const result = await ask("女子選手1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-athlete 1000m participants", async () => {
    const result = await ask("男子選手1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-athlete results", async () => {
    const result = await ask("9月22日の女子選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-athlete results", async () => {
    const result = await ask("9月22日の男子選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-athlete 1000m details", async () => {
    const result = await ask("女子選手1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-athlete 1000m details", async () => {
    const result = await ask("男子選手1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-of-athletes 1000m results", async () => {
    const result = await ask("女子の選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-of-athletes 1000m results", async () => {
    const result = await ask("男子の選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-of-athletes 1000m times", async () => {
    const result = await ask("女子の選手1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-of-athletes 1000m times", async () => {
    const result = await ask("男子の選手1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-of-athletes participants", async () => {
    const result = await ask("女子の選手1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-of-athletes participants", async () => {
    const result = await ask("男子の選手1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-of-athletes results", async () => {
    const result = await ask("9月22日の女子の選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-of-athletes results", async () => {
    const result = await ask("9月22日の男子の選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-of-athletes details", async () => {
    const result = await ask("女子の選手1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-of-athletes details", async () => {
    const result = await ask("男子の選手1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-middle-dot athlete results", async () => {
    const result = await ask("女子・選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-middle-dot athlete results", async () => {
    const result = await ask("男子・選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-middle-dot athlete times", async () => {
    const result = await ask("女子・選手1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-middle-dot athlete times", async () => {
    const result = await ask("男子・選手1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-middle-dot athlete participants", async () => {
    const result = await ask("女子・選手1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-middle-dot athlete participants", async () => {
    const result = await ask("男子・選手1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-middle-dot athlete results", async () => {
    const result = await ask("9月22日の女子・選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-middle-dot athlete results", async () => {
    const result = await ask("9月22日の男子・選手1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-middle-dot athlete details", async () => {
    const result = await ask("女子・選手1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-middle-dot athlete details", async () => {
    const result = await ask("男子・選手1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes women 1000m results", async () => {
    const result = await ask("women 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes men 1000m results", async () => {
    const result = await ask("men 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes women 1000m times", async () => {
    const result = await ask("women 1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes men 1000m times", async () => {
    const result = await ask("men 1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes women 1000m participants", async () => {
    const result = await ask("women 1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes men 1000m participants", async () => {
    const result = await ask("men 1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated women 1000m results", async () => {
    const result = await ask("9月22日のwomen 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated men 1000m results", async () => {
    const result = await ask("9月22日のmen 1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes women 1000m details", async () => {
    const result = await ask("women 1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes men 1000m details", async () => {
    const result = await ask("men 1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-track 1000m results", async () => {
    const result = await ask("女子陸上1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-track 1000m results", async () => {
    const result = await ask("男子陸上1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-track 1000m times", async () => {
    const result = await ask("女子陸上1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-track 1000m times", async () => {
    const result = await ask("男子陸上1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-track 1000m participants", async () => {
    const result = await ask("女子陸上1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-track 1000m participants", async () => {
    const result = await ask("男子陸上1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-track results", async () => {
    const result = await ask("9月22日の女子陸上1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-track results", async () => {
    const result = await ask("9月22日の男子陸上1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-track 1000m details", async () => {
    const result = await ask("女子陸上1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-track 1000m details", async () => {
    const result = await ask("男子陸上1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-middle-school 1000m results", async () => {
    const result = await ask("女子中学生1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-middle-school 1000m results", async () => {
    const result = await ask("男子中学生1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-middle-school 1000m times", async () => {
    const result = await ask("女子中学生1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-middle-school 1000m times", async () => {
    const result = await ask("男子中学生1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-middle-school 1000m participants", async () => {
    const result = await ask("女子中学生1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-middle-school 1000m participants", async () => {
    const result = await ask("男子中学生1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-middle-school results", async () => {
    const result = await ask("9月22日の女子中学生1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-middle-school results", async () => {
    const result = await ask("9月22日の男子中学生1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-middle-school 1000m details", async () => {
    const result = await ask("女子中学生1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-middle-school 1000m details", async () => {
    const result = await ask("男子中学生1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes abbreviated female-middle-school results", async () => {
    const result = await ask("女子中学1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes abbreviated male-middle-school results", async () => {
    const result = await ask("男子中学1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes abbreviated female-middle-school times", async () => {
    const result = await ask("女子中学1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes abbreviated male-middle-school times", async () => {
    const result = await ask("男子中学1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes abbreviated female-middle-school participants", async () => {
    const result = await ask("女子中学1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes abbreviated male-middle-school participants", async () => {
    const result = await ask("男子中学1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated abbreviated female-middle-school results", async () => {
    const result = await ask("9月22日の女子中学1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated abbreviated male-middle-school results", async () => {
    const result = await ask("9月22日の男子中学1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes abbreviated female-middle-school details", async () => {
    const result = await ask("女子中学1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes abbreviated male-middle-school details", async () => {
    const result = await ask("男子中学1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female 一千m results", async () => {
    const result = await ask("女子一千mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male 一千m results", async () => {
    const result = await ask("男子一千mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female 一千メートル results", async () => {
    const result = await ask("女子一千メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male 一千メートル results", async () => {
    const result = await ask("男子一千メートルの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female spaced 一千m results", async () => {
    const result = await ask("女子一千 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male spaced 一千m results", async () => {
    const result = await ask("男子一千 mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female 一千m results", async () => {
    const result = await ask("9月22日の女子一千mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male 一千m results", async () => {
    const result = await ask("9月22日の男子一千mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female 一千m details", async () => {
    const result = await ask("女子一千mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male 一千m details", async () => {
    const result = await ask("男子一千mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes 3.00km jog results", async () => {
    const result = await ask("3.00kmジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3.000km jog results", async () => {
    const result = await ask("3.000kmジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes spaced 3.00km jog results", async () => {
    const result = await ask("3.00 kmジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3.00キロ jog results", async () => {
    const result = await ask("3.00キロジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3.000キロ jog results", async () => {
    const result = await ask("3.000キロジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes 3.00km jog time questions", async () => {
    const result = await ask("3.00kmジョグのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3.000km jog detail questions", async () => {
    const result = await ask("3.000kmジョグはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("動きづくり");
  });

  it("routes 3.00km running results", async () => {
    const result = await ask("3.00kmランニングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes 3.000km running results", async () => {
    const result = await ask("3.000kmランニングの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("3kmジョグ");
  });

  it("routes yesterday 3.00km jog results", async () => {
    const result = await ask("昨日の3.00kmジョグの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("個別タイムは記録されていません");
  });

  it("routes female-student 1000m results", async () => {
    const result = await ask("女子生徒1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-student 1000m results", async () => {
    const result = await ask("男子生徒1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-student 1000m times", async () => {
    const result = await ask("女子生徒1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-student 1000m times", async () => {
    const result = await ask("男子生徒1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-student 1000m participants", async () => {
    const result = await ask("女子生徒1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-student 1000m participants", async () => {
    const result = await ask("男子生徒1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-student results", async () => {
    const result = await ask("9月22日の女子生徒1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-student results", async () => {
    const result = await ask("9月22日の男子生徒1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-student 1000m details", async () => {
    const result = await ask("女子生徒1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-student 1000m details", async () => {
    const result = await ask("男子生徒1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-division 1000m results", async () => {
    const result = await ask("女子部1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-division 1000m results", async () => {
    const result = await ask("男子部1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-division 1000m times", async () => {
    const result = await ask("女子部1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-division 1000m times", async () => {
    const result = await ask("男子部1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-division 1000m participants", async () => {
    const result = await ask("女子部1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-division 1000m participants", async () => {
    const result = await ask("男子部1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-division results", async () => {
    const result = await ask("9月22日の女子部1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-division results", async () => {
    const result = await ask("9月22日の男子部1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-division 1000m details", async () => {
    const result = await ask("女子部1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-division 1000m details", async () => {
    const result = await ask("男子部1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-runner 1000m results", async () => {
    const result = await ask("女子ランナー1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-runner 1000m results", async () => {
    const result = await ask("男子ランナー1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-runner 1000m times", async () => {
    const result = await ask("女子ランナー1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-runner 1000m times", async () => {
    const result = await ask("男子ランナー1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-runner 1000m participants", async () => {
    const result = await ask("女子ランナー1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-runner 1000m participants", async () => {
    const result = await ask("男子ランナー1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-runner results", async () => {
    const result = await ask("9月22日の女子ランナー1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-runner results", async () => {
    const result = await ask("9月22日の男子ランナー1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-runner 1000m details", async () => {
    const result = await ask("女子ランナー1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-runner 1000m details", async () => {
    const result = await ask("男子ランナー1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-athlete-of 1000m results", async () => {
    const result = await ask("女子選手の1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-athlete-of 1000m results", async () => {
    const result = await ask("男子選手の1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-athlete-of 1000m times", async () => {
    const result = await ask("女子選手の1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-athlete-of 1000m times", async () => {
    const result = await ask("男子選手の1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-athlete-of 1000m participants", async () => {
    const result = await ask("女子選手の1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-athlete-of 1000m participants", async () => {
    const result = await ask("男子選手の1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-athlete-of results", async () => {
    const result = await ask("9月22日の女子選手の1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-athlete-of results", async () => {
    const result = await ask("9月22日の男子選手の1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-athlete-of 1000m details", async () => {
    const result = await ask("女子選手の1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-athlete-of 1000m details", async () => {
    const result = await ask("男子選手の1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-member 1000m results", async () => {
    const result = await ask("女子部員1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-member 1000m results", async () => {
    const result = await ask("男子部員1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-member 1000m times", async () => {
    const result = await ask("女子部員1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-member 1000m times", async () => {
    const result = await ask("男子部員1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-member 1000m participants", async () => {
    const result = await ask("女子部員1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-member 1000m participants", async () => {
    const result = await ask("男子部員1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-member results", async () => {
    const result = await ask("9月22日の女子部員1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-member results", async () => {
    const result = await ask("9月22日の男子部員1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-member 1000m details", async () => {
    const result = await ask("女子部員1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-member 1000m details", async () => {
    const result = await ask("男子部員1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-member-word 1000m results", async () => {
    const result = await ask("女子メンバー1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-member-word 1000m results", async () => {
    const result = await ask("男子メンバー1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-member-word 1000m times", async () => {
    const result = await ask("女子メンバー1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-member-word 1000m times", async () => {
    const result = await ask("男子メンバー1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-member-word 1000m participants", async () => {
    const result = await ask("女子メンバー1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-member-word 1000m participants", async () => {
    const result = await ask("男子メンバー1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-member-word results", async () => {
    const result = await ask("9月22日の女子メンバー1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-member-word results", async () => {
    const result = await ask("9月22日の男子メンバー1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-member-word 1000m details", async () => {
    const result = await ask("女子メンバー1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-member-word 1000m details", async () => {
    const result = await ask("男子メンバー1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-side 1000m results", async () => {
    const result = await ask("女子側1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-side 1000m results", async () => {
    const result = await ask("男子側1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-side 1000m times", async () => {
    const result = await ask("女子側1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-side 1000m times", async () => {
    const result = await ask("男子側1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-side 1000m participants", async () => {
    const result = await ask("女子側1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-side 1000m participants", async () => {
    const result = await ask("男子側1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-side results", async () => {
    const result = await ask("9月22日の女子側1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-side results", async () => {
    const result = await ask("9月22日の男子側1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-side 1000m details", async () => {
    const result = await ask("女子側1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-side 1000m details", async () => {
    const result = await ask("男子側1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-group 1000m results", async () => {
    const result = await ask("女子組1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-group 1000m results", async () => {
    const result = await ask("男子組1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-group 1000m times", async () => {
    const result = await ask("女子組1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-group 1000m times", async () => {
    const result = await ask("男子組1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-group 1000m participants", async () => {
    const result = await ask("女子組1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-group 1000m participants", async () => {
    const result = await ask("男子組1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-group results", async () => {
    const result = await ask("9月22日の女子組1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-group results", async () => {
    const result = await ask("9月22日の男子組1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-group 1000m details", async () => {
    const result = await ask("女子組1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-group 1000m details", async () => {
    const result = await ask("男子組1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it("routes female-team 1000m results", async () => {
    const result = await ask("女子チーム1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("村上");
  });

  it("routes male-team 1000m results", async () => {
    const result = await ask("男子チーム1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("松野");
  });

  it("routes female-team 1000m times", async () => {
    const result = await ask("女子チーム1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("増岡");
  });

  it("routes male-team 1000m times", async () => {
    const result = await ask("男子チーム1000mのタイム");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("田上");
  });

  it("routes female-team 1000m participants", async () => {
    const result = await ask("女子チーム1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山﨑");
  });

  it("routes male-team 1000m participants", async () => {
    const result = await ask("男子チーム1000mの参加者");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("山本");
  });

  it("routes dated female-team results", async () => {
    const result = await ask("9月22日の女子チーム1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("角田");
  });

  it("routes dated male-team results", async () => {
    const result = await ask("9月22日の男子チーム1000mの結果");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("中尾");
  });

  it("routes female-team 1000m details", async () => {
    const result = await ask("女子チーム1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("塚原");
  });

  it("routes male-team 1000m details", async () => {
    const result = await ask("男子チーム1000mはどうだった？");
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain("南本");
  });

  it.each([
    ["女子陣1000mの結果", "村上"],
    ["男子陣1000mの結果", "松野"],
    ["女子陣1000mのタイム", "増岡"],
    ["男子陣1000mのタイム", "田上"],
    ["女子陣1000mの参加者", "山﨑"],
    ["男子陣1000mの参加者", "山本"],
    ["9月22日の女子陣1000mの結果", "角田"],
    ["9月22日の男子陣1000mの結果", "中尾"],
    ["女子陣1000mはどうだった？", "塚原"],
    ["男子陣1000mはどうだった？", "南本"],
  ])("routes gender-group wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子メン1000mの結果", "村上"],
    ["男子メン1000mの結果", "松野"],
    ["女子メン1000mのタイム", "増岡"],
    ["男子メン1000mのタイム", "田上"],
    ["女子メン1000mの参加者", "山﨑"],
    ["男子メン1000mの参加者", "山本"],
    ["9月22日の女子メン1000mの結果", "角田"],
    ["9月22日の男子メン1000mの結果", "中尾"],
    ["女子メン1000mはどうだった？", "塚原"],
    ["男子メン1000mはどうだった？", "南本"],
  ])("routes abbreviated-member wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子児童1000mの結果", "村上"],
    ["男子児童1000mの結果", "松野"],
    ["女子児童1000mのタイム", "増岡"],
    ["男子児童1000mのタイム", "田上"],
    ["女子児童1000mの参加者", "山﨑"],
    ["男子児童1000mの参加者", "山本"],
    ["9月22日の女子児童1000mの結果", "角田"],
    ["9月22日の男子児童1000mの結果", "中尾"],
    ["女子児童1000mはどうだった？", "塚原"],
    ["男子児童1000mはどうだった？", "南本"],
  ])("routes child-gender wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子少年1000mの結果", "村上"],
    ["男子少年1000mの結果", "松野"],
    ["女子少年1000mのタイム", "増岡"],
    ["男子少年1000mのタイム", "田上"],
    ["女子少年1000mの参加者", "山﨑"],
    ["男子少年1000mの参加者", "山本"],
    ["9月22日の女子少年1000mの結果", "角田"],
    ["9月22日の男子少年1000mの結果", "中尾"],
    ["女子少年1000mはどうだった？", "塚原"],
    ["男子少年1000mはどうだった？", "南本"],
  ])("routes youth-gender wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子ジュニア1000mの結果", "村上"],
    ["男子ジュニア1000mの結果", "松野"],
    ["女子ジュニア1000mのタイム", "増岡"],
    ["男子ジュニア1000mのタイム", "田上"],
    ["女子ジュニア1000mの参加者", "山﨑"],
    ["男子ジュニア1000mの参加者", "山本"],
    ["9月22日の女子ジュニア1000mの結果", "角田"],
    ["9月22日の男子ジュニア1000mの結果", "中尾"],
    ["女子ジュニア1000mはどうだった？", "塚原"],
    ["男子ジュニア1000mはどうだった？", "南本"],
  ])("routes junior-gender wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子ユース1000mの結果", "村上"],
    ["男子ユース1000mの結果", "松野"],
    ["女子ユース1000mのタイム", "増岡"],
    ["男子ユース1000mのタイム", "田上"],
    ["女子ユース1000mの参加者", "山﨑"],
    ["男子ユース1000mの参加者", "山本"],
    ["9月22日の女子ユース1000mの結果", "角田"],
    ["9月22日の男子ユース1000mの結果", "中尾"],
    ["女子ユース1000mはどうだった？", "塚原"],
    ["男子ユース1000mはどうだった？", "南本"],
  ])("routes youth-label wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子U15 1000mの結果", "村上"],
    ["男子U15 1000mの結果", "松野"],
    ["女子U15 1000mのタイム", "増岡"],
    ["男子U15 1000mのタイム", "田上"],
    ["女子U15 1000mの参加者", "山﨑"],
    ["男子U15 1000mの参加者", "山本"],
    ["9月22日の女子U15 1000mの結果", "角田"],
    ["9月22日の男子U15 1000mの結果", "中尾"],
    ["女子U15 1000mはどうだった？", "塚原"],
    ["男子U15 1000mはどうだった？", "南本"],
  ])("routes age-category wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子A1000mの結果", "村上"],
    ["男子A1000mの結果", "松野"],
    ["女子A1000mのタイム", "増岡"],
    ["男子A1000mのタイム", "田上"],
    ["女子A1000mの参加者", "山﨑"],
    ["男子A1000mの参加者", "山本"],
    ["9月22日の女子A1000mの結果", "角田"],
    ["9月22日の男子A1000mの結果", "中尾"],
    ["女子A1000mはどうだった？", "塚原"],
    ["男子A1000mはどうだった？", "南本"],
  ])("routes A-category wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子B1000mの結果", "村上"],
    ["男子B1000mの結果", "松野"],
    ["女子B1000mのタイム", "増岡"],
    ["男子B1000mのタイム", "田上"],
    ["女子B1000mの参加者", "山﨑"],
    ["男子B1000mの参加者", "山本"],
    ["9月22日の女子B1000mの結果", "角田"],
    ["9月22日の男子B1000mの結果", "中尾"],
    ["女子B1000mはどうだった？", "塚原"],
    ["男子B1000mはどうだった？", "南本"],
  ])("routes B-category wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子代表1000mの結果", "村上"], ["男子代表1000mの結果", "松野"],
    ["女子代表1000mのタイム", "増岡"], ["男子代表1000mのタイム", "田上"],
    ["女子代表1000mの参加者", "山﨑"], ["男子代表1000mの参加者", "山本"],
    ["9月22日の女子代表1000mの結果", "角田"], ["9月22日の男子代表1000mの結果", "中尾"],
    ["女子代表1000mはどうだった？", "塚原"], ["男子代表1000mはどうだった？", "南本"],
  ])("routes representative wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子カテゴリ1000mの結果", "村上"], ["男子カテゴリ1000mの結果", "松野"],
    ["女子カテゴリ1000mのタイム", "増岡"], ["男子カテゴリ1000mのタイム", "田上"],
    ["女子カテゴリ1000mの参加者", "山﨑"], ["男子カテゴリ1000mの参加者", "山本"],
    ["9月22日の女子カテゴリ1000mの結果", "角田"], ["9月22日の男子カテゴリ1000mの結果", "中尾"],
    ["女子カテゴリ1000mはどうだった？", "塚原"], ["男子カテゴリ1000mはどうだった？", "南本"],
  ])("routes category wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子種目1000mの結果", "村上"], ["男子種目1000mの結果", "松野"],
    ["女子種目1000mのタイム", "増岡"], ["男子種目1000mのタイム", "田上"],
    ["女子種目1000mの参加者", "山﨑"], ["男子種目1000mの参加者", "山本"],
    ["9月22日の女子種目1000mの結果", "角田"], ["9月22日の男子種目1000mの結果", "中尾"],
    ["女子種目1000mはどうだった？", "塚原"], ["男子種目1000mはどうだった？", "南本"],
  ])("routes event-label wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子区分1000mの結果", "村上"], ["男子区分1000mの結果", "松野"],
    ["女子区分1000mのタイム", "増岡"], ["男子区分1000mのタイム", "田上"],
    ["女子区分1000mの参加者", "山﨑"], ["男子区分1000mの参加者", "山本"],
    ["9月22日の女子区分1000mの結果", "角田"], ["9月22日の男子区分1000mの結果", "中尾"],
    ["女子区分1000mはどうだった？", "塚原"], ["男子区分1000mはどうだった？", "南本"],
  ])("routes division-label wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子グループ1000mの結果", "村上"], ["男子グループ1000mの結果", "松野"],
    ["女子グループ1000mのタイム", "増岡"], ["男子グループ1000mのタイム", "田上"],
    ["女子グループ1000mの参加者", "山﨑"], ["男子グループ1000mの参加者", "山本"],
    ["9月22日の女子グループ1000mの結果", "角田"], ["9月22日の男子グループ1000mの結果", "中尾"],
    ["女子グループ1000mはどうだった？", "塚原"], ["男子グループ1000mはどうだった？", "南本"],
  ])("routes group-label wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子カテゴリー1000mの結果", "村上"], ["男子カテゴリー1000mの結果", "松野"],
    ["女子カテゴリー1000mのタイム", "増岡"], ["男子カテゴリー1000mのタイム", "田上"],
    ["女子カテゴリー1000mの参加者", "山﨑"], ["男子カテゴリー1000mの参加者", "山本"],
    ["9月22日の女子カテゴリー1000mの結果", "角田"], ["9月22日の男子カテゴリー1000mの結果", "中尾"],
    ["女子カテゴリー1000mはどうだった？", "塚原"], ["男子カテゴリー1000mはどうだった？", "南本"],
  ])("routes katakana-category wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子枠1000mの結果", "村上"], ["男子枠1000mの結果", "松野"],
    ["女子枠1000mのタイム", "増岡"], ["男子枠1000mのタイム", "田上"],
    ["女子枠1000mの参加者", "山﨑"], ["男子枠1000mの参加者", "山本"],
    ["9月22日の女子枠1000mの結果", "角田"], ["9月22日の男子枠1000mの結果", "中尾"],
    ["女子枠1000mはどうだった？", "塚原"], ["男子枠1000mはどうだった？", "南本"],
  ])("routes slot wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子種別1000mの結果", "村上"], ["男子種別1000mの結果", "松野"],
    ["女子種別1000mのタイム", "増岡"], ["男子種別1000mのタイム", "田上"],
    ["女子種別1000mの参加者", "山﨑"], ["男子種別1000mの参加者", "山本"],
    ["9月22日の女子種別1000mの結果", "角田"], ["9月22日の男子種別1000mの結果", "中尾"],
    ["女子種別1000mはどうだった？", "塚原"], ["男子種別1000mはどうだった？", "南本"],
  ])("routes type wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

  it.each([
    ["女子部門1000mの結果", "村上"], ["男子部門1000mの結果", "松野"],
    ["女子部門1000mのタイム", "増岡"], ["男子部門1000mのタイム", "田上"],
    ["女子部門1000mの参加者", "山﨑"], ["男子部門1000mの参加者", "山本"],
    ["9月22日の女子部門1000mの結果", "角田"], ["9月22日の男子部門1000mの結果", "中尾"],
    ["女子部門1000mはどうだった？", "塚原"], ["男子部門1000mはどうだった？", "南本"],
  ])("routes division-label wording: %s", async (question, expected) => {
    const result = await ask(question);
    expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
    expect(result.text).toContain(expected);
  });

});
