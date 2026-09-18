import type { messagingApi } from "@line/bot-sdk";
import { answerQuestion, type AnswerDeps } from "../domain/answer.js";
import { NON_TEXT_GUIDANCE, splitLineText } from "./reply.js";

export type LineEvent = {
  type: string;
  replyToken?: string;
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

export async function handleWebhookEvents(
  body: LineWebhookBody,
  replyClient: ReplyClient,
  answerDeps: AnswerDeps = {},
): Promise<{ handled: number }> {
  const events = body.events ?? [];
  let handled = 0;

  for (const event of events) {
    if (!event.replyToken) continue;

    if (event.type === "message" && event.message?.type === "text") {
      const question = event.message.text ?? "";
      const result = await answerQuestion(question, answerDeps);
      const text =
        result.kind === "refused" ||
        result.kind === "answered" ||
        result.kind === "offline" ||
        result.kind === "error"
          ? result.text
          : NON_TEXT_GUIDANCE;
      const parts = splitLineText(text).slice(0, 5);
      await replyClient.replyMessage({
        replyToken: event.replyToken,
        messages: parts.map((t) => ({ type: "text", text: t })),
      });
      handled += 1;
      continue;
    }

    if (event.type === "message") {
      await replyClient.replyMessage({
        replyToken: event.replyToken,
        messages: [{ type: "text", text: NON_TEXT_GUIDANCE }],
      });
      handled += 1;
    }
  }

  return { handled };
}
