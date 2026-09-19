/**
 * Race-leg athlete questions vs LINE ops about 2区/5区距離.
 * Shared by meet routing, retrieval, and offline preview.
 */

const OPS_RE = /地点分担|2\.855|朝練|銀マット|タイム目安|43分|区間配分|補強メニュー/;
const DISTANCE_ONLY_RE = /距離は|何キロ/;
const WHO_RE = /誰|選手|ランナー|走った/;

/** 「案浦竜士は何区を走った？」— numbered 区 is not required. */
export function isLegAthleteQuestion(question: string): boolean {
  const q = question.normalize("NFKC");
  if (OPS_RE.test(q)) return false;
  if (DISTANCE_ONLY_RE.test(q) && !WHO_RE.test(q)) return false;
  if (/(?:何|\d+)区を?走った|は何区(?:を|？|\?|!|！|$)|何区？/.test(q)) return true;
  if (/\d区は誰|\d区の選手|\d区ランナー|何区は誰|区間選手/.test(q)) return true;
  return /\d区/.test(q) && /誰|選手|ランナー|走った|区間タイム|区間順/.test(q);
}
