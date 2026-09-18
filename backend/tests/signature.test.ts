import { createHmac } from "node:crypto";
import { describe, expect, it } from "vitest";
import { signLineBody, verifyLineSignature } from "../src/line/signature.js";

describe("verifyLineSignature", () => {
  const secret = "test-channel-secret";

  it("accepts valid signature", () => {
    const body = '{"events":[]}';
    const sig = signLineBody(body, secret);
    expect(verifyLineSignature(body, secret, sig)).toBe(true);
  });

  it("rejects tampered body", () => {
    const body = '{"events":[]}';
    const sig = signLineBody(body, secret);
    expect(verifyLineSignature('{"events":[1]}', secret, sig)).toBe(false);
  });

  it("rejects missing signature", () => {
    expect(verifyLineSignature("{}", secret, undefined)).toBe(false);
  });

  it("matches LINE documented HMAC-SHA256 base64", () => {
    const body = Buffer.from('{"destination":"x","events":[]}');
    const expected = createHmac("sha256", secret).update(body).digest("base64");
    expect(signLineBody(body, secret)).toBe(expected);
    expect(verifyLineSignature(body, secret, expected)).toBe(true);
  });
});
