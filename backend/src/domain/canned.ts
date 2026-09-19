/**
 * Deterministic short answers for known operational facts
 * (e.g. shared Drive folders) that must not depend on LLM recall.
 */

import { detectAragyokuBoardGender } from "./aragyokuBoardImages.js";

export const ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL =
  "https://drive.google.com/drive/folders/1no2bVU7GeyVbXFsCG8V8uwM0IuaFoOhi";

export const ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL =
  "https://drive.google.com/drive/folders/17MrxiZ_0CsDBgVrS_O3uZm3Oypu70Uoo";

/** @deprecated Use gender-specific folder URLs. Kept for tests that check either URL. */
export const ARAGYOKU_COURSE_VIDEO_FOLDER_URL = ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL;

export type CannedAnswer = {
  id: string;
  text: string;
};

/** True when the question is about 荒玉駅伝 course videos / course footage. */
export function isAragyokuCourseVideoQuestion(question: string): boolean {
  const q = question.trim();
  if (!q) return false;
  // ジュニア・なごみ等は荒玉コース動画の確定回答にしない
  if (/ジュニア|なごみ|金栗/.test(q)) return false;
  const hasVideo = /動画|映像|ビデオ|ムービー|movie|video/i.test(q);
  const hasCourse = /コース|コース図|ルート|地図|course/i.test(q);
  if (hasCourse && hasVideo) return true;
  // 「荒玉の動画どこ？」「駅伝コースの映像」など
  const hasAragyoku = /荒玉|駅伝|aragyoku|中体連/.test(q);
  return hasAragyoku && hasVideo && hasCourse;
}

function courseVideoCannedText(question: string): string {
  const gender = detectAragyokuBoardGender(question);
  if (gender === "女子") {
    return [
      "荒玉駅伝（女子）のコース動画は、次の Google ドライブフォルダにあります。",
      ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL,
    ].join("\n");
  }
  if (gender === "男子") {
    return [
      "荒玉駅伝（男子）のコース動画は、次の Google ドライブフォルダにあります。",
      ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL,
    ].join("\n");
  }
  return [
    "荒玉駅伝のコース動画は、次の Google ドライブフォルダにあります。",
    `女子: ${ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL}`,
    `男子: ${ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL}`,
  ].join("\n");
}

export function matchCannedAnswer(question: string): CannedAnswer | null {
  if (isAragyokuCourseVideoQuestion(question)) {
    return {
      id: "aragyoku-course-videos",
      text: courseVideoCannedText(question),
    };
  }
  return null;
}
