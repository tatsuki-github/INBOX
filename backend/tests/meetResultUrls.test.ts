import { describe, expect, it } from "vitest";
import {
  appendMeetResultUrls,
  findMeetResultUrls,
  wantsMeetResultUrl,
  withMeetResultUrls,
  type MeetResultUrlEntry,
} from "../src/domain/meetResultUrls.js";
import { formatForLine } from "../src/line/format.js";

const SAMPLE: MeetResultUrlEntry[] = [
  {
    title: "第４５回熊本市陸上競技選手権大会中長距離の部",
    date: "2026-04-18",
    year: 2026,
    urls: [
      "http://www.kcrk.jp/i-mode/kiroku/sisen_i/450418/PC/rel026.html",
      "http://www.kcrk.jp/i-mode/kiroku/sisen_i/450418/PC/rel013.html",
    ],
  },
  {
    title: "2026年度第２回熊本県長距離記録会",
    date: "2026-07-04",
    year: 2026,
    urls: ["http://www.kumariku.org/26/26,7,4long/kyougi.html"],
  },
];

describe("wantsMeetResultUrl", () => {
  it("detects result-oriented questions", () => {
    expect(wantsMeetResultUrl("熊本市選手権の結果は？")).toBe(true);
    expect(wantsMeetResultUrl("集合時間は？")).toBe(false);
  });
});

describe("findMeetResultUrls", () => {
  it("returns CSV URLs for a matching meet result question", () => {
    const urls = findMeetResultUrls("今年の熊本市陸上選手権の結果", SAMPLE, {
      defaultYear: 2026,
    });
    expect(urls[0]).toContain("kcrk.jp");
  });

  it("returns empty when no meet matches", () => {
    expect(
      findMeetResultUrls("来週の練習メニューは？", SAMPLE, { defaultYear: 2026 }),
    ).toEqual([]);
  });

  it("does not invent URLs when index is empty", () => {
    expect(findMeetResultUrls("ジュニア駅伝の結果", [], { defaultYear: 2025 })).toEqual([]);
  });

  it("does not attach URLs for unrelated result questions", () => {
    expect(
      findMeetResultUrls("なごみ駅伝の結果", SAMPLE, { defaultYear: 2026 }),
    ).toEqual([]);
  });

  it("prefers championship over 記録会 for 熊本市選手権", () => {
    const withKiroku: MeetResultUrlEntry[] = [
      {
        title: "第２７２回熊本市陸上競技記録会",
        date: "2026-04-04",
        year: 2026,
        urls: ["http://www.kcrk.jp/i-mode/kiroku/272/PC/rel062.html"],
      },
      ...SAMPLE,
    ];
    const urls = findMeetResultUrls("熊本市選手権の結果は？", withKiroku, {
      defaultYear: 2026,
    });
    expect(urls[0]).toContain("sisen_i/450418");
  });
});

describe("appendMeetResultUrls / formatForLine", () => {
  it("appends bare URLs that survive formatForLine", () => {
    const raw = appendMeetResultUrls("男子1500mは松野が4:25でした。", [
      "http://www.kcrk.jp/i-mode/kiroku/sisen_i/450418/PC/rel026.html",
    ]);
    const out = formatForLine(raw);
    expect(out).toContain("結果ページ:");
    expect(out).toContain("http://www.kcrk.jp/i-mode/kiroku/sisen_i/450418/PC/rel026.html");
  });

  it("withMeetResultUrls wires lookup + append", () => {
    const out = withMeetResultUrls("要点のみ", "長距離記録会の結果は？", {
      entries: SAMPLE,
      defaultYear: 2026,
    });
    expect(out).toContain("kumariku.org");
  });
});
