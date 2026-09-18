import { describe, expect, it } from "vitest";
import {
  ARAGYOKU_COURSE_VIDEO_FOLDER_URL,
  isAragyokuCourseVideoQuestion,
  matchCannedAnswer,
} from "../src/domain/canned.js";
import { formatForLine } from "../src/line/format.js";
import { answerQuestion } from "../src/domain/answer.js";

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

  it("returns the Drive folder URL", () => {
    const canned = matchCannedAnswer("荒玉のコース動画を教えて");
    expect(canned?.id).toBe("aragyoku-course-videos");
    expect(canned?.text).toContain(ARAGYOKU_COURSE_VIDEO_FOLDER_URL);
  });

  it("keeps bare Drive URL after formatForLine", () => {
    const canned = matchCannedAnswer("コース動画は？");
    expect(canned).not.toBeNull();
    const formatted = formatForLine(canned!.text);
    expect(formatted).toContain(ARAGYOKU_COURSE_VIDEO_FOLDER_URL);
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
      expect(result.text).toContain(ARAGYOKU_COURSE_VIDEO_FOLDER_URL);
      expect(result.sources).toEqual(["canned:aragyoku-course-videos"]);
    }
  });
});
