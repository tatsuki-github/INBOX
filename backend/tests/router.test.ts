import { describe, expect, it } from "vitest";
import { routeSources } from "../src/domain/router.js";
import type { KgQueryResult } from "../src/kg/query.js";

const kg: KgQueryResult = {
  question: "9/20の予定は？",
  matched_nodes: [
    {
      id: "topic:calendar",
      type: "Topic",
      label: "カレンダー",
      score: 2,
      hint: "予定",
      refs: ["input/events.2026.yaml"],
    },
  ],
  refs: ["input/events.2026.yaml"],
  corpus_sources: ["calendar/events.daiming.yaml"],
};

describe("routeSources", () => {
  it("falls back to KG sources without llm", async () => {
    const d = await routeSources("9/20の予定は？", kg, null);
    expect(d.via).toBe("fallback");
    expect(d.sources).toContain("calendar/events.daiming.yaml");
  });

  it("accepts llm json within allowlist", async () => {
    const d = await routeSources("9/20の予定は？", kg, {
      complete: async () =>
        JSON.stringify({
          sources: ["calendar/events.daiming.yaml", "../etc/passwd"],
          focus: "2026-09-20 なごみ",
          reason: "date",
        }),
    });
    expect(d.via).toBe("llm");
    expect(d.sources).toEqual(["calendar/events.daiming.yaml"]);
    expect(d.focus).toContain("なごみ");
  });
});
