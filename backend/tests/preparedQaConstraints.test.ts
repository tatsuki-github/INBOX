import { describe, expect, it } from "vitest";
import { matchPreparedAnswer, type PreparedQaEntry } from "../src/domain/preparedQa.js";

function match(query: string, candidate: string) {
  const entries: PreparedQaEntry[] = [{
    id: "fixture", questions: [candidate], answer: "定型回答", sources: [],
  }];
  return matchPreparedAnswer(query, { defaultYear: 2026, entries });
}

describe("prepared FAQ factual constraints", () => {
  it.each([
    ["2026-08-26のいだてん岱明朝練のメニュー", "2026-08-25のいだてん岱明朝練のメニュー"],
    ["2026年8月26日のいだてん岱明朝練のメニュー", "2026年8月26日のいだてん岱明夕練のメニュー"],
    ["2025年荒玉駅伝男子岱明2区の通過順位", "2025年荒玉駅伝男子岱明2区の区間順位"],
    ["2025年荒玉駅伝男子岱明2区の区間順位", "2025年荒玉駅伝男子岱明2区の通過順位"],
    ["2025年金栗駅伝男子岱明の結果", "2025年なごみ駅伝男子岱明の結果"],
    ["2025年荒玉駅伝男子岱明の結果と区間タイム一覧", "2025年荒玉駅伝女子岱明の結果と区間タイム一覧"],
    ["2025年荒玉駅伝男子岱明2区の区間タイムと通過順位", "2025年荒玉駅伝男子岱明3区の区間タイムと通過順位"],
    ["松野凛空の1500m自己ベスト", "松野凛空の3000m自己ベスト"],
    ["荒玉駅伝男子2区と3区の距離", "荒玉駅伝男子2区の距離"],
    ["荒玉男子1区を9:30で走ったら区間何位？", "荒玉男子1区を9:32で走ったら区間何位？"],
    ["荒玉駅伝女子の各区間5位の基準タイムは？", "荒玉駅伝女子の各区間6位の基準タイムは？"],
  ])("rejects conflicting facts: %s", (query, candidate) => {
    expect(match(query, candidate)).toBeNull();
  });

  it.each([
    ["2025年荒玉駅伝男子岱明2区のタイム", "2025年荒玉駅伝男子岱明2区のタイム"],
    ["松野凛空の1.5km自己ベスト", "松野凛空の1500m自己ベスト"],
    ["荒玉駅伝男子女子の距離", "荒玉駅伝男子女子の距離"],
  ])("preserves compatible facts: %s", (query, candidate) => {
    expect(match(query, candidate)?.id).toBe("fixture");
  });
});


it("does not answer today's events with static search help", () => {
  const entries = [{ id: "calendar-today", questions: ["今日の予定の聞き方は？", "予定の検索方法は？"], answer: "検索方法", sources: [] }];
  expect(matchPreparedAnswer("今日の予定は？", { entries })).toBeNull();
  expect(matchPreparedAnswer("今日の予定の聞き方は？", { entries })?.id).toBe("calendar-today");
});

it("requires a date for a specific practice session", () => {
  const entries = [{ id: "cal-2026-20260826-いだてん岱明朝練休み", questions: ["2026-08-26のいだてん岱明朝練のメニューは？"], answer: "朝練は休み", sources: [] }];
  expect(matchPreparedAnswer("いだてん岱明朝練のメニューは？", { entries })).toBeNull();
  expect(matchPreparedAnswer("2026-08-26のいだてん岱明朝練のメニューは？", { entries })?.text).toBe("朝練は休み");
});

it("serves corrected source facts from the published catalog", () => {
  const cases = [
    ["今年の荒玉地区の男子1500mSBランキングトップ20は？", ["20位 内野翼", "4:33.34"]],
    ["2025年荒玉女子の区間賞は？", ["4区 内田千惺", "5区 大木莉子"]],
    ["荒玉駅伝の過去の優勝校を全て提示して", ["2012年男子: 玉名", "2014年女子の優勝校は未収録"]],
    ["岱明のトラック1周は？", ["560m"]],
    ["2026年なごみ駅伝の全チームの総合順位は？", ["男子 18位 岱明A: 42:39", "女子 6位 岱明A: 30:18"]],
  ] as const;
  for (const [question, facts] of cases) {
    const answer = matchPreparedAnswer(question, { defaultYear: 2026 })?.text;
    for (const fact of facts) expect(answer, question).toContain(fact);
  }
}, 30000);
