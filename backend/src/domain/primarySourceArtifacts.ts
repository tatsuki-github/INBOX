/**
 * Primary source files that can be linked from LINE answers.
 *
 * LINE Messaging API cannot send PDF file messages. These links point to the
 * committed source-file mirror and, where known, the original Drive folder.
 */

import {
  currentFiscalYear,
  parseDateMentions,
  resolveRelativeDates,
  resolveRelativeYears,
} from "./dates.js";

export type PrimarySourceArtifact = {
  source: string;
  label: string;
  rawUrl: string;
  originalUrl?: string;
  date: string;
  meet: string;
};

const RAW_REPOSITORY_BASE = "https://raw.githubusercontent.com/tatsuki-github/INBOX/main";
const NAGOMI_FOLDER_URL =
  "https://drive.google.com/drive/folders/1k-zW0irJ-OjDjqQwUQLZIs4C6PfuR211";

function encodePath(path: string): string {
  return path.split("/").map((part) => encodeURIComponent(part)).join("/");
}

function rawRepositoryUrl(path: string): string {
  return `${RAW_REPOSITORY_BASE}/${encodePath(path)}`;
}

const NAGOMI_2026_ROOT =
  "input/idaten-corpus/drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会";

const NAGOMI_2026_ARTIFACTS: PrimarySourceArtifact[] = [
  {
    source: "drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/女子成績表.md",
    label: "女子成績表PDF",
    rawUrl: rawRepositoryUrl(`${NAGOMI_2026_ROOT}/女子成績表.pdf`),
    originalUrl: NAGOMI_FOLDER_URL,
    date: "2026-09-20",
    meet: "なごみ",
  },
  {
    source: "drive-text/大会/2026年度/0920_中学駅伝金栗四三生誕の地なごみ大会/男子成績表.md",
    label: "男子成績表PDF",
    rawUrl: rawRepositoryUrl(`${NAGOMI_2026_ROOT}/男子成績表.pdf`),
    originalUrl: NAGOMI_FOLDER_URL,
    date: "2026-09-20",
    meet: "なごみ",
  },
];

export function wantsPrimarySourceLinks(question: string): boolean {
  return /結果|成績|順位|区間|タイム|記録|公式|一次情報|原本|PDF|ファイル|添付|渡して|送って|リンク/.test(
    question.normalize("NFKC"),
  );
}

export function findPrimarySourceArtifacts(
  question: string,
  sources: string[],
  opts?: { defaultYear?: number; maxArtifacts?: number; now?: Date },
): PrimarySourceArtifact[] {
  if (!wantsPrimarySourceLinks(question)) return [];

  const q = question.normalize("NFKC");
  const defaultYear = opts?.defaultYear ?? currentFiscalYear(opts?.now);
  const dateMentions = [
    ...parseDateMentions(q, defaultYear),
    ...resolveRelativeDates(q, opts?.now),
  ];
  const years = resolveRelativeYears(q, defaultYear);
  const sourceSet = new Set(sources);
  const requestedGender = /女子|女の部|女子の部/.test(q)
    ? "女子"
    : /男子|男の部|男子の部/.test(q)
      ? "男子"
      : null;
  const selected = NAGOMI_2026_ARTIFACTS.filter((artifact) => {
    const exactSource = sourceSet.has(artifact.source);
    const dateMatch = dateMentions.some((mention) => mention.iso === artifact.date);
    const yearMatch = years.length > 0 && years.includes(Number(artifact.date.slice(0, 4)));
    const inferredFromQuestion = q.includes(artifact.meet) && (dateMatch || yearMatch);
    if (!exactSource && !inferredFromQuestion) return false;
    if (!requestedGender) return true;
    return artifact.label.startsWith(requestedGender);
  });

  return selected.slice(0, opts?.maxArtifacts ?? 4);
}

export function appendPrimarySourceLinks(
  text: string,
  artifacts: PrimarySourceArtifact[],
): string {
  if (artifacts.length === 0) return text;
  const existing = new Set(text.match(/https?:\/\/[^\s]+/gi) ?? []);
  const lines: string[] = [];
  for (const artifact of artifacts) {
    if (!existing.has(artifact.rawUrl)) {
      lines.push(`・${artifact.label}: ${artifact.rawUrl}`);
      existing.add(artifact.rawUrl);
    }
  }
  const originalUrls = [...new Set(artifacts.map((artifact) => artifact.originalUrl).filter(Boolean))] as string[];
  for (const url of originalUrls) {
    if (!existing.has(url)) {
      lines.push(`・原本フォルダ: ${url}`);
      existing.add(url);
    }
  }
  if (lines.length === 0) return text;
  return `${text.trim()}\n\n一次資料:\n${lines.join("\n")}`.trim();
}
