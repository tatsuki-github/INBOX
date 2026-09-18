import express, { type Request, type Response } from "express";
import { messagingApi } from "@line/bot-sdk";
import { hasLineCredentials, hasLlmCredentials, loadConfig, type AppConfig } from "./config.js";
import { parseDeniedUserIds } from "./domain/deny.js";
import { createLlmClient } from "./domain/llm.js";
import { verifyLineSignature } from "./line/signature.js";
import { handleWebhookEvents, type LineWebhookBody, type ReplyClient } from "./line/webhook.js";

export type AppOptions = {
  config?: AppConfig;
  replyClient?: ReplyClient;
};

function rawBodySaver(
  req: Request & { rawBody?: Buffer },
  _res: Response,
  buf: Buffer,
): void {
  req.rawBody = buf;
}

export function createApp(options: AppOptions = {}) {
  const config = options.config ?? loadConfig();
  const deniedUserIds = parseDeniedUserIds(config.LINE_DENIED_USER_IDS);
  const app = express();

  app.get("/health", (_req, res) => {
    res.json({
      ok: true,
      service: "idaten-line-backend",
      corpus: "input/idaten-corpus",
    });
  });

  app.post(
    "/webhook",
    express.json({
      verify: rawBodySaver,
      limit: "1mb",
    }),
    async (req: Request & { rawBody?: Buffer }, res: Response) => {
      const secret = config.LINE_CHANNEL_SECRET;
      if (!secret || !hasLineCredentials(config)) {
        res.status(503).json({ error: "LINE credentials not configured" });
        return;
      }

      const signature = req.get("x-line-signature") ?? undefined;
      if (!req.rawBody) {
        res.status(400).json({ error: "missing raw body" });
        return;
      }

      if (!verifyLineSignature(req.rawBody, secret, signature)) {
        res.status(401).json({ error: "invalid signature" });
        return;
      }

      const replyClient =
        options.replyClient ??
        new messagingApi.MessagingApiClient({
          channelAccessToken: config.LINE_CHANNEL_ACCESS_TOKEN!,
        });

      const llm = hasLlmCredentials(config) ? createLlmClient(config) : null;

      try {
        await handleWebhookEvents(req.body as LineWebhookBody, replyClient, {
          llm,
          deniedUserIds,
        });
        res.status(200).json({ ok: true });
      } catch {
        // Always 200 to LINE after signature OK to avoid retries storms when reply fails
        res.status(200).json({ ok: false });
      }
    },
  );

  return app;
}
