import { describe, expect, it } from "vitest";
import { formatForLine } from "../src/line/format.js";

describe("formatForLine", () => {
  it("strips bold/italic markers", () => {
    expect(formatForLine("**なごみ駅伝** です")).toBe("なごみ駅伝 です");
    expect(formatForLine("*調整*日")).toBe("調整日");
  });

  it("strips headings and list markers into readable lines", () => {
    const raw = ["## 予定", "", "- なごみ駅伝", "- 開催: 2026-09-20"].join("\n");
    const out = formatForLine(raw);
    expect(out).not.toMatch(/^#/m);
    expect(out).toContain("予定");
    expect(out).toContain("なごみ駅伝");
    expect(out).toContain("開催: 2026-09-20");
  });

  it("removes trailing source path footnotes", () => {
    const raw = "2026-09-20はなごみ駅伝です。\n\n根拠: calendar/events.daiming.yaml";
    expect(formatForLine(raw)).toBe("2026-09-20はなごみ駅伝です。");
  });

  it("unwraps markdown links", () => {
    expect(formatForLine("[開催要項](https://example.com)")).toBe("開催要項");
  });

  it("strips fenced code markers", () => {
    expect(formatForLine("```\n距離 3km\n```")).toBe("距離 3km");
  });

  it("keeps bare result-page URLs", () => {
    const raw =
      "要点\n\n結果ページ:\nhttp://www.kcrk.jp/i-mode/kiroku/sisen_i/450418/PC/rel026.html";
    expect(formatForLine(raw)).toContain(
      "http://www.kcrk.jp/i-mode/kiroku/sisen_i/450418/PC/rel026.html",
    );
  });

  it("preserves snake_case identifiers (not italic)", () => {
    expect(formatForLine("practice_meets_affect_load の設定値は？")).toContain(
      "practice_meets_affect_load",
    );
  });

  it("preserves Drive folder URLs with underscores", () => {
    const url =
      "https://drive.google.com/drive/folders/17MrxiZ_0CsDBgVrS_O3uZm3Oypu70Uoo";
    expect(formatForLine(`男子: ${url}`)).toContain(url);
  });
});
