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
  /自己ベスト|ベストタイム|自己記録|ベスト記録|ベスト|記録|タイム|距離|中学生|高校生|小学生|男子|女子|選手|学校|地区|学年|人数|優勝|順位|結果|成績|コース|地図|動画|画像|写真|名簿|作戦|ペース|目標|予想|分析|解説|評価|調子|体調|やる気|顧問|コーチ|先生|進学|志望校|何|誰|自分|私|俺|教えて|知りたい|調べたい|について|ですか|でしょうか|どの|どれ|最新|今季|今年度|今年|去年|昨年|SB|PB|は|を|の|が|に|で|と|も|って|か|？|\?|！|!|。|．|…|・|\s+/gi;

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
  "中学生",
  "高校生",
  "小学生",
  "男子",
  "女子",
  "選手",
  "学校",
  "地区",
  "学年",
  "人数",
  "優勝",
  "順位",
  "結果",
  "成績",
  "距離",
  "コース",
  "地図",
  "動画",
  "画像",
  "写真",
  "名簿",
  "作戦",
  "ペース",
  "目標",
  "予想",
  "分析",
  "解説",
  "評価",
  "調子",
  "体調",
  "やる気",
  "顧問",
  "コーチ",
  "先生",
  "進学",
  "志望校",
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
  if (
    /^(?:中学生|高校生|小学生)(?:の(?:記録|成績|SB|タイム))?(?:は|を|って|教えて|知りたい)?[？?！!。．]*$/iu.test(
      q,
    )
  ) {
    return true;
  }
  if (!/(?:記録|成績)/.test(q)) {
    return false;
  }
  if (/\d+\s*(?:m|km|メートル|キロ)|男子|女子|学校|チーム|大会|駅伝|練習会/.test(q)) {
    return false;
  }
  const subject = q.replace(/全?選手|陸上|トラック|記録一覧|記録|成績|一覧|中学生|高校生|小学生|を|は|が|に|の|で|と|も|見せて|見たい|みたい|教えて|知りたい|調べて|知り|全部|全て|すべて|ください|？|\?|。|！|!|\s+/gu, " ");
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
    /^(?:大会の)?(?:結果|順位|成績|優勝|優勝校|優勝チーム|何位)(?:は|を|って|教えて|知りたい)?[？?！!。．]*$/u.test(
      q,
    ) ||
    /^(?:誰が|どの(?:学校|チーム)が)?(?:勝った|優勝)(?:の|か)?[？?！!。．]*$/u.test(
      q,
    ) ||
    /^(?:地区の)?結果(?:は|を)?[？?！!。．]*$/u.test(q)
  ) {
    return true;
  }
  if (!/(?:結果|順位|何位|成績|優勝)/.test(q)) return false;
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
  // Bare relative day / week without「練習」→ avoid calendar dump.
  if (
    /^(?:今日|明日|今週|今月|次|次の大会)(?:は|を|って|教えて|知りたい)?[？?！!。．]*$/u.test(
      q,
    )
  ) {
    return true;
  }
  if (!/(?:いつ|日程|予定|カレンダー)/.test(q)) return false;
  if (
    /荒玉|なごみ|ジュニア|ナイター|金栗|県中|練習|大会|駅伝|記録会/.test(q)
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
    "・今日の練習メニューは？",
    "・2026-10-14の予定は？",
  ].join("\n");
}

/** Vague order / lineup questions without school+year. */
export function isUnderspecifiedOrderQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (!/(?:オーダー|区間メンバー|誰が何区|メンバー表|^メンバー(?:は|を|って)?)/.test(q)) {
    return false;
  }
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

/** Bare「タイムは？」without athlete / distance. */
export function isUnderspecifiedTimeQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (
    /^(?:タイム|記録タイム|走ったタイム|タイム教えて)(?:は|を|って|教えて|知りたい)?[？?！!。．]*$/u.test(
      q,
    )
  ) {
    return true;
  }
  if (!/タイム/.test(q)) return false;
  if (/\d+\s*(?:m|km|メートル|キロ)|自己ベスト|SB|PB|区間|荒玉|なごみ|ジュニア|ナイター|大会/.test(q)) {
    return false;
  }
  if (hasAthleteNameCue(q)) return false;
  return /タイム(?:は|を|って|教えて|知りたい)?[？?！!。．]*$/u.test(q) && q.length <= 12;
}

export function buildTimeClarifyText(): string {
  return [
    "誰の・どの距離や大会のタイムか具体的に書いてください。",
    "例:",
    "・今村昇磨の1500m自己ベストは？",
    "・2025年荒玉男子1区の区間タイムは？",
    "・松野凛空の3000mのSBは？",
  ].join("\n");
}

/** Named athlete +「タイム/速い」but no distance or meet. */
export function isNamedUnderspecifiedTimeQuestion(question: string): boolean {
  const raw = question.trim();
  const q = raw.normalize("NFKC");
  if (!q) return false;
  if (!/(?:タイム|速い|おそい|遅い|走力)/.test(q)) return false;
  if (/\d+\s*(?:m|km|メートル|キロ)|自己ベスト|SB|PB|区間|荒玉|なごみ|ジュニア|ナイター|大会|記録会/.test(q)) {
    return false;
  }
  if (!(hasAthleteNameCue(raw) || hasAthleteNameCue(q))) return false;
  return true;
}

export function buildNamedTimeClarifyText(): string {
  return [
    "どの距離・大会のタイムか指定してください。",
    "例:",
    "・〇〇の1500m自己ベストは？",
    "・〇〇の3000mのSBは？",
    "・〇〇の荒玉駅伝の区間タイムは？",
  ].join("\n");
}

/** Leg assignment advice without school/year context. */
export function isUnderspecifiedLegAdviceQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (
    !/(?:何区が(?:いい|良い|向いて)|どの区(?:が|を)|区間どう|区どうする|おすすめの区|何区を走|何区走)/.test(
      q,
    )
  ) {
    return false;
  }
  if (
    /岱明|南関|玉名|長洲|菊水|有明|玉陵|玉東|玉南|荒尾|天水|三加和|腹栄|20\d{2}|去年|昨年/.test(
      q,
    )
  ) {
    return false;
  }
  return true;
}

export function buildLegAdviceClarifyText(): string {
  return [
    "区間の適性は資料だけでは断定できません。事実ベースで聞くなら例:",
    "・2025年荒玉男子の岱明のオーダーは？",
    "・荒玉駅伝男子の区間距離は？",
    "・〇〇の1500m自己ベストは？",
    "方針はコーチに直接聞いてください。",
  ].join("\n");
}

/** Vague practice-feedback questions. */
export function isUnderspecifiedPracticeQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (
    !/(?:練習どう|練習できた|練習の(?:感想|様子)|どうだった.*練習|練習.*どうだった)/.test(
      q,
    )
  ) {
    return false;
  }
  if (/20\d{2}|今週|今日|明日|\d{1,2}\/\d{1,2}|\d{1,2}月\d{1,2}日/.test(q)) {
    return false;
  }
  return true;
}

export function buildPracticeClarifyText(): string {
  return [
    "どの日・どの練習か指定してください。",
    "例:",
    "・今週の練習は？",
    "・2026-10-14の予定は？",
    "・今日の練習メニューは？",
    "感想や評価はコーチに直接聞いてください。",
  ].join("\n");
}

/** 「速い人は？」「誰？」— ranking without filters. */
export function isUnderspecifiedWhoFastQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (/^(?:誰|だれ)[？?！!。．]*$/u.test(q)) return true;
  if (!/(?:速い人|誰が速い|だれが速い|おすすめの選手|強い人)/.test(q)) return false;
  if (/\d+\s*(?:m|km)|男子|女子|荒玉|なごみ|SB|トップ|上位|ランキング/.test(q)) {
    return false;
  }
  return true;
}

export function buildWhoFastClarifyText(): string {
  return [
    "種目・性別・大会を付けて聞いてください。",
    "例:",
    "・荒玉地区男子1500m SBトップ20は？",
    "・2025年荒玉男子1区の区間順位は？",
    "・女子3000mの荒玉地区ランキングは？",
  ].join("\n");
}

/** Bare distance / course without meet. */
export function isUnderspecifiedDistanceCourseQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (
    /^(?:距離|何キロ|コース|コース図|ルート|地図)(?:は|を|って|教えて|知りたい|見せて)?[？?！!。．]*$/u.test(
      q,
    )
  ) {
    return true;
  }
  if (!/(?:距離|何キロ|コース|ルート|地図)/.test(q)) return false;
  if (/荒玉|なごみ|ジュニア|ナイター|金栗|[1-6]区|男子|女子|20\d{2}/.test(q)) {
    return false;
  }
  return q.length <= 10;
}

export function buildDistanceCourseClarifyText(): string {
  return [
    "どの大会・区間の距離やコースか指定してください。",
    "例:",
    "・荒玉駅伝男子の区間距離は？",
    "・荒玉駅伝の女子4区は何地点から？",
    "・荒玉駅伝のコースの画像は？",
    "・荒玉駅伝のコース動画はどこ？",
  ].join("\n");
}

/** Bare media ask without meet / gender. */
export function isUnderspecifiedMediaQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  return /^(?:動画|映像|画像|写真|図|図解|ボード|結果ボード|PDF|URL|リンク)(?:は|を|って|見せて|教えて|欲しい)?[？?！!。．]*$/iu.test(
    q,
  );
}

export function buildMediaClarifyText(): string {
  return [
    "どの大会の動画・画像か指定してください。",
    "例:",
    "・荒玉駅伝のコース動画はどこ？",
    "・荒玉駅伝女子3区のコース動画を見せて",
    "・荒玉駅伝のコースの画像は？",
    "・2025年荒玉駅伝男子の結果ボードを見せて",
  ].join("\n");
}

/** Roster / headcount without school. */
export function isUnderspecifiedRosterQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (
    !/(?:名簿|生徒一覧|選手一覧|誰がいる|メンバー一覧|何人|人数|何年生|学年)/.test(
      q,
    )
  ) {
    return false;
  }
  if (
    /岱明|南関|玉名|長洲|菊水|有明|玉陵|玉東|玉南|荒尾|天水|三加和|腹栄|玉高|中学|高校/.test(
      q,
    )
  ) {
    return false;
  }
  return true;
}

export function buildRosterClarifyText(): string {
  return [
    "どの学校・所属の名簿か指定してください。",
    "例:",
    "・岱明中の生徒一覧は？",
    "・南関中所属選手の全記録一覧は？",
    "・2025年荒玉男子の岱明のオーダーは？",
  ].join("\n");
}

/** Rival / strong-school without school+meet. */
export function isUnderspecifiedRivalQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (!/(?:ライバル|強い学校|強豪|対抗)/.test(q)) return false;
  if (/荒玉|なごみ|ジュニア|岱明|南関|玉名|長洲|菊水|有明|玉陵|玉東|玉南|荒尾|天水|三加和|腹栄/.test(q)) {
    return false;
  }
  return true;
}

export function buildRivalClarifyText(): string {
  return [
    "どの大会・どの学校のライバルか指定してください。",
    "例:",
    "・荒玉駅伝で岱明のライバル校は？",
    "・2025年荒玉駅伝男子の優勝チームは？",
    "・なごみ駅伝の荒玉地区の結果は？",
  ].join("\n");
}

/** Pace / race plan without concrete inputs. */
export function isUnderspecifiedPaceAdviceQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (
    !/(?:ペース|ペース配分|作戦|どう走|走り方|どうすれば速|速くなる|目標タイム|目標は)/.test(
      q,
    )
  ) {
    return false;
  }
  if (
    /荒玉|なごみ|[1-6]区|\d+\s*(?:m|km|分|秒)|男子|女子|20\d{2}/.test(q)
  ) {
    return false;
  }
  return true;
}

export function buildPaceAdviceClarifyText(): string {
  return [
    "作戦・ペース配分の断定は資料だけではできません。事実で聞くなら例:",
    "・荒玉駅伝男子1区を10分で走るとペースは？",
    "・荒玉駅伝男子の区間距離は？",
    "・〇〇の1500m自己ベストは？",
    "方針はコーチに直接聞いてください。",
  ].join("\n");
}

/** Meet logistics (集合・持ち物等) — coach-facing. */
export function isUnderspecifiedLogisticsQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  return /^(?:集合(?:場所)?|持ち物|服装|弁当|バス|雨の日|練習休み|休めば(?:いい)?|エントリー(?:した)?|出場できる|県大会いける)(?:は|を|って|ですか)?[？?！!。．]*$/u.test(
    q,
  );
}

export function buildLogisticsClarifyText(): string {
  return [
    "集合・持ち物・エントリーなど当日連絡はコーチ／顧問に直接確認してください。",
    "資料で聞ける例:",
    "・荒玉駅伝はいつ？",
    "・今週の練習は？",
    "・荒玉駅伝で2位まで県駅伝に出られる？",
  ].join("\n");
}

/** Prediction / opinion / analysis without concrete fact ask. */
export function isUnderspecifiedOpinionQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (
    !/(?:予想|勝てる|いけそう|どう思う|評価して|分析して|解説して|最近どう|調子|体調|やる気|疲れた|つらい|泣いた|怒られた|怪我|ケガ|志望校|進学|部活やめる|休部|親に|コーチは|顧問は|先生は)/.test(
      q,
    )
  ) {
    return false;
  }
  if (
    /荒玉|なごみ|ジュニア|ナイター|\d+\s*(?:m|km)|20\d{2}|男子|女子|[1-6]区/.test(
      q,
    )
  ) {
    return false;
  }
  return true;
}

export function buildOpinionClarifyText(): string {
  return [
    "予想・体調・進路などの判断はコーチに直接聞いてください。",
    "事実ベースで聞くなら例:",
    "・2025年荒玉駅伝で岱明は何位？",
    "・2024と2025の荒玉駅伝で岱明の前年比は？",
    "・なごみ駅伝の荒玉地区の結果は？",
  ].join("\n");
}

const SCHOOL_NAME_RE =
  /^(?:岱明|南関|玉名|長洲|菊水|有明|玉陵|玉東|玉南|荒尾|天水|三加和|腹栄|玉高)(?:中|高校|附中|附属)?(?:は|を|って|どう|どうだった)?[？?！!。．]*$/u;

/** Bare school name without topic. */
export function isBareSchoolQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  return SCHOOL_NAME_RE.test(q);
}

export function buildBareSchoolClarifyText(): string {
  return [
    "学校について何を知りたいか具体的に書いてください。",
    "例:",
    "・2025年荒玉駅伝で岱明は何位？",
    "・岱明中の生徒一覧は？",
    "・2025年荒玉男子の岱明のオーダーは？",
    "・なごみ駅伝の荒玉地区の結果は？",
  ].join("\n");
}

/** Bare athlete name /「今村どう？」without topic. */
export function isBareAthleteQuestion(question: string): boolean {
  const raw = question.trim();
  const q = raw.normalize("NFKC");
  if (!q) return false;
  if (SCHOOL_NAME_RE.test(q)) return false;
  if (
    /自己ベスト|SB|PB|タイム|記録|成績|結果|区間|オーダー|大会|駅伝|練習|中学|高校|小学|男子|女子|優勝|順位|距離|コース|名簿|作戦|ペース|予想|分析|\d+\s*(?:m|km)/.test(
      q,
    )
  ) {
    return false;
  }
  // 「今村は？」「今村どう？」「今村昇磨は？」
  if (
    /^(?:[ァ-ヶヴー]{2,8}|[A-Za-z]{2,}|[\u3400-\u9fff\uf900-\ufaff]{1,8})(?:さん|くん|ちゃん|君)?(?:は|を|って|どう|どうだった)?[？?！!。．]*$/u.test(
      q,
    )
  ) {
    const asPossessive = q.replace(
      /(?:さん|くん|ちゃん|君)?(?:は|を|って|どう|どうだった)?[？?！!。．]*$/u,
      "の",
    );
    const base = q.replace(
      /(?:さん|くん|ちゃん|君)?(?:は|を|って|どう|どうだった)?[？?！!。．]*$/u,
      "",
    );
    if (NON_NAME_PREFIXES.has(base)) return false;
    return hasAthleteNameCue(raw) || hasAthleteNameCue(asPossessive);
  }
  return false;
}

export function buildBareAthleteClarifyText(): string {
  return [
    "選手について何を知りたいか、距離や大会を付けて書いてください。",
    "例:",
    "・〇〇の1500m自己ベストは？",
    "・〇〇の全ての記録は？",
    "・〇〇の荒玉駅伝の区間タイムは？",
  ].join("\n");
}

/** Topic openers like「駅伝って？」「荒玉のことは？」. */
export function isVagueTopicOpenerQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  return /^(?:駅伝|荒玉|なごみ|ジュニア|ナイター|金栗)(?:って|とは|について|のことは|のこと)?[？?！!。．]*$/u.test(
    q,
  );
}

export function buildVagueTopicOpenerClarifyText(): string {
  return [
    "何を知りたいか具体的に書いてください。",
    "例:",
    "・荒玉駅伝って何？",
    "・荒玉駅伝はいつ？",
    "・なごみ駅伝の結果は？",
    "・ジュニア駅伝の結果は？",
    "質問例の一覧は「使い方」と送ってください。",
  ].join("\n");
}

/** Time-gap / YoY without teams. */
export function isUnderspecifiedGapQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (!/(?:差|タイム差|前年比|比較)/.test(q)) return false;
  if (/荒玉|なごみ|岱明|南関|男子|女子|[1-6]区|20\d{2}|\d+位/.test(q)) {
    return false;
  }
  return /^(?:差|タイム差|前年比|比較)(?:は|を|って)?[？?！!。．]*$/u.test(q) || q.length <= 8;
}

export function buildGapClarifyText(): string {
  return [
    "どの大会・順位同士の差か指定してください。",
    "例:",
    "・去年の荒玉駅伝男子の2位と3位の差は？",
    "・2024と2025の荒玉駅伝で岱明の前年比は？",
    "・2025年荒玉男子1区の区間1位と2位の差は？",
  ].join("\n");
}

/**
 * Ultra-short / open-ended prompts that would otherwise dump「コーチに…」.
 * Keep narrow so concrete domain questions still reach prepared/RAG.
 */
export function isUltraVagueQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return true;
  if (
    /^(?:教えて|お願い|なに|何|どうすれば|どうしたら|おすすめ|おすすめは|なんか教えて|何か教えて|何でも答えて|なんでも聞いて|ちょっと聞いて|質問ある|ねえ|あのさ|すごい|かわいい|lol|www|test|asdf)[？?！!。．]*$/iu.test(
      q,
    )
  ) {
    return true;
  }
  // Punctuation-only / filler / single char / digits-only
  if (/^[？?！!。．…・～〜]+$/u.test(q)) return true;
  if (/^[ぁ-んァ-ヶー]{1,3}$/u.test(q)) return true;
  if (/^\d{1,4}$/.test(q)) return true;
  if (/^[a-z]{1,6}$/i.test(q)) return true;
  return false;
}

export function buildUltraVagueClarifyText(): string {
  return [
    "もう少し具体的に書いてください。",
    "例:",
    "・なごみ駅伝の結果は？",
    "・荒玉駅伝はいつ？",
    "・〇〇の1500m自己ベストは？",
    "・今週の練習は？",
    "質問例の一覧は「使い方」と送ってください。",
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
  if (isUnderspecifiedTimeQuestion(question)) {
    return {
      id: "clarify-time",
      text: buildTimeClarifyText(),
    };
  }
  if (isNamedUnderspecifiedTimeQuestion(question)) {
    return {
      id: "clarify-named-time",
      text: buildNamedTimeClarifyText(),
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
  if (isUnderspecifiedLegAdviceQuestion(question)) {
    return {
      id: "clarify-leg-advice",
      text: buildLegAdviceClarifyText(),
    };
  }
  if (isUnderspecifiedPracticeQuestion(question)) {
    return {
      id: "clarify-practice",
      text: buildPracticeClarifyText(),
    };
  }
  if (isUnderspecifiedWhoFastQuestion(question)) {
    return {
      id: "clarify-who-fast",
      text: buildWhoFastClarifyText(),
    };
  }
  if (isUnderspecifiedDistanceCourseQuestion(question)) {
    return {
      id: "clarify-distance-course",
      text: buildDistanceCourseClarifyText(),
    };
  }
  if (isUnderspecifiedMediaQuestion(question)) {
    return {
      id: "clarify-media",
      text: buildMediaClarifyText(),
    };
  }
  if (isUnderspecifiedRosterQuestion(question)) {
    return {
      id: "clarify-roster",
      text: buildRosterClarifyText(),
    };
  }
  if (isUnderspecifiedRivalQuestion(question)) {
    return {
      id: "clarify-rival",
      text: buildRivalClarifyText(),
    };
  }
  if (isUnderspecifiedPaceAdviceQuestion(question)) {
    return {
      id: "clarify-pace-advice",
      text: buildPaceAdviceClarifyText(),
    };
  }
  if (isUnderspecifiedLogisticsQuestion(question)) {
    return {
      id: "clarify-logistics",
      text: buildLogisticsClarifyText(),
    };
  }
  if (isUnderspecifiedOpinionQuestion(question)) {
    return {
      id: "clarify-opinion",
      text: buildOpinionClarifyText(),
    };
  }
  if (isUnderspecifiedGapQuestion(question)) {
    return {
      id: "clarify-gap",
      text: buildGapClarifyText(),
    };
  }
  if (isBareSchoolQuestion(question)) {
    return {
      id: "clarify-bare-school",
      text: buildBareSchoolClarifyText(),
    };
  }
  if (isBareAthleteQuestion(question)) {
    return {
      id: "clarify-bare-athlete",
      text: buildBareAthleteClarifyText(),
    };
  }
  if (isVagueTopicOpenerQuestion(question)) {
    return {
      id: "clarify-topic-opener",
      text: buildVagueTopicOpenerClarifyText(),
    };
  }
  // Last: open-ended fillers only (must not preempt「結果は？」等)
  if (isUltraVagueQuestion(question)) {
    return {
      id: "clarify-ultra-vague",
      text: buildUltraVagueClarifyText(),
    };
  }
  return null;
}
