import { describe, expect, it } from "vitest";
import {
  isUnderspecifiedPersonalBestQuestion,
  matchClarifyAnswer,
} from "../src/domain/clarify.js";
import { answerQuestion } from "../src/domain/answer.js";

describe("isUnderspecifiedPersonalBestQuestion", () => {
  it("flags vague PB questions", () => {
    expect(isUnderspecifiedPersonalBestQuestion("自分の自己ベストは？")).toBe(true);
    expect(isUnderspecifiedPersonalBestQuestion("自己ベストは？")).toBe(true);
    expect(isUnderspecifiedPersonalBestQuestion("SB教えて")).toBe(true);
    expect(isUnderspecifiedPersonalBestQuestion("最新の自己ベストは？")).toBe(true);
    expect(isUnderspecifiedPersonalBestQuestion("今の自己ベストは？")).toBe(true);
  });

  it("allows concrete named questions", () => {
    expect(isUnderspecifiedPersonalBestQuestion("今村昇磨の1500m自己ベストは？")).toBe(
      false,
    );
    expect(isUnderspecifiedPersonalBestQuestion("石川隼の3000mのSBは？")).toBe(false);
  });

  it("allows short / compat / latin / kana athlete names with distance", () => {
    expect(isUnderspecifiedPersonalBestQuestion("森の3000m自己ベストは？")).toBe(false);
    expect(isUnderspecifiedPersonalBestQuestion("小﨑の3000m自己ベストは？")).toBe(false);
    expect(isUnderspecifiedPersonalBestQuestion("FESTUSの5000m自己ベストは？")).toBe(
      false,
    );
    expect(isUnderspecifiedPersonalBestQuestion("ヴの3000m自己ベストは？")).toBe(false);
    expect(isUnderspecifiedPersonalBestQuestion("杉𠮷（STR）の3000m SBは？")).toBe(
      false,
    );
  });
});

describe("matchClarifyAnswer", () => {
  it("returns example question texts", () => {
    const c = matchClarifyAnswer("自分の自己ベストは？");
    expect(c?.id).toBe("clarify-personal-best");
    expect(c?.text).toContain("例:");
    expect(c?.text).toContain("今村昇磨の1500m自己ベストは？");
  });
});

describe("answerQuestion clarify", () => {
  it("returns concrete examples without calling LLM for vague PB", async () => {
    let llmCalled = false;
    const result = await answerQuestion("自分の自己ベストは？", {
      retrieve: () => [],
      llm: {
        complete: async () => {
          llmCalled = true;
          return "should not run";
        },
      },
      skipRouter: true,
      kgQuery: () => ({
        question: "x",
        matched_nodes: [],
        refs: [],
        corpus_sources: [],
      }),
    });
    expect(llmCalled).toBe(false);
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.text).toContain("例:");
      expect(result.sources[0]).toBe("clarify:clarify-personal-best");
    }
  });
});
