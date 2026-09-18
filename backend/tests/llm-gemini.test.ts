import { describe, expect, it, vi } from "vitest";
import { loadConfig, hasLlmCredentials } from "../src/config.js";
import { createGeminiClient, createLlmClient, GEMINI_MODEL } from "../src/domain/llm.js";

describe("loadConfig gemini", () => {
  it("defaults AI_PROVIDER to gemini", () => {
    const config = loadConfig({ PORT: "3001" });
    expect(config.AI_PROVIDER).toBe("gemini");
  });

  it("treats blank GEMINI_API_KEY as missing credentials", () => {
    const config = loadConfig({
      AI_PROVIDER: "gemini",
      GEMINI_API_KEY: "",
      PORT: "3001",
    });
    expect(config.GEMINI_API_KEY).toBeUndefined();
    expect(hasLlmCredentials(config)).toBe(false);
  });

  it("detects GEMINI_API_KEY when set", () => {
    const config = loadConfig({
      AI_PROVIDER: "gemini",
      GEMINI_API_KEY: "test-key",
      PORT: "3001",
    });
    expect(hasLlmCredentials(config)).toBe(true);
    expect(createLlmClient(config)).not.toBeNull();
  });
});

describe("createGeminiClient", () => {
  it("extracts text from generateContent response", async () => {
    const fetchImpl = vi.fn(async () =>
      new Response(
        JSON.stringify({
          candidates: [{ content: { parts: [{ text: "岱明は3位です。" }] } }],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    ) as unknown as typeof fetch;

    const client = createGeminiClient("test-key", { fetchImpl });
    const text = await client.complete("system", "user question");
    expect(text).toBe("岱明は3位です。");

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toContain(`/models/${GEMINI_MODEL}:generateContent`);
    expect((init.headers as Record<string, string>)["x-goog-api-key"]).toBe("test-key");
    const body = JSON.parse(String(init.body)) as {
      systemInstruction: { parts: Array<{ text: string }> };
      contents: Array<{ role: string; parts: Array<{ text: string }> }>;
    };
    expect(body.systemInstruction.parts[0]?.text).toBe("system");
    expect(body.contents[0]?.parts[0]?.text).toBe("user question");
  });

  it("throws on non-2xx", async () => {
    const fetchImpl = vi.fn(async () =>
      new Response("rate limited", { status: 429 }),
    ) as unknown as typeof fetch;
    const client = createGeminiClient("test-key", { fetchImpl });
    await expect(client.complete("s", "u")).rejects.toThrow(/Gemini error 429/);
  });
});
