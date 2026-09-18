import { config as loadDotenv } from "dotenv";
import { createApp } from "./app.js";
import { loadConfig } from "./config.js";

loadDotenv();

const config = loadConfig();
const app = createApp({ config });

app.listen(config.PORT, () => {
  console.log(`idaten-line-backend listening on :${config.PORT}`);
  console.log(`health: http://localhost:${config.PORT}/health`);
  if (!config.LINE_CHANNEL_SECRET || !config.LINE_CHANNEL_ACCESS_TOKEN) {
    console.log("LINE credentials not set — /webhook returns 503 until configured in .env");
  }
  if (!config.OPENAI_API_KEY && !config.ANTHROPIC_API_KEY) {
    console.log("LLM API key not set — answers use offline corpus excerpts");
  }
});
