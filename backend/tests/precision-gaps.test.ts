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
});
