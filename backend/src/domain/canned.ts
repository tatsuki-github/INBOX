/**
 * Deterministic short answers for known operational facts
 * (e.g. shared Drive folders / help text) that must not depend on LLM recall.
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

/** True when the user asks how to use the bot or wants example questions. */
export function isHelpOrExampleQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;

  if (/使い方|ヘルプ|\bhelp\b|質問例|聞き方|どう使(え|う|えば)|使い方教えて/i.test(q)) {
    return true;
  }
  if (/何が(できる|聞ける)|何を(聞け|質問|聞けば)|できること/.test(q)) {
    return true;
  }
  if (/(この)?(ボット|アプリ)(は|の)?/.test(q) && /(何|どう|使い|機能|できる|聞ける)/.test(q)) {
    return true;
  }
  if (/^メニュー$|^案内(して)?$|^はじめて$|^初めて$|^スタート$/.test(q)) {
    return true;
  }
  return false;
}

/**
 * Help / example questions. Aragyoku-centric, no personal names, covers app surface.
 * Keep under LINE comfort length; bullets use 「・」 for formatForLine friendliness.
 */
export function buildHelpExamplesText(): string {
  return [
    "いだてん岱明の練習・大会・駅伝・記録について答えます。",
    "天気・ニュースなど外部の話題は対象外です。",
    "",
    "▼ 質問例（荒玉駅伝）",
    "・荒玉駅伝って何？",
    "・荒玉男子の区間距離は？",
    "・今年の荒玉はいつ？",
    "・2012年荒玉男子の優勝チームは？",
    "・2025年荒玉で岱明は何位？",
    "・2025年荒玉女子の区間賞は？",
    "・2025年荒玉男子の大会記録は？",
    "・男子2区の大会区間記録は？",
    "・荒玉男子1区を10分で走るとペースは？",
    "・2024と2025の荒玉で岱明の前年比は？",
    "・荒玉のコース動画はどこ？",
    "・荒玉女子3区のコース動画を見せて",
    "・2025年荒玉男子の結果ボードを見せて",
    "",
    "▼ ほかにも聞けること",
    "・なごみ駅伝はいつ？",
    "・9/20の練習予定は？",
    "・県中体連の結果URLは？",
    "・〇〇の1500m自己ベストは？（選手名と距離を書いて）",
    "",
    "具体的に書いて送ってください。分からないことは「コーチに直接聞いてください。」と返します。",
  ].join("\n");
}

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
  // Help first: 「使い方」等はコース動画より優先
  if (isHelpOrExampleQuestion(question)) {
    return {
      id: "help-examples",
      text: buildHelpExamplesText(),
    };
  }
  if (isAragyokuCourseVideoQuestion(question)) {
    return {
      id: "aragyoku-course-videos",
      text: courseVideoCannedText(question),
    };
  }
  return null;
}
