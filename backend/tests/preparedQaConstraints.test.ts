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
    ["2025年荒玉駅伝男子岱明の結果と区間タイム一覧", "2025年荒玉駅伝女子岱明の結果と区間タイム一覧"],
    ["2025年荒玉駅伝男子岱明2区の区間タイムと通過順位", "2025年荒玉駅伝男子岱明3区の区間タイムと通過順位"],
    ["松野凛空の1500m自己ベスト", "松野凛空の3000m自己ベスト"],
    ["荒玉駅伝男子2区と3区の距離", "荒玉駅伝男子2区の距離"],
    ["荒玉男子1区を9:30で走ったら区間何位？", "荒玉男子1区を9:32で走ったら区間何位？"],
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
