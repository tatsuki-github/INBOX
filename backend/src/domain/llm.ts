import type { AppConfig } from "../config.js";

export type LlmClient = {
  complete(system: string, user: string): Promise<string>;
};

export function createLlmClient(config: AppConfig): LlmClient | null {
  if (config.AI_PROVIDER === "anthropic") {
    if (!config.ANTHROPIC_API_KEY) return null;
    return createAnthropicClient(config.ANTHROPIC_API_KEY);
  }
  if (!config.OPENAI_API_KEY) return null;
  return createOpenAiClient(config.OPENAI_API_KEY);
}

function createOpenAiClient(apiKey: string): LlmClient {
  return {
    async complete(system, user) {
      const res = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          temperature: 0.2,
          max_tokens: 700,
          messages: [
            { role: "system", content: system },
            { role: "user", content: user },
          ],
        }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`OpenAI error ${res.status}: ${body.slice(0, 200)}`);
      }
      const data = (await res.json()) as {
        choices?: Array<{ message?: { content?: string } }>;
      };
      return data.choices?.[0]?.message?.content?.trim() || "回答を生成できませんでした。";
    },
  };
}

function createAnthropicClient(apiKey: string): LlmClient {
  return {
    async complete(system, user) {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "claude-3-5-haiku-latest",
          max_tokens: 700,
          system,
          messages: [{ role: "user", content: user }],
        }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Anthropic error ${res.status}: ${body.slice(0, 200)}`);
      }
      const data = (await res.json()) as {
        content?: Array<{ type: string; text?: string }>;
      };
      const text = data.content?.find((c) => c.type === "text")?.text;
      return text?.trim() || "回答を生成できませんでした。";
    },
  };
}
