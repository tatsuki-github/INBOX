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
});
