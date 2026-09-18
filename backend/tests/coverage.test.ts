import { describe, expect, it } from "vitest";
import {
  expandWithNeighbors,
  loadIndex,
  resetRetrieverCache,
} from "../src/rag/retrieve.js";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { queryKnowledgeGraph, resetKgCache } from "../src/kg/query.js";
import { answerQuestion } from "../src/domain/answer.js";

const indexPath = join(dirname(fileURLToPath(import.meta.url)), "../data/rag_index.json");
const kgPath = join(dirname(fileURLToPath(import.meta.url)), "../data/knowledge-graph.json");

describe("coverage expansion", () => {
  it("KG routes なごみ to meet / ekiden sources with content hints", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("なごみ駅伝の開催要項は？", { kgPath });
    expect(
      result.matched_nodes.some(
        (n) => n.id.includes("なごみ") || n.label.includes("なごみ") || n.hint.includes("なごみ"),
      ) || result.corpus_sources.some((s) => s.includes("なごみ") || s.includes("0920")),
    ).toBe(true);
  });

  it("expands calendar hits with neighboring chunks", () => {
    resetRetrieverCache();
    const index = loadIndex(indexPath);
    const cal = index.chunks.find((c) => c.id === "calendar/events.daiming.yaml:50");
    expect(cal).toBeTruthy();
    const expanded = expandWithNeighbors(
      [{ chunk: cal!, score: 10 }],
      { radius: 2, path: indexPath },
    );
    expect(expanded.length).toBeGreaterThan(1);
    expect(expanded.every((r) => r.chunk.source.startsWith("calendar/"))).toBe(true);
  });

  it("keeps weather hard-refused even with KG", async () => {
    resetKgCache();
    const result = await answerQuestion("今日の天気は？", { llm: null });
    expect(result.kind).toBe("refused");
  });
});
