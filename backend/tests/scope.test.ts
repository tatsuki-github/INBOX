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

  it("accepts repo-wide questions without idaten keywords", () => {
    expect(classifyScope("knowledge graph の用途は？").kind).toBe("in_scope");
    expect(classifyScope("ADR 016 は何を決めた？").kind).toBe("in_scope");
    expect(classifyScope("こんにちは").kind).toBe("in_scope");
  });

  it("refuses weather questions hard", () => {
    const d = classifyScope("今日の天気は？");
    expect(d.kind).toBe("out_of_scope");
    if (d.kind === "out_of_scope") {
      expect(d.hard).toBe(true);
      expect(d.message).toBe(OUT_OF_SCOPE_MESSAGE);
    }
  });

  it("refuses clearly unrelated chat hard", () => {
    for (const q of [
      "プログラミングの宿題手伝って",
      "トランプ大統領について",
      "野球の試合結果は？",
      "英語翻訳して",
      "占いして",
      "漫画のおすすめは？",
      "今日の夕食のおすすめは？",
      "AIで小説書いて",
      "競馬の予想して",
      "暗号通貨いくら？",
      "恋の相談乗って",
      "仮想通貨いくら",
      "Rust書いて",
      "ゴルフの試合結果は？",
      "Geminiとは",
      "四柱推命して",
      "小説おすすめは？",
      "内閣について",
    ]) {
      const d = classifyScope(q);
      expect(d.kind, q).toBe("out_of_scope");
    }
  });

  it("refuses empty", () => {
    expect(classifyScope("").kind).toBe("out_of_scope");
  });

  it("accepts bare date schedule questions", () => {
    const d = classifyScope("9/20の予定は？");
    expect(d.kind).toBe("in_scope");
  });

  it("accepts なごみ / 大会 keywords", () => {
    expect(classifyScope("なごみ駅伝の距離は？").kind).toBe("in_scope");
    expect(classifyScope("次の大会はいつ？").kind).toBe("in_scope");
  });
});
