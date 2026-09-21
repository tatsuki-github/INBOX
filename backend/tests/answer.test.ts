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

  it("starts a 合同練習会 fee answer at the fee row", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("合同練習会の会費は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
      expect(result.text).toContain("会費: 学生 1,000円／一般 2,000円");
      expect(result.text).toContain("学生 1,000円／一般 2,000円");
      expect(result.text).not.toContain("申込締切");
      expect(result.text).not.toContain("熊日駅伝に向けた親睦");
    }
  });

  it("recognizes 参加料 as a 合同練習会 fee alias", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("合同練習会の参加料は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("学生 1,000円／一般 2,000円");
      expect(result.text).not.toContain("熊日駅伝に向けた親睦");
    }
  });

  it("recognizes 費用 as a 合同練習会 fee alias", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("合同練習会の費用は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("学生 1,000円／一般 2,000円");
      expect(result.text).not.toContain("熊日駅伝に向けた親睦");
    }
  });

  it("routes a title-only 玉名市練習会 venue question to its dated note", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉名市練習会の会場は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("drive-text/練習/玉名市練習会/2026-09-22.md");
      expect(result.text).toContain("おおはまふれあいセンター");
      expect(result.text).not.toContain("3＋加速200×2");
    }
  });

  it("keeps title-only 合同練習会 time answers on the current practice note", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉名市合同練習会の集合時間は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
      expect(result.text).toContain("午前 8:00");
      expect(result.text).not.toContain("3km 山本哲瑠");
      expect(result.text).not.toContain("お別れ会");
    }
  });

  it("uses the current practice note for 合同練習会 without city wording", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("合同練習会の集合時刻は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources).toEqual(["drive-text/練習/玉名市練習会/2026-09-22.md"]);
      expect(result.text).toContain("午前 8:00");
      expect(result.text).not.toContain("2026-01");
    }
  });

  it("starts 岱明朝練 weekday answers at the staff schedule section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("岱明の朝練は何曜日？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/line-chats/daiming-staff.md");
      expect(result.text).toContain("朝練のリズム");
      expect(result.text).toContain("月・火・木・金");
      expect(result.text).not.toContain("2025-09: 女子結果");
    }
  });

  it("answers 岱明のトラック周長 from the practice source", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("岱明のトラック1周は何メートル？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("practice/daiming-practice-menus-kpace.md");
      expect(result.text).toContain("560m");
      expect(result.text).not.toContain("練習メニューの記録なし");
    }
  });

  it("starts named 地点分担 answers at the staff assignment table", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("地点分担で熊澤先生の場所は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/line-chats/daiming-staff.md");
      expect(result.text).toContain("地点分担（荒玉）");
      expect(result.text).toContain("熊澤=C地点");
      expect(result.text).not.toContain("2026-01");
    }
  });

  it("recognizes 何地点 as a 地点分担 alias", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("熊澤先生は何地点？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
      expect(result.text).toContain("地点分担（荒玉）");
      expect(result.text).toContain("熊澤=C地点");
      expect(result.text).not.toContain("ジュニア駅伝");
    }
  });

  it("recognizes short 姓名の地点は phrasing for assignment lookup", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("熊澤先生の地点は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
      expect(result.text).toContain("地点分担（荒玉）");
      expect(result.text).toContain("熊澤=C地点");
      expect(result.text).not.toContain("2026-01");
    }
  });

  it("starts お別れ会 schedule answers at the farewell section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("お別れ会いつやる？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/line-chats/daiming-staff.md");
      expect(result.text).toContain("金栗駅伝・お別れ会");
      expect(result.text).toContain("3/15 12:30–15:00");
      expect(result.text).not.toContain("2026-01");
    }
  });

  it("routes お別れ会の時間 phrasing to the same farewell section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("お別れ会の時間は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/line-chats/daiming-staff.md");
      expect(result.text).toContain("金栗駅伝・お別れ会");
      expect(result.text).toContain("3/15 12:30–15:00");
      expect(result.text).not.toContain("2026-09");
    }
  });

  it("routes お別れ会の予定 phrasing to the farewell section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("お別れ会の予定は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
      expect(result.text).toContain("金栗駅伝・お別れ会");
      expect(result.text).toContain("3/15 12:30–15:00");
      expect(result.text).not.toContain("ジュニア駅伝");
    }
  });

  it("recognizes 時刻 as an お別れ会 schedule alias", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("お別れ会の時刻は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("3/15 12:30–15:00");
      expect(result.text).not.toContain("ジュニア駅伝（2026-09）");
    }
  });

  it("starts 銀マット size answers at the parent size summary", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("銀マット何センチ？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/line-chats/daiming-parents.md");
      expect(result.text).toContain("銀マット");
      expect(result.text).toContain("180cm");
      expect(result.text).toContain("60cm");
      expect(result.text).toContain("15mm");
      expect(result.text).not.toContain("保護者グループ）運用メモ");
    }
  });

  it("routes 銀マットの厚み phrasing to the parent size summary", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("銀マットの厚みは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/line-chats/daiming-parents.md");
      expect(result.text).toContain("### 銀マット");
      expect(result.text).toContain("15mm");
      expect(result.text).not.toContain("保護者グループ）運用メモ");
    }
  });

  it("recognizes 寸法 as a 銀マット size alias", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("銀マットの寸法は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("60×180×15mm");
      expect(result.text).not.toContain("保護者グループ）運用メモ");
    }
  });

  it("starts 2区と5区 distance answers at the staff distance summary", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2区と5区の距離は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources).toEqual(["out-analysis/line-chats/daiming-staff.md"]);
      expect(result.text).toContain("2区と5区の距離");
      expect(result.text).toContain("2.855km");
      expect(result.text).not.toContain("仲間達）運用メモ");
    }
  });

  it("starts なごみ集合場所 answers at the parent meet section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の集合場所は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources).toEqual(["out-analysis/line-chats/daiming-parents.md"]);
      expect(result.text).toContain("### なごみ駅伝");
      expect(result.text).toContain("和水町三加和公民館");
      expect(result.text).toContain("7時集合");
      expect(result.text).not.toContain("保護者グループ）運用メモ");
    }
  });

  it("keeps an unavailable 金栗駅伝 venue answer on the 2026 canonical note", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("金栗駅伝の会場は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources).toEqual(["drive-text/大会/2026年度/0315_金栗駅伝/概要.md"]);
      expect(result.text).toContain("金栗駅伝");
      expect(result.text).toContain("正本資料には記載がありません");
      expect(result.text).not.toContain("朝練のリズム");
    }
  });

  it("keeps 金栗駅伝 date answers on the 2026 canonical note", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("金栗駅伝の開催日は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources).toEqual(["drive-text/大会/2026年度/0315_金栗駅伝/概要.md"]);
      expect(result.text).toContain("2026-03-15");
      expect(result.text).not.toContain("ジュニア駅伝");
    }
  });

  it("formats a short 金栗駅伝 date question as a calendar date", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("金栗駅伝はいつ？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2026年3月15日");
    }
  });

  it("formats a 金栗駅伝 month question from the canonical date", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("金栗駅伝の開催月は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toContain("0315_金栗駅伝/概要.md");
      expect(result.text).toContain("2026年3月15日");
      expect(result.text).toContain("3/15");
      expect(result.text).not.toContain("ジュニア駅伝");
    }
  });

  it("routes explicit year/gender winner-school questions to winners-by-year", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉女子優勝校は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝女子の優勝校");
      expect(result.text).toContain("玉名");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("focuses an explicit-year winner-school answer on its result sentence", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2024年荒玉男子の優勝校は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2024年荒玉駅伝男子の優勝校は「南関」");
      expect(result.text).not.toContain("2025年荒玉駅伝男子");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("lists every team for an explicit-year result-list question", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉女子の結果一覧は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/transcripts/2025-女子.json");
      expect(result.text).toContain("1位 玉名 41:58");
      expect(result.text).toContain("8位 荒尾海陽 46:16");
      expect(result.text).toContain("15位 天水 51:29");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("lists every team when a year-gender question asks for overall ranks", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉女子の順位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/transcripts/2025-女子.json");
      expect(result.text).toContain("1位 玉名 41:58");
      expect(result.text).toContain("15位 天水 51:29");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("defaults a yearless result-list question to the latest transcript year", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉女子の結果一覧は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/transcripts/2025-女子.json");
      expect(result.text).toContain("2025年荒玉駅伝女子の結果");
      expect(result.text).toContain("15位 天水 51:29");
      expect(result.text).not.toContain("2026年度中学");
    }
  });

  it("treats a plain gendered meet-result question as a full result lookup", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝女子の結果は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/transcripts/2025-女子.json");
      expect(result.text).toContain("1位 玉名 41:58");
      expect(result.text).toContain("15位 天水 51:29");
      expect(result.text).not.toContain("優勝校は「玉名」");
    }
  });

  it("treats 優勝チーム as a winner-school lookup", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉男子の優勝チームは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("defaults a genderless 優勝チーム question to the latest men and women results", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の優勝チームは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝女子の優勝校は「玉名」");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」");
      expect(result.text).not.toContain("2024年荒玉駅伝");
    }
  });

  it("answers an unqualified 優勝校 question for both genders", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の優勝校は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年男子優勝校: 菊水（56:17）");
      expect(result.text).toContain("2025年女子優勝校: 玉名（41:58）");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("answers an unqualified winner-time question for both genders", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の優勝タイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年女子優勝タイム: 41:58");
      expect(result.text).toContain("2025年男子優勝タイム: 56:17");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("answers an unqualified runner-up question for both genders", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の準優勝は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年女子準優勝校: 南関");
      expect(result.text).toContain("2025年男子準優勝校: 玉陵");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("answers an unqualified first-place question for both genders", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の1位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年女子1位: 玉名");
      expect(result.text).toContain("2025年男子1位: 菊水");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("answers an unqualified third-place question for both genders", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の3位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年男子3位: 玉高附属（58:37）");
      expect(result.text).toContain("2025年女子3位: 玉東（44:24）");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("answers an unqualified fourth-place question for both genders", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の4位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年男子4位: 長洲（58:49）");
      expect(result.text).toContain("2025年女子4位: 長洲（44:33）");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("answers an unqualified fifth-place question for both genders", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の5位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年男子5位: 荒尾三（58:58）");
      expect(result.text).toContain("2025年女子5位: 荒尾三（44:56）");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("answers a gendered nagomi rank question from the official result table", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ男子の2位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2026年なごみ男子2位: 金栗PROJECT A（38:49）");
      expect(result.text).not.toContain("区間オーダー");
    }
  });

  it("lists all historical winners for a gender-specific 歴代 question", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉女子の歴代優勝校は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2012年荒玉駅伝女子の優勝校は「玉名」");
      expect(result.text).toContain("2025年荒玉駅伝女子の優勝校は「玉名」");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("lists both genders for a genderless historical winner question", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の歴代優勝校は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2012年荒玉駅伝女子の優勝校は「玉名」");
      expect(result.text).toContain("2012年荒玉駅伝男子の優勝校は「玉名」");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」");
    }
  });

  it("routes generic gender/leg record phrasing to the meet-record board", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝女子2区の記録は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("女子の2区大会区間記録");
      expect(result.text).toContain("井上智世");
      expect(result.text).not.toContain("区間賞・区間順位");
    }
  });

  it("starts explicit year/leg record answers at the requested board row", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉駅伝女子2区の記録保持者は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("2025年荒玉駅伝女子の2区大会区間記録");
      expect(result.text).toContain("井上智世");
      expect(result.text).not.toContain("2025年荒玉駅伝女子の1区大会区間記録");
    }
  });

  it("starts omitted-meet gender/leg record answers at the board row", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("女子4区の大会区間記録の保持者は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("荒玉駅伝女子の4区大会区間記録");
      expect(result.text).toContain("浦浜実里");
      expect(result.text).toContain("6:42");
      expect(result.text).not.toContain("正本は各年 transcript");
    }
  });

  it("defaults a short gender/leg record-holder question to the latest board row", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("女子4区の記録保持者は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("浦浜実里");
      expect(result.text).toContain("6:42");
    }
  });

  it("finds a named historical holder on the meet-record board", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("一瀬弘樹の男子1区大会区間記録は何年ボード？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("2012年荒玉駅伝男子の1区大会区間記録");
      expect(result.text).toContain("12:28");
      expect(result.text).not.toContain("米村和真");
    }
  });

  it("keeps a named holder's record answer to one board sentence", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("永尾海斗の大会区間記録は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("永尾海斗");
      expect(result.text).toContain("9:38");
      expect(result.text).not.toContain("2024年荒玉駅伝女子");
    }
  });

  it("routes a named board-record alias to the holder row", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("一瀬弘樹のボード記録は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("2012年荒玉駅伝男子の1区大会区間記録");
      expect(result.text).toContain("12:28");
      expect(result.text).not.toContain("正本は各年 transcript");
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
      expect(result.text).toContain("2025年2区 山本悠斗の区間タイムは8:37。");
      expect(result.text).not.toContain("# 天水 荒玉駅伝 歴代結果");
    }
  });

  it("uses the latest year for a yearless named runner split query", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("村上咲稀の区間タイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/岱明.md");
      expect(result.text).toContain("2025年1区 村上咲稀の区間タイムは11:02。");
      expect(result.text).not.toContain("2024年4区 村上咲稀の区間タイムは7:50。");
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

  it("routes explicit year/gender runner-up questions to winners-by-year", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉男子の2位チームは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は");
      expect(result.text).toContain("準優勝校は「玉陵」");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("focuses an explicit-year 2位 alias on the runner-up result", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2024年荒玉男子の2位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2024年荒玉駅伝男子の優勝校は「南関」");
      expect(result.text).toContain("準優勝校は「玉高附属」");
      expect(result.text).not.toContain("2025年荒玉駅伝男子");
    }
  });

  it("routes latest winner questions to the winners digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子の最新優勝校は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」");
      expect(result.text).not.toContain("大会記録・区間記録");
    }
  });

  it("defaults a yearless winner-school question to the latest result", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子の優勝校は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」");
      expect(result.text).not.toContain("大会記録・区間記録");
    }
  });

  it("defaults a yearless 1位 question to the latest winner", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子の1位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」");
      expect(result.text).not.toContain("2026年度荒玉男子.pdf");
    }
  });

  it("focuses an explicit-year 1位 question on the winner row", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉女子の1位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝女子の優勝校は「玉名」");
      expect(result.text).not.toContain("2024年荒玉駅伝");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("routes yearless 荒玉 total-time questions to the latest result", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子の総合タイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」（総合 56:17）");
      expect(result.text).not.toContain("2026年度荒玉男子.pdf");
    }
  });

  it("routes yearless 荒玉 winner-time questions to the latest result", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子の優勝タイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」（総合 56:17）");
      expect(result.text).not.toContain("大会記録・区間記録");
    }
  });

  it("keeps an explicit historical winner-time question on its requested year", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2012年荒玉駅伝男子の優勝タイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2012年荒玉駅伝男子の優勝校は「玉名」（総合 63:47）");
      expect(result.text).not.toContain("2025年荒玉駅伝男子の優勝校は");
    }
  });

  it("routes yearless 荒玉 runner-up questions to the latest result", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子の準優勝校は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」");
      expect(result.text).toContain("準優勝校は「玉陵」");
      expect(result.text).not.toContain("大会記録・区間記録");
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
      expect(result.text).toContain("現行男子4区は3km。");
      expect(result.text).not.toContain("| 1区 | 3km |");
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

  it("recognizes 何着 as a team-rank alias", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉男子で岱明は何着？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/岱明.md");
      expect(result.text).toContain("岱明は6位");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("keeps combined rank and total-time questions on the team digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉駅伝男子の岱明は何位？総合タイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/岱明.md");
      expect(result.text).toContain("6位");
      expect(result.text).toContain("59:08");
      expect(result.text).not.toContain("2025年荒玉駅伝男子の優勝校は");
      expect(result.text).not.toContain("2024年荒玉駅伝男子 岱明は");
    }
  });

  it("defaults a yearless team-rank question to the latest team result", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("岱明男子の順位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/岱明.md");
      expect(result.text).toContain("2025年荒玉駅伝男子 岱明は6位・総合59:08");
      expect(result.text).not.toContain("2017年荒玉駅伝女子 岱明は");
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

  it("recognizes separated total-record phrasing", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2024年荒玉男子総合の大会記録は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("2024年荒玉駅伝男子のボード上部・総合大会記録");
      expect(result.text).toContain("56:38");
      expect(result.text).toContain("南関中");
    }
  });

  it("recognizes total-record phrasing without 大会", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉男子の総合記録は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("2025年荒玉駅伝男子のボード上部・総合大会記録");
      expect(result.text).toContain("56:38");
      expect(result.text).not.toContain("6区大会区間記録");
    }
  });

  it("defaults a yearless 荒玉 total-record question to the latest board row", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子の総合記録は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("2025年荒玉駅伝男子のボード上部・総合大会記録は56:38");
      expect(result.text).toContain("南関中");
      expect(result.text).not.toContain("2026年度荒玉男子.pdf");
    }
  });

  it("recognizes omitted-meet board record phrasing", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("男子4区のボード記録は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("荒玉駅伝男子の4区大会区間記録");
      expect(result.text).toContain("9:13");
      expect(result.text).toContain("田崎空汰");
      expect(result.text).not.toContain("正本は各年 transcript");
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

  it("answers a year-to-year seconds-faster question concisely", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("有明女子は2024から2025で何秒速くなった？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_2024_2025_focus_teams.md");
      expect(result.text).toContain("有明女子は33.00秒短縮（2025年のほうが速い）。");
      expect(result.text).not.toContain("順位差+1");
    }
  });

  it("routes combined total-time and winner-margin phrasing to focus analysis", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年岱明男子総合タイムと優勝差は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_2024_2025_focus_teams.md");
      expect(result.text).toContain("59:08");
      expect(result.text).toContain("2:51");
      expect(result.text).not.toContain("女子・直近5年");
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
      expect(result.text).toContain("2024年1区 山本悠斗の区間タイムは9:45。");
      expect(result.text).not.toContain("2025年荒玉駅伝男子");
    }
  });

  it("focuses an explicit 荒玉 year/team/leg athlete question", async () => {
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
      expect(result.text).toContain("2024年1区 米村和真の区間タイムは9:01。");
      expect(result.text).not.toContain("2024年荒玉駅伝男子 有明は11位");
    }
  });

  it("recognizes a team/leg question that omits the meet name", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("菊水の2025男子1区は誰？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/菊水.md");
      expect(result.text).toContain("2025年1区 松浦眞大の区間タイムは9:30。");
      expect(result.text).not.toContain("優勝校");
    }
  });

  it("includes the split rank for a team leg question", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年岱明男子5区は誰で区間順は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_2024_2025_focus_teams.md");
      expect(result.text).toContain("2025年5区 山本哲瑠（区間順2位・9:37）。");
      expect(result.text).not.toContain("# 岱明 荒玉駅伝 歴代結果");
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

  it("focuses composite winner-time phrasing on the requested result sentence", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2024年荒玉男子の優勝は南関でタイムは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2024年荒玉駅伝男子の優勝校は「南関」（総合 56:38）");
      expect(result.text).not.toContain("女子・直近5年");
    }
  });

  it("focuses compact winner total-time phrasing on the requested result sentence", async () => {
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
      expect(result.text).toContain("2025年荒玉駅伝女子の優勝校は「玉名」（総合 41:58）");
      expect(result.text).not.toContain("2024年荒玉駅伝男子の優勝校は");
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

  it("recognizes 長さ as an 荒玉 leg-distance question", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("今の荒玉男子4区の長さは？", {
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

  it("recognizes compact year/gender/leg record phrasing", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉男子2区記録は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("2区大会区間記録は8:41");
      expect(result.text).toContain("荒木琉偉");
    }
  });

  it("defaults an unqualified year/gender/leg record to 荒玉", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025男子3区の大会記録は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("9:24");
      expect(result.text).toContain("亀井遼希");
    }
  });

  it("defaults an unqualified gender/leg record to the meet-record board", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("女子2区の大会記録だれ？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_meet_records.md");
      expect(result.text).toContain("井上智世");
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

  it("answers yearless relative winner questions with only the latest gender rows", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("去年の荒玉駅伝の優勝校は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2025年荒玉駅伝女子の優勝校は「玉名」");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」");
      expect(result.text).not.toContain("2024年荒玉駅伝");
      expect(result.text).not.toContain("深掘り分析");
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

  it("focuses an explicit year/gender 区間賞 question on that section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉女子の区間賞は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_leg_awards.md");
      expect(result.text).toContain("2025年女子");
      expect(result.text).toContain("区間賞");
      expect(result.text).not.toContain("2025年男子");
    }
  });

  it("treats 区間1位 as a leg-award lookup", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉女子の区間1位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_leg_awards.md");
      expect(result.text).toContain("2025年女子");
      expect(result.text).toContain("坂井優花");
      expect(result.text).not.toContain("2025年男子");
    }
  });

  it("treats a short 区間2位 expression as a leg-rank lookup", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉女子の区間2位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_leg_awards.md");
      expect(result.text).toContain("2025年女子");
      expect(result.text).toContain("川原芽吹");
      expect(result.text).not.toContain("2025年男子");
    }
  });

  it("defaults a yearless gendered 区間賞 question to the latest section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子の区間賞は誰？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_leg_awards.md");
      expect(result.text).toContain("2025年男子");
      expect(result.text).toContain("江口大尊");
      expect(result.text).not.toContain("2024年男子");
    }
  });

  it("focuses a requested leg-rank section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉男子の1区区間順位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_leg_awards.md");
      expect(result.text).toContain("2025年荒玉駅伝男子1区の区間1位は江口大尊");
      expect(result.text).toContain("区間2位は山戸耀輝");
      expect(result.text).not.toContain("2025年荒玉駅伝男子2区の区間1位");
    }
  });

  it("defaults an unqualified leg-rank question to the latest matching section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子1区の区間順位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_leg_awards.md");
      expect(result.text).toContain("2025年荒玉駅伝男子1区の区間1位は江口大尊");
      expect(result.text).not.toContain("2024年荒玉駅伝男子1区");
      expect(result.text).not.toContain("2025年荒玉駅伝男子2区");
    }
  });

  it("keeps a natural の1区 phrasing on the women's leg-rank section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2025年荒玉女子の1区区間順位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_leg_awards.md");
      expect(result.text).toContain("2025年荒玉駅伝女子1区の区間1位");
      expect(result.text).not.toContain("2025年荒玉駅伝男子");
    }
  });

  it("defaults a gendered leg-rank list to the latest full section", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子の区間順位は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_leg_awards.md");
      expect(result.text).toContain("2025年男子・区間別上位");
      expect(result.text).toContain("2025年荒玉駅伝男子1区の区間1位");
      expect(result.text).not.toContain("2024年男子・区間別上位");
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

  it("answers the なごみ開催日 from the canonical schedule", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の開催日は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2026年9月20日");
      expect(result.sources[0]).toContain("当日スケジュール.md");
      expect(result.text).not.toContain("予想");
      expect(result.text).not.toContain("2025年度");
    }
  });

  it("answers the なごみ会場 from the canonical program", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の会場は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("和水町三加和公民館");
      expect(result.sources[0]).toContain("プログラム.pdf.md");
      expect(result.sources.every((source) => !source.includes("daiming-parents"))).toBe(true);
    }
  });

  it("states when 金栗駅伝 results are not recorded", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("金栗駅伝の結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("結果・順位はまだ記載されていません");
      expect(result.sources[0]).toBe("drive-text/大会/2026年度/0315_金栗駅伝/概要.md");
      expect(result.sources.every((source) => !source.includes("2025年度"))).toBe(true);
    }
  });

  it("routes なごみ優勝質問 to actual result tables", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の優勝校は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("NJAC");
      expect(result.text).toContain("金栗PROJECT A");
      expect(result.sources[0]).toContain("男子成績表.md");
      expect(result.sources.every((source) => !source.includes("SB予想"))).toBe(true);
    }
  });

  it("summarizes the requested なごみ gender result table", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の女子結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2026年なごみ駅伝女子の結果");
      expect(result.text).toContain("1位 金栗PROJECT A 26:55");
      expect(result.text).toContain("23位 湯浦 37:18");
      expect(result.sources[0]).toContain("女子成績表.md");
      expect(result.text).not.toContain("原本:");
    }
  });

  it("summarizes both genders for an unqualified なごみ result query", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2026年なごみ駅伝の結果");
      expect(result.text).toContain("男子:");
      expect(result.text).toContain("女子:");
      expect(result.text).toContain("NJAC");
      expect(result.text).toContain("金栗PROJECT A");
      expect(result.sources[0]).toContain("男子成績表.md");
      expect(result.sources[1]).toContain("女子成績表.md");
    }
  });

  it("answers なごみ区間1位 from actual results, not the order list", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の男子1区の区間1位は誰？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("德永蓮翔");
      expect(result.text).toContain("9:24");
      expect(result.sources[0]).toContain("男子成績表.md");
      expect(result.sources.every((source) => !source.includes("区間オーダーリスト"))).toBe(true);
    }
  });

  it("keeps a なごみ区間順位 list query as a result-table view", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の男子2区の区間順位は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("男子成績表");
      expect(result.text).toContain("NJAC");
      expect(result.text).not.toContain("区間1位:");
      expect(result.sources[0]).toContain("男子成績表.md");
    }
  });

  it("routes a dated 岱明 result question to the team digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("岱明の2025年結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年荒玉駅伝男子 岱明は6位");
      expect(result.text).toContain("2025年荒玉駅伝女子 岱明は7位");
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/岱明.md");
      expect(result.sources.every((source) => !source.includes("daiming-staff"))).toBe(true);
    }
  });

  it("defaults an unqualified team result question to the latest year", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("岱明の結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年荒玉駅伝男子 岱明は6位・総合59:08");
      expect(result.text).toContain("2025年荒玉駅伝女子 岱明は7位・総合45:22");
      expect(result.text).not.toContain("2024年荒玉駅伝");
    }
  });

  it("supports additional 荒玉 teams in unqualified result questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒尾三の結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年荒玉駅伝男子 荒尾三は5位・総合58:58");
      expect(result.text).toContain("2025年荒玉駅伝女子 荒尾三は5位・総合44:56");
      expect(result.sources[0]).toContain("aragyoku-teams/荒尾三.md");
    }
  });

  it("routes a dated 荒尾四 result to its team digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒尾四の2025年結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年荒玉駅伝男子 荒尾四は10位・総合61:15");
      expect(result.sources[0]).toContain("aragyoku-teams/荒尾四.md");
    }
  });

  it("supports 玉名 in unqualified team result questions", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉名の結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年荒玉駅伝男子 玉名は9位・総合60:52");
      expect(result.text).toContain("2025年荒玉駅伝女子 玉名は1位・総合41:58");
    }
  });

  it("filters dated team results by the requested gender", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("岱明の2025女子結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年荒玉駅伝女子 岱明は7位・総合45:22");
      expect(result.text).not.toContain("2025年荒玉駅伝男子 岱明は6位");
    }
  });

  it("answers 岱明の区間順位 from the latest team table", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("岱明男子の区間順位は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("倉田裕斗");
      expect(result.text).toContain("9:32");
      expect(result.text).toContain("案浦竜士");
      expect(result.sources[0]).toBe("out-analysis/aragyoku-teams/岱明.md");
    }
  });

  it("summarizes a named athlete self-best row", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("村上咲稀の自己ベストは？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("村上咲稀（岱明中）の自己ベスト");
      expect(result.text).toContain("800m 2:23.45");
      expect(result.text).toContain("1500m 5:05.65");
      expect(result.text).not.toContain("名前,所属,性別,カテゴリー");
    }
  });

  it("answers the 荒玉駅伝開催日 from the calendar", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の開催日は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2026年開催日は10月14日");
      expect(result.text).toContain("予備日10月15日");
      expect(result.sources[0]).toBe("calendar/events.daiming.yaml");
      expect(result.text).not.toContain("深掘り分析");
    }
  });

  it("accepts the short 荒玉開催日 phrasing", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉の開催日は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2026年開催日は10月14日");
      expect(result.sources[0]).toBe("calendar/events.daiming.yaml");
    }
  });

  it("routes the short 荒玉会場 phrasing to one calendar answer", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉の会場は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text.match(/会場は、手元の正本資料では確認できません/g)?.length).toBe(1);
      expect(result.sources[0]).toBe("calendar/events.daiming.yaml");
    }
  });

  it("routes an unqualified 荒玉結果 question to both result transcripts", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("2025年荒玉駅伝の結果");
      expect(result.text).toContain("男子:");
      expect(result.text).toContain("女子:");
      expect(result.text).toContain("菊水");
      expect(result.text).toContain("玉名");
      expect(result.sources[0]).toBe("aragyoku/transcripts/2025-男子.json");
    }
  });

  it("does not invent an 荒玉駅伝 venue when the source omits it", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉駅伝の会場は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("会場は、手元の正本資料では確認できません");
      expect(result.text).toContain("10月14日");
      expect(result.sources[0]).toBe("calendar/events.daiming.yaml");
      expect(result.text).not.toContain("和水町三加和公民館");
    }
  });

  it("states when the 2026 荒玉 result is not recorded yet", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2026年荒玉駅伝の結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("結果・順位はまだ記載されていません");
      expect(result.sources[0]).toContain("1014-1015_荒玉中体連駅伝/概要.md");
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

  it("routes a yearless なごみ順位 question to actual result tables", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("なごみ駅伝の順位は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe(
        "drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/男子成績表.md",
      );
      expect(result.text).toContain("男子成績表");
      expect(result.text).toContain("NJAC");
      expect(result.text).not.toContain("SB予想");
    }
  });

  it("extracts the requested なごみ team result from the actual table", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2026年なごみ駅伝岱明男子の結果は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("岱明A");
      expect(result.text).toContain("18位");
      expect(result.text).toContain("42:39");
      expect(result.text).toContain("岱明B");
      expect(result.text).not.toContain("予実比較");
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

  it("calculates a leg pace from the canonical distance", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子1区を10分で走るとペースは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.text).toContain("男子1区（3km）を10分で走るペースは、約3:20/km");
      expect(result.text).not.toContain("歴代平均ペース");
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

  it("answers 男子1500m 上位4人平均順位 from the school ranking", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("男子1500m上位4人平均で岱明は何位？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/2026_men_1500m_pb_school_ranking.md");
      expect(result.text).toContain("5位");
      expect(result.text).toContain("4:30.05");
      expect(result.text).not.toContain("荒玉駅伝");
    }
  });

  it("answers a school-only 女子800m ranking question from the school ranking", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("女子800mPB学校別で荒尾三は何位？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/2026_women_800m_1500m_pb_school_ranking.md");
      expect(result.text).toContain("2位");
      expect(result.text).toContain("2:27.99");
      expect(result.text).not.toContain("荒玉駅伝");
    }
  });

  it("routes a generic 女子800m ranking query away from raw SB CSV", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("女子800mのランキングは？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/2026_women_800m_1500m_pb_school_ranking.md");
      expect(result.text).toContain("800m・上位3人平均");
      expect(result.text).not.toContain("名前,所属,性別,カテゴリー");
    }
  });

  it("routes a 女子1500m ranking query to the women's ranking digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("女子1500mのランキングは？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/2026_women_800m_1500m_pb_school_ranking.md");
      expect(result.text).toContain("女子800m／1500m PB 学校別ランキング");
      expect(result.text).not.toContain("男子1500m SB 個人ランキング");
    }
  });

  it("extracts the fastest women 800m PB from the canonical ranking", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("2026年女子800mの最速は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/2026_women_800m_1500m_pb_school_ranking.md");
      expect(result.text).toContain("村上咲稀（岱明中）の2:20.11");
      expect(result.text).not.toContain("名前,所属,性別,カテゴリー");
    }
  });

  it("extracts the fastest men 3000m SB from the ranking digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("男子3000mで一番速いのは？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/2026_aragyoku_men_3000m_sb_ranking.md");
      expect(result.text).toContain("隈部侑成（金栗PROJECT）の8:54.61");
      expect(result.text).not.toContain("荒尾三中");
    }
  });

  it("answers an unqualified men 1500m PB question with the fastest record", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("男子1500mの自己ベストは？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md");
      expect(result.text).toContain("隈部侑成（金栗PROJECT）の4:11.60");
      expect(result.text).not.toContain("トップ20");
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

  it("summarizes the most frequent 荒玉男子 top-two schools", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子で総合2位以内回数が多い学校は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/aragyoku_top2_finish_counts.md");
      expect(result.text).toContain("荒玉男子の総合2位以内回数最多は玉名・菊水（各6回）。");
      expect(result.text).not.toContain("2025年荒玉駅伝男子の優勝校");
    }
  });

  it("finds the historical 荒玉男子 runner-up year for a named school", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉高附属が荒玉男子で2位になったのは何年？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("玉高附属が荒玉男子で2位（準優勝）になった年は2024年です。");
      expect(result.text).not.toContain("2025年荒玉駅伝男子の優勝校");
    }
  });

  it("lists historical runner-ups instead of defaulting to the latest row", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉男子の歴代準優勝校は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("2012年荒玉駅伝男子の優勝校は「玉名」");
      expect(result.text).toContain("2025年荒玉駅伝男子の優勝校は「菊水」");
      expect(result.text).not.toMatch(/^.*2025年荒玉駅伝男子.*\n?1\. .*2025年荒玉駅伝男子/);
    }
  });

  it("reverse-looks up the years a named school won", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("玉名が優勝した年は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("玉名が荒玉駅伝で優勝した年:");
      expect(result.text).toContain("2012年（女子）");
      expect(result.text).toContain("2012年（男子）");
      expect(result.text).toContain("2025年（女子）");
      expect(result.text).not.toContain("中学選手権");
    }
  });

  it("lets 歴代 phrasing reverse-lookup a named winner too", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("菊水の歴代優勝年は？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("aragyoku/winners-by-year.md");
      expect(result.text).toContain("菊水が荒玉駅伝で優勝した年:");
      expect(result.text).toContain("2014年（男子）");
      expect(result.text).toContain("2025年（男子）");
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

  it("routes 一番速い男子1500m phrasing to the individual ranking", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("男子1500mで一番速いのは？", {
      llm: null,
      skipRouter: true,
      defaultYear: 2026,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md");
      expect(result.text).toContain("隈部侑成");
      expect(result.text).toContain("4:11.60");
      expect(result.text).not.toContain("一番瀬大聖");
    }
  });

  it("keeps named 1500m SB rank questions on the individual ranking digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("荒玉地区男子1500mSBで隈部侑成は何位？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/2026_aragyoku_men_1500m_sb_individual_top20.md");
      expect(result.text).toContain("1 | 隈部侑成");
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

  it("keeps a named team's full-record list on its team digest", async () => {
    resetRetrieverCache();
    resetKgCache();
    const result = await answerQuestion("南関中所属選手の全記録一覧は？", {
      skipRouter: true,
      defaultYear: 2026,
      llm: null,
    });
    expect(result.kind).toBe("offline");
    if (result.kind === "offline") {
      expect(result.sources[0]).toBe("out-analysis/arato-tamana-teams/南関中.md");
      expect(result.text).toContain("内田健太");
      expect(result.text).toContain("2:14.99");
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
