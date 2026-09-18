import { describe, expect, it } from "vitest";
import {
  expandDateQuery,
  parseDateMentions,
  resolveRelativeYears,
} from "../src/domain/dates.js";

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

describe("resolveRelativeYears", () => {
  it("maps 去年/今年/おととし from defaultYear", () => {
    expect(resolveRelativeYears("去年の荒玉", 2026)).toEqual([2025]);
    expect(resolveRelativeYears("今年の大会", 2026)).toEqual([2026]);
    expect(resolveRelativeYears("おととしの優勝", 2026)).toEqual([2024]);
    expect(resolveRelativeYears("昨年の結果", 2026)).toEqual([2025]);
  });

  it("keeps explicit YYYY年", () => {
    expect(resolveRelativeYears("2024年男子", 2026)).toContain(2024);
  });
});

describe("expandDateQuery", () => {
  it("appends iso and mmdd tokens for retrieval", () => {
    const expanded = expandDateQuery("9/20の予定は？", 2026);
    expect(expanded).toContain("2026-09-20");
    expect(expanded).toContain("0920");
  });

  it("appends year for 去年 queries", () => {
    const expanded = expandDateQuery("去年の荒玉駅伝の優勝校は？", 2026);
    expect(expanded).toContain("2025");
    expect(expanded).toContain("2025年");
  });
});
