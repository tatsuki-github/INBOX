import { describe, expect, it } from "vitest";
import { answerQuestion } from "../src/domain/answer.js";
import type { RetrievedChunk } from "../src/rag/retrieve.js";

const fakeRetrieve = (question: string): RetrievedChunk[] => [
  {
    chunk: {
      id: "ekiden-ocr/2024-男子.md:0",
      source: "ekiden-ocr/2024-男子.md",
      text: `質問関連: ${question}\n荒玉駅伝2024男子 岱明中 順位`,
    },
    score: 1.2,
  },
];

describe("answerQuestion", () => {
  it("refuses out-of-scope without calling retrieve/llm", async () => {
    let called = false;
    const result = await answerQuestion("今日の天気は？", {
      retrieve: () => {
        called = true;
        return [];
      },
      llm: {
        complete: async () => {
          called = true;
          return "should not run";
        },
      },
    });
    expect(result.kind).toBe("refused");
    expect(called).toBe(false);
  });

  it("returns offline answer when llm missing", async () => {
    const result = await answerQuestion("荒玉駅伝で岱明は何位？", {
      retrieve: fakeRetrieve,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("オフライン");
      expect(result.sources).toContain("ekiden-ocr/2024-男子.md");
    }
  });

  it("returns answered when llm succeeds", async () => {
    const result = await answerQuestion("荒玉駅伝で岱明は何位？", {
      retrieve: fakeRetrieve,
      llm: {
        complete: async () => "岱明は○位です。",
      },
    });
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.text).toContain("岱明");
    }
  });
});
