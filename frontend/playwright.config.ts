import { defineConfig } from "@playwright/test"

const liveBaseURL = process.env.LIVE_E2E_BASE_URL

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.ts",
  use: { baseURL: liveBaseURL ?? "http://127.0.0.1:5173" },
  webServer: liveBaseURL ? undefined : { command: "npm run dev -- --host 127.0.0.1", url: "http://127.0.0.1:5173" },
})
