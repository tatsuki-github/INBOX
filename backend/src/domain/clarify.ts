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

/**
 * CJK Unified + Extension A + Compatibility Ideographs + rare Ext B (𠮷 etc.).
 * Includes single-kanji surnames (森/旭/俵) and 﨑/髙-style compat forms.
 */
const CJK_NAME_CHAR =
  "[\\u3400-\\u9fff\\uf900-\\ufaff\\u{20000}-\\u{2fa1f}]";

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
  "今",
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

const NAME_TOKEN = `(?:[A-Za-z]{2,}|[ァ-ヶヴー]{1,8}|${CJK_NAME_CHAR}{1,8})`;

function hasAthleteNameCue(question: string): boolean {
  // Keep original codepoints (compat ideographs / Ext B); NFKC can erase name cues.
  const q = question.trim();
  // 「森の3000m」「小﨑のSB」「FESTUSの5000m」「ヴの3000m」「杉𠮷（STR）の」
  const namedRe = new RegExp(
    `(${NAME_TOKEN})(さん|くん|ちゃん|君)?の`,
    "gu",
  );
  const named = q.match(namedRe) ?? [];
  for (const m of named) {
    const base = m.replace(/(さん|くん|ちゃん|君)?の$/u, "");
    if (!NON_NAME_PREFIXES.has(base)) return true;
  }
  // Affiliation form: 森（鎮西学院）の / 杉𠮷（STR）の
  const affilRe = new RegExp(
    `(${NAME_TOKEN})[（(][^）)]{1,24}[）)]の`,
    "u",
  );
  const affil = q.match(affilRe);
  if (affil?.[1] && !NON_NAME_PREFIXES.has(affil[1])) return true;

  const leftoverRaw = q
    .replace(NON_NAME_RE, "")
    .replace(/\d+\s*m?/gi, "")
    .replace(/[（(][^）)]*[）)]/g, "");
  const cjk2 = new RegExp(`${CJK_NAME_CHAR}{2,}`, "u");
  const hasDist = /\d+\s*(m|km)|キロ/i.test(q);
  const cjk1WithDist =
    hasDist && new RegExp(`${CJK_NAME_CHAR}`, "u").test(leftoverRaw);
  const kana1WithDist = hasDist && /[ァ-ヶヴー]/.test(leftoverRaw);
  return (
    cjk2.test(leftoverRaw) ||
    cjk1WithDist ||
    kana1WithDist ||
    /[ァ-ヶヴー]{3,}/.test(leftoverRaw) ||
    /[A-Za-z]{2,}/.test(leftoverRaw)
  );
}

/** True when the user asks about PB/SB without naming who (or enough detail). */
export function isUnderspecifiedPersonalBestQuestion(question: string): boolean {
  const raw = question.trim();
  const q = raw.normalize("NFKC");
  if (!q) return false;

  const isPbTopic =
    PB_TOPIC_RE.test(q) ||
    /^ベスト([はをって]?[？?！!。．]*)?$/i.test(q) ||
    /(^|[^ぁ-ん])ベスト([はをっ？?]|$)/.test(q);

  if (!isPbTopic) return false;
  // Check both raw (compat/Ext B) and NFKC forms for name cues.
  if (hasAthleteNameCue(raw) || hasAthleteNameCue(q)) return false;
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
  if (!/(?:記録|成績)/.test(q)) {
    return false;
  }
  if (/\d+\s*(?:m|km|メートル|キロ)|男子|女子|学校|チーム|大会|駅伝|練習会/.test(q)) {
    return false;
  }
  const subject = q.replace(/全?選手|陸上|トラック|記録一覧|記録|成績|一覧|を|は|が|に|の|で|と|も|見せて|見たい|みたい|教えて|知りたい|調べて|知り|全部|全て|すべて|ください|？|\?|。|！|!|\s+/gu, " ");
  if (hasAthleteNameCue(subject)) return false;
  return true;
}

export function buildRecordLookupClarifyText(): string {
  return [
    "どの選手・種目の記録か具体的に書いてください。",
    "例:",
    "・今村昇磨の1500mの記録は？",
    "・女子3000mの荒玉地区ランキングは？",
    "・岱明中の全選手の記録一覧は？",
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
  if (isUnderspecifiedRecordLookupQuestion(question)) {
    return {
      id: "clarify-record-lookup",
      text: buildRecordLookupClarifyText(),
    };
  }
  return null;
}
