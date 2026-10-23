import { defineConfig } from "@playwright/test";

const apiOrigin = process.env.DUBAIIO_API_ORIGIN ?? "http://127.0.0.1:8030";

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  use: { baseURL: "http://127.0.0.1:3041" },
  webServer: {
    command: "npm run build && npm run start -- -p 3041",
    url: "http://127.0.0.1:3041",
    reuseExistingServer: false,
    timeout: 240_000,
    env: { DUBAIIO_API_ORIGIN: apiOrigin },
  },
});
