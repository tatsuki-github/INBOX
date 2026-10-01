import { describe, expect, it, vi } from "vitest";
import { answerQuestion } from "../src/domain/answer.js";
import { classifyScope, REMUNERATION_PRIVATE_MESSAGE } from "../src/domain/scope.js";

describe("remuneration privacy", () => {
  it.each([
    "2026年1月30日のいだてん岱明謝礼はいくら？",
    "地域部活動の謝金の時給を教えて",
    "コーチの報酬と練習メニューを一緒に教えて",
    "地域部活動指導者の時給は？",
  ])("refuses before prepared lookup, KG, retrieval or LLM: %s", async question => {
    const retrieve = vi.fn(() => []);
    const kgQuery = vi.fn();
    const complete = vi.fn(async () => "private payment");
    expect(classifyScope(question)).toMatchObject({ kind: "out_of_scope", hard: true });
    expect(await answerQuestion(question, { retrieve, kgQuery, llm: { complete } }))
      .toEqual({ kind: "refused", text: REMUNERATION_PRIVATE_MESSAGE });
    expect(retrieve).not.toHaveBeenCalled();
    expect(kgQuery).not.toHaveBeenCalled();
    expect(complete).not.toHaveBeenCalled();
  });
  it("keeps ordinary training and membership fee questions in scope", () => {
    expect(classifyScope("岱明の練習メニューは？").kind).toBe("in_scope");
    expect(classifyScope("地域部活動の年会費はいくら？").kind).toBe("in_scope");
  });
});
