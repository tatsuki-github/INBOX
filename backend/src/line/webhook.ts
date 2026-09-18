import type { messagingApi } from "@line/bot-sdk";
import { answerQuestion, type AnswerDeps } from "../domain/answer.js";
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

export async function handleWebhookEvents(
  body: LineWebhookBody,
  replyClient: ReplyClient,
  options: WebhookHandleOptions = {},
): Promise<{ handled: number }> {
  const { deniedUserIds = new Set<string>(), ...answerDeps } = options;
  const events = body.events ?? [];
  let handled = 0;

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
        const parts = splitLineText(formatForLine(text)).slice(0, 5);
        await replyClient.replyMessage({
          replyToken: event.replyToken,
          messages: parts.map((t) => ({ type: "text", text: t })),
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
