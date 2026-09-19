import { describe, expect, it, beforeEach } from "vitest";
import {
  detectCourseVideoLeg,
  resetAragyokuCourseVideoCache,
  resolveCourseVideoGender,
  selectAragyokuCourseVideos,
  toLineVideoMessages,
  type AragyokuCourseVideo,
} from "../src/domain/aragyokuCourseVideos.js";
import { loadAragyokuCourseVideos } from "../src/domain/aragyokuCourseVideos.js";

const SAMPLE: AragyokuCourseVideo[] = [
  {
    gender: "女子",
    leg: null,
    kind: "full",
    driveFileId: "women-full",
    title: "女子全区間",
    fileSizeBytes: 151_000_000,
    folderId: "women-folder",
    originalContentUrl: "https://drive.usercontent.google.com/download?id=women-full&export=download",
    previewImageUrl: "https://lh3.googleusercontent.com/d/women-full",
    lineEligible: false,
  },
  {
    gender: "女子",
    leg: 3,
    kind: "leg",
    driveFileId: "women-3",
    title: "女子3区",
    fileSizeBytes: 25_000_000,
    folderId: "women-folder",
    originalContentUrl: "https://drive.usercontent.google.com/download?id=women-3&export=download",
    previewImageUrl: "https://lh3.googleusercontent.com/d/women-3",
    lineEligible: true,
  },
  {
    gender: "男子",
    leg: null,
    kind: "full",
    driveFileId: "men-full",
    title: "男子全区間",
    fileSizeBytes: 229_000_000,
    folderId: "men-folder",
    originalContentUrl: "https://drive.usercontent.google.com/download?id=men-full&export=download",
    previewImageUrl: "https://lh3.googleusercontent.com/d/men-full",
    lineEligible: false,
  },
  {
    gender: "男子",
    leg: 1,
    kind: "leg",
    driveFileId: "men-1",
    title: "男子1区",
    fileSizeBytes: 40_000_000,
    folderId: "men-folder",
    originalContentUrl: "https://drive.usercontent.google.com/download?id=men-1&export=download",
    previewImageUrl: "https://lh3.googleusercontent.com/d/men-1",
    lineEligible: true,
  },
  {
    gender: "男子",
    leg: 6,
    kind: "leg",
    driveFileId: "men-6",
    title: "男子6区",
    fileSizeBytes: 44_000_000,
    folderId: "men-folder",
    originalContentUrl: "https://drive.usercontent.google.com/download?id=men-6&export=download",
    previewImageUrl: "https://lh3.googleusercontent.com/d/men-6",
    lineEligible: true,
  },
];

describe("resolveCourseVideoGender / detectCourseVideoLeg", () => {
  it("maps gender (default men)", () => {
    expect(resolveCourseVideoGender("女子コース動画")).toBe("女子");
    expect(resolveCourseVideoGender("男子コース動画")).toBe("男子");
    expect(resolveCourseVideoGender("荒玉のコース映像")).toBe("男子");
  });

  it("detects leg or null for full", () => {
    expect(detectCourseVideoLeg("女子3区のコース動画")).toBe(3);
    expect(detectCourseVideoLeg("男子 6 区 コース")).toBe(6);
    expect(detectCourseVideoLeg("荒玉コース動画")).toBeNull();
  });
});

describe("selectAragyokuCourseVideos", () => {
  beforeEach(() => {
    resetAragyokuCourseVideoCache();
  });

  it("returns women leg 3 when asked", () => {
    const vids = selectAragyokuCourseVideos("荒玉 女子 3区 コース動画", {
      videos: SAMPLE,
    });
    expect(vids).toHaveLength(1);
    expect(vids[0]?.driveFileId).toBe("women-3");
  });

  it("returns empty when full is not lineEligible", () => {
    const vids = selectAragyokuCourseVideos("荒玉 男子 コース動画", {
      videos: SAMPLE,
    });
    expect(vids).toHaveLength(0);
  });

  it("defaults to men when gender omitted", () => {
    const vids = selectAragyokuCourseVideos("荒玉駅伝のコース映像を見たい", {
      videos: SAMPLE,
    });
    // no leg → men full → not eligible
    expect(vids).toHaveLength(0);
  });

  it("returns men 6ku when asked", () => {
    const vids = selectAragyokuCourseVideos("男子6区のコース動画は？", {
      videos: SAMPLE,
    });
    expect(vids).toHaveLength(1);
    expect(vids[0]?.leg).toBe(6);
  });

  it("returns empty for women 6ku (no catalog entry)", () => {
    const vids = selectAragyokuCourseVideos("女子6区のコース動画", {
      videos: SAMPLE,
    });
    expect(vids).toHaveLength(0);
  });

  it("returns empty for non-course-video questions", () => {
    expect(
      selectAragyokuCourseVideos("2025年荒玉男子の区間賞は？", { videos: SAMPLE }),
    ).toHaveLength(0);
    expect(
      selectAragyokuCourseVideos("ジュニア駅伝のコース動画", { videos: SAMPLE }),
    ).toHaveLength(0);
  });

  it("loads real catalog with eligible legs", () => {
    const catalog = loadAragyokuCourseVideos();
    expect(catalog.length).toBeGreaterThan(0);
    const women3 = selectAragyokuCourseVideos("荒玉女子3区コース動画");
    expect(women3).toHaveLength(1);
    expect(women3[0]?.lineEligible).toBe(true);
    expect(women3[0]?.leg).toBe(3);
  });
});

describe("toLineVideoMessages", () => {
  it("maps eligible videos only", () => {
    const msgs = toLineVideoMessages(SAMPLE);
    expect(msgs.every((m) => m.type === "video")).toBe(true);
    expect(msgs).toHaveLength(3);
    expect(msgs[0]?.originalContentUrl).toContain("download?id=");
    expect(msgs[0]?.previewImageUrl).toMatch(/^https:\/\/lh3\.googleusercontent\.com\/d\//);
  });
});
