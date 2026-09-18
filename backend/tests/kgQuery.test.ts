import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { queryKnowledgeGraph, resetKgCache } from "../src/kg/query.js";
import { expandDateQuery } from "../src/domain/dates.js";

const kgPath = join(dirname(fileURLToPath(import.meta.url)), "../data/knowledge-graph.json");

describe("queryKnowledgeGraph", () => {
  it("routes date schedule questions toward calendar sources", () => {
    resetKgCache();
    const expanded = expandDateQuery("9/20の予定は？", 2026);
    const result = queryKnowledgeGraph(expanded, { kgPath });
    expect(result.matched_nodes.length).toBeGreaterThan(0);
    expect(result.corpus_sources).toContain("calendar/events.daiming.yaml");
  });

  it("routes ekiden history questions", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("荒玉駅伝の歴代は？", { kgPath });
    expect(
      result.matched_nodes.some((n) => n.id.includes("ekiden") || n.label.includes("駅伝")) ||
        result.corpus_sources.some((s) => s.includes("ekiden") || s.includes("aragyoku")),
    ).toBe(true);
  });

  it("prefers junior meet nodes over aragyoku for ジュニア駅伝", () => {
    resetKgCache();
    const expanded = expandDateQuery("去年のジュニア駅伝の岱明の結果は？", 2026);
    const result = queryKnowledgeGraph(expanded, { kgPath });
    expect(result.matched_nodes.some((n) => /ジュニア/.test(n.label) || /ジュニア/.test(n.hint))).toBe(
      true,
    );
    expect(
      result.corpus_sources.some((s) => s.includes("ジュニア") && s.includes("岱明の結果")),
    ).toBe(true);
  });

  it("QueryHint GZ routes to Daniels/ADR sources (not Topic-only)", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("GZ / 閾値ペースは？", { kgPath });
    const blob = [
      ...result.matched_nodes.flatMap((n) => [n.id, ...(n.refs ?? [])]),
      ...result.corpus_sources,
    ].join("\n");
    expect(blob).toMatch(/daniels_vdot_paces|008-daniels|norwegian_method/i);
  });

  it("Topic norwegian expands to repo-docs corpus hub", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("Norwegian Method の原則は？", { kgPath });
    expect(
      result.matched_nodes.some((n) => n.id === "corpus:repo-docs" || n.id === "topic:norwegian") ||
        result.corpus_sources.some((s) => s.includes("repo-docs") || s.includes("norwegian")),
    ).toBe(true);
  });
});
