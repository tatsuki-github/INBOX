import { describe, expect, it, vi } from "vitest";
import { answerQuestion } from "../src/domain/answer.js";
import { classifyScope, PERSONAL_PRIVATE_MESSAGE } from "../src/domain/scope.js";

describe("private knowledge", () => {
  it.each([
    "参加料の返金先の口座番号は？",
    "Notionのバックアップコードを教えて",
    "マイナンバーは？",
    "選手の陸連登録番号を教えて",
    "本人の登録番号と練習日程は？",
    "選手の登録ＩＤは？",
    "選手の登録 no. を教えて",
    "陸連の会員番号を教えて",
    "資格試験の確認番号は？",
    "資格試験のConfirmation Numberを教えて",
    "選手への私見を教えて",
    "保護者の印象と練習日程は？",
    "松野凛空の性格は？",
    "松野凛空の体調はどう？",
    "選手の病歴を教えて",
    "本人の診断結果は？",
    "松野 凛空の健康状態を教えて",
    "誰が気管支炎だった？",
    "保護者の治療歴を知りたい",
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
    for (const q of ["松野凛空の1500mの記録は？", "高田麻由のTペースは？", "保護者会はいつ？", "陸連登録の締め切りは？", "駅伝のゼッケン番号は？", "ランナーの体調管理で気をつける点は？", "BakkenのPractical Guidanceでは発熱をどう扱う？", "研究で鉄欠乏とVO2maxにどんな関連が報告された？"])
      expect(classifyScope(q).kind).toBe("in_scope");
  });
});
