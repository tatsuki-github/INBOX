import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { RETRIEVAL_BUDGET } from "../src/domain/answer.js";
import {
  Bm25Retriever,
  expandWithNeighbors,
  extractAthleteNameHints,
  loadIndex,
  mergeRetrieved,
  resetRetrieverCache,
  retrieveBySources,
  retrieveContext,
  tokenize,
  truncateRetrieved,
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

  it("drops aragyoku BM25 hits for ジュニア queries even with wide topK", () => {
    const preferred = [hit("jr", 10, "ジュニア結果", "drive-text/大会/2025年度/ジュニア/岱明の結果.md")];
    const bm25 = [
      hit("arag", 50, "荒玉優勝", "aragyoku/winners-by-year.md"),
      hit("ocr", 40, "OCR", "ekiden-ocr/2025-男子.md"),
    ];
    const merged = mergeRetrieved(preferred, bm25, 64, {
      query: "去年のジュニア駅伝の岱明の結果",
    });
    expect(merged.every((m) => !m.chunk.source.startsWith("aragyoku/"))).toBe(true);
    expect(merged.every((m) => !m.chunk.source.startsWith("ekiden-ocr/"))).toBe(true);
    expect(merged.some((m) => m.chunk.id === "jr")).toBe(true);
  });

  it("drops chunks that quote the coach refuse template", () => {
    const preferred = [hit("fact", 10, "玉名市練習会をすべて中止", "calendar/events.daiming.yaml")];
    const bm25 = [
      hit("meta", 99, "無いことはコーチに直接聞いてください。と答える", "docs/adr/025.md"),
    ];
    const merged = mergeRetrieved(preferred, bm25, 64, {
      query: "県民スポーツ大会中止に伴う練習会",
    });
    expect(merged.map((m) => m.chunk.id)).toEqual(["fact"]);
  });
});

describe("RETRIEVAL_BUDGET 100k", () => {
  it("caps context at 100000 chars and fills most of the budget", () => {
    expect(RETRIEVAL_BUDGET.maxChars).toBe(100_000);
    const capacity = RETRIEVAL_BUDGET.topK + RETRIEVAL_BUDGET.neighborMaxExtra;
    expect(capacity * 500).toBeGreaterThanOrEqual(100_000);

    const hits = Array.from({ length: 300 }, (_, i) =>
      hit(`c${i}`, 100 - i * 0.01, "あ".repeat(500), `src/${i % 20}`),
    );
    const out = truncateRetrieved(hits, RETRIEVAL_BUDGET.maxChars);
    const used = out.reduce((sum, r) => sum + r.chunk.text.length, 0);
    expect(used).toBeLessThanOrEqual(100_000);
    expect(used).toBeGreaterThan(90_000);
    expect(out.length).toBeGreaterThan(150);
  });

  it("widened retrieve+merge+neighbors exceed the old 28k ceiling before truncate", () => {
    resetRetrieverCache();
    const query = "なごみ駅伝 開催要項 結果 ジュニア 荒玉 予定 練習";
    const sources = [
      "calendar/events.daiming.yaml",
      "drive-text/大会",
      "sb/中学生SB.csv",
      "aragyoku",
      "ekiden-ocr",
      "practice",
      "notion-db",
      "repo-docs",
    ];
    const fromSources = retrieveBySources(sources, {
      query,
      path: indexPath,
      perSource: RETRIEVAL_BUDGET.perSource,
      maxChunks: RETRIEVAL_BUDGET.maxChunks,
    });
    const fromBm25 = retrieveContext(query, RETRIEVAL_BUDGET.topK, indexPath);
    const merged = mergeRetrieved(fromSources, fromBm25, RETRIEVAL_BUDGET.topK, {
      query,
    });
    const withNeighbors = expandWithNeighbors(merged, {
      path: indexPath,
      radius: RETRIEVAL_BUDGET.neighborRadius,
      maxExtra: RETRIEVAL_BUDGET.neighborMaxExtra,
    });
    const before = withNeighbors.reduce((sum, r) => sum + r.chunk.text.length, 0);
    expect(before).toBeGreaterThan(28_000);
    const truncated = truncateRetrieved(withNeighbors, RETRIEVAL_BUDGET.maxChars);
    const used = truncated.reduce((sum, r) => sum + r.chunk.text.length, 0);
    expect(used).toBeLessThanOrEqual(RETRIEVAL_BUDGET.maxChars);
    expect(used).toBeGreaterThan(28_000);
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
