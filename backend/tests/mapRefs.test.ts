import { describe, expect, it } from "vitest";
import { mapRefToCorpusSource, mapRefsToCorpusSources } from "../src/kg/mapRefs.js";

describe("mapRefToCorpusSource", () => {
  it("maps events YAML to daiming calendar", () => {
    expect(mapRefToCorpusSource("input/events.2026.yaml")).toBe(
      "calendar/events.daiming.yaml",
    );
  });

  it("maps ekiden OCR paths", () => {
    expect(
      mapRefToCorpusSource(
        "input/external/notion/media/ekiden-history/ocr/2024-男子.md",
      ),
    ).toBe("ekiden-ocr/2024-男子.md");
  });

  it("rejects path traversal", () => {
    expect(mapRefToCorpusSource("../etc/passwd")).toBeNull();
    expect(mapRefToCorpusSource("input/events.2026.yaml/../../secret")).toBeNull();
  });

  it("dedupes mapped refs", () => {
    const sources = mapRefsToCorpusSources([
      "input/events.2026.yaml",
      "input/events.2025.yaml",
      "input/aragyoku/taimei-records-2012-2025.md",
    ]);
    expect(sources).toEqual([
      "calendar/events.daiming.yaml",
      "aragyoku/taimei-records-2012-2025.md",
    ]);
  });

  it("maps practice and drive 練習 refs", () => {
    expect(mapRefToCorpusSource("input/practice/foo.md")).toBe("practice/foo.md");
    expect(mapRefToCorpusSource("input/external/drive/shared/練習/練習の記録.md")).toBe(
      "drive-text/練習/練習の記録.md",
    );
  });
});
