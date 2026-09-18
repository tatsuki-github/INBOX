import { describe, expect, it } from "vitest";
import { expandDateQuery, parseDateMentions } from "../src/domain/dates.js";

describe("parseDateMentions", () => {
  it("parses slash dates like 9/20", () => {
    const hits = parseDateMentions("9/20の予定は？", 2026);
    expect(hits).toEqual([
      {
        iso: "2026-09-20",
        mmdd: "0920",
        month: 9,
        day: 20,
        year: 2026,
      },
    ]);
  });

  it("parses Japanese month-day", () => {
    const hits = parseDateMentions("9月20日の大会は？", 2026);
    expect(hits[0]?.iso).toBe("2026-09-20");
    expect(hits[0]?.mmdd).toBe("0920");
  });

  it("parses ISO dates", () => {
    const hits = parseDateMentions("2026-09-20 なにがある？", 2026);
    expect(hits[0]?.iso).toBe("2026-09-20");
  });

  it("uses explicit year when present with slash date", () => {
    const hits = parseDateMentions("2025/9/21", 2026);
    expect(hits[0]?.iso).toBe("2025-09-21");
    expect(hits[0]?.mmdd).toBe("0921");
  });
});

describe("expandDateQuery", () => {
  it("appends iso and mmdd tokens for retrieval", () => {
    const expanded = expandDateQuery("9/20の予定は？", 2026);
    expect(expanded).toContain("2026-09-20");
    expect(expanded).toContain("0920");
    expect(expanded).toContain("9/20の予定は？");
  });

  it("returns original when no date", () => {
    expect(expandDateQuery("荒玉駅伝で岱明は何位？", 2026)).toBe(
      "荒玉駅伝で岱明は何位？",
    );
  });
});
