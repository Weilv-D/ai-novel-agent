import { test as base, expect, Page, APIRequestContext } from "@playwright/test";

const API_KEY = "e2e-test-key";
const API_KEY_HEADER = "X-API-Key";

type TestFixtures = {
  authenticatedPage: Page;
  apiContext: APIRequestContext;
  testProjectId: string;
};

export const test = base.extend<TestFixtures>({
  apiContext: async ({ playwright }, use) => {
    const context = await playwright.request.newContext({
      baseURL: "http://localhost:8001",
      extraHTTPHeaders: {
        [API_KEY_HEADER]: API_KEY,
        "Content-Type": "application/json",
      },
    });
    await use(context);
    await context.dispose();
  },

  authenticatedPage: async ({ page }, use) => {
    await page.goto("/");
    await page.evaluate((key) => {
      localStorage.setItem("api_key", key);
    }, API_KEY);
    await use(page);
  },

  testProjectId: async ({ apiContext }, use) => {
    const response = await apiContext.post("/api/v1/projects", {
      data: {
        name: `E2E Test Project ${Date.now()}`,
        genre: "测试题材",
        target_audience: "测试受众",
        agent_profile_id: "default",
      },
    });
    expect(response.ok()).toBeTruthy();
    const project = await response.json();
    await use(project.id);
    await apiContext.delete(`/api/v1/projects/${project.id}`);
  },
});

export async function createProject(apiContext: APIRequestContext, name?: string) {
  const response = await apiContext.post("/api/v1/projects", {
    data: {
      name: name || `E2E Test Project ${Date.now()}`,
      genre: "测试题材",
      target_audience: "测试受众",
      agent_profile_id: "default",
    },
  });
  if (!response.ok()) {
    throw new Error(`Failed to create project: ${await response.text()}`);
  }
  return response.json();
}

export async function getThread(apiContext: APIRequestContext, projectId: string) {
  const response = await apiContext.post("/api/v1/agent/threads", {
    data: { project_id: projectId },
  });
  if (!response.ok()) {
    throw new Error(`Failed to get thread: ${await response.text()}`);
  }
  return response.json();
}

export async function sendMessage(
  apiContext: APIRequestContext,
  threadId: string,
  content: string
) {
  const response = await apiContext.post(
    `/api/v1/agent/threads/${threadId}/messages`,
    {
      data: { content, context: {} },
    }
  );
  if (!response.ok()) {
    throw new Error(`Failed to send message: ${await response.text()}`);
  }
  return response.json();
}

export async function confirmRun(apiContext: APIRequestContext, runId: string) {
  const response = await apiContext.post(`/api/v1/agent/runs/${runId}/confirm`);
  if (!response.ok()) {
    throw new Error(`Failed to confirm run: ${await response.text()}`);
  }
  return response.json();
}

export async function confirmHighRiskRun(apiContext: APIRequestContext, runId: string) {
  const response = await apiContext.post(
    `/api/v1/agent/runs/${runId}/confirm-high-risk`
  );
  if (!response.ok()) {
    throw new Error(`Failed to confirm high-risk run: ${await response.text()}`);
  }
  return response.json();
}

export async function waitForRunStatus(
  apiContext: APIRequestContext,
  runId: string,
  expectedStatus: string,
  timeout = 10000
): Promise<void> {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    const response = await apiContext.get(`/api/v1/agent/runs/${runId}`);
    if (!response.ok()) {
      throw new Error(`Failed to get run: ${await response.text()}`);
    }
    const run = await response.json();
    if (run.status === expectedStatus) {
      return;
    }
    if (run.status === "failed" || run.status === "cancelled") {
      throw new Error(`Run ended with status ${run.status}: ${run.error_message}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timeout waiting for run status ${expectedStatus}`);
}

export async function getCharacter(
  apiContext: APIRequestContext,
  projectId: string,
  characterId: string
) {
  const response = await apiContext.get(
    `/api/v1/projects/${projectId}/characters/${characterId}`
  );
  if (!response.ok()) {
    return null;
  }
  return response.json();
}

export async function listCharacters(apiContext: APIRequestContext, projectId: string) {
  const response = await apiContext.get(
    `/api/v1/projects/${projectId}/characters`
  );
  if (!response.ok()) {
    throw new Error(`Failed to list characters: ${await response.text()}`);
  }
  return response.json();
}

export async function getWorldSetting(
  apiContext: APIRequestContext,
  projectId: string,
  settingId: string
) {
  const response = await apiContext.get(
    `/api/v1/projects/${projectId}/world-settings/${settingId}`
  );
  if (!response.ok()) {
    return null;
  }
  return response.json();
}

export async function listWorldSettings(apiContext: APIRequestContext, projectId: string) {
  const response = await apiContext.get(
    `/api/v1/projects/${projectId}/world-settings`
  );
  if (!response.ok()) {
    throw new Error(`Failed to list world settings: ${await response.text()}`);
  }
  return response.json();
}

export async function getChapter(
  apiContext: APIRequestContext,
  projectId: string,
  chapterId: string
) {
  const response = await apiContext.get(
    `/api/v1/projects/${projectId}/chapters/${chapterId}`
  );
  if (!response.ok()) {
    return null;
  }
  return response.json();
}

export async function listChapters(apiContext: APIRequestContext, projectId: string) {
  const response = await apiContext.get(
    `/api/v1/projects/${projectId}/chapters`
  );
  if (!response.ok()) {
    throw new Error(`Failed to list chapters: ${await response.text()}`);
  }
  return response.json();
}

export { expect };
