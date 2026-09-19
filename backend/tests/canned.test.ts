import { describe, expect, it } from "vitest";
import {
  ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL,
  ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL,
  isAragyokuCourseVideoQuestion,
  matchCannedAnswer,
} from "../src/domain/canned.js";
import { formatForLine } from "../src/line/format.js";
import { answerQuestion } from "../src/domain/answer.js";
import { buildReplyMessages } from "../src/line/webhook.js";

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
