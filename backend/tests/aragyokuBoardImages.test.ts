import { describe, expect, it, beforeEach } from "vitest";
import {
  detectAragyokuBoardGender,
  resetAragyokuBoardImageCache,
  selectAragyokuBoardImages,
  wantsAragyokuBoardImages,
  type AragyokuBoardImage,
} from "../src/domain/aragyokuBoardImages.js";
import { buildReplyMessages } from "../src/line/webhook.js";

const SAMPLE: AragyokuBoardImage[] = [
  {
    year: 2025,
    gender: "男子",
    driveFileId: "men2025",
    originalContentUrl: "https://lh3.googleusercontent.com/d/men2025",
    previewImageUrl: "https://lh3.googleusercontent.com/d/men2025=w480",
  },
  {
    year: 2025,
    gender: "女子",
    driveFileId: "women2025",
    originalContentUrl: "https://lh3.googleusercontent.com/d/women2025",
    previewImageUrl: "https://lh3.googleusercontent.com/d/women2025=w480",
  },
  {
    year: 2024,
    gender: "男子",
    driveFileId: "men2024",
    originalContentUrl: "https://lh3.googleusercontent.com/d/men2024",
    previewImageUrl: "https://lh3.googleusercontent.com/d/men2024=w480",
  },
];

describe("wantsAragyokuBoardImages", () => {
  it("accepts year + 荒玉 questions", () => {
    expect(wantsAragyokuBoardImages("2025年の荒玉駅伝の区間賞は？")).toBe(true);
    expect(wantsAragyokuBoardImages("去年の荒玉の優勝校は？")).toBe(true);
  });

  it("rejects without year or wrong meet", () => {
    expect(wantsAragyokuBoardImages("荒玉駅伝のコース距離は？")).toBe(false);
    expect(wantsAragyokuBoardImages("2025年のジュニア駅伝は？")).toBe(false);
    expect(wantsAragyokuBoardImages("なごみ駅伝2025の結果は？")).toBe(false);
  });
});

describe("selectAragyokuBoardImages", () => {
  beforeEach(() => {
    resetAragyokuBoardImageCache();
  });

  it("returns men only when 男子 is specified", () => {
    const imgs = selectAragyokuBoardImages("2025年荒玉駅伝男子の区間賞は？", {
      images: SAMPLE,
      defaultYear: 2026,
    });
    expect(imgs).toHaveLength(1);
    expect(imgs[0]?.gender).toBe("男子");
    expect(imgs[0]?.year).toBe(2025);
  });

  it("returns women only when 女子 is specified", () => {
    const imgs = selectAragyokuBoardImages("2025年荒玉女子の優勝校は？", {
      images: SAMPLE,
      defaultYear: 2026,
    });
    expect(imgs).toHaveLength(1);
    expect(imgs[0]?.gender).toBe("女子");
  });

  it("returns both genders (max 2) when year only", () => {
    const imgs = selectAragyokuBoardImages("2025年の荒玉駅伝の結果は？", {
      images: SAMPLE,
      defaultYear: 2026,
    });
    expect(imgs).toHaveLength(2);
    expect(imgs.map((i) => i.gender)).toEqual(["男子", "女子"]);
  });

  it("resolves 去年 to defaultYear-1", () => {
    const imgs = selectAragyokuBoardImages("去年の荒玉駅伝男子の優勝は？", {
      images: SAMPLE,
      defaultYear: 2026,
    });
    expect(imgs).toHaveLength(1);
    expect(imgs[0]?.year).toBe(2025);
    expect(imgs[0]?.gender).toBe("男子");
  });

  it("detectAragyokuBoardGender", () => {
    expect(detectAragyokuBoardGender("男子区間賞")).toBe("男子");
    expect(detectAragyokuBoardGender("女子の部")).toBe("女子");
    expect(detectAragyokuBoardGender("2025年荒玉")).toBe("both");
  });
});

describe("buildReplyMessages", () => {
  it("appends up to 2 image messages after text", () => {
    // Use real catalog for year that exists; stub via env not needed —
    // inject by temporarily relying on select with real file. For isolation,
    // call with a question that won't match catalog if empty — use unit select path.
    const messages = buildReplyMessages("回答本文です。", "2025年の荒玉駅伝の区間賞は？", {
      defaultYear: 2026,
      attachBoardImages: true,
    });
    expect(messages[0]).toMatchObject({ type: "text", text: "回答本文です。" });
    const images = messages.filter((m) => m.type === "image");
    expect(images.length).toBeGreaterThanOrEqual(1);
    expect(images.length).toBeLessThanOrEqual(2);
    for (const img of images) {
      if (img.type === "image") {
        expect(img.originalContentUrl).toMatch(/^https:\/\/lh3\.googleusercontent\.com\/d\//);
        expect(img.previewImageUrl).toMatch(/^https:\/\/lh3\.googleusercontent\.com\/d\//);
      }
    }
  });

  it("skips images when attachBoardImages is false", () => {
    const messages = buildReplyMessages("拒否", "2025年の荒玉駅伝の区間賞は？", {
      attachBoardImages: false,
    });
    expect(messages.every((m) => m.type === "text")).toBe(true);
  });

  it("does not keep the coach fallback when an image is attached", () => {
    const messages = buildReplyMessages("コーチに直接聞いてください。", "2025年の荒玉駅伝の区間賞は？", {
      defaultYear: 2026,
      attachBoardImages: true,
    });
    const text = messages
      .filter((m) => m.type === "text")
      .map((m) => (m.type === "text" ? m.text : ""))
      .join("\n");
    expect(text).not.toContain("コーチに直接聞いてください");
    expect(text).toContain("画像を表示します。");
    expect(messages.some((m) => m.type === "image")).toBe(true);
  });

  it("caps combined image and video attachments at two", () => {
    const messages = buildReplyMessages(
      "回答本文です。",
      "2025年荒玉駅伝3区の結果とコース動画",
      { defaultYear: 2026, attachBoardImages: true, attachCourseVideos: true },
    );
    const media = messages.filter((m) => m.type === "image" || m.type === "video");
    expect(media.length).toBeLessThanOrEqual(2);
  });
});
