import { describe, expect, it } from "vitest";
import { classifyScope, OUT_OF_SCOPE_MESSAGE } from "../src/domain/scope.js";

describe("classifyScope", () => {
  it("accepts いだてん岱明 ekiden questions", () => {
    const d = classifyScope("2024年男子の荒玉駅伝で岱明は何位？");
    expect(d.kind).toBe("in_scope");
  });

  it("accepts practice questions", () => {
    const d = classifyScope("いだてん岱明の夕練メニューは？");
    expect(d.kind).toBe("in_scope");
  });

  it("refuses weather questions", () => {
    const d = classifyScope("今日の天気は？");
    expect(d.kind).toBe("out_of_scope");
    if (d.kind === "out_of_scope") {
      expect(d.message).toBe(OUT_OF_SCOPE_MESSAGE);
    }
  });

  it("refuses empty and unrelated", () => {
    expect(classifyScope("").kind).toBe("out_of_scope");
    expect(classifyScope("こんにちは").kind).toBe("out_of_scope");
  });

  it("accepts bare date schedule questions", () => {
    const d = classifyScope("9/20の予定は？");
    expect(d.kind).toBe("in_scope");
    if (d.kind === "in_scope") {
      expect(d.reason === "date_question" || d.reason.startsWith("keyword:")).toBe(true);
    }
  });

  it("accepts なごみ / 大会 keywords", () => {
    expect(classifyScope("なごみ駅伝の距離は？").kind).toBe("in_scope");
    expect(classifyScope("次の大会はいつ？").kind).toBe("in_scope");
  });
});
