import { describe, expect, it, beforeEach } from "vitest";
import {
  loadAragyokuCourseImages,
  resetAragyokuCourseImageCache,
  selectAragyokuCourseImages,
  toLineCourseImageMessages,
} from "../src/domain/aragyokuCourseImages.js";
import {
  ARAGYOKU_COURSE_IMAGE_DRIVE_URL,
  isAragyokuCourseImageQuestion,
  isAragyokuCourseVideoQuestion,
  matchCannedAnswer,
} from "../src/domain/canned.js";
import { answerQuestion } from "../src/domain/answer.js";
import { buildReplyMessages } from "../src/line/webhook.js";
import { formatForLine } from "../src/line/format.js";

describe("isAragyokuCourseImageQuestion", () => {
  it("detects course image / diagram questions", () => {
    expect(isAragyokuCourseImageQuestion("荒玉駅伝のコースの画像は？")).toBe(true);
    expect(isAragyokuCourseImageQuestion("コース図を見せて")).toBe(true);
    expect(isAragyokuCourseImageQuestion("共通ポイントの図")).toBe(true);
    expect(isAragyokuCourseImageQuestion("荒玉のコース図解")).toBe(true);
  });

  it("rejects video / other-meet / board questions", () => {
    expect(isAragyokuCourseImageQuestion("荒玉駅伝のコース動画は？")).toBe(false);
    expect(isAragyokuCourseVideoQuestion("荒玉駅伝のコース動画は？")).toBe(true);
    expect(isAragyokuCourseImageQuestion("ジュニア駅伝のコースの画像")).toBe(false);
    expect(isAragyokuCourseImageQuestion("なごみのコース図")).toBe(false);
    expect(isAragyokuCourseImageQuestion("2025年荒玉男子の結果ボード")).toBe(false);
    expect(isAragyokuCourseImageQuestion("去年の優勝校は？")).toBe(false);
  });
});

describe("selectAragyokuCourseImages", () => {
  beforeEach(() => {
    resetAragyokuCourseImageCache();
  });

  it("returns one catalog image for course-image questions", () => {
    const imgs = selectAragyokuCourseImages("荒玉駅伝のコースの画像は？");
    expect(imgs).toHaveLength(1);
    expect(imgs[0]?.id).toBe("common-points");
    expect(imgs[0]?.originalContentUrl).toMatch(/^https:\/\/lh3\.googleusercontent\.com\/d\//);
  });

  it("returns empty for non-matching questions", () => {
    expect(selectAragyokuCourseImages("荒玉駅伝のコース動画は？")).toEqual([]);
    expect(selectAragyokuCourseImages("2025年荒玉男子の結果は？")).toEqual([]);
  });

  it("loads catalog from disk", () => {
    const all = loadAragyokuCourseImages();
    expect(all.length).toBeGreaterThanOrEqual(1);
    expect(all[0]?.driveFileId).toBeTruthy();
  });
});

describe("canned aragyoku course images", () => {
  it("returns Drive URL canned answer", () => {
    const canned = matchCannedAnswer("荒玉駅伝のコースの画像は？");
    expect(canned?.id).toBe("aragyoku-course-images");
    expect(canned?.text).toContain(ARAGYOKU_COURSE_IMAGE_DRIVE_URL);
    expect(canned?.text).toMatch(/共通ポイント|図解/);
  });

  it("keeps bare Drive URL after formatForLine", () => {
    const canned = matchCannedAnswer("コース図を見せて");
    expect(canned).not.toBeNull();
    const formatted = formatForLine(canned!.text);
    expect(formatted).toContain(ARAGYOKU_COURSE_IMAGE_DRIVE_URL);
  });

  it("prefers video canned when both cues appear", () => {
    const canned = matchCannedAnswer("荒玉のコース画像と動画");
    expect(canned?.id).toBe("aragyoku-course-videos");
  });

  it("answerQuestion short-circuits without LLM", async () => {
    let llmCalled = false;
    const result = await answerQuestion("荒玉駅伝のコースの画像は？", {
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
      expect(result.text).toContain(ARAGYOKU_COURSE_IMAGE_DRIVE_URL);
      expect(result.sources).toEqual(["canned:aragyoku-course-images"]);
    }
  });
});

describe("buildReplyMessages course image", () => {
  it("appends one image for course diagram question", () => {
    const messages = buildReplyMessages("図解案内", "荒玉駅伝のコースの画像は？", {
      attachBoardImages: true,
      attachCourseImages: true,
      attachCourseVideos: true,
    });
    expect(messages[0]).toMatchObject({ type: "text" });
    const images = messages.filter((m) => m.type === "image");
    expect(images).toHaveLength(1);
    if (images[0]?.type === "image") {
      expect(images[0].originalContentUrl).toMatch(/^https:\/\/lh3\.googleusercontent\.com\/d\//);
      expect(images[0].previewImageUrl).toMatch(/=w480$/);
    }
    expect(messages.filter((m) => m.type === "video")).toHaveLength(0);
  });

  it("skips course image when attachCourseImages is false", () => {
    const messages = buildReplyMessages("案内", "荒玉駅伝のコースの画像は？", {
      attachCourseImages: false,
    });
    expect(messages.every((m) => m.type === "text")).toBe(true);
  });

  it("toLineCourseImageMessages maps URLs", () => {
    const msgs = toLineCourseImageMessages([
      {
        id: "common-points",
        title: "t",
        driveFileId: "abc",
        driveUrl: "https://drive.google.com/file/d/abc/view",
        imagePath: "x.png",
        originalContentUrl: "https://lh3.googleusercontent.com/d/abc",
        previewImageUrl: "https://lh3.googleusercontent.com/d/abc=w480",
      },
    ]);
    expect(msgs).toEqual([
      {
        type: "image",
        originalContentUrl: "https://lh3.googleusercontent.com/d/abc",
        previewImageUrl: "https://lh3.googleusercontent.com/d/abc=w480",
      },
    ]);
  });
});
