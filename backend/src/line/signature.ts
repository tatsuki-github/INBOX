import { createHmac, timingSafeEqual } from "node:crypto";

/**
 * Verify LINE Messaging API request signature (HMAC-SHA256, base64).
 * @see https://developers.line.biz/en/docs/messaging-api/receiving-messages/
 */
export function verifyLineSignature(
  body: string | Buffer,
  channelSecret: string,
  signatureHeader: string | undefined,
): boolean {
  if (!signatureHeader || !channelSecret) {
    return false;
  }
  const bodyBuf = typeof body === "string" ? Buffer.from(body, "utf8") : body;
  const digest = createHmac("sha256", channelSecret).update(bodyBuf).digest("base64");
  const a = Buffer.from(digest);
  const b = Buffer.from(signatureHeader);
  if (a.length !== b.length) {
    return false;
  }
  return timingSafeEqual(a, b);
}

export function signLineBody(body: string | Buffer, channelSecret: string): string {
  const bodyBuf = typeof body === "string" ? Buffer.from(body, "utf8") : body;
  return createHmac("sha256", channelSecret).update(bodyBuf).digest("base64");
}
