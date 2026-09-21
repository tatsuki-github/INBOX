import { describe, expect, it } from "vitest";
import { answerQuestion } from "../src/domain/answer.js";
import { currentDateMention } from "../src/domain/dates.js";
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
      // Prefer not leaking raw corpus path prefixes; digests may cite `*.md` filenames.
      expect(result.text).not.toMatch(/ekiden-ocr\/|calendar\/|\.yaml/);
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

  it("anchors yearless retrieval to the supplied current fiscal year", async () => {
    let retrievedQuery = "";
    const result = await answerQuestion("なごみ駅伝の結果は？", {
      defaultYear: 2026,
      skipRouter: true,
      kgQuery: () => ({
        question: "x",
        matched_nodes: [],
        refs: [],
        corpus_sources: [],
      }),
      retrieve: (query) => {
        retrievedQuery = query;
        return [];
      },
      llm: null,
    });
    expect(result.kind).toBe("offline");
    expect(retrievedQuery).toContain("2026年度");
  });

  it("anchors relative-date retrieval to today's Japan calendar date", async () => {
    let retrievedQuery = "";
    const result = await answerQuestion("今日の予定は？", {
      defaultYear: 2026,
      skipRouter: true,
      kgQuery: () => ({
        question: "x",
        matched_nodes: [],
        refs: [],
        corpus_sources: [],
      }),
      retrieve: (query) => {
        retrievedQuery = query;
        return [];
      },
      llm: null,
    });
    const today = currentDateMention();
    expect(result.kind).toBe("offline");
    expect(retrievedQuery).toContain(today.iso);
    expect(retrievedQuery).toContain(today.mmdd);
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

  it("shows the date and venue for the 玉名市合同練習会 offline", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉名市合同練習会はいつどこ？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2026年9月22日");
      expect(result.text).toContain("おおはまふれあいセンター");
    }
  });

  it("routes a named runner's 区間タイム to the team race digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("天水の山本悠斗の区間タイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources).toContain("out-analysis/aragyoku-teams/天水.md");
      expect(result.text).toContain("8:37");
    }
  });

  it("keeps 荒玉の大会区間記録 on the meet-record board digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝男子2区の大会記録は誰？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("荒木琉偉");
      expect(result.text).toContain("8:41");
    }
  });

  it("prioritizes the named team's digest for a year/team/leg question", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("有明中の荒玉2024男子1区は誰？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/有明.md");
      expect(result.text).toContain("米村和真");
      expect(result.text).toContain("9:01");
    }
  });

  it("routes compact year/gender winner totals to the winners digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025女子優勝の玉名の総合タイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("41:58");
      expect(result.text).toContain("玉名");
    }
  });

  it("routes team year-over-year questions to the focus analysis digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("有明女子は前年比でどうなった？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_2024_2025_focus_teams.md");
      expect(result.text).toContain("-33.00s");
      expect(result.text).toContain("47:24");
    }
  });

  it("routes current 荒玉 leg-distance questions to the distance overview", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉の現行男子4区の距離は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-overview.md");
      expect(result.text).toContain("4区");
      expect(result.text).toContain("3km");
    }
  });

  it("includes the parent LINE digest for なごみ駅伝集合場所", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の集合場所は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources.some((s) => s.includes("line-chats/daiming-parents"))).toBe(true);
      expect(result.text).toContain("三加和公民館");
    }
  });

  it("shows the named team's rank for a year/gender total query", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉駅伝男子の岱明は何位？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/岱明.md");
      expect(result.text).toContain("6位");
      expect(result.text).toContain("59:08");
    }
  });

  it("does not confuse 玉名付属中 with the 玉名 team digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉名付属中の女子は2025年荒玉で何位？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/玉高附属.md");
      expect(result.text).toContain("10位");
    }
  });

  it("starts a year/gender winner preview at the matching result sentence", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2024年荒玉男子の優勝は南関でタイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2024年荒玉駅伝男子の優勝校は");
      expect(result.text).toContain("56:38");
    }
  });

  it("starts a year/gender leg-record preview at the requested section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉男子3区の大会区間記録保持者は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("2025年荒玉駅伝男子の3区大会区間記録");
      expect(result.text).toContain("亀井遼希");
    }
  });

  it("starts a board total-record preview at the requested year", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年ボードの男子総合大会記録は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("2025年荒玉駅伝男子のボード上部・総合大会記録");
      expect(result.text).toContain("56:38");
    }
  });

  it("keeps year-over-year shortening on the named team's digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("岱明男子は2024から2025で何分短縮した？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/岱明.md");
      expect(result.text).toContain("-6:07.00");
      expect(result.text).toContain("59:08");
    }
  });

  it("resolves a compact school/year/gender rank question to the team digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉高附属女子2025は何位？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/玉高附属.md");
      expect(result.text).toContain("10位");
    }
  });

  it("classifies a compact school/year/gender 順位 question as 荒玉", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("有明男子2025の順位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/有明.md");
      expect(result.text).toContain("12位");
    }
  });

  it("prioritizes the team digest for a named runner's yearless team phrase", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("山本悠斗の荒玉2024区間タイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/天水.md");
      expect(result.text).toContain("9:45");
    }
  });

  it("handles the short なごみ集合場所 phrasing", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみの集合場所どこ？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources.some((s) => s.includes("line-chats/daiming-parents"))).toBe(true);
      expect(result.text).toContain("和水町三加和公民館");
    }
  });

  it("finds the explicit year in a compact winner-time question", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉2025男子の優勝タイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は");
      expect(result.text).toContain("56:17");
    }
  });

  it("defaults an underspecified 荒玉 distance question to the current course", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子4区は何キロ？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("4区");
      expect(result.text).toContain("3km");
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

  it("resolves 明日の玉名市練習会 to the exact dated practice note", async () => {
    resetRetrieverCache();
    resetKgCache();
    let systemPrompt = "";
    let userPrompt = "";
    const result = await answerQuestion("明日の玉名市練習会の予定は？", {
      skipRouter: true,
      defaultYear: 2026,
      now: new Date("2026-09-21T00:00:00+09:00"),
      llm: {
        complete: async (system, user) => {
          systemPrompt = system;
          userPrompt = user;
          return "2026年9月22日（火祝）は午前8時集合、おおはまふれあいセンターです。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    expect(systemPrompt).toContain("日付解釈");
    expect(userPrompt).toContain("日付解釈: 2026-09-22");
    expect(userPrompt).toContain("2026年9月22日（火祝）");
    expect(userPrompt).toContain("おおはまふれあいセンター");
    expect(userPrompt).not.toContain("phase-5-6");
    if (result.kind === "answered") {
      expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
    }
  });

  it("adds primary result PDF links for 昨日のなごみ駅伝の結果", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("昨日のなごみ駅伝の結果のPDF渡して", {
      skipRouter: true,
      defaultYear: 2026,
      now: new Date("2026-09-21T00:00:00+09:00"),
      llm: { complete: async () => "結果を確認しました。コーチに直接聞いてください。" },
    });
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.text).toContain("一次資料:");
      expect(result.text).toContain("女子成績表PDF");
      expect(result.text).toContain("男子成績表PDF");
      expect(result.text).toContain(
        "https://drive.google.com/file/d/1Z1NPn0w-6O18CrKcv0keqymhv39N9Ydi/view",
      );
      expect(result.text).toContain(
        "https://drive.google.com/file/d/1Yyv2TLVAfSjSE296Q6xrEMm0J2QbQF21/view",
      );
      expect(result.text).not.toContain("github.com");
      expect(result.text).not.toContain("コーチに直接聞いてください");
      expect(result.text).toContain("drive.google.com/drive/folders/1k-zW0irJ-OjDjqQwUQLZIs4C6PfuR211");
    }
  });

  it("does not add the coach fallback when PDF links answer the request", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("昨日のなごみ駅伝の結果のPDF渡して", {
      skipRouter: true,
      llm: null,
      retrieve: () => [],
      defaultYear: 2026,
      now: new Date("2026-09-21T00:00:00+09:00"),
      kgQuery: () => ({
        question: "昨日のなごみ駅伝の結果のPDF渡して",
        matched_nodes: [],
        refs: [],
        corpus_sources: [],
      }),
    });
    expect(result.kind).toBe("offline");
    expect(result.text).not.toContain("コーチに直接聞いてください");
    expect(result.text).toContain("女子成績表PDF");
    expect(result.text).toContain("男子成績表PDF");
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

  it("covers women runners-up for 過去5年の優勝・準優勝", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion(
      "女子の荒玉駅伝の過去5年間の優勝校、準優勝校は？",
      {
        skipRouter: true,
        defaultYear: 2026,
        llm: {
          complete: async (_sys, user) => {
            userPrompt = user;
            return (
              "2021荒尾四/荒尾三、2022長洲/荒尾四、2023荒尾三/荒尾四、" +
              "2024南関/荒尾三、2025玉名/南関です。"
            );
          },
        },
      },
    );
    expect(result.kind).toBe("answered");
    expect(userPrompt).toMatch(/優勝/);
    expect(userPrompt).toMatch(/準優勝/);
    // All five years' runners-up must appear in context (not just winners)
    expect(userPrompt).toMatch(/荒尾三/);
    expect(userPrompt).toMatch(/荒尾四/);
    expect(userPrompt).toMatch(/南関/);
    expect(userPrompt).toMatch(/長洲/);
    expect(userPrompt).toMatch(/玉名/);
    if (result.kind === "answered") {
      expect(result.sources.some((s) => s.includes("winners-by-year"))).toBe(true);
    }
  });

  it("offline preview for 優勝・準優勝 includes runners-up table", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion(
      "女子の荒玉駅伝の過去5年間の優勝校、準優勝校は？",
      {
        skipRouter: true,
        defaultYear: 2026,
        llm: null,
      },
    );
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/準優勝/);
      expect(result.text).toMatch(/荒尾三|荒尾四|南関/);
      expect(result.sources.some((s) => s.includes("winners-by-year"))).toBe(true);
    }
  });

  it("puts leg awards digest for 区間賞 questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion("2025年の荒玉駅伝の区間賞の名前と学年は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: {
        complete: async (_sys, user) => {
          userPrompt = user;
          return "2025年男子の区間賞は江口大尊（3年）ほかです。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    expect(userPrompt).toMatch(/区間賞/);
    expect(userPrompt).toMatch(/江口大尊/);
    expect(userPrompt).toMatch(/学年|3/);
    if (result.kind === "answered") {
      expect(result.sources[0]).toMatch(/leg_awards/);
      expect(result.sources.every((s) => !s.includes("meet_records"))).toBe(true);
      expect(result.sources.every((s) => !s.includes("focus_teams"))).toBe(true);
    }
  });

  it("offline preview for 区間賞 hits names and grades", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年の荒玉駅伝の区間賞の名前と学年は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/江口大尊|山本悠斗|草野瑠唯/);
      expect(result.text).toMatch(/3|1|2/);
      expect(result.sources.some((s) => s.includes("leg_awards"))).toBe(true);
    }
  });

  it("puts all-teams average pace for 〇位の平均ペース questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion("荒玉駅伝男子1位の平均ペースは？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: {
        complete: async (_sys, user) => {
          userPrompt = user;
          return "男子1位の歴代平均ペースは約3:13/kmです。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    expect(userPrompt).toMatch(/平均ペース/);
    expect(userPrompt).toMatch(/1位/);
    expect(userPrompt).toMatch(/3:\d{2}/);
    if (result.kind === "answered") {
      expect(
        result.sources.some((s) => s.includes("all_teams_average_pace") || s.includes("top6_historical")),
      ).toBe(true);
    }
  });

  it("offline preview for rank average pace hits the digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("女子3位の平均ペースは？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/平均ペース/);
      expect(result.text).toMatch(/3位/);
      expect(
        result.sources.some((s) => s.includes("all_teams_average_pace") || s.includes("average_pace")),
      ).toBe(true);
    }
  });

  it("narrows to winners digest for 優勝校を全て提示して", async () => {
    resetRetrieverCache();
    resetKgCache();
    let sysPrompt = "";
    let userPrompt = "";
    const result = await answerQuestion("荒玉駅伝の過去の優勝校を全て提示して", {
      skipRouter: true,
      defaultYear: 2026,
      llm: {
        complete: async (sys, user) => {
          sysPrompt = sys;
          userPrompt = user;
          return "男子・女子の年度別優勝校を列挙します。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.sources[0]).toMatch(/winners-by-year/);
      expect(result.sources.every((s) => !s.includes("analysis-ocr"))).toBe(true);
      expect(result.sources.every((s) => !s.includes("all_teams_average_pace"))).toBe(true);
    }
    expect(sysPrompt).toMatch(/完全列挙|漏れなく列挙/);
    expect(userPrompt).toMatch(/完全提示|省略せず列挙/);
    expect(userPrompt).toMatch(/優勝/);
    // Multiple years should be in context (full digest coverage)
    expect(userPrompt).toMatch(/2012|2013|2024|2025/);
  });

  it("offline exhaustive winners list uses winners-by-year not focus analysis", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の優勝校を全部出して", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toMatch(/winners-by-year/);
      expect(result.text).toMatch(/優勝/);
      expect(result.text).toMatch(/男子|女子/);
    }
  });

  it("exhaustive 平均ペース covers year section from all-teams digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion(
      "2025年荒玉男子の全チームの平均ペースを全て提示して",
      {
        skipRouter: true,
        defaultYear: 2026,
        llm: {
          complete: async (_sys, user) => {
            userPrompt = user;
            return "2025年男子の全チーム平均ペースを列挙します。";
          },
        },
      },
    );
    expect(result.kind).toBe("answered");
    if (result.kind === "answered") {
      expect(result.sources[0]).toMatch(/all_teams_average_pace/);
    }
    expect(userPrompt).toMatch(/2025/);
    expect(userPrompt).toMatch(/平均ペース/);
    // Several team rows, not just one
    const paceHits = userPrompt.match(/\d:\d{2}\.\d\/km/g) ?? [];
    expect(paceHits.length).toBeGreaterThanOrEqual(5);
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

  it("answers なごみ 岱明男子1区 from 2026 order list, not 金栗駅伝", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の岱明男子1区は誰？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/山本\s*哲瑠/);
      expect(result.text).not.toContain("コーチに直接聞いてください");
      expect(result.sources.some((s) => /なごみ.*区間オーダーリスト/.test(s))).toBe(true);
      expect(result.sources[0]).not.toMatch(/金栗駅伝|金栗記念|\.meta\.json/);
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

  it("puts 2024-2025 focus analysis for 岱明・天水 questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion(
      "2024年と2025年の荒玉駅伝で岱明男子と天水はどうだった？",
      {
        skipRouter: true,
        defaultYear: 2026,
        llm: {
          complete: async (_sys, user) => {
            userPrompt = user;
            return "岱明男子は15位から6位へ上昇、天水は2区区間新がありました。";
          },
        },
      },
    );
    expect(result.kind).toBe("answered");
    expect(userPrompt).toMatch(/59:08|6位|山本悠斗|8:37/);
    expect(userPrompt).not.toMatch(/コーチに直接聞いてください/);
    if (result.kind === "answered") {
      expect(
        result.sources.some(
          (s) =>
            s.includes("aragyoku_2024_2025_focus_teams") ||
            s.includes("aragyoku-teams/岱明") ||
            s.includes("aragyoku-teams/天水"),
        ),
      ).toBe(true);
    }
  });

  it("answers 「案浦竜士は何区を走った」from aragyoku team digest not スタートリスト", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("案浦竜士は何区を走った？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("案浦竜士");
      expect(result.text).toMatch(/6区/);
      expect(result.text).not.toContain("コーチに直接聞いてください");
      expect(result.sources.some((s) => /aragyoku-teams\/岱明|focus_teams/.test(s))).toBe(true);
      expect(result.sources[0]).not.toMatch(/スタートリスト|通信陸上/);
    }
  });

  it("answers 「佐藤央琉は何区」from 岱明 digest as 4区", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("佐藤央琉は何区？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("佐藤央琉");
      expect(result.text).toMatch(/4区/);
      expect(result.sources.some((s) => /aragyoku-teams\/岱明|focus_teams/.test(s))).toBe(true);
    }
  });

  it("answers short 「2025年岱明男子5区は誰」from team digest not LINE", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年岱明男子5区は誰？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("山本哲瑠");
      expect(result.text).not.toContain("コーチに直接聞いてください");
      expect(result.sources.some((s) => /aragyoku-teams\/岱明|focus_teams/.test(s))).toBe(
        true,
      );
      expect(result.sources[0]).not.toMatch(/line-chats/);
    }
  });

  it("answers 女子800m 上位3人平均 from school ranking not SB CSV", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("女子800mで岱明の上位3人平均は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/2:28/);
      expect(result.text).not.toContain("コーチに直接聞いてください");
      expect(result.sources.some((s) => s.includes("women_800m_1500m_pb_school_ranking"))).toBe(
        true,
      );
      expect(result.sources[0]).not.toMatch(/^sb\//);
    }
  });

  it("answers 優勝との差 from focus analysis not meet_records board", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年岱明男子の優勝との差は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/2:51/);
      expect(result.text).not.toContain("コーチに直接聞いてください");
      expect(
        result.sources.some(
          (s) => s.includes("aragyoku_2024_2025_focus_teams") || s.includes("aragyoku-teams/岱明"),
        ),
      ).toBe(true);
    }
  });

  it("still puts line-chats for 地点分担 / 2.855 questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉の地点分担で土山はどこ？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/D地点/);
      expect(result.sources.some((s) => s.includes("line-chats"))).toBe(true);
    }
  });

  it("puts line-chats context for 銀マット / 合同練習 questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion("岱明の銀マットのサイズは？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: {
        complete: async (_sys, user) => {
          userPrompt = user;
          return "長さ180cm、幅60cmでも可です。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    expect(userPrompt).toMatch(/180cm|銀マット/);
    if (result.kind === "answered") {
      expect(result.sources.some((s) => s.includes("line-chats"))).toBe(true);
    }
  });

  it("puts arita-taisho line-chats for 有田の補強・分割走 questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    let userPrompt = "";
    const result = await answerQuestion("有田先輩の補強や分割走の考え方は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: {
        complete: async (_sys, user) => {
          userPrompt = user;
          return "手押し車・犬歩きと分割走を優先する、とのメモです。";
        },
      },
    });
    expect(result.kind).toBe("answered");
    expect(userPrompt).toMatch(/手押し車|犬歩き|分割走/);
    if (result.kind === "answered") {
      expect(result.sources.some((s) => s.includes("arita-taisho"))).toBe(true);
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

  it("answers 高田麻那 from digest without 高田麻由", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("高田麻那の記録", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/5:21\.76|11:05\.84|文徳/);
      expect(result.text).not.toContain("コーチに直接聞いてください");
      // Digest may mention 麻由 as “別人” — forbid presenting 麻由 as the subject athlete row
      expect(result.text).not.toMatch(/高田麻由,岱明|高田麻由（選手）|^[^\n]*高田麻由[^\n]*自己ベスト/m);
      expect(
        result.sources.some(
          (s) => s.includes("takada-mana") || s.includes("SBデータベース"),
        ),
      ).toBe(true);
      expect(result.sources.some((s) => s.includes("takada-mana"))).toBe(true);
    }
  });

  it("answers 荒玉 2位まで school counts from top2 digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の2位までに入ったことがある学校と回数", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/玉名/);
      expect(result.text).toMatch(/15/);
      expect(result.text).toMatch(/荒尾三|菊水/);
      expect(result.text).not.toContain("コーチに直接聞いてください");
      expect(result.sources.some((s) => s.includes("top2_finish_counts"))).toBe(true);
    }
  });

  it("answers 荒玉地区 3000m fastest from ranking digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉地区で3000mが1番速いのは？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/隈部侑成|8:54\.61/);
      expect(result.text).not.toContain("コーチに直接聞いてください");
    }
  });

  it("answers 男子1500m SB top20 from individual ranking digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("今年の荒玉地区の男子1500mSBランキングトップ20", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/隈部侑成/);
      expect(result.text).toMatch(/4:11\.60/);
      expect(result.text).not.toContain("コーチに直接聞いてください");
    }
  });

  it("answers ATRC full records from team digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("ATRCの選手の全記録", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toMatch(/ATRC|800m|1500m/);
      expect(result.text).not.toContain("コーチに直接聞いてください");
      expect(result.sources.some((s) => /ATRC/.test(s))).toBe(true);
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
