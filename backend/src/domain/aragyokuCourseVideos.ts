/**
 * 荒玉駅伝コース動画（公開 Drive）を LINE Video メッセージ用 URL に解決する。
 * カタログ: backend/data/aragyoku-course-videos.json
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isAragyokuCourseVideoQuestion } from "./canned.js";
import { detectAragyokuBoardGender, type AragyokuBoardGender } from "./aragyokuBoardImages.js";

export type AragyokuCourseVideoGender = AragyokuBoardGender;

export type AragyokuCourseVideoKind = "full" | "leg";

export type AragyokuCourseVideo = {
  gender: AragyokuCourseVideoGender;
  leg: number | null;
  kind: AragyokuCourseVideoKind;
  driveFileId: string;
  title: string;
  fileSizeBytes: number;
  folderId: string;
  originalContentUrl: string;
  previewImageUrl: string;
  lineEligible: boolean;
};

export type AragyokuCourseVideoFolderMeta = {
  folderId: string;
  folderUrl: string;
};

export type AragyokuCourseVideoIndex = {
  version: number;
  folders: Record<AragyokuCourseVideoGender, AragyokuCourseVideoFolderMeta>;
  videos: AragyokuCourseVideo[];
};

const __dirname = dirname(fileURLToPath(import.meta.url));

let cachedVideos: AragyokuCourseVideo[] | null = null;
let cachedFolders: Record<AragyokuCourseVideoGender, AragyokuCourseVideoFolderMeta> | null =
  null;

export function defaultAragyokuCourseVideoIndexPath(): string {
  return join(__dirname, "../../data/aragyoku-course-videos.json");
}

function loadIndex(
  path = defaultAragyokuCourseVideoIndexPath(),
): { videos: AragyokuCourseVideo[]; folders: Record<AragyokuCourseVideoGender, AragyokuCourseVideoFolderMeta> } {
  const emptyFolders = {
    男子: { folderId: "", folderUrl: "" },
    女子: { folderId: "", folderUrl: "" },
  } as const;
  try {
    const raw = JSON.parse(readFileSync(path, "utf8")) as AragyokuCourseVideoIndex;
    const videos = Array.isArray(raw.videos) ? raw.videos : [];
    const folders = raw.folders ?? emptyFolders;
    return { videos, folders };
  } catch {
    return { videos: [], folders: { ...emptyFolders } };
  }
}

export function loadAragyokuCourseVideos(
  path = defaultAragyokuCourseVideoIndexPath(),
): AragyokuCourseVideo[] {
  if (cachedVideos && path === defaultAragyokuCourseVideoIndexPath()) return cachedVideos;
  const { videos, folders } = loadIndex(path);
  if (path === defaultAragyokuCourseVideoIndexPath()) {
    cachedVideos = videos;
    cachedFolders = folders;
  }
  return videos;
}

export function loadAragyokuCourseVideoFolders(
  path = defaultAragyokuCourseVideoIndexPath(),
): Record<AragyokuCourseVideoGender, AragyokuCourseVideoFolderMeta> {
  if (cachedFolders && path === defaultAragyokuCourseVideoIndexPath()) return cachedFolders;
  const { videos, folders } = loadIndex(path);
  if (path === defaultAragyokuCourseVideoIndexPath()) {
    cachedVideos = videos;
    cachedFolders = folders;
  }
  return folders;
}

/** Reset cache (tests). */
export function resetAragyokuCourseVideoCache(): void {
  cachedVideos = null;
  cachedFolders = null;
}

/**
 * コース動画添付用の性別。両方 or なし → 男子（max 1）。
 */
export function resolveCourseVideoGender(question: string): AragyokuCourseVideoGender {
  const g = detectAragyokuBoardGender(question);
  if (g === "女子") return "女子";
  return "男子";
}

/** 質問から区間番号（1–6）を取る。なければ null（全区間）。 */
export function detectCourseVideoLeg(question: string): number | null {
  const q = question.normalize("NFKC");
  const m = q.match(/([1-6])\s*区/);
  if (!m) return null;
  return Number(m[1]);
}

/**
 * コース動画を最大 1 件返す（lineEligible のみ）。
 * - トリガ: isAragyokuCourseVideoQuestion
 * - 性別: 女子のみ → 女子 / それ以外 → 男子
 * - 区間あり → その区 / なし → 全区間
 */
export function selectAragyokuCourseVideos(
  question: string,
  opts?: {
    videos?: AragyokuCourseVideo[];
    maxVideos?: number;
  },
): AragyokuCourseVideo[] {
  const q = question.trim();
  if (!isAragyokuCourseVideoQuestion(q)) return [];

  const maxVideos = opts?.maxVideos ?? 1;
  const catalog = opts?.videos ?? loadAragyokuCourseVideos();
  if (catalog.length === 0) return [];

  const gender = resolveCourseVideoGender(q);
  const leg = detectCourseVideoLeg(q);

  let hit: AragyokuCourseVideo | undefined;
  if (leg != null) {
    hit = catalog.find(
      (v) => v.gender === gender && v.kind === "leg" && v.leg === leg && v.lineEligible,
    );
  } else {
    hit = catalog.find(
      (v) => v.gender === gender && v.kind === "full" && v.lineEligible,
    );
  }

  return hit ? [hit].slice(0, maxVideos) : [];
}

/** LINE messagingApi.Message 用の video オブジェクトに変換。 */
export function toLineVideoMessages(
  videos: AragyokuCourseVideo[],
): Array<{
  type: "video";
  originalContentUrl: string;
  previewImageUrl: string;
}> {
  return videos
    .filter((v) => v.lineEligible)
    .map((v) => ({
      type: "video" as const,
      originalContentUrl: v.originalContentUrl,
      previewImageUrl: v.previewImageUrl,
    }));
}
