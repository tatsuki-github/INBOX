import { describe, expect, it, vi } from "vitest";
import * as preparedQa from "../src/domain/preparedQa.js";
import { answerQuestion } from "../src/domain/answer.js";
import { buildSystemPrompt } from "../src/rag/prompt.js";

const question = "2025年の中体連駅伝女子の岱明の詳細結果\n区間タイムと区間順位と通過タイムと通過順位";
const emptyKg = { question, refs: [], corpus_sources: [], matched_nodes: [] };

describe("prepared QA grounded synthesis", { timeout: 30_000 }, () => {
  it("routes multi-field relay details to the complete answer instead of a summary", async () => {
    for (const q of [question, "2025年荒玉駅伝女子岱明の詳細を区間タイム・区間順位・通過タイム・通過順位付きで教えて"])
      expect(preparedQa.matchPreparedAnswer(q, { defaultYear: 2026 })?.id).toBe("aragyoku-2025-女子-岱明-leg-detail");
    const result = await answerQuestion(question, { llm: null, defaultYear: 2026 });
    for (const line of [
      "11:02（区間順位 7位） / 通過タイム 11:02（通過順位 7位）",
      "7:01（区間順位 3位） / 通過タイム 18:03（通過順位 4位）",
      "7:44（区間順位 8位） / 通過タイム 25:47（通過順位 8位）",
      "8:03（区間順位 8位） / 通過タイム 33:50（通過順位 8位）",
      "11:32（区間順位 6位） / 通過タイム 45:22（通過順位 7位）",
    ]) expect(result.text).toContain(line);
  });

  it("calls the LLM with an incomplete QA plus KG-routed primary facts and returns its synthesis", async () => {
    const match = vi.spyOn(preparedQa, "matchPreparedAnswer").mockReturnValueOnce({
      id: "incomplete-fixture", text: "2025年岱明女子は7位・45:22。", score: 1,
      matchedQuestion: question, sources: [],
    });
    const kgQuery = vi.fn(() => ({ ...emptyKg,
      refs: ["input/aragyoku/transcripts/2025-女子.json"],
      corpus_sources: ["aragyoku/transcripts/2025-女子.json"],
      matched_nodes: [{ id: "fixture", type: "Source", label: "結果", score: 100,
        hint: "このヒントは事実として使わない", refs: [] }],
    }));
    const complete = vi.fn(async (_system: string, user: string) => {
      expect(user).toContain("想定QAの回答候補");
      expect(user).toContain("2025年岱明女子は7位・45:22。");
      for (const fact of ["村上咲稀", "増岡里俐", '区間タイム7:01 区間順位3位 通過タイム（累計）18:03 通過順位4位'])
        expect(user).toContain(fact);
      expect(user).not.toContain("このヒントは事実として使わない");
      expect(user).not.toContain("FAQ自身を根拠にするな");
      return "2区 増岡里俐、区間7:01・区間3位、通過18:03・通過4位。";
    });
    try {
      const result = await answerQuestion(question, {
        kgQuery, defaultYear: 2026, llm: { complete },
        retrieve: () => [{ chunk: { id: "self", source: "faq/prepared-qa.v1.yaml", text: "FAQ自身を根拠にするな" }, score: 999 }],
      });
      expect(kgQuery).toHaveBeenCalledOnce();
      expect(complete).toHaveBeenCalledOnce();
      expect(result.kind).toBe("answered");
      expect(result.text).toContain("通過18:03・通過4位");
      if (result.kind === "answered") expect(result.sources).toContain("aragyoku/transcripts/2025-女子.json");
    } finally { match.mockRestore(); }
  });

  it("does not silently return the static QA when LLM synthesis fails", async () => {
    const complete = vi.fn(async () => { throw new Error("test synthesis failure"); });
    const result = await answerQuestion(question, { defaultYear: 2026,
      kgQuery: () => emptyKg, retrieve: () => [], llm: { complete } });
    expect(complete).toHaveBeenCalledOnce();
    expect(result.kind).toBe("error");
  });

  it("instructs the model to resolve conflicts from primary facts and mark absent fields", () => {
    const system = buildSystemPrompt();
    expect(system).toContain("一次資料を優先");
    expect(system).toContain("資料に無い項目は未確認");
    expect(system).toContain("質問で求められた項目を省略しない");
  });
});
