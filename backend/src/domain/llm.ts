import type { AppConfig } from "../config.js";

/** Free-tier friendly; 2.5-flash-lite is blocked for new API keys (404). */
export const GEMINI_MODEL = "gemini-3.5-flash-lite";

export type LlmClient = {
  complete(system: string, user: string): Promise<string>;
};

export function createLlmClient(config: AppConfig): LlmClient | null {
  if (config.AI_PROVIDER === "gemini") {
    if (!config.GEMINI_API_KEY) return null;
    return createGeminiClient(config.GEMINI_API_KEY);
  }
  if (config.AI_PROVIDER === "anthropic") {
    if (!config.ANTHROPIC_API_KEY) return null;
    return createAnthropicClient(config.ANTHROPIC_API_KEY);
  }
  if (!config.OPENAI_API_KEY) return null;
  return createOpenAiClient(config.OPENAI_API_KEY);
}

export function createGeminiClient(apiKey: string, opts?: { fetchImpl?: typeof fetch }): LlmClient {
  const fetchImpl = opts?.fetchImpl ?? fetch;
  return {
    async complete(system, user) {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`;
      const res = await fetchImpl(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": apiKey,
        },
        body: JSON.stringify({
          systemInstruction: {
            parts: [{ text: system }],
          },
          contents: [
            {
              role: "user",
              parts: [{ text: user }],
            },
          ],
          generationConfig: {
            maxOutputTokens: 1200,
            temperature: 0.2,
          },
        }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Gemini error ${res.status}: ${body.slice(0, 200)}`);
      }
      const data = (await res.json()) as {
        candidates?: Array<{
          content?: { parts?: Array<{ text?: string }> };
        }>;
      };
      const text = data.candidates?.[0]?.content?.parts
        ?.map((p) => p.text ?? "")
        .join("")
        .trim();
      return text || "回答を生成できませんでした。";
    },
  };
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
