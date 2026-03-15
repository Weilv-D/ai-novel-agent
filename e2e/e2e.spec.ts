import { test, expect } from "./fixtures/test-helpers";

test.describe("E2E 测试套件", () => {
  test.describe("项目创建与管理", () => {
    test("创建项目并进入项目工作台", async ({ authenticatedPage, apiContext }) => {
      await authenticatedPage.goto("/projects");
      await authenticatedPage.click('[data-testid="new-project-btn"]');

      await authenticatedPage.fill('[data-testid="project-name-input"]', "E2E 测试项目");
      await authenticatedPage.click('[data-testid="create-project-btn"]');

      await authenticatedPage.waitForURL(/\/projects\/[a-f0-9-]+/);

      await expect(authenticatedPage.locator("h1")).toContainText("E2E 测试项目");

      const url = authenticatedPage.url();
      const projectId = url.split("/projects/")[1];
      if (projectId) {
        await apiContext.delete(`/api/v1/projects/${projectId}`);
      }
    });
  });

  test.describe("Agent 工作流", () => {
    test("通过 Agent 创建人物并确认执行，页面刷新后人物存在", async ({
      authenticatedPage,
      apiContext,
      testProjectId,
    }) => {
      await authenticatedPage.goto(`/projects/${testProjectId}`);

      await authenticatedPage.fill(
        '[data-testid="agent-input"]',
        "创建一个测试人物"
      );
      await authenticatedPage.click('[data-testid="agent-send-btn"]');

      await expect(authenticatedPage.locator('[data-testid="confirm-run-btn"]')).toBeVisible({
        timeout: 10000,
      });

      await authenticatedPage.click('[data-testid="confirm-run-btn"]');

      await expect(authenticatedPage.locator("text=林逸风")).toBeVisible({ timeout: 10000 });

      await authenticatedPage.goto(`/projects/${testProjectId}/characters`);
      await expect(authenticatedPage.locator("text=林逸风")).toBeVisible();
    });

    test("通过 Agent 修改世界观并确认执行，详情页内容更新", async ({
      authenticatedPage,
      testProjectId,
    }) => {
      await authenticatedPage.goto(`/projects/${testProjectId}`);

      await authenticatedPage.fill(
        '[data-testid="agent-input"]',
        "修改世界观设定"
      );
      await authenticatedPage.click('[data-testid="agent-send-btn"]');

      await expect(authenticatedPage.locator('[data-testid="confirm-run-btn"]')).toBeVisible({
        timeout: 10000,
      });

      await authenticatedPage.click('[data-testid="confirm-run-btn"]');

      await expect(authenticatedPage.locator("text=灵气体系")).toBeVisible({ timeout: 10000 });

      await authenticatedPage.goto(`/projects/${testProjectId}/worldsettings`);
      await expect(authenticatedPage.locator("text=灵气体系")).toBeVisible();
    });

    test("通过 Agent 执行高风险章节正文覆盖，必须经过二次确认", async ({
      authenticatedPage,
      apiContext,
      testProjectId,
    }) => {
      const chapterResponse = await apiContext.post(
        `/api/v1/projects/${testProjectId}/chapters`,
        {
          data: {
            chapter_number: 1,
            title: "测试章节",
            content: "原有内容",
          },
        }
      );
      expect(chapterResponse.ok()).toBeTruthy();
      const chapter = await chapterResponse.json();

      await authenticatedPage.goto(`/projects/${testProjectId}`);

      await authenticatedPage.fill(
        '[data-testid="agent-input"]',
        "高风险正文覆盖"
      );
      await authenticatedPage.click('[data-testid="agent-send-btn"]');

      await expect(authenticatedPage.locator('[data-testid="confirm-run-btn"]')).toBeVisible({
        timeout: 10000,
      });

      await authenticatedPage.click('[data-testid="confirm-run-btn"]');

      await expect(authenticatedPage.locator('[data-testid="confirm-high-risk-btn"]')).toBeVisible({
        timeout: 10000,
      });

      await expect(authenticatedPage.locator("text=高风险")).toBeVisible();

      await authenticatedPage.click('[data-testid="confirm-high-risk-btn"]');

      await expect(authenticatedPage.locator("text=新的章节正文内容")).toBeVisible({
        timeout: 10000,
      });

      const chapterDetailResponse = await apiContext.get(
        `/api/v1/projects/${testProjectId}/chapters/${chapter.id}`
      );
      const updatedChapter = await chapterDetailResponse.json();
      expect(updatedChapter.content).toContain("新的章节正文内容");
    });
  });

  test.describe("导出功能", () => {
    test("导出项目文本成功", async ({ authenticatedPage, testProjectId }) => {
      await authenticatedPage.goto(`/projects/${testProjectId}`);

      const downloadPromise = authenticatedPage.waitForEvent("download");

      await authenticatedPage.click('[data-testid="export-txt-btn"]');

      const download = await downloadPromise;
      expect(download.suggestedFilename()).toContain(".txt");
    });

    test("导出项目包成功", async ({ authenticatedPage, testProjectId }) => {
      await authenticatedPage.goto(`/projects/${testProjectId}`);

      const downloadPromise = authenticatedPage.waitForEvent("download");

      await authenticatedPage.click('[data-testid="export-package-btn"]');

      const download = await downloadPromise;
      expect(download.suggestedFilename()).toContain(".zip");
    });
  });

  test.describe("项目包导入功能", () => {
    test("导出后重新导入得到新项目副本", async ({
      authenticatedPage,
      apiContext,
      testProjectId,
    }) => {
      await authenticatedPage.goto(`/projects/${testProjectId}`);

      const downloadPromise = authenticatedPage.waitForEvent("download");
      await authenticatedPage.click('[data-testid="export-package-btn"]');
      const download = await downloadPromise;
      expect(download.suggestedFilename()).toContain(".zip");

      const zipPath = await download.path();

      await authenticatedPage.goto("/projects");

      const fileInput = authenticatedPage.locator('[data-testid="import-package-input"]');
      await fileInput.setInputFiles(zipPath);

      await expect(authenticatedPage.locator("text=导入成功")).toBeVisible({ timeout: 15000 });

      await authenticatedPage.click("text=确定");

      await authenticatedPage.waitForURL(/\/projects\/[a-f0-9-]+/);

      const url = authenticatedPage.url();
      const newProjectId = url.split("/projects/")[1];
      expect(newProjectId).toBeTruthy();
      expect(newProjectId).not.toBe(testProjectId);

      const newProjectResponse = await apiContext.get(`/api/v1/projects/${newProjectId}`);
      expect(newProjectResponse.ok()).toBeTruthy();
      const newProject = await newProjectResponse.json();
      expect(newProject.name).toContain("导入副本");
    });
  });
});
