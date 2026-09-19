import { describe, expect, it } from "vitest";
import { isLegAthleteQuestion } from "../src/domain/legs.js";

describe("isLegAthleteQuestion", () => {
  it("treats 何区を走った / は何区 as race-leg questions", () => {
    expect(isLegAthleteQuestion("案浦竜士は何区を走った？")).toBe(true);
    expect(isLegAthleteQuestion("佐藤央琉は何区？")).toBe(true);
    expect(isLegAthleteQuestion("草野瑠唯は荒玉で何区を走った？")).toBe(true);
    expect(isLegAthleteQuestion("案浦は何区走った？")).toBe(true);
  });

  it("still matches numbered 区は誰", () => {
    expect(isLegAthleteQuestion("2025年岱明男子5区は誰？")).toBe(true);
  });

  it("does not match LINE ops or distance questions", () => {
    expect(isLegAthleteQuestion("2区と5区の距離は？")).toBe(false);
    expect(isLegAthleteQuestion("地点分担で土山はどこ？")).toBe(false);
    expect(isLegAthleteQuestion("荒玉男子2区の距離は何キロ？")).toBe(false);
  });
});
