import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export type RagChunk = {
  id: string;
  source: string;
  text: string;
  metadata?: Record<string, unknown>;
};

export type RagIndex = {
  version: number;
  corpus: string;
  chunk_count: number;
  chunks: RagChunk[];
};

export type RetrievedChunk = {
  chunk: RagChunk;
  score: number;
};

const __dirname = dirname(fileURLToPath(import.meta.url));

/** Only allow reading the packaged index under backend/data. */
export function defaultIndexPath(): string {
  return join(__dirname, "../../data/rag_index.json");
}

function tokenize(text: string): string[] {
  const lower = text.toLowerCase();
  // Keep ISO dates intact before general tokenization (schedule matching).
  const isoDates = lower.match(/20\d{2}-\d{2}-\d{2}/g) ?? [];
  const withoutIso = lower.replace(/20\d{2}-\d{2}-\d{2}/g, " ");
  // Keep CJK runs and alnum tokens
  const tokens = withoutIso.match(
    /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]+|[\w\d]+/gu,
  );
  const out: string[] = [...isoDates];
  if (!tokens) {
    return out;
  }
  // Further split long CJK into bigrams for better recall
  for (const t of tokens) {
    if (/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]/u.test(t) && t.length > 1) {
      out.push(t);
      for (let i = 0; i < t.length - 1; i += 1) {
        out.push(t.slice(i, i + 2));
      }
    } else {
      out.push(t);
    }
  }
  return out;
}

export class Bm25Retriever {
  private readonly chunks: RagChunk[];
  private readonly docTokens: string[][];
  private readonly docLens: number[];
  private readonly avgdl: number;
  private readonly df = new Map<string, number>();
  private readonly k1: number;
  private readonly b: number;

  constructor(chunks: RagChunk[], opts?: { k1?: number; b?: number }) {
    this.chunks = chunks;
    this.k1 = opts?.k1 ?? 1.5;
    this.b = opts?.b ?? 0.75;
    this.docTokens = chunks.map((c) => tokenize(c.text));
    this.docLens = this.docTokens.map((t) => t.length);
    this.avgdl = this.docLens.reduce((a, n) => a + n, 0) / Math.max(this.docLens.length, 1);
    for (const tokens of this.docTokens) {
      for (const term of new Set(tokens)) {
        this.df.set(term, (this.df.get(term) ?? 0) + 1);
      }
    }
  }

  private idf(term: string): number {
    const n = this.df.get(term) ?? 0;
    const nd = this.chunks.length;
    return Math.log(1 + (nd - n + 0.5) / (n + 0.5));
  }

  search(query: string, topK = 5): RetrievedChunk[] {
    const qTokens = tokenize(query);
    if (qTokens.length === 0) {
      return [];
    }
    const scored: RetrievedChunk[] = [];
    for (let i = 0; i < this.docTokens.length; i += 1) {
      const tokens = this.docTokens[i]!;
      const tf = new Map<string, number>();
      for (const t of tokens) {
        tf.set(t, (tf.get(t) ?? 0) + 1);
      }
      const dl = this.docLens[i]!;
      let score = 0;
      for (const term of qTokens) {
        const freq = tf.get(term);
        if (!freq) continue;
        const idf = this.idf(term);
        const denom = freq + this.k1 * (1 - this.b + (this.b * dl) / this.avgdl);
        score += (idf * (freq * (this.k1 + 1))) / denom;
      }
      if (score > 0) {
        scored.push({ chunk: this.chunks[i]!, score });
      }
    }
    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, topK);
  }
}

let cached: Bm25Retriever | null = null;

export function loadIndex(path: string = defaultIndexPath()): RagIndex {
  const raw = readFileSync(path, "utf8");
  const data = JSON.parse(raw) as RagIndex;
  if (!data.chunks || !Array.isArray(data.chunks)) {
    throw new Error("Invalid rag_index.json: missing chunks");
  }
  if (data.corpus !== "input/idaten-corpus") {
    throw new Error(`Unexpected corpus root: ${data.corpus}`);
  }
  return data;
}

export function getRetriever(path: string = defaultIndexPath()): Bm25Retriever {
  if (!cached) {
    const index = loadIndex(path);
    cached = new Bm25Retriever(index.chunks);
  }
  return cached;
}

/** Test helper to reset singleton. */
export function resetRetrieverCache(): void {
  cached = null;
}

export function retrieveContext(
  query: string,
  topK = 5,
  path: string = defaultIndexPath(),
): RetrievedChunk[] {
  return getRetriever(path).search(query, topK);
}

function chunkBaseSource(source: string): string {
  // ids may be "path:offset" — take path before last :digit only when pattern matches
  const m = source.match(/^(.*):\d+$/);
  return m ? m[1]! : source;
}

/** Discover drive-text/大会 sources whose path contains any of the given tokens (e.g. 0920). */
export function findSourcesContaining(
  tokens: string[],
  opts?: { prefix?: string; path?: string; limit?: number },
): string[] {
  if (tokens.length === 0) return [];
  const path = opts?.path ?? defaultIndexPath();
  const prefix = opts?.prefix ?? "drive-text/大会/";
  const limit = opts?.limit ?? 8;
  const index = loadIndex(path);
  const found: string[] = [];
  const seen = new Set<string>();
  for (const chunk of index.chunks) {
    const base = chunkBaseSource(chunk.source);
    if (!base.startsWith(prefix)) continue;
    const lower = base.toLowerCase();
    if (!tokens.some((t) => t && lower.includes(t.toLowerCase()))) continue;
    if (seen.has(base)) continue;
    seen.add(base);
    found.push(base);
    if (found.length >= limit) break;
  }
  return found;
}

/** Fetch chunks whose source matches any of the given corpus sources (prefix OK). */
export function retrieveBySources(
  sources: string[],
  opts?: {
    query?: string;
    perSource?: number;
    maxChunks?: number;
    path?: string;
  },
): RetrievedChunk[] {
  if (sources.length === 0) return [];
  const path = opts?.path ?? defaultIndexPath();
  const index = loadIndex(path);
  const perSource = opts?.perSource ?? 4;
  const maxChunks = opts?.maxChunks ?? 16;
  const query = opts?.query ?? "";
  const qTokens = query ? tokenize(query) : [];

  const bySource = new Map<string, RagChunk[]>();
  for (const chunk of index.chunks) {
    const base = chunkBaseSource(chunk.source);
    const matched = sources.find((s) => base === s || base.startsWith(s + "/"));
    if (!matched) continue;
    const list = bySource.get(matched) ?? [];
    list.push(chunk);
    bySource.set(matched, list);
  }

  const scored: RetrievedChunk[] = [];
  for (const src of sources) {
    const chunks = bySource.get(src) ?? [];
    const ranked = chunks
      .map((chunk) => {
        let score = 0.1;
        const lower = chunk.text.toLowerCase();
        const sourceLower = chunk.source.toLowerCase();
        if (qTokens.length > 0) {
          for (const t of qTokens) {
            if (lower.includes(t) || sourceLower.includes(t)) score += 1;
          }
        }
        // Exact ISO date / MMDD hits are decisive for schedule questions
        for (const t of qTokens) {
          if (/^\d{4}-\d{2}-\d{2}$/.test(t) && lower.includes(t)) score += 500;
          // Year folder / text (2026)
          if (/^20\d{2}$/.test(t) && (lower.includes(t) || sourceLower.includes(t))) score += 15;
          // MMDD token (0205) from expandDateQuery
          if (/^(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])$/.test(t) && (lower.includes(t) || sourceLower.includes(t))) {
            score += 40;
          }
        }
        return { chunk, score };
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, perSource);
    scored.push(...ranked);
  }

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, maxChunks);
}

/** Merge KG-sourced chunks with BM25 hits; keep primary first, then fill with secondary. */
export function mergeRetrieved(
  primary: RetrievedChunk[],
  secondary: RetrievedChunk[],
  topK = 10,
): RetrievedChunk[] {
  const out: RetrievedChunk[] = [];
  const seen = new Set<string>();
  for (const r of primary) {
    if (seen.has(r.chunk.id)) continue;
    seen.add(r.chunk.id);
    // Prefer routed sources strongly over raw BM25
    out.push({ ...r, score: r.score + 1000 });
  }
  for (const r of secondary) {
    if (seen.has(r.chunk.id)) continue;
    seen.add(r.chunk.id);
    out.push(r);
  }
  return out.sort((a, b) => b.score - a.score).slice(0, topK);
}

/** Truncate retrieved texts to a character budget for LLM context. */
export function truncateRetrieved(
  retrieved: RetrievedChunk[],
  maxChars = 14000,
): RetrievedChunk[] {
  const out: RetrievedChunk[] = [];
  let used = 0;
  for (const r of retrieved) {
    const len = r.chunk.text.length;
    if (used + len > maxChars && out.length > 0) break;
    if (used + len > maxChars) {
      out.push({
        ...r,
        chunk: { ...r.chunk, text: r.chunk.text.slice(0, Math.max(0, maxChars - used)) },
      });
      break;
    }
    out.push(r);
    used += len;
  }
  return out;
}

/**
 * Expand hits with neighboring chunks from the same source (by :N index)
 * so calendar / long docs don't lose surrounding context.
 */
export function expandWithNeighbors(
  hits: RetrievedChunk[],
  opts?: { radius?: number; path?: string; maxExtra?: number },
): RetrievedChunk[] {
  if (hits.length === 0) return hits;
  const radius = opts?.radius ?? 2;
  const maxExtra = opts?.maxExtra ?? 24;
  const path = opts?.path ?? defaultIndexPath();
  const index = loadIndex(path);

  const bySource = new Map<string, RagChunk[]>();
  for (const chunk of index.chunks) {
    const base = chunkBaseSource(chunk.source);
    const list = bySource.get(base) ?? [];
    list.push(chunk);
    bySource.set(base, list);
  }
  for (const [, list] of bySource) {
    list.sort((a, b) => {
      const ia = Number((a.id.match(/:(\d+)$/) || [])[1] ?? 0);
      const ib = Number((b.id.match(/:(\d+)$/) || [])[1] ?? 0);
      return ia - ib;
    });
  }

  const out: RetrievedChunk[] = [];
  const seen = new Set<string>();
  let extra = 0;
  for (const hit of hits) {
    if (!seen.has(hit.chunk.id)) {
      seen.add(hit.chunk.id);
      out.push(hit);
    }
    const base = chunkBaseSource(hit.chunk.source);
    const list = bySource.get(base);
    if (!list || list.length <= 1) continue;
    const idx = list.findIndex((c) => c.id === hit.chunk.id);
    if (idx < 0) continue;
    for (let d = 1; d <= radius; d += 1) {
      for (const j of [idx - d, idx + d]) {
        if (j < 0 || j >= list.length) continue;
        const chunk = list[j]!;
        if (seen.has(chunk.id)) continue;
        if (extra >= maxExtra) break;
        seen.add(chunk.id);
        out.push({ chunk, score: hit.score * 0.85 });
        extra += 1;
      }
    }
  }
  return out;
}
