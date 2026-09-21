import { describe, expect, it } from "vitest";
import {
  ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL,
  ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL,
  buildHelpExamplesText,
  isAragyokuCourseVideoQuestion,
  isHelpOrExampleQuestion,
  matchCannedAnswer,
} from "../src/domain/canned.js";
import { formatForLine } from "../src/line/format.js";
import { answerQuestion } from "../src/domain/answer.js";
import { buildReplyMessages } from "../src/line/webhook.js";

describe("canned help / example questions", () => {
  it("detects help and example intents", () => {
    expect(isHelpOrExampleQuestion("使い方")).toBe(true);
    expect(isHelpOrExampleQuestion("ヘルプ")).toBe(true);
    expect(isHelpOrExampleQuestion("help")).toBe(true);
    expect(isHelpOrExampleQuestion("質問例を教えて")).toBe(true);
    expect(isHelpOrExampleQuestion("このボットは何ができる？")).toBe(true);
    expect(isHelpOrExampleQuestion("何が聞ける？")).toBe(true);
    expect(isHelpOrExampleQuestion("メニュー")).toBe(true);
    expect(isHelpOrExampleQuestion("荒玉男子の優勝は？")).toBe(false);
    expect(isHelpOrExampleQuestion("荒玉のコース動画は？")).toBe(false);
  });

  it("returns help canned without LLM", async () => {
    let llmCalled = false;
    const result = await answerQuestion("このボットは何ができる？", {
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
      expect(result.sources).toEqual(["canned:help-examples"]);
      expect(result.text).toMatch(/練習|大会|記録|いだてん/);
      expect(result.text).toContain("荒玉");
    }
  });

  it("help text has no personal names and is Aragyoku-majority", () => {
    const text = buildHelpExamplesText();
    // Known athlete names that must not appear in help examples
    for (const name of ["今村昇磨", "石川隼", "佐藤央琉", "案浦竜士", "松野凛空"]) {
      expect(text).not.toContain(name);
    }
    expect(text).toContain("荒玉男子1区を10分で走るとペースは？");
    expect(text).not.toContain("12分");
    expect(text).not.toContain("銀マット");
    expect(text).not.toContain("9/20の練習予定");
    expect(text).toContain("○○/〇〇の大会予定は？");
    expect(text).not.toMatch(/20(?:0\d|1\d|2[0-3])/); // 直近2年（2024–）以外の西暦年を入れない
    expect(text).toContain("2024年荒玉男子の優勝チームは？");
    expect(text).toContain("2025年");
    const exampleLines = text
      .split("\n")
      .filter((l) => l.startsWith("・"))
      .map((l) => l.slice(1));
    expect(exampleLines.length).toBeGreaterThanOrEqual(12);
    const aragyokuCount = exampleLines.filter((l) => /荒玉/.test(l)).length;
    expect(aragyokuCount).toBeGreaterThan(exampleLines.length / 2);

    // App coverage cues (no personal names)
    for (const cue of [
      "区間距離",
      "優勝",
      "何位",
      "区間賞",
      "大会記録",
      "ペース",
      "前年比",
      "コース動画",
      "結果ボード",
      "なごみ",
      "大会予定",
      "結果URL",
      "自己ベスト",
      "対象外",
    ]) {
      expect(text).toContain(cue);
    }
  });

  it("matchCannedAnswer prefers help over course-video phrasing in help intents", () => {
    const canned = matchCannedAnswer("使い方");
    expect(canned?.id).toBe("help-examples");
  });
});

describe("canned aragyoku course videos", () => {
  it("detects course-video questions", () => {
    expect(isAragyokuCourseVideoQuestion("荒玉駅伝のコース動画は？")).toBe(true);
    expect(isAragyokuCourseVideoQuestion("コース動画どこ？")).toBe(true);
    expect(isAragyokuCourseVideoQuestion("駅伝のコース映像を見たい")).toBe(true);
    expect(isAragyokuCourseVideoQuestion("去年の優勝校は？")).toBe(false);
    expect(isAragyokuCourseVideoQuestion("荒玉駅伝で岱明は何位？")).toBe(false);
    expect(isAragyokuCourseVideoQuestion("ジュニア駅伝のコース動画は？")).toBe(false);
    expect(isAragyokuCourseVideoQuestion("なごみ駅伝のコース映像")).toBe(false);
  });

  it("returns gender-specific Drive folder URL", () => {
    const women = matchCannedAnswer("荒玉女子のコース動画を教えて");
    expect(women?.id).toBe("aragyoku-course-videos");
    expect(women?.text).toContain(ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL);
    expect(women?.text).not.toContain(ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL);

    const men = matchCannedAnswer("荒玉男子のコース動画");
    expect(men?.text).toContain(ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL);
    expect(men?.text).not.toContain(ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL);
  });

  it("lists both folders when gender omitted", () => {
    const canned = matchCannedAnswer("荒玉のコース動画を教えて");
    expect(canned?.text).toContain(ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL);
    expect(canned?.text).toContain(ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL);
  });

  it("keeps bare Drive URL after formatForLine", () => {
    const canned = matchCannedAnswer("女子コース動画は？");
    expect(canned).not.toBeNull();
    const formatted = formatForLine(canned!.text);
    expect(formatted).toContain(ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL);
  });

  it("answerQuestion short-circuits without LLM", async () => {
    let llmCalled = false;
    const result = await answerQuestion("荒玉駅伝のコース動画はどこ？", {
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
      expect(result.text).toContain(ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL);
      expect(result.text).toContain(ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL);
      expect(result.sources).toEqual(["canned:aragyoku-course-videos"]);
    }
  });
});

describe("buildReplyMessages course video", () => {
  it("appends one video for women 3ku course question", () => {
    const messages = buildReplyMessages(
      "フォルダ案内",
      "荒玉 女子 3区 コース動画",
      { attachBoardImages: true, attachCourseVideos: true },
    );
    expect(messages[0]).toMatchObject({ type: "text" });
    const videos = messages.filter((m) => m.type === "video");
    expect(videos).toHaveLength(1);
    if (videos[0]?.type === "video") {
      expect(videos[0].originalContentUrl).toContain("export=download");
      expect(videos[0].previewImageUrl).toMatch(/^https:\/\/lh3\.googleusercontent\.com\/d\//);
    }
  });

  it("skips video when full-course is not lineEligible", () => {
    const messages = buildReplyMessages("案内", "荒玉 男子 コース動画", {
      attachCourseVideos: true,
    });
    expect(messages.filter((m) => m.type === "video")).toHaveLength(0);
  });

  it("skips video when attachCourseVideos is false", () => {
    const messages = buildReplyMessages("案内", "荒玉女子3区コース動画", {
      attachCourseVideos: false,
    });
    expect(messages.every((m) => m.type === "text")).toBe(true);
  });
});
