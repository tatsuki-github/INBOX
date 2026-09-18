import { describe, expect, it, vi } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";
import { signLineBody } from "../src/line/signature.js";
import type { ReplyClient } from "../src/line/webhook.js";
import { OUT_OF_SCOPE_MESSAGE } from "../src/domain/scope.js";

describe("POST /webhook", () => {
  const secret = "test-secret";
  const token = "test-token";

  it("GET /health works", async () => {
    const app = createApp({
      config: {
        LINE_CHANNEL_SECRET: secret,
        LINE_CHANNEL_ACCESS_TOKEN: token,
        AI_PROVIDER: "openai",
        PORT: 3001,
      },
    });
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body.corpus).toBe("input/idaten-corpus");
  });

  it("rejects invalid signature with 401", async () => {
    const app = createApp({
      config: {
        LINE_CHANNEL_SECRET: secret,
        LINE_CHANNEL_ACCESS_TOKEN: token,
        AI_PROVIDER: "openai",
        PORT: 3001,
      },
    });
    const body = { events: [] };
    const res = await request(app)
      .post("/webhook")
      .set("x-line-signature", "invalid")
      .send(body);
    expect(res.status).toBe(401);
  });

  it("replies refuse text for out-of-scope message", async () => {
    const replyMessage = vi.fn(async () => ({}));
    const replyClient: ReplyClient = { replyMessage };

    const app = createApp({
      config: {
        LINE_CHANNEL_SECRET: secret,
        LINE_CHANNEL_ACCESS_TOKEN: token,
        AI_PROVIDER: "openai",
        PORT: 3001,
      },
      replyClient,
    });

    const body = {
      events: [
        {
          type: "message",
          replyToken: "reply-1",
          message: { type: "text", text: "今日の天気は？" },
        },
      ],
    };
    const raw = JSON.stringify(body);
    const sig = signLineBody(raw, secret);

    const res = await request(app)
      .post("/webhook")
      .set("Content-Type", "application/json")
      .set("x-line-signature", sig)
      .send(raw);

    expect(res.status).toBe(200);
    expect(replyMessage).toHaveBeenCalledTimes(1);
    const arg = replyMessage.mock.calls[0]?.[0] as
      | {
          replyToken: string;
          messages: Array<{ type: string; text: string }>;
        }
      | undefined;
    expect(arg?.replyToken).toBe("reply-1");
    expect(arg?.messages[0]?.text).toBe(OUT_OF_SCOPE_MESSAGE);
  });

  it("replies guidance for non-text message", async () => {
    const replyMessage = vi.fn(async () => ({}));
    const app = createApp({
      config: {
        LINE_CHANNEL_SECRET: secret,
        LINE_CHANNEL_ACCESS_TOKEN: token,
        AI_PROVIDER: "openai",
        PORT: 3001,
      },
      replyClient: { replyMessage },
    });

    const body = {
      events: [
        {
          type: "message",
          replyToken: "reply-2",
          message: { type: "sticker" },
        },
      ],
    };
    const raw = JSON.stringify(body);
    const sig = signLineBody(raw, secret);
    const res = await request(app)
      .post("/webhook")
      .set("Content-Type", "application/json")
      .set("x-line-signature", sig)
      .send(raw);
    expect(res.status).toBe(200);
    expect(replyMessage).toHaveBeenCalled();
  });
});
