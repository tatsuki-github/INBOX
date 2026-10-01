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

  it("clarifies vague meet-result / schedule / order questions", () => {
    expect(matchClarifyAnswer("結果は？")?.id).toBe("clarify-meet-result");
    expect(matchClarifyAnswer("誰が勝った？")?.id).toBe("clarify-meet-result");
    expect(matchClarifyAnswer("いつ？")?.id).toBe("clarify-schedule");
    expect(matchClarifyAnswer("日程は？")?.id).toBe("clarify-schedule");
    expect(matchClarifyAnswer("オーダーは？")?.id).toBe("clarify-order");
    expect(matchClarifyAnswer("なごみ駅伝の結果は？")).toBeNull();
    expect(matchClarifyAnswer("荒玉駅伝はいつ？")).toBeNull();
    expect(matchClarifyAnswer("2025年荒玉男子の岱明のオーダーは？")).toBeNull();
  });

  it("clarifies unexpected vague questions with examples", () => {
    expect(matchClarifyAnswer("タイムは？")?.id).toBe("clarify-time");
    expect(matchClarifyAnswer("メンバーは？")?.id).toBe("clarify-order");
    expect(matchClarifyAnswer("何区がいい？")?.id).toBe("clarify-leg-advice");
    expect(matchClarifyAnswer("区間どうする？")?.id).toBe("clarify-leg-advice");
    expect(matchClarifyAnswer("練習どうだった？")?.id).toBe("clarify-practice");
    expect(matchClarifyAnswer("速い人は？")?.id).toBe("clarify-who-fast");
    expect(matchClarifyAnswer("誰？")?.id).toBe("clarify-who-fast");
    expect(matchClarifyAnswer("松野は速い？")?.id).toBe("clarify-named-time");
    expect(matchClarifyAnswer("松野のタイムは？")?.id).toBe("clarify-named-time");
    expect(matchClarifyAnswer("教えて")?.id).toBe("clarify-ultra-vague");
    expect(matchClarifyAnswer("おすすめは？")?.id).toBe("clarify-ultra-vague");
    expect(matchClarifyAnswer("？")?.id).toBe("clarify-ultra-vague");
    expect(matchClarifyAnswer("タイムは？")?.text).toContain("例:");
    expect(matchClarifyAnswer("今村昇磨の1500m自己ベストは？")).toBeNull();
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

  it("returns examples for unexpected vague questions without LLM", async () => {
    for (const q of ["タイムは？", "何区がいい？", "練習どうだった？", "教えて"]) {
      const result = await answerQuestion(q, {
        retrieve: () => {
          throw new Error("retrieve should not run");
        },
        llm: {
          complete: async () => "should not run",
        },
        skipRouter: true,
        kgQuery: () => ({
          question: q,
          matched_nodes: [],
          refs: [],
          corpus_sources: [],
        }),
      });
      expect(result.kind, q).toBe("answered");
      if (result.kind === "answered") {
        expect(result.sources[0], q).toMatch(/^clarify:/);
        expect(result.text, q).toMatch(/例:|使い方/);
        expect(result.text, q).not.toMatch(/名前,所属,性別/);
      }
    }
  });
});
