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

  it("routes 2024-2025 focus-team aragyoku analysis questions", () => {
    resetKgCache();
    const result = queryKnowledgeGraph(
      "2024年と2025年の荒玉駅伝で岱明・玉名付属・天水・有明はどうだった？",
      { kgPath },
    );
    const blob = [
      ...result.matched_nodes.flatMap((n) => [n.id, ...(n.refs ?? [])]),
      ...result.corpus_sources,
    ].join("\n");
    expect(blob).toMatch(/aragyoku_2024_2025_focus_teams/);
  });

  it("routes 玉名付属 alias to 玉高附属 focus analysis", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("玉名付属中の荒玉駅伝2024と2025は？", { kgPath });
    const blob = [
      ...result.matched_nodes.flatMap((n) => [n.id, ...(n.refs ?? [])]),
      ...result.corpus_sources,
    ].join("\n");
    expect(blob).toMatch(/aragyoku_2024_2025_focus_teams|玉高附属/);
  });

  it("routes school PB average questions to school ranking digest", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("女子800mで岱明の上位3人平均は？", { kgPath });
    const blob = [
      ...result.matched_nodes.flatMap((n) => [n.id, ...(n.refs ?? [])]),
      ...result.corpus_sources,
    ].join("\n");
    expect(blob).toMatch(/2026_women_800m_1500m_pb_school_ranking/);
  });

  it("routes winner-margin questions to focus-team analysis", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("2025年岱明男子の優勝との差は？", { kgPath });
    const blob = [
      ...result.matched_nodes.flatMap((n) => [n.id, ...(n.refs ?? [])]),
      ...result.corpus_sources,
    ].join("\n");
    expect(blob).toMatch(/aragyoku_2024_2025_focus_teams/);
  });

  it("routes team-leg questions to the exact aragyoku-teams digest", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("菊水の荒玉駅伝の1区は誰？", { kgPath });
    expect(result.corpus_sources.some((s) => s.includes("aragyoku-teams/菊水.md"))).toBe(true);
  });

  it("routes なごみ 1区 questions to なごみ大会, not 金栗駅伝", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("なごみ駅伝の岱明男子1区は誰？", { kgPath });
    const blob = [...result.corpus_sources, ...result.refs].join("\n");
    expect(blob).toMatch(/なごみ/);
    expect(result.corpus_sources[0] ?? "").not.toMatch(/0315_金栗駅伝|金栗記念/);
  });

  it("routes 金栗PROJECT full records to arato-tamana digest, not nagomi hubs", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("金栗PROJECT所属選手の全記録", { kgPath });
    expect(result.corpus_sources.some((s) => s.includes("arato-tamana-teams/金栗PROJECT.md"))).toBe(
      true,
    );
    const top = result.matched_nodes.slice(0, 8);
    expect(top.some((n) => /なごみ/.test(n.label))).toBe(false);
    expect(result.refs.slice(0, 12).some((r) => r.includes("なごみ"))).toBe(false);
  });

  it("routes unnamed 何区を走った to aragyoku team digests not スタートリスト", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("案浦竜士は何区を走った？", { kgPath });
    const blob = [...result.corpus_sources, ...result.refs].join("\n");
    expect(blob).toMatch(/aragyoku-teams/);
    expect(result.corpus_sources[0] ?? "").not.toMatch(/スタートリスト|通信陸上/);
  });

  it("routes track lap questions to practice menus digest", () => {
    resetKgCache();
    const result = queryKnowledgeGraph("岱明のトラック1周は？", { kgPath });
    const blob = [...result.refs, ...result.corpus_sources].join("\n");
    expect(blob).toMatch(/daiming-practice-menus-kpace/);
  });
});
