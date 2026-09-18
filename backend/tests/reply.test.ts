import { describe, expect, it } from "vitest";
import { splitLineText, LINE_TEXT_MAX } from "../src/line/reply.js";

describe("splitLineText", () => {
  it("returns single part when short", () => {
    expect(splitLineText("hello")).toEqual(["hello"]);
  });

  it("splits long text under max", () => {
    const text = "あ".repeat(LINE_TEXT_MAX + 100);
    const parts = splitLineText(text);
    expect(parts.length).toBeGreaterThan(1);
    expect(parts.every((p) => p.length <= LINE_TEXT_MAX)).toBe(true);
    expect(parts.join("")).toBe(text);
  });
});
