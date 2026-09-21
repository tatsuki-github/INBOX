import type { messagingApi } from "@line/bot-sdk";
import { answerQuestion, type AnswerDeps } from "../domain/answer.js";
import {
  selectAragyokuBoardImages,
  toLineImageMessages,
} from "../domain/aragyokuBoardImages.js";
import {
  selectAragyokuCourseVideos,
  toLineVideoMessages,
} from "../domain/aragyokuCourseVideos.js";
import { isDeniedUserId } from "../domain/deny.js";
import { NON_TEXT_GUIDANCE, splitLineText } from "./reply.js";
import { formatForLine } from "./format.js";
import { currentFiscalYear } from "../domain/dates.js";

export type LineEvent = {
  type: string;
  replyToken?: string;
  source?: {
    type?: string;
    userId?: string;
  };
  message?: {
    type: string;
    text?: string;
  };
};

export type LineWebhookBody = {
  events?: LineEvent[];
};

export type ReplyClient = {
  replyMessage: (args: {
    replyToken: string;
    messages: messagingApi.Message[];
  }) => Promise<unknown>;
};

export type WebhookHandleOptions = AnswerDeps & {
  deniedUserIds?: Set<string>;
};

/** LINE は 1 reply あたり最大 5 メッセージ。テキストを削って画像・動画枠を確保する。 */
export function buildReplyMessages(
  text: string,
  question: string,
  opts?: {
    defaultYear?: number;
    attachBoardImages?: boolean;
    attachCourseVideos?: boolean;
  },
): messagingApi.Message[] {
  const attachImages = opts?.attachBoardImages !== false;
  const attachVideos = opts?.attachCourseVideos !== false;
  const images = attachImages
    ? toLineImageMessages(
        selectAragyokuBoardImages(question, { defaultYear: opts?.defaultYear }),
      )
    : [];
  const videos = attachVideos
    ? toLineVideoMessages(selectAragyokuCourseVideos(question))
    : [];
  const mediaCount = images.length + videos.length;
  const textSlots = Math.max(1, 5 - mediaCount);
  const parts = splitLineText(formatForLine(text)).slice(0, textSlots);
  const messages: messagingApi.Message[] = parts.map((t) => ({ type: "text", text: t }));
  for (const img of images) {
    messages.push(img);
  }
  for (const vid of videos) {
    messages.push(vid);
  }
  return messages;
}

export async function handleWebhookEvents(
  body: LineWebhookBody,
  replyClient: ReplyClient,
  options: WebhookHandleOptions = {},
): Promise<{ handled: number }> {
  const { deniedUserIds = new Set<string>(), ...answerDeps } = options;
  const events = body.events ?? [];
  let handled = 0;
  const defaultYear = answerDeps.defaultYear ?? currentFiscalYear();

  for (const event of events) {
    if (!event.replyToken) continue;

    if (event.type === "message") {
      const userId = event.source?.userId;
      if (userId) {
        console.info(`line message userId=${userId}`);
      }

      if (isDeniedUserId(userId, deniedUserIds)) {
        console.info(`line denied userId=${userId}`);
        continue;
      }

      if (event.message?.type === "text") {
        const question = event.message.text ?? "";
        const result = await answerQuestion(question, answerDeps);
        const text =
          result.kind === "refused" ||
          result.kind === "answered" ||
          result.kind === "offline" ||
          result.kind === "error"
            ? result.text
            : NON_TEXT_GUIDANCE;
        const attachMedia = result.kind === "answered" || result.kind === "offline";
        await replyClient.replyMessage({
          replyToken: event.replyToken,
          messages: buildReplyMessages(text, question, {
            defaultYear,
            attachBoardImages: attachMedia,
            attachCourseVideos: attachMedia,
          }),
        });
        handled += 1;
        continue;
      }

      await replyClient.replyMessage({
        replyToken: event.replyToken,
        messages: [{ type: "text", text: NON_TEXT_GUIDANCE }],
      });
      handled += 1;
    }
  }

  return { handled };
}
