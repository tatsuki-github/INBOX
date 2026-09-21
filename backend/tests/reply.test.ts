import { describe, expect, it } from "vitest";
import {
  splitLineText,
  splitLineTextPreservingPrimarySources,
  LINE_TEXT_MAX,
} from "../src/line/reply.js";

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

  it("keeps primary source links in the reserved final message slot", () => {
    const text = `${"本文\n".repeat(LINE_TEXT_MAX * 2)}\n\n一次資料:\n・女子成績表PDF: https://example.test/women.pdf`;
    const parts = splitLineTextPreservingPrimarySources(text, 5);
    expect(parts).toHaveLength(5);
    expect(parts.at(-1)).toContain("女子成績表PDF");
  });
});
