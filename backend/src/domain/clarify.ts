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
  /自己ベスト|ベストタイム|自己記録|ベスト記録|ベスト|記録|タイム|距離|何|誰|自分|私|俺|教えて|知りたい|について|ですか|でしょうか|どの|どれ|最新|今季|今年度|今年|去年|昨年|SB|PB|は|を|の|が|に|で|と|も|って|か|？|\?|！|!|。|．|…|・|\s+/gi;

function hasAthleteNameCue(question: string): boolean {
  const q = question.normalize("NFKC");
  // 「今村昇磨の1500m」「石川のSB」— exclude pronouns like 自分の / 私の
  const named = q.match(/([\u4e00-\u9fff]{2,4})(さん|くん|ちゃん|君)?の/g) ?? [];
  for (const m of named) {
    const base = m.replace(/(さん|くん|ちゃん|君)?の$/, "");
    if (!/^(自分|私|俺|僕|あたし|だれ|誰|何|何時)$/.test(base)) return true;
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

/** Match underspecified questions that should return example phrasings. */
export function matchClarifyAnswer(question: string): ClarifyResult | null {
  if (isUnderspecifiedPersonalBestQuestion(question)) {
    return {
      id: "clarify-personal-best",
      text: buildPersonalBestClarifyText(),
    };
  }
  return null;
}
