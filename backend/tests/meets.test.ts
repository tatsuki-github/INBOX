import { describe, expect, it } from "vitest";
import {
  detectMeetKind,
  isAragyokuCorpusSource,
  meetDriveTokens,
  meetResultPathBoost,
  otherMeetDriveTokens,
} from "../src/domain/meets.js";

describe("detectMeetKind", () => {
  it("classifies ジュニア駅伝 as junior even when 駅伝 is present", () => {
    expect(detectMeetKind("去年のジュニア駅伝の岱明の結果は？")).toBe("junior");
    expect(detectMeetKind("熊本県ジュニア駅伝")).toBe("junior");
  });

  it("classifies なごみ / 金栗 as nagomi", () => {
    expect(detectMeetKind("なごみ駅伝の集合時間は？")).toBe("nagomi");
    expect(detectMeetKind("金栗四三生誕の地なごみ大会")).toBe("nagomi");
  });

  it("classifies explicit 荒玉 and bare 駅伝 as aragyoku", () => {
    expect(detectMeetKind("去年の荒玉駅伝の優勝校は？")).toBe("aragyoku");
    expect(detectMeetKind("荒玉の歴代")).toBe("aragyoku");
    expect(detectMeetKind("駅伝の優勝校は？")).toBe("aragyoku");
  });

  it("does not treat ジュニア as aragyoku", () => {
    expect(detectMeetKind("ジュニア駅伝")).not.toBe("aragyoku");
  });

  it("classifies 玉名市民マラソン as other", () => {
    expect(detectMeetKind("去年の玉名市民マラソンの結果")).toBe("other");
  });
});

describe("isAragyokuCorpusSource", () => {
  it("detects aragyoku and ekiden-ocr paths", () => {
    expect(isAragyokuCorpusSource("aragyoku/winners-by-year.md")).toBe(true);
    expect(isAragyokuCorpusSource("ekiden-ocr/2025-男子.md")).toBe(true);
    expect(
      isAragyokuCorpusSource(
        "drive-text/大会/2025年度/0927_第２回熊本県ジュニア駅伝競走大会/岱明の結果.md",
      ),
    ).toBe(false);
  });
});

describe("meetDriveTokens / otherMeetDriveTokens", () => {
  it("returns junior/nagomi/aragyoku fixed tokens", () => {
    expect(meetDriveTokens("junior")).toEqual(["ジュニア"]);
    expect(meetDriveTokens("nagomi")).toContain("なごみ");
    expect(meetDriveTokens("aragyoku")).toContain("荒玉");
  });

  it("extracts path tokens for other named meets from the query", () => {
    expect(otherMeetDriveTokens("去年の玉名市民マラソンの結果")).toContain("玉名市民マラソン");
    expect(meetDriveTokens("other", "去年の玉名市民マラソンの結果")).toContain("玉名市民マラソン");
    expect(meetDriveTokens("other", "ナイターの結果は？")).toContain("ナイター");
  });
});

describe("meetResultPathBoost", () => {
  it("boosts 岱明の結果 paths for result queries", () => {
    const path =
      "drive-text/大会/2025年度/1130_玉名市民マラソン/岱明の結果.md";
    expect(meetResultPathBoost(path, "去年の玉名市民マラソンの結果")).toBeGreaterThanOrEqual(40);
    expect(meetResultPathBoost(path, "岱明の結果は？")).toBeGreaterThanOrEqual(60);
  });
});
