/** LINE text message max length is 5000. */
export const LINE_TEXT_MAX = 5000;

export function splitLineText(text: string, maxLen = LINE_TEXT_MAX): string[] {
  if (text.length <= maxLen) {
    return [text];
  }
  const parts: string[] = [];
  let rest = text;
  while (rest.length > maxLen) {
    let cut = rest.lastIndexOf("\n", maxLen);
    if (cut < maxLen * 0.5) {
      cut = maxLen;
    }
    parts.push(rest.slice(0, cut));
    rest = rest.slice(cut).replace(/^\n+/, "");
  }
  if (rest) {
    parts.push(rest);
  }
  return parts;
}

/** Keep the primary-source block reachable when a long offline answer is capped at 5 messages. */
export function splitLineTextPreservingPrimarySources(
  text: string,
  textSlots: number,
  maxLen = LINE_TEXT_MAX,
): string[] {
  const marker = "\n\n一次資料:\n";
  const markerIndex = text.indexOf(marker);
  if (markerIndex < 0) return splitLineText(text, maxLen).slice(0, textSlots);

  const body = text.slice(0, markerIndex);
  const primarySources = text.slice(markerIndex + 2);
  const sourceParts = splitLineText(primarySources, maxLen);
  const bodySlots = Math.max(0, textSlots - sourceParts.length);
  const bodyParts = splitLineText(body, maxLen).slice(0, bodySlots);
  return [...bodyParts, ...sourceParts].slice(-textSlots);
}

export const NON_TEXT_GUIDANCE =
  "テキストで質問してください。いだてん岱明の練習・駅伝・記録・名簿について答えます。";
