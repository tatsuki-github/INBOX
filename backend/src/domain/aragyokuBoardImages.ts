/**
 * 荒玉駅伝の結果ボード画像（公開 Drive）を LINE Image メッセージ用 URL に解決する。
 * 正本 ID: input/aragyoku/transcripts/*.json の source_drive_id
 * カタログ: backend/data/aragyoku-board-images.json
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { currentFiscalYear, resolveRelativeYears } from "./dates.js";

export type AragyokuBoardGender = "男子" | "女子";

export type AragyokuBoardImage = {
  year: number;
  gender: AragyokuBoardGender;
  driveFileId: string;
  originalContentUrl: string;
  previewImageUrl: string;
};

export type AragyokuBoardImageIndex = {
  version: number;
  folderId: string;
  folderUrl: string;
  images: AragyokuBoardImage[];
};

const __dirname = dirname(fileURLToPath(import.meta.url));

let cached: AragyokuBoardImage[] | null = null;

export function defaultAragyokuBoardImageIndexPath(): string {
  return join(__dirname, "../../data/aragyoku-board-images.json");
}

export function loadAragyokuBoardImages(
  path = defaultAragyokuBoardImageIndexPath(),
): AragyokuBoardImage[] {
  if (cached && path === defaultAragyokuBoardImageIndexPath()) return cached;
  try {
    const raw = JSON.parse(readFileSync(path, "utf8")) as AragyokuBoardImageIndex;
    const images = Array.isArray(raw.images) ? raw.images : [];
    if (path === defaultAragyokuBoardImageIndexPath()) cached = images;
    return images;
  } catch {
    return [];
  }
}

/** Reset cache (tests). */
export function resetAragyokuBoardImageCache(): void {
  cached = null;
}

/** 荒玉駅伝の「特定年」結果ボードを添付すべき質問か。 */
export function wantsAragyokuBoardImages(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  // 他大会（荒玉と併記していない場合）は除外
  if (/ジュニア|なごみ|金栗/.test(q) && !/荒玉/.test(q)) return false;
  if (!/荒玉|中体連/.test(q)) return false;
  // 特定年が必要（西暦 or 相対年）
  if (!/20\d{2}/.test(q) && !/去年|昨年|今年|おととし|一昨年/.test(q)) return false;
  // コース動画だけの質問は canned Drive フォルダ回答に任せる
  if (/動画|映像|ビデオ/.test(q) && /コース/.test(q) && !/結果|順位|区間|優勝|学年|選手|タイム/.test(q)) {
    return false;
  }
  return true;
}

export function detectAragyokuBoardGender(question: string): AragyokuBoardGender | "both" {
  const q = question.normalize("NFKC");
  const men = /男子|男の部|男子の部/.test(q);
  const women = /女子|女の部|女子の部/.test(q);
  if (men && !women) return "男子";
  if (women && !men) return "女子";
  return "both";
}

/**
 * 該当年の結果ボード画像を最大 2 枚返す。
 * - 男子のみ指定 → 1 枚
 * - 女子のみ指定 → 1 枚
 * - 性別なし → 男子・女子（あるもの）最大 2 枚
 * - 複数年 → 最新の年を 1 つ選ぶ
 */
export function selectAragyokuBoardImages(
  question: string,
  opts?: {
    defaultYear?: number;
    images?: AragyokuBoardImage[];
    maxImages?: number;
  },
): AragyokuBoardImage[] {
  const q = question.trim();
  if (!wantsAragyokuBoardImages(q)) return [];

  const defaultYear = opts?.defaultYear ?? currentFiscalYear();
  const maxImages = opts?.maxImages ?? 2;
  const catalog = opts?.images ?? loadAragyokuBoardImages();
  if (catalog.length === 0) return [];

  const years = resolveRelativeYears(q, defaultYear);
  if (years.length === 0) return [];
  const year = years[0]!; // resolveRelativeYears は降順

  const gender = detectAragyokuBoardGender(q);
  const forYear = catalog.filter((img) => img.year === year);
  const picked: AragyokuBoardImage[] = [];

  if (gender === "男子" || gender === "女子") {
    const hit = forYear.find((img) => img.gender === gender);
    if (hit) picked.push(hit);
  } else {
    for (const g of ["男子", "女子"] as const) {
      const hit = forYear.find((img) => img.gender === g);
      if (hit) picked.push(hit);
    }
  }

  return picked.slice(0, maxImages);
}

/** LINE messagingApi.Message 用の image オブジェクトに変換。 */
export function toLineImageMessages(
  images: AragyokuBoardImage[],
): Array<{
  type: "image";
  originalContentUrl: string;
  previewImageUrl: string;
}> {
  return images.map((img) => ({
    type: "image" as const,
    originalContentUrl: img.originalContentUrl,
    previewImageUrl: img.previewImageUrl,
  }));
}
