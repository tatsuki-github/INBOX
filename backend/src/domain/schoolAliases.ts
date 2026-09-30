/**
 * 学校・チーム名の表記揺れを正規化する。
 * 荒玉コーパスの短名（荒尾四 / 玉高附属）を正とし、
 * トラック所属一覧などでは recordName（荒尾第四中 等）へ戻せるようにする。
 */

export type SchoolAliasGroup = {
  /** 荒玉 transcript / prepared FAQ 側の正規名 */
  canon: string;
  /** 長い表記を先に置く（部分置換事故防止） */
  aliases: string[];
  /** arato-tamana-teams 等の所属ファイル名（中付き） */
  recordName?: string;
};

/** 荒玉地区の主な表記揺れ。追加はここに集約する。 */
export const SCHOOL_ALIAS_GROUPS: SchoolAliasGroup[] = [
  {
    canon: "荒尾四",
    aliases: ["荒尾第四中学校", "荒尾第四中", "荒尾第四", "荒尾四中", "荒尾4中", "荒尾４中"],
    recordName: "荒尾第四中",
  },
  {
    canon: "荒尾三",
    aliases: ["荒尾第三中学校", "荒尾第三中", "荒尾第三", "荒尾三中", "荒尾3中", "荒尾３中"],
    recordName: "荒尾三中",
  },
  {
    canon: "荒尾海陽",
    aliases: ["荒尾海陽中学校", "荒尾海陽中"],
    recordName: "荒尾海陽中",
  },
  {
    canon: "玉高附属",
    aliases: [
      "玉名高校附属中学校",
      "玉名高校附属中",
      "玉名高校附属",
      "玉名付属中学校",
      "玉名付属中",
      "玉名附属中学校",
      "玉名附属中",
      "玉名付属",
      "玉名附属",
      "玉高附中",
      "玉名附中",
      "玉名附",
      "玉名付中",
      "付属中",
      "附属中",
      "附中",
    ],
    recordName: "玉名附中",
  },
  {
    canon: "岱明",
    aliases: ["岱明中学校", "岱明中", "いだてん岱明"],
    recordName: "岱明中",
  },
  {
    canon: "南関",
    aliases: ["南関中学校", "南関中"],
    recordName: "南関中",
  },
  {
    canon: "天水",
    aliases: ["天水中学校", "天水中"],
    recordName: "天水中",
  },
  {
    canon: "有明",
    aliases: ["有明中学校", "有明中"],
    recordName: "有明中",
  },
  {
    canon: "菊水",
    aliases: ["菊水中学校", "菊水中"],
    recordName: "菊水中",
  },
  {
    canon: "長洲",
    aliases: ["長洲中学校", "長洲中"],
    recordName: "長洲中",
  },
  {
    canon: "玉名",
    aliases: ["玉名中学校", "玉名中"],
    recordName: "玉名中",
  },
  {
    canon: "玉陵",
    aliases: ["玉陵中学校", "玉陵中"],
    recordName: "玉陵中",
  },
  {
    canon: "玉南",
    aliases: ["玉南中学校", "玉南中"],
    recordName: "玉南中",
  },
  {
    canon: "玉東",
    aliases: ["玉東中学校", "玉東中"],
    recordName: "玉東中",
  },
  {
    canon: "三加和",
    aliases: ["三加和中学校", "三加和中"],
  },
];

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** すべての別名 → 正規名（長い表記優先）。 */
export function canonicalizeSchoolNames(text: string): string {
  let out = text.normalize("NFKC");
  const pairs: { from: string; to: string }[] = [];
  for (const group of SCHOOL_ALIAS_GROUPS) {
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

/** 質問に含まれる学校の所属一覧用ファイル名（あれば）。 */
export function resolveSchoolRecordName(text: string): string | undefined {
  const q = text.normalize("NFKC");
  // 長い表記から判定
  const candidates: { name: string; key: string }[] = [];
  for (const group of SCHOOL_ALIAS_GROUPS) {
    if (!group.recordName) continue;
    candidates.push({ name: group.recordName, key: group.recordName });
    candidates.push({ name: group.recordName, key: group.canon });
    for (const alias of group.aliases) {
      candidates.push({ name: group.recordName, key: alias });
    }
  }
  candidates.sort((a, b) => b.key.length - a.key.length);
  for (const c of candidates) {
    if (q.includes(c.key)) return c.name;
  }
  return undefined;
}

/** preparedQa 用: [正規名, ...別名]（長い別名を先に）。 */
export function schoolSynonymGroups(): string[][] {
  return SCHOOL_ALIAS_GROUPS.map((g) => {
    const alts = [...g.aliases].sort((a, b) => b.length - a.length);
    return [g.canon, ...alts.filter((a) => a !== g.canon)];
  });
}

/** 検索クエリに別名トークンを足す（BM25 用）。 */
export function expandSchoolAliasQuery(text: string): string {
  const q = text.normalize("NFKC");
  const extras: string[] = [];
  for (const group of SCHOOL_ALIAS_GROUPS) {
    const keys = [group.canon, ...group.aliases, group.recordName].filter(Boolean) as string[];
    if (!keys.some((k) => q.includes(k))) continue;
    for (const k of keys) {
      if (!q.includes(k) && !extras.includes(k)) extras.push(k);
    }
  }
  if (extras.length === 0) return text;
  return `${text} ${extras.join(" ")}`.trim();
}

/** テスト・デバッグ用 */
export function schoolAliasPattern(): RegExp {
  const keys = SCHOOL_ALIAS_GROUPS.flatMap((g) => [g.canon, ...g.aliases, g.recordName ?? []]).flat();
  const uniq = [...new Set(keys)].sort((a, b) => b.length - a.length).map(escapeRegExp);
  return new RegExp(uniq.join("|"), "g");
}
