import { describe, expect, it, beforeEach } from "vitest";
import {
  loadPreparedQa,
  matchPreparedAnswer,
  normalizePreparedQuestion,
  resetPreparedQaCache,
} from "../src/domain/preparedQa.js";
import { answerQuestion } from "../src/domain/answer.js";

describe("preparedQa catalog", () => {
  beforeEach(() => {
    resetPreparedQaCache();
  });

  it("loads 100 entries", () => {
    const entries = loadPreparedQa();
    expect(entries).toHaveLength(100);
    expect(entries[0]?.id).toBeTruthy();
    expect(entries[0]?.answer.length).toBeGreaterThan(10);
  });
});

describe("normalizePreparedQuestion", () => {
  it("expands relative years and strips trailing noise", () => {
    expect(normalizePreparedQuestion("去年の荒玉女子優勝は誰？", { defaultYear: 2026 })).toContain(
      "2025",
    );
    expect(normalizePreparedQuestion("コース図を見せて", { defaultYear: 2026 })).toMatch(/画像|コース/);
  });
});

describe("matchPreparedAnswer", () => {
  beforeEach(() => {
    resetPreparedQaCache();
  });

  it("hits canonical questions", () => {
    const hit = matchPreparedAnswer("荒玉駅伝って何？", { defaultYear: 2026 });
    expect(hit?.id).toBe("aragyoku-what");
    expect(hit?.text).toContain("中体連駅伝");
  });

  it("hits paraphrases", () => {
    const hit = matchPreparedAnswer("県ジュニアの結果PDFを見せて", { defaultYear: 2026 });
    expect(hit?.id).toBe("junior-2025-pdf");
    expect(hit?.text).toContain("drive.google.com/file/d/");
  });

  it("hits relative-year wording", () => {
    const hit = matchPreparedAnswer("去年の荒玉男子優勝は誰？", { defaultYear: 2026 });
    expect(hit?.id).toBe("aragyoku-2025-men-winner");
    expect(hit?.text).toContain("菊水");
  });

  it("returns null for unrelated chatter without prepared entry", () => {
    // deliberately odd; if someday prepared, this assertion should be updated
    const hit = matchPreparedAnswer("宇宙の果てはどこ？", { defaultYear: 2026 });
    expect(hit).toBeNull();
  });
});

describe("answerQuestion prepared path", () => {
  it("short-circuits without LLM for prepared FAQ", async () => {
    let llmCalled = false;
    const result = await answerQuestion("2025年荒玉駅伝の岱明男子は何位？", {
      defaultYear: 2026,
      llm: {
        complete: async () => {
          llmCalled = true;
          return "should not run";
        },
      },
      retrieve: () => {
        throw new Error("retrieve should not run");
      },
    });
    expect(llmCalled).toBe(false);
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.sources[0]).toBe("prepared:aragyoku-2025-daiming-men");
      expect(result.text).toContain("6位");
      expect(result.text).toContain("59:08");
      expect(result.text).not.toContain("コーチに直接聞いてください");
    }
  });

  it("returns junior result prepared answer instead of coach fallback", async () => {
    const result = await answerQuestion("ジュニア駅伝の結果は？", {
      defaultYear: 2026,
      llm: null,
      retrieve: () => [],
    });
    expect(result.kind).toBe("answered");
    expect(result.text).toMatch(/ジュニア|36:52|44:23|Drive|drive\.google/);
    expect(result.text).not.toContain("コーチに直接聞いてください");
    expect(result.sources?.[0]).toMatch(/^prepared:/);
  });

  it("keeps dynamic course-video canned ahead of prepared", async () => {
    const result = await answerQuestion("荒玉駅伝のコース動画は？", {
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.sources[0]).toBe("canned:aragyoku-course-videos");
    }
  });
});
