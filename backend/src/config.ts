import { z } from "zod";

const envSchema = z
  .object({
    LINE_CHANNEL_SECRET: z.string().min(1).optional(),
    LINE_CHANNEL_ACCESS_TOKEN: z.string().min(1).optional(),
    AI_PROVIDER: z.enum(["openai", "anthropic"]).default("openai"),
    OPENAI_API_KEY: z.string().optional(),
    ANTHROPIC_API_KEY: z.string().optional(),
    PORT: z.coerce.number().default(3001),
    NODE_ENV: z.string().optional(),
  })
  .superRefine((val, ctx) => {
    if (val.AI_PROVIDER === "openai" && !val.OPENAI_API_KEY && val.NODE_ENV === "production") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "OPENAI_API_KEY required when AI_PROVIDER=openai",
        path: ["OPENAI_API_KEY"],
      });
    }
    if (
      val.AI_PROVIDER === "anthropic" &&
      !val.ANTHROPIC_API_KEY &&
      val.NODE_ENV === "production"
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "ANTHROPIC_API_KEY required when AI_PROVIDER=anthropic",
        path: ["ANTHROPIC_API_KEY"],
      });
    }
  });

export type AppConfig = z.infer<typeof envSchema>;

export function loadConfig(env: NodeJS.ProcessEnv = process.env): AppConfig {
  return envSchema.parse(env);
}

export function hasLineCredentials(config: AppConfig): boolean {
  return Boolean(config.LINE_CHANNEL_SECRET && config.LINE_CHANNEL_ACCESS_TOKEN);
}

export function hasLlmCredentials(config: AppConfig): boolean {
  if (config.AI_PROVIDER === "anthropic") {
    return Boolean(config.ANTHROPIC_API_KEY);
  }
  return Boolean(config.OPENAI_API_KEY);
}
