/**
 * Underspecified questions → concrete question examples (LINE-friendly).
 * e.g. 「自分の自己ベストは？」 lacks athlete name / distance.
 */

export type ClarifyResult = {
  id: string;
  text: string;
};

const PB_TOPIC_RE = /自己ベスト|ベストタイム|自己記録|\bSB\b|\bPB\b|ベスト記録/;

/** Words/particles that are not athlete names when stripped for name detection. */
const NON_NAME_RE =
  /自己ベスト|ベストタイム|自己記録|ベスト記録|ベスト|記録|タイム|距離|何|誰|自分|私|俺|教えて|知りたい|調べたい|について|ですか|でしょうか|どの|どれ|最新|今季|今年度|今年|去年|昨年|SB|PB|は|を|の|が|に|で|と|も|って|か|？|\?|！|!|。|．|…|・|\s+/gi;

/** Temporal / meta nouns that look like「Xの」but are not athlete names. */
const NON_NAME_PREFIXES = new Set([
  "自分",
  "私",
  "俺",
  "僕",
  "あたし",
  "だれ",
  "誰",
  "何",
  "何時",
  "最新",
  "今季",
  "今年度",
  "今年",
  "去年",
  "昨年",
  "前回",
  "今回",
  "来年",
  "再来年",
]);

function hasAthleteNameCue(question: string): boolean {
  const q = question.normalize("NFKC");
  // 「今村昇磨の1500m」「石川のSB」— exclude pronouns / temporal like 自分の / 最新の
  const named = q.match(/([\u4e00-\u9fff]{2,4})(さん|くん|ちゃん|君)?の/g) ?? [];
  for (const m of named) {
    const base = m.replace(/(さん|くん|ちゃん|君)?の$/, "");
    if (!NON_NAME_PREFIXES.has(base)) return true;
  }
  const leftover = q.replace(NON_NAME_RE, "").replace(/\d+m?/gi, "");
  // At least 2 kanji/kana left that look like a name
  return /[\u4e00-\u9fff]{2,}/.test(leftover) || /[ァ-ヶー]{3,}/.test(leftover);
}

/** True when the user asks about PB/SB without naming who (or enough detail). */
export function isUnderspecifiedPersonalBestQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;

  const isPbTopic =
    PB_TOPIC_RE.test(q) ||
    /^ベスト([はをって]?[？?！!。．]*)?$/i.test(q) ||
    /(^|[^ぁ-ん])ベスト([はをっ？?]|$)/.test(q);

  if (!isPbTopic) return false;
  if (hasAthleteNameCue(q)) return false;
  return true;
}

export function buildPersonalBestClarifyText(): string {
  return [
    "誰の・どの距離の自己ベストか具体的に書いてください。",
    "例:",
    "・今村昇磨の1500m自己ベストは？",
    "・石川隼の3000mのSBは？",
    "・〇〇の800mベストタイムは？",
  ].join("\n");
}

/** Vague “look up records” without athlete / distance. */
export function isUnderspecifiedRecordLookupQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (!/(記録を調べ|記録が知り|記録知り|記録教えて|記録みたい|記録見たい|記録を見)/.test(q)) {
    return false;
  }
  if (hasAthleteNameCue(q)) return false;
  return true;
}

/** Match underspecified questions that should return example phrasings. */
export function matchClarifyAnswer(question: string): ClarifyResult | null {
  if (isUnderspecifiedPersonalBestQuestion(question)) {
    return {
      id: "clarify-personal-best",
      text: buildPersonalBestClarifyText(),
    };
  }
  if (isUnderspecifiedRecordLookupQuestion(question)) {
    return {
      id: "clarify-record-lookup",
      text: buildPersonalBestClarifyText(),
    };
  }
  return null;
}
