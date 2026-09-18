/**
 * Map knowledge-graph refs (repo-relative) to rag_index chunk.source paths
 * under input/idaten-corpus/. Unmappable / unsafe refs return null.
 */

const CORPUS_PREFIXES = [
  "calendar/",
  "drive-text/",
  "ekiden-ocr/",
  "aragyoku/",
  "notion-db/",
  "notion-pages/",
  "analysis-ocr/",
  "practice/",
  "sb/",
  "docs/",
  "media-manifest.slim.json",
] as const;

function normalizeSlashes(p: string): string {
  return p.replace(/\\/g, "/").replace(/^\.\//, "");
}

function isSafeRelative(p: string): boolean {
  if (!p || p.startsWith("/") || p.includes("\0")) return false;
  const parts = p.split("/");
  return !parts.some((seg) => seg === ".." || seg === "");
}

function looksLikeCorpusSource(p: string): boolean {
  return CORPUS_PREFIXES.some((pref) => p === pref.replace(/\/$/, "") || p.startsWith(pref));
}

/**
 * Convert a KG ref to a corpus-relative source path, or null if not in the packaged index.
 */
export function mapRefToCorpusSource(ref: string): string | null {
  let p = normalizeSlashes(ref.trim());
  if (!isSafeRelative(p)) return null;

  // Strip source: prefix used in some node ids (not usual in refs, but defensive)
  if (p.startsWith("source:")) p = p.slice("source:".length);

  // Already corpus-relative
  if (looksLikeCorpusSource(p)) return p;

  // Packaged corpus root
  if (p.startsWith("input/idaten-corpus/")) {
    const rest = p.slice("input/idaten-corpus/".length);
    return isSafeRelative(rest) && looksLikeCorpusSource(rest) ? rest : null;
  }

  // Calendar events YAML → filtered daiming calendar in corpus
  if (/^input\/events\.\d{4}\.yaml$/.test(p)) {
    return "calendar/events.daiming.yaml";
  }

  // Aragyoku
  if (p.startsWith("input/aragyoku/")) {
    return "aragyoku/" + p.slice("input/aragyoku/".length);
  }

  // Ekiden OCR
  const ekidenOcr = "input/external/notion/media/ekiden-history/ocr/";
  if (p.startsWith(ekidenOcr)) {
    return "ekiden-ocr/" + p.slice(ekidenOcr.length);
  }

  // Notion databases
  const notionDb = "input/external/notion/databases/";
  if (p.startsWith(notionDb)) {
    return "notion-db/" + p.slice(notionDb.length);
  }

  // Notion pages (markdown exports)
  const notionPages = "input/external/notion/pages/";
  if (p.startsWith(notionPages)) {
    return "notion-pages/" + p.slice(notionPages.length);
  }

  // Drive analysis OCR
  const analysis = "input/external/drive/shared/分析/";
  if (p.startsWith(analysis) && p.endsWith(".md")) {
    return "analysis-ocr/" + p.slice(analysis.length);
  }

  // Drive 大会 text
  const taikai = "input/external/drive/shared/大会/";
  if (p.startsWith(taikai)) {
    const rest = p.slice(taikai.length);
    // Prefer .md companions for binaries
    const asMd = rest.match(/\.(pdf|heic|jpg|jpeg|png)$/i) ? `${rest}.md` : rest;
    return "drive-text/大会/" + asMd;
  }

  // Drive personal memos sometimes copied under drive-text/personal
  const personal = "input/external/drive/shared/個人メモ/";
  if (p.startsWith(personal)) {
    return "drive-text/personal/" + p.slice(personal.length).split("/").pop();
  }

  // Docs copied into corpus/docs
  if (p.startsWith("docs/")) {
    const name = p.slice("docs/".length);
    // Only top-level docs that were copied (filename)
    if (!name.includes("/")) return "docs/" + name;
    // ADR etc. may not be in corpus — drop
    return null;
  }

  // Media manifest
  if (p === "input/external/media-manifest.json") {
    return "media-manifest.slim.json";
  }

  return null;
}

/** Dedupe mapped sources preserving order. */
export function mapRefsToCorpusSources(refs: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const ref of refs) {
    const mapped = mapRefToCorpusSource(ref);
    if (mapped && !seen.has(mapped)) {
      seen.add(mapped);
      out.push(mapped);
    }
  }
  return out;
}

export function isAllowedCorpusSource(source: string): boolean {
  const p = normalizeSlashes(source);
  return isSafeRelative(p) && looksLikeCorpusSource(p);
}
