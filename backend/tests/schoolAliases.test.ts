import { beforeEach, describe, expect, it } from "vitest";
import {
  canonicalizeSchoolNames,
  resolveSchoolRecordName,
} from "../src/domain/schoolAliases.js";
import {
  matchPreparedAnswer,
  normalizePreparedQuestion,
  resetPreparedQaCache,
} from "../src/domain/preparedQa.js";
import { answerQuestion } from "../src/domain/answer.js";
import { resetKgCache } from "../src/kg/query.js";
import { resetRetrieverCache } from "../src/rag/retrieve.js";

describe("canonicalizeSchoolNames", () => {
  it("maps 荒尾第四 / 荒尾四中 to 荒尾四", () => {
    expect(canonicalizeSchoolNames("荒尾第四の順位は？")).toContain("荒尾四");
    expect(canonicalizeSchoolNames("荒尾第四中の選手一覧")).toContain("荒尾四");
    expect(canonicalizeSchoolNames("荒尾四中の結果")).toContain("荒尾四");
    expect(canonicalizeSchoolNames("荒尾第四中の選手一覧")).not.toContain("第四");
  });

  it("maps 荒尾第三 variants to 荒尾三", () => {
    expect(canonicalizeSchoolNames("荒尾第三中のSB")).toContain("荒尾三");
    expect(canonicalizeSchoolNames("荒尾三中の選手")).toContain("荒尾三");
  });

  it("keeps 玉高附属 as the 付属 canon", () => {
    expect(canonicalizeSchoolNames("玉名付属中の順位")).toContain("玉高附属");
    expect(canonicalizeSchoolNames("玉名附属の選手")).toContain("玉高附属");
  });
});

describe("resolveSchoolRecordName", () => {
  it("resolves short and long forms to the track digest filename", () => {
    expect(resolveSchoolRecordName("荒尾四の選手一覧")).toBe("荒尾第四中");
    expect(resolveSchoolRecordName("荒尾第四中の選手一覧")).toBe("荒尾第四中");
    expect(resolveSchoolRecordName("荒尾三のSB一覧")).toBe("荒尾三中");
  });
});

describe("preparedQa school aliases", () => {
  beforeEach(() => {
    resetPreparedQaCache();
  });

  it("normalizes 荒尾第四 into the same token as 荒尾四", () => {
    const a = normalizePreparedQuestion("2025年荒玉男子の荒尾四は何位？", { defaultYear: 2026 });
    const b = normalizePreparedQuestion("2025年荒玉男子の荒尾第四は何位？", { defaultYear: 2026 });
    const c = normalizePreparedQuestion("2025年荒玉男子の荒尾四中は何位？", { defaultYear: 2026 });
    expect(a).toBe(b);
    expect(a).toBe(c);
  });

  it("hits the 荒尾四 rank FAQ from 荒尾第四 wording", () => {
    for (const q of [
      "2025年荒玉駅伝男子の荒尾第四は何位？",
      "2025年荒玉男子荒尾四中の順位は？",
      "2025年の荒玉男子で荒尾第四中の成績は？",
    ]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toBe("aragyoku-2025-男子-team-荒尾四-rank");
      expect(hit?.text, q).toContain("10位");
    }
  });
});

describe("answerQuestion school aliases", () => {
  async function ask(question: string) {
    resetKgCache();
    resetRetrieverCache();
    resetPreparedQaCache();
    return answerQuestion(question, { defaultYear: 2026, llm: null, skipRouter: true });
  }

  it("routes 荒尾第四中 player lists to prepared roster (or school digest)", async () => {
    const result = await ask("荒尾第四中の選手一覧");
    expect(result.sources?.[0]).toMatch(
      /^(?:prepared:roster-aff-荒尾第四中|out-analysis\/arato-tamana-teams\/荒尾第四中\.md)$/,
    );
    expect(result.text).toContain("荒尾第四中");
  });

  it("routes 荒尾四中 alias to the same roster / school digest", async () => {
    const result = await ask("荒尾四中の選手一覧");
    expect(result.sources?.[0]).toMatch(
      /^(?:prepared:roster-aff-荒尾第四中|out-analysis\/arato-tamana-teams\/荒尾第四中\.md)$/,
    );
  });
});
