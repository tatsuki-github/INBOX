import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  Bm25Retriever,
  extractAthleteNameHints,
  loadIndex,
  mergeRetrieved,
  resetRetrieverCache,
  tokenize,
  type RagChunk,
  type RetrievedChunk,
} from "../src/rag/retrieve.js";
import { mapRefToCorpusSource } from "../src/kg/mapRefs.js";

const indexPath = join(dirname(fileURLToPath(import.meta.url)), "../data/rag_index.json");

function chunk(id: string, text: string, source = "x"): RagChunk {
  return { id, source, text };
}

function hit(id: string, score: number, text = id, source = "x"): RetrievedChunk {
  return { chunk: chunk(id, text, source), score };
}

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

describe("mergeRetrieved", () => {
  it("does not let weak preferred drown a strong BM25 hit", () => {
    const preferred = [hit("weak-pref", 1.1, "unrelated header")];
    const bm25 = [hit("strong-bm25", 20, "正解の自己ベスト 11:04.38")];
    const merged = mergeRetrieved(preferred, bm25, 2);
    expect(merged.map((m) => m.chunk.id)).toContain("strong-bm25");
    expect(merged[0]!.chunk.id).toBe("strong-bm25");
  });

  it("still prefers strong preferred signals (name/date boosts)", () => {
    const preferred = [hit("name-row", 85, "森,鎮西学院,,,11:04.38")];
    const bm25 = [hit("noise", 12, "3000m予想タイム")];
    const merged = mergeRetrieved(preferred, bm25, 2);
    expect(merged[0]!.chunk.id).toBe("name-row");
  });
});

describe("extractAthleteNameHints", () => {
  it("extracts names without の particle near distance tokens", () => {
    expect(extractAthleteNameHints("森 3000m 自己ベスト")).toContain("森");
    expect(extractAthleteNameHints("今村昇磨 1500m自己ベスト")).toContain("今村昇磨");
    expect(extractAthleteNameHints("森の3000m自己ベストは？")).toContain("森");
  });

  it("ignores temporal pronouns", () => {
    expect(extractAthleteNameHints("今の自己ベストは？")).not.toContain("今");
    expect(extractAthleteNameHints("最新の自己ベストは？")).not.toContain("最新");
  });
});

describe("tokenize", () => {
  it("keeps ISO dates and applies NFKC", () => {
    const toks = tokenize("２０２６-０９-２０ なごみ");
    expect(toks).toContain("2026-09-20");
  });
});
