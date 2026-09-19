import type { messagingApi } from "@line/bot-sdk";
import { answerQuestion, type AnswerDeps } from "../domain/answer.js";
import {
  selectAragyokuBoardImages,
  toLineImageMessages,
} from "../domain/aragyokuBoardImages.js";
import { isDeniedUserId } from "../domain/deny.js";
import { NON_TEXT_GUIDANCE, splitLineText } from "./reply.js";
import { formatForLine } from "./format.js";

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

/** LINE は 1 reply あたり最大 5 メッセージ。テキストを削って画像枠を確保する。 */
export function buildReplyMessages(
  text: string,
  question: string,
  opts?: { defaultYear?: number; attachBoardImages?: boolean },
): messagingApi.Message[] {
  const attach = opts?.attachBoardImages !== false;
  const images = attach
    ? toLineImageMessages(
        selectAragyokuBoardImages(question, { defaultYear: opts?.defaultYear }),
      )
    : [];
  const textSlots = Math.max(1, 5 - images.length);
  const parts = splitLineText(formatForLine(text)).slice(0, textSlots);
  const messages: messagingApi.Message[] = parts.map((t) => ({ type: "text", text: t }));
  for (const img of images) {
    messages.push(img);
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
  const defaultYear = answerDeps.defaultYear ?? new Date().getFullYear();

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
        const attachBoardImages = result.kind === "answered" || result.kind === "offline";
        await replyClient.replyMessage({
          replyToken: event.replyToken,
          messages: buildReplyMessages(text, question, {
            defaultYear,
            attachBoardImages,
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
