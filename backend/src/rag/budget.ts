/**
 * LLM に渡すコーパス抜粋の取得幅。
 * maxChars=100k を実質埋めるため、topK / ソース内件数 / 近傍も合わせて広げている。
 * （avg≈540字チャンクなら topK+neighbors で約 10万字規模まで供給可能）
 */
export const RETRIEVAL_BUDGET = {
  maxChars: 100_000,
  topK: 64,
  routeSources: 24,
  perSource: 12,
  maxChunks: 96,
  neighborRadius: 2,
  neighborMaxExtra: 160,
} as const;
