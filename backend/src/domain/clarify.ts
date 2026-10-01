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

function isUnderspecifiedMiddleSchoolSbQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!/中学生/.test(q) || !/\bSB\b|シーズンベスト/.test(q)) return false;
  if (/とは|の意味|何の略/.test(q)) return false;
  if (/20\d{2}|\d+\s*(?:m|km|メートル|キロ)|800|1500|3000|5000|男子|女子/.test(q)) return false;
  const subject = q.replace(/中学生|シーズンベスト|全記録|全データ|一覧|記録|データ|SB|提示して|提示|出して|欲しい|を|は|が|に|の|で|と|も|見せて|見たい|みたい|教えて|知りたい|調べて|全部|全て|すべて|ください|？|\?|。|！|!|\s+/giu, " ");
  return !hasAthleteNameCue(subject);
}

function buildMiddleSchoolSbClarifyText(): string {
  return [
    "どの選手・距離・所属の中学生SBか指定してください。",
    "例:",
    "・岱明中の男子1500m SB一覧は？",
    "・内田健太の3000m SBは？",
    "・女子800mのSB上位20人は？",
  ].join("\n");
}

/** Vague meet-result questions without a concrete meet name. */
export function isUnderspecifiedMeetResultQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  // Ultra-short forms first (「結果」itself looks like a 2-kanji "name" to cues).
  if (
    /^(?:大会の)?(?:結果|順位|成績)(?:は|を|って|教えて|知りたい)?[？?！!。．]*$/u.test(
      q,
    ) ||
    /^(?:誰が|どの(?:学校|チーム)が)?(?:勝った|優勝)(?:の|か)?[？?！!。．]*$/u.test(
      q,
    )
  ) {
    return true;
  }
  if (!/(?:結果|順位|何位|成績)/.test(q)) return false;
  // Already names a known meet / school / athlete cue → let prepared/RAG handle.
  if (
    /荒玉|なごみ|ジュニア|ナイター|金栗|県中|通信|選手権|岱明|南関|玉名|長洲|菊水|有明|玉陵|玉東|玉南|荒尾|天水|三加和|腹栄/.test(
      q,
    )
  ) {
    return false;
  }
  if (/20\d{2}|去年|昨年|今年|今年度/.test(q) && /大会|駅伝|記録会/.test(q)) {
    return false;
  }
  return false;
}

export function buildMeetResultClarifyText(): string {
  return [
    "どの大会の結果か、大会名を付けて聞いてください。",
    "例:",
    "・なごみ駅伝の結果は？",
    "・2025年荒玉駅伝男子の岱明は何位？",
    "・ジュニア駅伝の結果は？",
    "・玉名郡ナイターの結果は？",
  ].join("\n");
}

/** Vague schedule questions without event name. */
export function isUnderspecifiedScheduleQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (!/(?:いつ|日程|予定|カレンダー)/.test(q)) return false;
  if (
    /荒玉|なごみ|ジュニア|ナイター|金栗|県中|練習|大会|駅伝|記録会|今週|今月|今日|明日/.test(
      q,
    )
  ) {
    return false;
  }
  return /^(?:いつ|日程|予定)(?:は|を|って|教えて|知りたい)?[？?！!。．]*$/u.test(q);
}

export function buildScheduleClarifyText(): string {
  return [
    "どの予定か、大会名や日付を付けて聞いてください。",
    "例:",
    "・荒玉駅伝はいつ？",
    "・ジュニア駅伝の日程は？",
    "・今週の練習は？",
    "・2026-10-14の予定は？",
  ].join("\n");
}

/** Vague order / lineup questions without school+year. */
export function isUnderspecifiedOrderQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (!/(?:オーダー|区間メンバー|誰が何区|メンバー表)/.test(q)) return false;
  if (
    /岱明|南関|玉名|長洲|菊水|有明|玉陵|玉東|玉南|荒尾|天水|三加和|腹栄|玉高|20\d{2}|去年|昨年|今年/.test(
      q,
    )
  ) {
    return false;
  }
  return true;
}

export function buildOrderClarifyText(): string {
  return [
    "どの年・学校のオーダーか指定してください。",
    "例:",
    "・2025年荒玉男子の岱明のオーダーは？",
    "・岱明の2026荒玉暫定オーダーは？",
    "・2025年荒玉女子の南関5区は誰？",
  ].join("\n");
}

/** Match underspecified questions that should return example phrasings. */
export function matchClarifyAnswer(question: string): ClarifyResult | null {
  if (isUnderspecifiedMiddleSchoolSbQuestion(question)) {
    return {
      id: "clarify-middle-school-sb",
      text: buildMiddleSchoolSbClarifyText(),
    };
  }
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
  if (isUnderspecifiedMeetResultQuestion(question)) {
    return {
      id: "clarify-meet-result",
      text: buildMeetResultClarifyText(),
    };
  }
  if (isUnderspecifiedScheduleQuestion(question)) {
    return {
      id: "clarify-schedule",
      text: buildScheduleClarifyText(),
    };
  }
  if (isUnderspecifiedOrderQuestion(question)) {
    return {
      id: "clarify-order",
      text: buildOrderClarifyText(),
    };
  }
  return null;
}
