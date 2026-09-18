import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { Bm25Retriever, loadIndex, resetRetrieverCache } from "../src/rag/retrieve.js";
import { mapRefToCorpusSource } from "../src/kg/mapRefs.js";

const indexPath = join(dirname(fileURLToPath(import.meta.url)), "../data/rag_index.json");

describe("retrieve", () => {
  it("loads idaten corpus index only", () => {
    resetRetrieverCache();
    const index = loadIndex(indexPath);
    expect(index.corpus).toBe("input/idaten-corpus");
    expect(index.chunks.length).toBeGreaterThan(10);
  });

  it("hits ekiden OCR for 荒玉駅伝 岱明 query", () => {
    const index = loadIndex(indexPath);
    const retriever = new Bm25Retriever(index.chunks);
    const hits = retriever.search("荒玉駅伝 男子 岱明 順位", 8);
    expect(hits.length).toBeGreaterThan(0);
    const sources = hits.map((h) => h.chunk.source).join(" ");
    expect(
      /ekiden|aragyoku|駅伝|岱明|analysis/i.test(sources) ||
        hits.some((h) => /岱明|荒玉|駅伝/.test(h.chunk.text)),
    ).toBe(true);
  });

  it("finds non-Daiming athlete rows in full SB CSV", () => {
    resetRetrieverCache();
    const index = loadIndex(indexPath);
    expect(index.chunks.some((c) => c.source === "sb/中学生SB.csv")).toBe(true);
    const retriever = new Bm25Retriever(index.chunks);
    const hits = retriever.search("坂本春翔 1500m 自己ベスト", 12);
    expect(hits.some((h) => /坂本春翔/.test(h.chunk.text))).toBe(true);
    expect(hits.some((h) => /4:08\.05|錦中/.test(h.chunk.text))).toBe(true);
  });

  it("maps external SB wide CSV ref to corpus sb path", () => {
    expect(mapRefToCorpusSource("input/external/sb/middle-school/wide/中学生SB.csv")).toBe(
      "sb/中学生SB.csv",
    );
  });
});
