import { afterEach, describe, expect, it, vi } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";
import { signLineBody } from "../src/line/signature.js";
import type { ReplyClient } from "../src/line/webhook.js";
import { OUT_OF_SCOPE_MESSAGE } from "../src/domain/scope.js";
import type { AppConfig } from "../src/config.js";

describe("POST /webhook", () => {
  const secret = "test-secret";
  const token = "test-token";

  function baseConfig(extra: Partial<AppConfig> = {}): AppConfig {
    return {
      LINE_CHANNEL_SECRET: secret,
      LINE_CHANNEL_ACCESS_TOKEN: token,
      AI_PROVIDER: "openai",
      PORT: 3001,
      ...extra,
    };
  }

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("GET /health works", async () => {
    const app = createApp({ config: baseConfig() });
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body.corpus).toBe("input/idaten-corpus");
  });

  it("rejects invalid signature with 401", async () => {
    const app = createApp({ config: baseConfig() });
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
    const info = vi.spyOn(console, "info").mockImplementation(() => {});

    const app = createApp({
      config: baseConfig(),
      replyClient,
    });

    const body = {
      events: [
        {
          type: "message",
          replyToken: "reply-1",
          source: { type: "user", userId: "U-allowed" },
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
    expect(info).toHaveBeenCalledWith("line message userId=U-allowed");
  });

  it("keeps primary result PDF links in the LINE reply", async () => {
    const replyMessage = vi.fn(async () => ({}));
    const app = createApp({
      config: baseConfig(),
      replyClient: { replyMessage },
    });

    const body = {
      events: [
        {
          type: "message",
          replyToken: "reply-pdf",
          source: { type: "user", userId: "U-allowed" },
          message: { type: "text", text: "昨日のなごみ駅伝の結果のPDF渡して" },
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
    const arg = replyMessage.mock.calls[0]?.[0] as
      | { messages: Array<{ type: string; text?: string }> }
      | undefined;
    const text = arg?.messages.map((message) => message.text ?? "").join("\n") ?? "";
    expect(text).toContain("女子成績表PDF");
    expect(text).toContain("raw.githubusercontent.com");
  });

  it("replies guidance for non-text message", async () => {
    const replyMessage = vi.fn(async () => ({}));
    const app = createApp({
      config: baseConfig(),
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

  it("does not reply when userId is on deny list", async () => {
    const replyMessage = vi.fn(async () => ({}));
    const info = vi.spyOn(console, "info").mockImplementation(() => {});

    const app = createApp({
      config: baseConfig({ LINE_DENIED_USER_IDS: "U-denied, U-other" }),
      replyClient: { replyMessage },
    });

    const body = {
      events: [
        {
          type: "message",
          replyToken: "reply-deny",
          source: { type: "user", userId: "U-denied" },
          message: { type: "text", text: "荒玉駅伝で岱明は何位？" },
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
    expect(replyMessage).not.toHaveBeenCalled();
    expect(info).toHaveBeenCalledWith("line message userId=U-denied");
    expect(info).toHaveBeenCalledWith("line denied userId=U-denied");
  });

  it("still replies when source.userId is missing even if deny list is set", async () => {
    const replyMessage = vi.fn(async () => ({}));
    const app = createApp({
      config: baseConfig({ LINE_DENIED_USER_IDS: "U-denied" }),
      replyClient: { replyMessage },
    });

    const body = {
      events: [
        {
          type: "message",
          replyToken: "reply-nosource",
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
  });
});
