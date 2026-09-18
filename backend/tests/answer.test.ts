import { describe, expect, it } from "vitest";
import { answerQuestion } from "../src/domain/answer.js";
import type { RetrievedChunk } from "../src/rag/retrieve.js";
import { resetRetrieverCache } from "../src/rag/retrieve.js";
import { resetKgCache } from "../src/kg/query.js";

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
      skipRouter: true,
      kgQuery: () => ({
        question: "荒玉駅伝で岱明は何位？",
        matched_nodes: [],
        refs: [],
        corpus_sources: ["ekiden-ocr/2024-男子.md"],
      }),
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("オフライン");
      expect(result.text).not.toMatch(/ekiden-ocr|calendar\/|\.yaml|\.md/);
    }
  });

  it("returns answered when llm succeeds", async () => {
    const result = await answerQuestion("荒玉駅伝で岱明は何位？", {
      retrieve: fakeRetrieve,
      skipRouter: true,
      kgQuery: () => ({
        question: "x",
        matched_nodes: [],
        refs: [],
        corpus_sources: ["ekiden-ocr/2024-男子.md"],
      }),
      llm: {
        complete: async () => "岱明は○位です。",
      },
    });
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.text).toContain("岱明");
    }
  });

  it("appends CSV result URLs after formatting", async () => {
    const result = await answerQuestion("熊本市選手権の結果は？", {
      retrieve: () => [],
      skipRouter: true,
      defaultYear: 2026,
      meetResultUrls: [
        {
          title: "第４５回熊本市陸上競技選手権大会中長距離の部",
          date: "2026-04-18",
          year: 2026,
          urls: ["http://www.kcrk.jp/i-mode/kiroku/sisen_i/450418/PC/rel026.html"],
        },
      ],
      kgQuery: () => ({
        question: "x",
        matched_nodes: [],
        refs: [],
        corpus_sources: [],
      }),
      llm: {
        complete: async () => "男子1500mは松野が走りました。",
      },
    });
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.text).toContain("結果ページ:");
      expect(result.text).toContain("sisen_i/450418");
    }
  });

  it("answers 9/20 schedule offline with なごみ in context", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("9/20の予定は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/なごみ/);
      expect(result.sources.some((s) => s.includes("calendar") || s.includes("なごみ") || s.includes("0920"))).toBe(
        true,
      );
    }
  });

  it("llm sees なごみ context for 9/20", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion("9/20の予定は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: {
        complete: async (_sys, user) => {
          userPrompt = user;
          return "2026-09-20はなごみ駅伝です。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    expect(userPrompt).toMatch(/なごみ/);
    expect(userPrompt).not.toMatch(/source=/);
    if (result.kind === "answered") {
      expect(result.text).toMatch(/なごみ/);
    }
  });

  it("formats llm markdown and strips source footers", async () => {
    const result = await answerQuestion("荒玉駅伝で岱明は何位？", {
      retrieve: fakeRetrieve,
      skipRouter: true,
      kgQuery: () => ({
        question: "x",
        matched_nodes: [],
        refs: [],
        corpus_sources: ["ekiden-ocr/2024-男子.md"],
      }),
      llm: {
        complete: async () =>
          "**岱明は3位**です。\n\n根拠: ekiden-ocr/2024-男子.md",
      },
    });
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.text).toContain("岱明は3位");
      expect(result.text).not.toContain("**");
      expect(result.text).not.toMatch(/根拠|ekiden-ocr|\.md/);
    }
  });

  it("puts 2025 winners in context for 去年の荒玉駅伝の優勝校", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion("去年の荒玉駅伝の優勝校は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: {
        complete: async (_sys, user) => {
          userPrompt = user;
          return "男子は菊水、女子は玉名です。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    // Context must include 2025 winner facts (菊水 / 玉名) from transcripts or winners summary
    expect(userPrompt).toMatch(/2025/);
    expect(userPrompt).toMatch(/菊水/);
    expect(userPrompt).toMatch(/玉名/);
    if (result.kind === "answered") {
      expect(result.sources.some((s) => s.includes("aragyoku") || s.includes("2025"))).toBe(true);
    }
  });

  it("does not return 荒玉 sources for 去年のジュニア駅伝の岱明の結果", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion("去年のジュニア駅伝の岱明の結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: {
        complete: async (_sys, user) => {
          userPrompt = user;
          return "女子・男子ともチャレンジ優勝です。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.sources.some((s) => s.includes("ジュニア"))).toBe(true);
      expect(result.sources.some((s) => s.includes("岱明の結果"))).toBe(true);
      expect(result.sources.every((s) => !s.startsWith("aragyoku/") && s !== "aragyoku")).toBe(
        true,
      );
      expect(result.sources.every((s) => !s.startsWith("ekiden-ocr/"))).toBe(true);
    }
    expect(userPrompt).toMatch(/ジュニア|チャレンジ|36分47秒|45分07秒/);
    expect(userPrompt).not.toMatch(/winners-by-year|荒玉中体連/);
  });

  it("does not boost aragyoku for なごみ駅伝 questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の開催要項は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources.some((s) => /なごみ|金栗/.test(s) || s.includes("calendar"))).toBe(
        true,
      );
      expect(result.sources.every((s) => !s.startsWith("aragyoku/transcripts/"))).toBe(true);
    }
  });

  it("hits SB row for short name without の particle", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("森 3000m 自己ベスト", {
      skipRouter: true,
      llm: null,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources.some((s) => s.includes("sb/"))).toBe(true);
      expect(result.text).toMatch(/11:04\.38|森,/);
      expect(result.text).not.toContain("コーチに直接聞いてください");
    }
  });

  it("puts aragyoku team markdown context for detailed 菊水 区間 questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion("2025年荒玉駅伝男子の菊水の1区は誰？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: {
        complete: async (_sys, user) => {
          userPrompt = user;
          return "松浦眞大です。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    expect(userPrompt).toMatch(/松浦眞大/);
    expect(userPrompt).toMatch(/菊水/);
    expect(userPrompt).not.toMatch(/コーチに直接聞いてください/);
    if (result.kind === "answered") {
      expect(
        result.sources.some(
          (s) => s.includes("aragyoku-teams") || s.includes("transcripts/2025-男子"),
        ),
      ).toBe(true);
    }
  });

  it("puts aragyoku overview for 男子2区 ペース questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion(
      "荒玉駅伝の男子2区を9分でいくとペースはどれくらい？",
      {
        skipRouter: true,
        defaultYear: 2026,
        llm: {
          complete: async (_sys, user) => {
            userPrompt = user;
            return "現行男子2区は2.855kmなので、9:00は約3:09/kmです。";
          },
        },
      },
    );
    expect(result.kind).toBe("answered");
    expect(userPrompt).toMatch(/3:09\.1\/km|2\.855km/);
    expect(userPrompt).toMatch(/ペース|男子2区/);
    expect(userPrompt).not.toMatch(/コーチに直接聞いてください/);
    if (result.kind === "answered") {
      expect(
        result.sources.some(
          (s) =>
            s.includes("aragyoku-overview") ||
            s.includes("aragyoku-ekiden-distance-definitions"),
        ),
      ).toBe(true);
    }
  });

  it("puts arato-tamana team records for 金栗PROJECT 所属記録", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion("金栗PROJECTの3000m記録一覧を教えて", {
      skipRouter: true,
      defaultYear: 2026,
      llm: {
        complete: async (_sys, user) => {
          userPrompt = user;
          return "金栗PROJECTの3000m記録です。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    expect(userPrompt).toMatch(/金栗PROJECT|3000m/);
    expect(userPrompt).not.toMatch(/コーチに直接聞いてください/);
    if (result.kind === "answered") {
      expect(result.sources.some((s) => s.includes("arato-tamana-teams"))).toBe(true);
    }
  });

  it("offline empty retrieval tells user to ask the coach", async () => {
    const result = await answerQuestion("存在しない架空の大会XYZの詳細は？", {
      retrieve: () => [],
      llm: null,
      skipRouter: true,
      kgQuery: () => ({
        question: "x",
        matched_nodes: [],
        refs: [],
        corpus_sources: [],
      }),
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("コーチに直接聞いてください。");
      expect(result.text).not.toContain("コーパスに情報がありません");
    }
  });

  it("system prompt instructs missing-info coach message", async () => {
    let systemPrompt = "";
    await answerQuestion("荒玉駅伝で岱明は何位？", {
      retrieve: fakeRetrieve,
      skipRouter: true,
      kgQuery: () => ({
        question: "x",
        matched_nodes: [],
        refs: [],
        corpus_sources: ["ekiden-ocr/2024-男子.md"],
      }),
      llm: {
        complete: async (sys) => {
          systemPrompt = sys;
          return "ok";
        },
      },
    });
    expect(systemPrompt).toContain("コーチに直接聞いてください。");
    expect(systemPrompt).not.toContain("コーパスに情報がありません");
  });
});
