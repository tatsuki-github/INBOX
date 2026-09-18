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

export const NON_TEXT_GUIDANCE =
  "テキストで質問してください。いだてん岱明の練習・駅伝・記録・名簿について答えます。";
