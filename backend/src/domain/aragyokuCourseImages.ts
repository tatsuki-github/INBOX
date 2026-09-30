/**
 * 荒玉駅伝コース図解画像（公開 Drive）を LINE Image メッセージ用 URL に解決する。
 * 正本: input/aragyoku/course-points.json の drive_file_id
 * カタログ: backend/data/aragyoku-course-images.json
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { isAragyokuCourseImageQuestion } from "./canned.js";

export type AragyokuCourseImage = {
  id: string;
  title: string;
  driveFileId: string;
  driveUrl: string;
  imagePath: string;
  originalContentUrl: string;
  previewImageUrl: string;
};

export type AragyokuCourseImageIndex = {
  version: number;
  driveFileId: string;
  driveUrl: string;
  parentFolderId?: string | null;
  parentFolderUrl?: string | null;
  source?: string;
  note?: string;
  images: AragyokuCourseImage[];
};

const __dirname = dirname(fileURLToPath(import.meta.url));

let cached: AragyokuCourseImage[] | null = null;
let cachedMeta: Pick<AragyokuCourseImageIndex, "driveUrl" | "driveFileId"> | null = null;

export function defaultAragyokuCourseImageIndexPath(): string {
  return join(__dirname, "../../data/aragyoku-course-images.json");
}

function loadIndex(
  path = defaultAragyokuCourseImageIndexPath(),
): {
  images: AragyokuCourseImage[];
  meta: Pick<AragyokuCourseImageIndex, "driveUrl" | "driveFileId">;
} {
  try {
    const raw = JSON.parse(readFileSync(path, "utf8")) as AragyokuCourseImageIndex;
    const images = Array.isArray(raw.images) ? raw.images : [];
    return {
      images,
      meta: {
        driveFileId: raw.driveFileId ?? "",
        driveUrl: raw.driveUrl ?? "",
      },
    };
  } catch {
    return { images: [], meta: { driveFileId: "", driveUrl: "" } };
  }
}

export function loadAragyokuCourseImages(
  path = defaultAragyokuCourseImageIndexPath(),
): AragyokuCourseImage[] {
  if (cached && path === defaultAragyokuCourseImageIndexPath()) return cached;
  const { images, meta } = loadIndex(path);
  if (path === defaultAragyokuCourseImageIndexPath()) {
    cached = images;
    cachedMeta = meta;
  }
  return images;
}

export function loadAragyokuCourseImageMeta(
  path = defaultAragyokuCourseImageIndexPath(),
): Pick<AragyokuCourseImageIndex, "driveUrl" | "driveFileId"> {
  if (cachedMeta && path === defaultAragyokuCourseImageIndexPath()) return cachedMeta;
  const { images, meta } = loadIndex(path);
  if (path === defaultAragyokuCourseImageIndexPath()) {
    cached = images;
    cachedMeta = meta;
  }
  return meta;
}

/** Reset cache (tests). */
export function resetAragyokuCourseImageCache(): void {
  cached = null;
  cachedMeta = null;
}

/**
 * コース図解画像を最大 1 枚返す。
 * - トリガ: isAragyokuCourseImageQuestion
 */
export function selectAragyokuCourseImages(
  question: string,
  opts?: {
    images?: AragyokuCourseImage[];
    maxImages?: number;
  },
): AragyokuCourseImage[] {
  const q = question.trim();
  if (!isAragyokuCourseImageQuestion(q)) return [];

  const maxImages = opts?.maxImages ?? 1;
  const catalog = opts?.images ?? loadAragyokuCourseImages();
  if (catalog.length === 0) return [];

  return catalog.slice(0, maxImages);
}

/** LINE messagingApi.Message 用の image オブジェクトに変換。 */
export function toLineCourseImageMessages(
  images: AragyokuCourseImage[],
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
