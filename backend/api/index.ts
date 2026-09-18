import { createApp } from "../src/app.js";
import { loadConfig } from "../src/config.js";

const config = loadConfig();
export default createApp({ config });
