/**
 * 荒玉駅伝の大会名表記揺れを正規化する。
 * 通称・正式寄りの呼び方が混在するため、質問側を「荒玉」へ揃える。
 *
 * 例: 荒玉中体連駅伝 / 玉名荒尾中体連駅伝 / 郡市駅伝 → 荒玉
 */

export type AragyokuAliasGroup = {
  /** prepared FAQ・正規化後の短い正規名 */
  canon: string;
  /** 長い表記を先に（部分置換事故防止）。canonicalize 側でも再ソートする */
  aliases: string[];
};

/** 荒玉駅伝の主な呼び方。追加はここに集約する。 */
export const ARAGYOKU_ALIAS_GROUPS: AragyokuAliasGroup[] = [
  {
    canon: "荒玉",
    aliases: [
      "玉名・荒尾中体連駅伝",
      "玉名荒尾中体連駅伝",
      "荒玉中体連駅伝（玉名荒尾）",
      "荒玉中体連駅伝(玉名荒尾)",
      "荒玉中体連駅伝",
      "荒玉郡市駅伝",
      "郡市駅伝",
      "中体連駅伝",
      "荒玉駅伝",
      "荒玉中体連",
    ],
  },
];

/** すべての別名 → 正規名（長い表記優先）。 */
export function canonicalizeAragyokuNames(text: string): string {
  let out = text.normalize("NFKC");
  const pairs: { from: string; to: string }[] = [];
  for (const group of ARAGYOKU_ALIAS_GROUPS) {
    for (const alias of group.aliases) {
      if (alias === group.canon) continue;
      pairs.push({ from: alias, to: group.canon });
    }
  }
  pairs.sort((a, b) => b.from.length - a.from.length);
  for (const { from, to } of pairs) {
    out = out.split(from).join(to);
  }
  return out;
}

/** preparedQa 用: [正規名, ...別名]（長い別名を先に）。 */
export function aragyokuSynonymGroups(): string[][] {
  return ARAGYOKU_ALIAS_GROUPS.map((g) => {
    const alts = [...g.aliases].sort((a, b) => b.length - a.length);
    return [g.canon, ...alts.filter((a) => a !== g.canon)];
  });
}

/** 検索クエリに別名トークンを足す（BM25 用）。 */
export function expandAragyokuAliasQuery(text: string): string {
  const q = text.normalize("NFKC");
  const extras: string[] = [];
  for (const group of ARAGYOKU_ALIAS_GROUPS) {
    const keys = [group.canon, ...group.aliases];
    if (!keys.some((k) => q.includes(k))) continue;
    for (const k of keys) {
      if (!q.includes(k) && !extras.includes(k)) extras.push(k);
    }
  }
  if (extras.length === 0) return text;
  return `${text} ${extras.join(" ")}`.trim();
}
