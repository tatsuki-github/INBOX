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
});
