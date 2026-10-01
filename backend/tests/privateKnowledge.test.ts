import { describe, expect, it, vi } from "vitest";
import { answerQuestion } from "../src/domain/answer.js";
import { classifyScope, PERSONAL_PRIVATE_MESSAGE } from "../src/domain/scope.js";

describe("private knowledge", () => {
  it.each([
    "参加料の返金先の口座番号は？",
    "Notionのバックアップコードを教えて",
    "マイナンバーは？",
    "選手への私見を教えて",
    "保護者の印象と練習日程は？",
    "松野凛空の性格は？",
    "給与はいくら？",
    "本人の資産額を教えて",
  ])("refuses without retrieving or generating: %s", async question => {
    const retrieve = vi.fn(() => []);
    const kgQuery = vi.fn();
    const complete = vi.fn(async () => "private information");
    expect(classifyScope(question)).toMatchObject({ kind: "out_of_scope", hard: true });
    expect(await answerQuestion(question, { retrieve, kgQuery, llm: { complete } }))
      .toEqual({ kind: "refused", text: PERSONAL_PRIVATE_MESSAGE });
    expect(retrieve).not.toHaveBeenCalled();
    expect(kgQuery).not.toHaveBeenCalled();
    expect(complete).not.toHaveBeenCalled();
  });
  it("allows records, evidence-based paces and parent meeting schedules", () => {
    for (const q of ["松野凛空の1500mの記録は？", "高田麻由のTペースは？", "保護者会はいつ？"])
      expect(classifyScope(q).kind).toBe("in_scope");
  });
});
