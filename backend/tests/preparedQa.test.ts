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

  it("loads prepared catalog entries", () => {
    const entries = loadPreparedQa();
    expect(entries.length).toBeGreaterThanOrEqual(17000);
    expect(entries[0]?.id).toBeTruthy();
    expect(entries[0]?.answer.length).toBeGreaterThan(10);
  });

  it("covers diversified bulk ids beyond the first 100", () => {
    const entries = loadPreparedQa();
    const ids = new Set(entries.map((e) => e.id));
    expect(ids.has("aragyoku-what")).toBe(true);
    // bulk generators + aragyoku athlete SB bank + knowledge cover
    expect([...ids].some((id) => id.startsWith("sb-2026-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("sb-2012-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("cal-"))).toBe(true);
    expect([...ids].some((id) => id.includes("-leg"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("meet-result-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("records-team-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("profile-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("topic-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("sb-school-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("records-athlete-2026-"))).toBe(true);
    expect(ids.has("records-athlete-2026-南本幸治郎")).toBe(true);
    expect([...ids].some((id) => id.startsWith("race-2026-"))).toBe(true);
    expect([...ids].some((id) => id.startsWith("aragyoku-career-"))).toBe(true);
    expect([...ids].some((id) => id.endsWith("-order"))).toBe(true);
  });

  it("covers knowledge topics via prepared answers", () => {
    const cases: Array<[string, RegExp]> = [
      ["南関中の記録一覧は？", /南関中/],
      ["松野凛空のプロフィールは？", /岱明中/],
      ["岱明の1500m最速は誰？", /4:22\.33|松野凛空/],
      ["玉名郡ナイター中・長距離記録会の結果は？", /4:29\.8|松野凛空/],
      ["選手記録はどこで分かる？", /自己ベスト|選手名/],
      ["南本幸治郎の今年度の全ての記録", /5:23\.50|kumariku\.org/],
    ];
    for (const [q, re] of cases) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit, q).toBeTruthy();
      expect(hit?.text, q).toMatch(re);
      expect(hit?.text, q).not.toContain("コーチに直接聞いてください");
    }
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
    // 年なしは今年度（2026）の PDF/フォルダ案内
    expect(hit?.id).toBe("junior-2026-pdf");
    expect(hit?.text).toMatch(/2026|drive\.google\.com/);
  });

  it("hits relative-year wording", () => {
    const hit = matchPreparedAnswer("去年の荒玉男子優勝は誰？", { defaultYear: 2026 });
    expect(hit?.id).toBe("aragyoku-2025-men-winner");
    expect(hit?.text).toContain("菊水");
  });

  it("maps 昨年/去年 junior results to 2025, not 2026", () => {
    for (const q of ["昨年のジュニア駅伝の結果", "去年のジュニア駅伝の結果", "昨年の県ジュニア駅伝の結果は？"]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("junior-2025-result");
      expect(hit?.text, q).toContain("2025");
      expect(hit?.text, q).toContain("36:47");
      expect(hit?.text, q).not.toContain("36:52");
    }
  });

  it("keeps yearless junior result on current-year entry", () => {
    const hit = matchPreparedAnswer("ジュニア駅伝の結果は？", { defaultYear: 2026 });
    expect(hit?.id).toBe("junior-2026-result");
  });

  it("returns current SB for 田上颯人, not stale 4:58.03", () => {
    const hit = matchPreparedAnswer("田上颯人の自己ベストは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("sb-2026-田上颯人");
    expect(hit?.text).toContain("4:37.20");
    expect(hit?.text).toContain("10:24.08");
    expect(hit?.text).toMatch(/大会結果:\s*https?:\/\//);
    expect(hit?.text).not.toContain("4:58.03");
    expect(hit?.text).not.toMatch(/自己ベストは 10:41\.62/);
  });

  it("returns current SB for 松野凛空, not stale 4:36.05", () => {
    const hit = matchPreparedAnswer("松野凛空の自己ベストは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("sb-2026-松野凛空");
    expect(hit?.text).toContain("4:22.33");
    expect(hit?.text).toContain("9:37.84");
    expect(hit?.text).toContain("http://www.kumariku.org/26/26,7,4long/rel015.html");
    expect(hit?.text).toContain("http://www.kumariku.org/26/26,6,13tsushin/rel196.html");
    expect(hit?.text).not.toContain("4:36.05");
  });

  it("includes meet result link on distance-specific SB answers", () => {
    const hit = matchPreparedAnswer("松野凛空の1500mSBは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("sb-2026-松野凛空-1500m");
    expect(hit?.text).toContain("4:22.33");
    expect(hit?.text).toContain("大会結果: http://www.kumariku.org/26/26,7,4long/rel015.html");
  });

  it("lists いだてん岱明 students instead of who-is-daiming", () => {
    for (const q of ["いだてん岱明の生徒一覧", "いだてん岱明の部員は誰？", "岱明中の生徒一覧", "部員名簿は？"]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("roster");
      expect(hit?.text, q).toContain("部員名簿（15名）");
      expect(hit?.text, q).toContain("松野凛空");
      expect(hit?.text, q).toContain("村上咲稀");
      expect(hit?.text, q).toContain("中尾快叶");
      expect(hit?.text, q).not.toContain("玉名市の中学校チーム");
    }
  });

  it("keeps who-is-daiming for team-identity questions", () => {
    const hit = matchPreparedAnswer("いだてん岱明とはどんなチーム？", { defaultYear: 2026 });
    expect(hit?.id).toBe("who-is-daiming");
    expect(hit?.text).toContain("玉名市の中学校チーム");
  });

  it("returns user-friendly 荒玉 calendar answer without repo jargon", () => {
    for (const q of ["荒玉中体連駅伝はいつ？", "荒玉中体連駅伝について教えて"]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.text, q).toContain("2026-10-14");
      expect(hit?.text, q).toContain("drive.google.com/drive/folders/1G8IlaBp9xVmXUynBAjV9ZZQPfFqzj4Yi");
      expect(hit?.text, q).not.toContain("状態:");
      expect(hit?.text, q).not.toContain("input/idaten-corpus");
      expect(hit?.text, q).not.toContain("coverage.csv");
      expect(hit?.text, q).not.toContain("docs/aragyoku");
    }
  });

  it("returns 2026 玉名郡ナイター result with Drive links", () => {
    for (const q of ["玉名郡ナイターの結果", "今年の玉名郡ナイターの結果", "玉名郡ナイター中・長距離記録会の結果"]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("nighter-2026-result");
      expect(hit?.text, q).toContain("drive.google.com/drive/folders/1L9RE6ZK_qmehh9sj7bYK7W5A4wKZU82t");
      expect(hit?.text, q).toContain("docs.google.com/document/d/1k4ka2olKO0ZQPgwTYKxOzMlGaHFjWwAzQsx3uanjMf4");
      expect(hit?.text, q).toContain("4:29.8");
      expect(hit?.text, q).not.toContain("2025年度/0830_玉名郡ナイター");
    }
  });

  it("returns junior detail for 南関中 and 玉名附属中, not coach fallback", () => {
    for (const q of [
      "ジュニア駅伝の南関中と玉名附属中の結果の詳細",
      "ジュニア駅伝の南関と玉名附属の結果の詳細",
      "今年のジュニアで玉名附属はどうだった？",
    ]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("junior-2026-nankan-tamafz-detail");
      expect(hit?.text, q).toContain("35:09");
      expect(hit?.text, q).toContain("43:11");
      expect(hit?.text, q).toContain("44:15");
      expect(hit?.text, q).not.toContain("コーチに直接聞いてください");
    }
  });

  it("treats yearless questions as current fiscal year", () => {
    const nagomi = matchPreparedAnswer("なごみ駅伝はいつ？", { defaultYear: 2026 });
    expect(nagomi?.id).toMatch(/cal-2026-.*なごみ|20260920/);
    expect(nagomi?.text).toContain("2026");
    expect(nagomi?.text).not.toContain("2025-09-21");

    const pdf = matchPreparedAnswer("ジュニア駅伝の結果PDF", { defaultYear: 2026 });
    expect(pdf?.id).toBe("junior-2026-pdf");
    expect(pdf?.text).toContain("2026");

    const tsushin = matchPreparedAnswer("通信陸上はいつ？", { defaultYear: 2026 });
    expect(tsushin?.id).toMatch(/cal-2026-/);
    expect(tsushin?.text).toContain("2026");
  });

  it("returns all season races with meet links for 南本幸治郎", () => {
    for (const q of [
      "南本幸治郎の今年度の全ての記録",
      "南本幸治郎の全ての記録",
      "南本幸治郎の全記録は？",
    ]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("records-athlete-2026-南本幸治郎");
      expect(hit?.text, q).toContain("全5件");
      expect(hit?.text, q).toContain("5:23.50");
      expect(hit?.text, q).toContain("5:43.60");
      expect(hit?.text, q).toMatch(/大会結果:\s*https?:\/\//);
      expect(hit?.text, q).toContain("http://www.kumariku.org/26/26,7,18chutairen/rel075.html");
      // 距離別SB定型へ誤吸しない
      expect(hit?.id, q).not.toMatch(/^sb-/);
    }
  });

  it("returns past-3-year all records for aragyoku athletes", () => {
    const hit = matchPreparedAnswer("松野凛空の過去3年の全ての記録", { defaultYear: 2026 });
    expect(hit?.id).toBe("records-athlete-3y-松野凛空");
    expect(hit?.text).toMatch(/2024|2025|2026/);
    expect(hit?.text).toMatch(/大会結果:\s*https?:\/\//);
  });

  it("returns meet-specific race result with link", () => {
    const hit = matchPreparedAnswer("南本幸治郎の通信陸上の記録は？", { defaultYear: 2026 });
    expect(hit?.id).toBe("race-2026-南本幸治郎-通信陸上");
    expect(hit?.text).toContain("5:44.50");
    expect(hit?.text).toContain("http://www.kumariku.org/26/26,6,13tsushin/rel178.html");
  });

  it("returns aragyoku team order for 岱明 2025 men", () => {
    const hit = matchPreparedAnswer("2025年荒玉駅伝男子の岱明のオーダーは？", { defaultYear: 2026 });
    expect(hit?.id).toBe("aragyoku-2025-男子-team-岱明-order");
    expect(hit?.text).toContain("松野凛空");
    expect(hit?.text).toContain("6位");
  });

  it("returns aragyoku career history", () => {
    const hit = matchPreparedAnswer("松野凛空の荒玉出走歴は？", { defaultYear: 2026 });
    expect(hit?.id).toBe("aragyoku-career-松野凛空");
    expect(hit?.text).toContain("2025年男子・岱明2区");
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
