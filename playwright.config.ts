import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3000",
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
      reuseExistingServer: !process.env.CI,
      env: {
        DATABASE_URL: "sqlite+aiosqlite:///./e2e_test.db",
        ADMIN_API_KEY: "e2e-test-key",
        AGENT_E2E_MODE: "fixture",
        AGENT_E2E_FIXTURE_PATH: "./e2e/fixtures",
        LLM_API_KEY: "",
        EMBEDDING_API_KEY: "",
        EMBEDDING_DIMENSION: "1536",
        CORS_ORIGINS: "http://localhost:3000",
      },
    },
    {
      command: "cd frontend && npm run dev -- -p 3000",
      port: 3000,
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
      env: {
        NEXT_PUBLIC_API_URL: "http://localhost:8001",
      },
    },
  ],
});
