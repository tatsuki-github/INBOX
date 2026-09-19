import { describe, expect, it } from "vitest";
import { answerQuestion } from "../src/domain/answer.js";
import { retrieveBySources, resetRetrieverCache } from "../src/rag/retrieve.js";
import { resetKgCache } from "../src/kg/query.js";

describe("team full-record routing", () => {
  it("retrieveBySources prefers exact 玉名附中 digest", () => {
    resetRetrieverCache();
    const hits = retrieveBySources(
      [
        "out-analysis/arato-tamana-teams/玉名附中.md",
        "out-analysis/arato-tamana-teams",
      ],
      { query: "玉名附中所属選手の全記録一覧は？", perSource: 12, maxChunks: 32 },
    );
    expect(hits.some((h) => h.chunk.source.includes("玉名附中"))).toBe(true);
  });

  it("answers 玉名附中 full records from exact digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉名附中所属選手の全記録一覧は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources.some((s) => s.includes("玉名附中"))).toBe(true);
      expect(result.text).not.toContain("コーチに直接聞いてください");
    }
  });

  it("answers 玉南中 full records from exact digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉南中所属選手の全記録一覧は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources.some((s) => s.includes("玉南中"))).toBe(true);
      expect(result.text).toMatch(/玉南/);
    }
  });

  it("answers 玉・有明中 full records from exact digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉・有明中所属選手の全記録一覧は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources.some((s) => s.includes("玉・有明中"))).toBe(true);
    }
  });
});
