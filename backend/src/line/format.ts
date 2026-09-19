/**
 * Convert LLM markdown-ish text into LINE-friendly plain text.
 * LINE text messages do not render Markdown.
 */

const SOURCE_FOOTER_RE =
  /(?:^|\n)\s*(?:根拠|ソース|source|出典|参考)\s*[:：]?\s*[^\n]*$/i;

export function formatForLine(text: string): string {
  let t = text.replace(/\r\n/g, "\n").trim();

  // Drop trailing "根拠: path/..." style footers (paths must not appear in replies)
  t = t.replace(SOURCE_FOOTER_RE, "").trim();
  // Drop lines that look like bare repo / corpus paths
  t = t
    .split("\n")
    .filter((line) => {
      const s = line.trim();
      if (/^(根拠|ソース|source|出典)\s*[:：]/i.test(s)) return false;
      if (/^(input\/|out\/|docs\/|backend\/|calendar\/|drive-text\/|ekiden-ocr\/)/.test(s)) {
        return false;
      }
      if (/\.(ya?ml|json|md|csv)\s*$/i.test(s) && !/[\u3040-\u30ff\u3400-\u9fff]/.test(s)) {
        return false;
      }
      return true;
    })
    .join("\n");

  // Fenced code blocks → content only
  t = t.replace(/```[\w]*\n?([\s\S]*?)```/g, (_, code: string) => code.trim());

  // Headings
  t = t.replace(/^#{1,6}\s+/gm, "");

  // Bold / italic / strike — protect URLs and snake_case ids so underscores
  // in Drive folder IDs / practice_meets_affect_load are not eaten as italic.
  const placeholders = new Map<string, string>();
  const protect = (m: string): string => {
    const key = `\u0000PH${placeholders.size}\u0000`;
    placeholders.set(key, m);
    return key;
  };
  t = t.replace(/https?:\/\/[^\s<>\]]+/gi, protect);
  t = t.replace(/\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b/g, protect);
  t = t.replace(/\*\*(.+?)\*\*/g, "$1");
  t = t.replace(/__(.+?)__/g, "$1");
  t = t.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "$1");
  t = t.replace(/(?<!_)_(?!_)(.+?)(?<!_)_(?!_)/g, "$1");
  t = t.replace(/~~(.+?)~~/g, "$1");
  t = t.replace(/`([^`]+)`/g, "$1");
  for (const [key, value] of placeholders) {
    t = t.split(key).join(value);
  }

  // Links / images
  t = t.replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1");
  t = t.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");

  // Unordered lists
  t = t.replace(/^\s*[-*+]\s+/gm, "・");
  // Ordered lists keep number but normalize
  t = t.replace(/^\s*(\d+)[.)]\s+/gm, "$1. ");

  // Blockquotes
  t = t.replace(/^\s*>\s?/gm, "");

  // Horizontal rules
  t = t.replace(/^\s*([-*_]){3,}\s*$/gm, "");

  // Collapse excess blank lines
  t = t.replace(/\n{3,}/g, "\n\n").trim();
  return t;
}
