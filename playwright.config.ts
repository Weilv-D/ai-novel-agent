import { defineConfig, devices } from "@playwright/test";

const reuseServer = process.env.PW_REUSE_SERVER === "1";
const frontendPort = 3100;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: `http://localhost:${frontendPort}`,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "cd backend && ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001",
      port: 8001,
      timeout: 120 * 1000,
      reuseExistingServer: reuseServer,
      env: {
        DATABASE_URL: "sqlite+aiosqlite:///./e2e_test.db",
        ADMIN_API_KEY: "e2e-test-key",
        AGENT_E2E_MODE: "fixture",
        AGENT_E2E_FIXTURE_PATH: "../e2e/fixtures",
        LLM_API_KEY: "",
        EMBEDDING_API_KEY: "",
        EMBEDDING_DIMENSION: "1536",
        CORS_ORIGINS: `http://localhost:${frontendPort}`,
      },
    },
    {
      command: `cd frontend && npm run dev -- -p ${frontendPort}`,
      port: frontendPort,
      timeout: 120 * 1000,
      reuseExistingServer: reuseServer,
      env: {
        NEXT_PUBLIC_API_URL: "http://localhost:8001",
      },
    },
  ],
});
