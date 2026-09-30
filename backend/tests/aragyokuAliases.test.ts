import { beforeEach, describe, expect, it } from "vitest";
import { canonicalizeAragyokuNames } from "../src/domain/aragyokuAliases.js";
import {
  matchPreparedAnswer,
  normalizePreparedQuestion,
  resetPreparedQaCache,
} from "../src/domain/preparedQa.js";

describe("canonicalizeAragyokuNames", () => {
  it("maps long forms to 荒玉 without duplicating tokens", () => {
    // NFKC で全角？→半角? になる
    expect(canonicalizeAragyokuNames("荒玉中体連駅伝って何？")).toBe("荒玉って何?");
    expect(canonicalizeAragyokuNames("玉名荒尾中体連駅伝って何？")).toBe("荒玉って何?");
    expect(canonicalizeAragyokuNames("郡市駅伝って何？")).toBe("荒玉って何?");
    expect(canonicalizeAragyokuNames("荒玉駅伝って何？")).toBe("荒玉って何?");
    expect(canonicalizeAragyokuNames("荒玉中体連駅伝って何？")).not.toContain("荒玉荒玉");
  });
});

describe("preparedQa aragyoku aliases", () => {
  beforeEach(() => {
    resetPreparedQaCache();
  });

  it("normalizes alias forms to the same token as 荒玉駅伝", () => {
    const base = normalizePreparedQuestion("荒玉駅伝って何？", { defaultYear: 2026 });
    for (const q of [
      "荒玉中体連駅伝って何？",
      "玉名荒尾中体連駅伝って何？",
      "郡市駅伝って何？",
      "荒玉郡市駅伝って何？",
    ]) {
      expect(normalizePreparedQuestion(q, { defaultYear: 2026 }), q).toBe(base);
    }
  });

  it("hits 荒玉 FAQ from 郡市駅伝 / 中体連 wording", () => {
    for (const q of [
      "荒玉中体連駅伝って何？",
      "郡市駅伝って何？",
      "玉名荒尾中体連駅伝って何？",
      "荒玉駅伝と荒玉中体連駅伝は同じ？",
      "郡市駅伝は荒玉駅伝のこと？",
    ]) {
      const hit = matchPreparedAnswer(q, { defaultYear: 2026 });
      expect(hit?.id, q).toMatch(/^(aragyoku-what|aragyoku-alias-same)$/);
      expect(hit?.text, q).toMatch(/荒玉|中体連|郡市/);
    }
  });

  it("keeps other aragyoku prepared hits when asked with aliases", () => {
    const pref = matchPreparedAnswer("郡市駅伝で何位まで県駅伝に出られる？", {
      defaultYear: 2026,
    });
    expect(pref?.id).toMatch(/^aragyoku-pref-top2-/);
    expect(pref?.text).toContain("2位まで");

    const rivals = matchPreparedAnswer(
      "荒玉中体連駅伝で岱明中とライバルになりそうな学校は？",
      { defaultYear: 2026 },
    );
    expect(rivals?.id).toBe("daiming-rivals-core");
    expect(rivals?.text).toContain("荒尾三");
  });
});
