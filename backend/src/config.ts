import { z } from "zod";

/** Treat missing / blank env as undefined so .env.example copies still boot. */
const optionalNonEmpty = z.preprocess(
  (v) => (typeof v === "string" && v.trim() === "" ? undefined : v),
  z.string().min(1).optional(),
);

const envSchema = z.object({
  LINE_CHANNEL_SECRET: optionalNonEmpty,
  LINE_CHANNEL_ACCESS_TOKEN: optionalNonEmpty,
  /** Comma-separated LINE userIds that receive no bot replies. */
  LINE_DENIED_USER_IDS: z.string().optional(),
  AI_PROVIDER: z.enum(["gemini", "openai", "anthropic"]).default("gemini"),
  GEMINI_API_KEY: optionalNonEmpty,
  OPENAI_API_KEY: optionalNonEmpty,
  ANTHROPIC_API_KEY: optionalNonEmpty,
  PORT: z.coerce.number().default(3001),
  NODE_ENV: z.string().optional(),
});

export type AppConfig = z.infer<typeof envSchema>;

export function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  return envSchema.parse(env);
}

export function hasLineCredentials(config: AppConfig): boolean {
  return Boolean(config.LINE_CHANNEL_SECRET && config.LINE_CHANNEL_ACCESS_TOKEN);
}

export function hasLlmCredentials(config: AppConfig): boolean {
  if (config.AI_PROVIDER === "gemini") {
    return Boolean(config.GEMINI_API_KEY);
  }
  if (config.AI_PROVIDER === "anthropic") {
    return Boolean(config.ANTHROPIC_API_KEY);
  }
  return Boolean(config.OPENAI_API_KEY);
}
