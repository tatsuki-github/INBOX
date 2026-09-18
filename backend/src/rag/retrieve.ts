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
  // Keep CJK runs and alnum tokens
  const tokens = lower.match(/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}]+|[\w\d]+/gu);
  if (!tokens) {
    return [];
  }
  // Further split long CJK into bigrams for better recall
  const out: string[] = [];
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
