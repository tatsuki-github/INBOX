import { describe, expect, it } from "vitest";
import { loadPreparedQa, matchPreparedAnswer, normalizePreparedQuestion } from "../src/domain/preparedQa.js";

describe("additional source-backed school comparisons", () => {
  it("loads exactly 5000 additional answers and resolves all their questions uniquely", async () => {
    const entries = loadPreparedQa();
    const batch = entries.filter(e => e.id.startsWith("edgecmp-"));
    expect(batch).toHaveLength(5000);
    const normOwners = new Map<string, Set<string>>();
    let processed = 0;
    for (const e of entries) for (const q of e.questions) {
      if (++processed % 1000 === 0) await new Promise(resolve => setTimeout(resolve, 0));
      const norm = normalizePreparedQuestion(q, { defaultYear: 2026 });
      const owners = normOwners.get(norm) ?? new Set<string>();
      owners.add(e.id);
      normOwners.set(norm, owners);
    }
    for (const e of batch) for (const q of e.questions) {
      if (++processed % 100 === 0) await new Promise(resolve => setTimeout(resolve, 0));
      expect([...normOwners.get(normalizePreparedQuestion(q, { defaultYear: 2026 }))!], q).toEqual([e.id]);
      expect(matchPreparedAnswer(q, { defaultYear: 2026 })?.id, q).toBe(e.id);
    }
  }, 120000);
});

describe("comparison identity and measure constraints", () => {
  const question = "2025年荒玉駅伝男子の岱明と玉名の2区の区間タイム差は？";
  const entries = [{ id: "fixture", questions: [question], answer: "fixture", sources: [] }];
  it.each([
    "2025年荒玉駅伝男子の岱明と玉東の2区の区間タイム差は？",
    "2025年荒玉駅伝男子の岱明と玉名の2区終了時点の累計タイム差は？",
    "2025年荒玉駅伝女子の岱明と玉名の2区の区間タイム差は？",
    "2025年荒玉駅伝男子の岱明と玉名の3区の区間タイム差は？",
    "今年の荒玉駅伝男子の岱明と玉名の2区の区間タイム差は？",
  ])("does not answer a different comparison: %s", query => {
    expect(matchPreparedAnswer(query, { defaultYear: 2026, entries })).toBeNull();
  });
});
