/**
 * Knowledge-graph query (TypeScript port of scripts/knowledge_graph/query.py scoring).
 * Reads only backend/data/knowledge-graph.json — no repo filesystem walks.
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { mapRefsToCorpusSources } from "./mapRefs.js";

export type KgNode = {
  id: string;
  type: string;
  label: string;
  hint?: string;
  topics?: string[];
  refs?: string[];
};

export type KgEdge = {
  from: string;
  to: string;
  rel: string;
};

export type KnowledgeGraph = {
  version: number;
  generated_at?: string;
  nodes: KgNode[];
  edges: KgEdge[];
};

export type MatchedNode = {
  id: string;
  type: string;
  label: string;
  score: number;
  hint: string;
  refs: string[];
};

export type KgQueryResult = {
  question: string;
  matched_nodes: MatchedNode[];
  refs: string[];
  corpus_sources: string[];
};

const __dirname = dirname(fileURLToPath(import.meta.url));

export function defaultKgPath(): string {
  return join(__dirname, "../../data/knowledge-graph.json");
}

const TOKEN_RE = /[A-Za-z0-9_]+|[\u3040-\u30ff]+|[\u3400-\u9fff]+/gu;
const PARTICLE_SPLIT = /[のとへをはがでにでもや]+/;

export function tokenizeKg(text: string): string[] {
  const lower = text.toLowerCase().trim();
  const tokens: string[] = [];
  for (const part of lower.split(PARTICLE_SPLIT)) {
    const p = part.trim();
    if (!p) continue;
    const matches = p.match(TOKEN_RE) ?? [];
    for (const m of matches) {
      if (m.length >= 1) tokens.push(m);
    }
    const chars = p.match(/[\u3400-\u9fff]/gu) ?? [];
    if (chars.length >= 2) {
      for (let i = 0; i < chars.length - 1; i += 1) {
        tokens.push(chars[i]! + chars[i + 1]!);
      }
    }
  }
  const seen = new Set<string>();
  const out: string[] = [];
  for (const t of tokens) {
    if (!seen.has(t)) {
      seen.add(t);
      out.push(t);
    }
  }
  return out;
}

function scoreNode(node: KgNode, qTokens: string[], query: string): number {
  const label = (node.label || "").toLowerCase();
  const nodeType = node.type;
  const hint = (node.hint || "").toLowerCase();
  const topics = (node.topics || []).join(" ").toLowerCase();
  const refs = (node.refs || []).join(" ").toLowerCase();
  const blob = [node.id, label, hint, topics, refs].join(" ").toLowerCase();
  const q = query.toLowerCase().trim();
  let score = 0;
  if (label && q.includes(label)) score += 8;
  for (const tok of qTokens) {
    if (!tok) continue;
    // Ignore ultra-short / pure-digit tokens that flood MediaAsset paths
    if (/^\d{1,3}$/.test(tok)) continue;
    if (tok === label) {
      score += 6;
      continue;
    }
    if (tok && label.includes(tok)) {
      score += 3;
      continue;
    }
    if (nodeType === "Athlete" || nodeType === "MediaAsset") continue;
    if (blob.includes(tok)) score += tok.length >= 2 ? 2 : 0.5;
  }
  if (nodeType !== "Athlete" && nodeType !== "MediaAsset" && q && blob.includes(q)) score += 5;
  if (score <= 0) return 0;
  const boost: Record<string, number> = {
    QueryHint: 1.5,
    Topic: 1.2,
    Source: 1.0,
    Athlete: 1.4,
    Template: 1.1,
    Entity: 1.25,
    Year: 1.0,
    MediaAsset: 1.35,
  };
  return score * (boost[nodeType] ?? 1);
}

function adjacency(edges: KgEdge[]): Map<string, Array<{ to: string; rel: string }>> {
  const adj = new Map<string, Array<{ to: string; rel: string }>>();
  for (const e of edges) {
    const list = adj.get(e.from) ?? [];
    list.push({ to: e.to, rel: e.rel });
    adj.set(e.from, list);
  }
  return adj;
}

let cachedGraph: KnowledgeGraph | null = null;

export function loadKnowledgeGraph(path: string = defaultKgPath()): KnowledgeGraph {
  const raw = readFileSync(path, "utf8");
  const data = JSON.parse(raw) as KnowledgeGraph;
  if (!Array.isArray(data.nodes) || !Array.isArray(data.edges)) {
    throw new Error("Invalid knowledge-graph.json");
  }
  return data;
}

export function getKnowledgeGraph(path: string = defaultKgPath()): KnowledgeGraph {
  if (!cachedGraph) cachedGraph = loadKnowledgeGraph(path);
  return cachedGraph;
}

/** Test helper */
export function resetKgCache(): void {
  cachedGraph = null;
}

export function queryKnowledgeGraph(
  question: string,
  opts?: {
    graph?: KnowledgeGraph;
    topK?: number;
    expandHops?: number;
    kgPath?: string;
  },
): KgQueryResult {
  const topK = opts?.topK ?? 16;
  const expandHops = opts?.expandHops ?? 2;
  const graph = opts?.graph ?? getKnowledgeGraph(opts?.kgPath);
  const nodes = new Map(graph.nodes.map((n) => [n.id, n]));
  const adj = adjacency(graph.edges);
  const qTokens = tokenizeKg(question);

  let scored: Array<[string, number]> = [];
  for (const [nid, node] of nodes) {
    const s = scoreNode(node, qTokens, question);
    if (s > 0) scored.push([nid, s]);
  }
  scored.sort((a, b) => b[1]! - a[1]!);
  let seeds = scored.slice(0, topK);

  if (
    seeds.some(([nid, s]) => {
      const t = nodes.get(nid)?.type;
      return (t === "Athlete" || t === "Template" || t === "Year") && s >= 8;
    })
  ) {
    const filtered = seeds.filter(([nid, s]) => {
      const t = nodes.get(nid)?.type;
      return (t !== "Topic" && t !== "QueryHint") || s >= 20;
    });
    seeds = filtered.length > 0 ? filtered : seeds.slice(0, 3);
  }

  if (seeds.length === 0) {
    const mapping: Array<[string[], string]> = [
      [["練習", "メニュー", "jog", "interval", "欠席"], "topic:practice"],
      [["記録", "タイム", "選手", "PB"], "topic:athlete_records"],
      [["カレンダー", "予定", "祝日", "inbox", "大会"], "topic:calendar"],
      [["norwegian", "gz", "閾値", "vdot", "ペース"], "topic:norwegian"],
      [["ai", "生成", "プロンプト"], "topic:ai"],
      [["ケガ", "障害", "rri", "怪我"], "topic:injury"],
      [["駅伝", "荒玉", "なごみ", "ekiden", "ジュニア", "開催要項", "大会"], "topic:ekiden"],
      [["名簿", "部員", "生徒"], "topic:practice"],
      [["sb", "SB", "記録会"], "topic:athlete_records"],
    ];
    const q = question.toLowerCase();
    const fallback: Array<[string, number]> = [];
    // Date-like queries always route to calendar
    if (
      /\d{1,2}\/\d{1,2}/.test(question) ||
      /\d{1,2}\s*月\s*\d{1,2}\s*日/.test(question) ||
      /20\d{2}-\d{2}-\d{2}/.test(question) ||
      /予定/.test(question)
    ) {
      if (nodes.has("topic:calendar")) fallback.push(["topic:calendar", 5.0]);
      const yearHit = [...nodes.keys()].find((id) => /^entity:year:20\d{2}$/.test(id) && q.includes(id.slice(-4)));
      if (yearHit) fallback.push([yearHit, 3.0]);
    }
    for (const [keys, tid] of mapping) {
      if (keys.some((k) => q.includes(k.toLowerCase())) && nodes.has(tid)) {
        fallback.push([tid, 1.0]);
      }
    }
    if (fallback.length > 0) {
      seeds = fallback.slice(0, topK);
    } else if (nodes.has("topic:meta")) {
      seeds = [["topic:meta", 1.0]];
    } else {
      seeds = scored.slice(0, topK);
    }
  }

  const selected = new Map<string, number>(seeds);
  let frontier = [...selected.keys()];
  const routeRels = new Set(["search_here", "documented_in", "mentioned_in", "see_also"]);
  for (let hop = 0; hop < Math.max(0, expandHops); hop += 1) {
    const nxt: string[] = [];
    for (const nid of frontier) {
      for (const { to: neighbor, rel } of adj.get(nid) ?? []) {
        if (!routeRels.has(rel)) continue;
        const boost = rel === "see_also" ? 0.55 : 0.85;
        const newScore = (selected.get(nid) ?? 0) * boost;
        if (!selected.has(neighbor) || newScore > (selected.get(neighbor) ?? 0)) {
          selected.set(neighbor, newScore);
          nxt.push(neighbor);
        }
      }
    }
    frontier = nxt;
  }

  const orderedIds = [...selected.keys()].sort(
    (a, b) => (selected.get(b) ?? 0) - (selected.get(a) ?? 0),
  );
  const hitNodes = orderedIds.map((id) => nodes.get(id)!).filter(Boolean);

  const refs: string[] = [];
  const seenRefs = new Set<string>();
  for (const node of hitNodes) {
    for (const ref of node.refs ?? []) {
      if (!seenRefs.has(ref)) {
        seenRefs.add(ref);
        refs.push(ref);
      }
    }
  }

  return {
    question,
    matched_nodes: hitNodes.slice(0, Math.max(topK * 3, 12)).map((n) => ({
      id: n.id,
      type: n.type,
      label: n.label,
      score: Math.round((selected.get(n.id) ?? 0) * 1000) / 1000,
      hint: n.hint ?? "",
      refs: n.refs ?? [],
    })),
    refs,
    corpus_sources: mapRefsToCorpusSources(refs),
  };
}
