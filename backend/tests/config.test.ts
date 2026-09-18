import { describe, expect, it } from "vitest";
import { loadConfig, hasLlmCredentials } from "../src/config.js";

describe("loadConfig", () => {
  it("accepts blank env strings from .env.example", () => {
    const config = loadConfig({
      LINE_CHANNEL_SECRET: "",
      LINE_CHANNEL_ACCESS_TOKEN: "",
      OPENAI_API_KEY: "",
      AI_PROVIDER: "openai",
      PORT: "3001",
    });
    expect(config.PORT).toBe(3001);
    expect(config.LINE_CHANNEL_SECRET).toBeUndefined();
    expect(hasLlmCredentials(config)).toBe(false);
  });
});
