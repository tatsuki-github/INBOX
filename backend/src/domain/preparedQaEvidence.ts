import type { PreparedQaMatch } from "./preparedQa.js";
import type { KgQueryResult } from "../kg/query.js";
import { mapRefsToCorpusSources } from "../kg/mapRefs.js";
import { RETRIEVAL_BUDGET } from "../rag/budget.js";
import {
  expandWithNeighbors, mergeRetrieved, retrieveBySources,
  retrieveContext, truncateRetrieved, type RetrievedChunk,
} from "../rag/retrieve.js";

/** Read the QA's primary references and the KG's routed documents, not KG hints. */
export function retrievePreparedEvidence(
  question: string,
  prepared: PreparedQaMatch,
  kg: KgQueryResult,
  retrieve: (question: string, topK?: number) => RetrievedChunk[] = retrieveContext,
): RetrievedChunk[] {
  const options = {
    query: question,
    perSource: RETRIEVAL_BUDGET.perSource,
    maxChunks: RETRIEVAL_BUDGET.maxChunks,
  };
  // Separate retrieval keeps broad KG hubs from crowding out the QA's references.
  const primary = retrieveBySources(mapRefsToCorpusSources(prepared.sources), options);
  const graph = retrieveBySources([...new Set([
    ...kg.corpus_sources, ...mapRefsToCorpusSources(kg.refs),
  ])], options);
  const relevant = retrieve(question, RETRIEVAL_BUDGET.topK);
  const merged = mergeRetrieved(primary, mergeRetrieved(graph, relevant, RETRIEVAL_BUDGET.maxChunks, {
    query: question, preferPrimaryOrder: true,
  }), RETRIEVAL_BUDGET.maxChunks, { query: question, preferPrimaryOrder: true });
  const withNeighbors = expandWithNeighbors(merged, {
    radius: RETRIEVAL_BUDGET.neighborRadius,
    maxExtra: RETRIEVAL_BUDGET.neighborMaxExtra,
    query: question,
  });
  // A generated FAQ copy is not independent corroboration of its own answer.
  return truncateRetrieved(withNeighbors.filter((row) =>
    !/(?:^|\/)faq\//.test(row.chunk.source) && !/prepared-qa\./.test(row.chunk.source),
  ), RETRIEVAL_BUDGET.maxChars);
}
