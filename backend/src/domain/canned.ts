/**
 * Deterministic short answers for known operational facts
 * (e.g. shared Drive folders / help text) that must not depend on LLM recall.
 */

import { detectAragyokuBoardGender } from "./aragyokuBoardImages.js";

export const ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL =
  "https://drive.google.com/drive/folders/1no2bVU7GeyVbXFsCG8V8uwM0IuaFoOhi";

export const ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL =
  "https://drive.google.com/drive/folders/17MrxiZ_0CsDBgVrS_O3uZm3Oypu70Uoo";

export const ARAGYOKU_COURSE_VIDEO_YOUTUBE_PLAYLIST_URL =
  "https://youtube.com/playlist?list=PLfEmEvJWOhLE&si=xNbUO5aLL8ly9axJ";

/** @deprecated Use gender-specific folder URLs. Kept for tests that check either URL. */
export const ARAGYOKU_COURSE_VIDEO_FOLDER_URL = ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL;

/** 男女コース共通ポイント図解（course-points.json の drive_url と同期）。 */
export const ARAGYOKU_COURSE_IMAGE_DRIVE_URL =
  "https://drive.google.com/file/d/1j9iRk5WAnNVdMyO_fDJX5MaMAVDrESzG/view?usp=drivesdk";

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

/** Greeting / thanks / ack — avoid bare「コーチに…」for social openers. */
export function isGreetingOrThanksQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  return /^(?:こんにちは|こんにちわ|こんばんは|おはよう(?:ございます)?|はじめまして|宜しく|よろしく(?:お願い(?:します|いたします)?)?|ありがとう(?:ございます)?|どうも|お疲れ(?:さま|様)?(?:です)?|おつかれ(?:さま|様)?(?:です)?|すみません|ごめん(?:なさい)?|了解|りょうかい|なるほど|わかった|オーケー|OK|ok|hi|hello|hey|bye|バイバイ|ばいばい|またね|じゃあね)[！!。．～〜]*$/iu.test(
    q,
  );
}

export function buildGreetingOrThanksText(question: string): string {
  const q = question.normalize("NFKC").trim();
  const bye = /bye|バイバイ|ばいばい|またね|じゃあね/i.test(q);
  if (bye) {
    return [
      "また聞いてください。",
      "質問例は「使い方」と送ってください。",
    ].join("\n");
  }
  const ack = /了解|りょうかい|なるほど|わかった|オーケー|\bOK\b/i.test(q);
  if (ack) {
    return [
      "了解です。ほかにも大会結果や記録について聞けます。",
      "質問例は「使い方」と送ってください。",
    ].join("\n");
  }
  const thanks = /ありがとう|どうも|お疲れ|おつかれ|すみません|ごめん/.test(q);
  if (thanks) {
    return [
      "どういたしまして。",
      "大会結果・記録・練習予定なども聞けます。質問例は「使い方」と送ってください。",
    ].join("\n");
  }
  return [
    "こんにちは。いだてん岱明の練習・大会・駅伝・記録について答えます。",
    "大会名・選手名・年を付けて聞いてください。質問例は「使い方」と送ってください。",
  ].join("\n");
}

/**
 * Help / example questions. Aragyoku-centric, no personal names, covers app surface.
 * Keep under LINE comfort length; bullets use 「・」 for formatForLine friendliness.
 * Examples mirror prepared-Q&A coverage (相対年・結果・区間・差・名簿・全記録 等).
 */
export function buildHelpExamplesText(): string {
  return [
    "いだてん岱明の練習・大会・駅伝・記録について答えます。",
    "天気・ニュースなど外部の話題は対象外です。",
    "「去年」「昨年」はひとつ前の年度（いまは2025年）として扱います。年なしは今年度です。",
    "",
    "▼ 質問例（荒玉駅伝）",
    "・荒玉駅伝って何？",
    "・今年の荒玉駅伝はいつ？",
    "・荒玉駅伝男子の区間距離は？",
    "・荒玉駅伝の女子4区は何地点から？",
    "・2024年荒玉駅伝男子の優勝チームは？",
    "・去年の岱明の女子の結果は？",
    "・去年の男子2区の荒玉駅伝の区間順位は？",
    "・去年の荒玉駅伝男子の2位と3位の差は？",
    "・2025年荒玉駅伝で岱明は何位？",
    "・荒玉駅伝で2位まで県駅伝に出られる？",
    "・荒玉駅伝で岱明のライバル校は？",
    "・荒玉駅伝男子1区を10分で走るとペースは？",
    "・2024と2025の荒玉駅伝で岱明の前年比は？",
    "・荒玉駅伝のコース動画はどこ？",
    "・荒玉駅伝女子3区のコース動画を見せて",
    "・荒玉駅伝のコースの画像は？",
    "・2025年荒玉駅伝男子の結果ボードを見せて",
    "",
    "▼ ほかにも聞けること",
    "・なごみ駅伝の荒玉地区の結果は？",
    "・ジュニア駅伝の結果は？",
    "・玉名郡ナイターの結果は？",
    "・○○中の生徒一覧は？（学校・所属名を書いて）",
    "・〇〇の全ての記録は？（選手名を書いて）",
    "・〇〇の1500m自己ベストは？（選手名と距離を書いて）",
    "・○○/〇〇の大会予定は？",
    "・県中体連の結果URLは？",
    "",
    "大会名・年・男女・学校名を具体的に書いてください。",
    "曖昧なときは聞き方の例を返します。根拠が無いことは「コーチに直接聞いてください。」と案内します。",
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

/**
 * True when the question asks for the 荒玉駅伝 course diagram / course image.
 * Video questions take precedence (handled by isAragyokuCourseVideoQuestion).
 */
export function isAragyokuCourseImageQuestion(question: string): boolean {
  const q = question.normalize("NFKC").trim();
  if (!q) return false;
  if (/ジュニア|なごみ|金栗/.test(q)) return false;
  // 動画はコース動画 canned へ
  if (/動画|映像|ビデオ|ムービー|movie|video/i.test(q)) return false;
  // 結果ボードは別経路
  if (/結果ボード|成績表|順位表|結果画像/.test(q)) return false;

  const hasImageCue =
    /画像|図解|図面|写真|イメージ|\bimage\b|\.png/i.test(q) || /コース図|ポイント図|共通ポイント/.test(q);
  const hasCourse = /コース|ルート|共通ポイント|course/i.test(q);
  if (hasCourse && hasImageCue) return true;

  const hasAragyoku = /荒玉|駅伝|aragyoku|中体連/.test(q);
  return hasAragyoku && /コース図|共通ポイント/.test(q);
}

function courseVideoCannedText(question: string): string {
  const gender = detectAragyokuBoardGender(question);
  const youtube = `限定公開YouTubeプレイリスト: ${ARAGYOKU_COURSE_VIDEO_YOUTUBE_PLAYLIST_URL}`;
  if (gender === "女子") {
    return [
      "荒玉駅伝（女子）のコース動画は、次の Google ドライブフォルダにあります。",
      ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL,
      youtube,
    ].join("\n");
  }
  if (gender === "男子") {
    return [
      "荒玉駅伝（男子）のコース動画は、次の Google ドライブフォルダにあります。",
      ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL,
      youtube,
    ].join("\n");
  }
  return [
    "荒玉駅伝のコース動画は、次の Google ドライブフォルダにあります。",
    `女子: ${ARAGYOKU_COURSE_VIDEO_WOMEN_FOLDER_URL}`,
    `男子: ${ARAGYOKU_COURSE_VIDEO_MEN_FOLDER_URL}`,
    youtube,
  ].join("\n");
}

function courseImageCannedText(): string {
  return [
    "荒玉駅伝の男女コース共通ポイント図解は、次の画像です（女子1〜5区・男子1〜6区が共有する地点）。",
    ARAGYOKU_COURSE_IMAGE_DRIVE_URL,
    "詳細: 橋の上の1km、A/B/C/D/E、1周4.855km、男子スタートはCの145m手前。",
  ].join("\n");
}

export function matchCannedAnswer(question: string): CannedAnswer | null {
  // Help first: 「使い方」等はコース動画・画像より優先
  if (isHelpOrExampleQuestion(question)) {
    return {
      id: "help-examples",
      text: buildHelpExamplesText(),
    };
  }
  if (isGreetingOrThanksQuestion(question)) {
    return {
      id: "greeting-thanks",
      text: buildGreetingOrThanksText(question),
    };
  }
  if (isAragyokuCourseVideoQuestion(question)) {
    return {
      id: "aragyoku-course-videos",
      text: courseVideoCannedText(question),
    };
  }
  if (isAragyokuCourseImageQuestion(question)) {
    return {
      id: "aragyoku-course-images",
      text: courseImageCannedText(),
    };
  }
  return null;
}
