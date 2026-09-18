import { createApp } from "./app.js";
import { loadConfig } from "./config.js";

const config = loadConfig();
const app = createApp({ config });

app.listen(config.PORT, () => {
  console.log(`idaten-line-backend listening on :${config.PORT}`);
});
