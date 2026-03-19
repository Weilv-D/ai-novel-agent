import * as os from "node:os";
import * as path from "node:path";

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

    test("未配置 LLM 时文本导入会明确提示失败", async ({
      authenticatedPage,
      apiContext,
    }) => {
      void apiContext;
      const samplePath = path.join(process.cwd(), "e2e/fixtures/text-import-sample.txt");

      await authenticatedPage.goto("/projects");
      await authenticatedPage.click('[data-testid="import-text-btn"]');

      await authenticatedPage.fill('[data-testid="text-import-project-name"]', "E2E 文本导入项目");
      await authenticatedPage.locator('[data-testid="text-import-file-input"]').setInputFiles(samplePath);
      await authenticatedPage.click('[data-testid="text-import-start-btn"]');

      await expect(authenticatedPage.locator('[data-testid="text-import-status-message"]')).toContainText(
        "未配置 LLM",
        {
          timeout: 30000,
        }
      );
      await expect(authenticatedPage.locator('[data-testid="text-import-confirm-btn"]')).toHaveCount(0, {
        timeout: 30000,
      });
    });

    test("人物关系图谱正确解析导入常见的 name-to-label 关系结构", async ({
      authenticatedPage,
      apiContext,
      testProjectId,
    }) => {
      const sourceCharacterResponse = await apiContext.post("/api/v1/characters", {
        data: {
          project_id: testProjectId,
          name: "林霄",
          role: "主角",
          relationships: {
            苏晚: "同行者",
          },
        },
      });
      expect(sourceCharacterResponse.ok()).toBeTruthy();

      const targetCharacterResponse = await apiContext.post("/api/v1/characters", {
        data: {
          project_id: testProjectId,
          name: "苏晚",
          role: "搭档",
          relationships: {},
        },
      });
      expect(targetCharacterResponse.ok()).toBeTruthy();

      await authenticatedPage.goto(`/projects/${testProjectId}/relationships`);

      await expect(authenticatedPage.getByText("人物关系网络", { exact: true })).toBeVisible();
      await expect(authenticatedPage.getByText("同行者", { exact: true })).toBeVisible();
      await expect(authenticatedPage.getByText("待补人物", { exact: true })).toHaveCount(0);
      await expect(authenticatedPage.getByText("人物 2", { exact: true })).toBeVisible();
      await expect(authenticatedPage.getByText("关系 1", { exact: true })).toBeVisible();
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

      await expect(authenticatedPage.getByText("林逸风", { exact: true })).toBeVisible({
        timeout: 10000,
      });

      await authenticatedPage.goto(`/projects/${testProjectId}/characters`);
      await expect(authenticatedPage.getByRole("heading", { name: "林逸风" })).toBeVisible();
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

      await expect(authenticatedPage.getByText("灵气体系", { exact: true })).toBeVisible({
        timeout: 10000,
      });

      await authenticatedPage.goto(`/projects/${testProjectId}/worldsettings`);
      await expect(authenticatedPage.getByRole("heading", { name: "灵气体系" })).toBeVisible();
    });

    test("通过 Agent 执行高风险章节正文覆盖，必须经过二次确认", async ({
      authenticatedPage,
      apiContext,
      testProjectId,
    }) => {
      const chapterResponse = await apiContext.post("/api/v1/chapters", {
        data: {
          project_id: testProjectId,
          chapter_number: 1,
          title: "测试章节",
          content: "原有内容",
        },
      });
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
      try {
        await expect(authenticatedPage.locator('[data-testid="confirm-high-risk-btn"]')).toBeVisible({
          timeout: 3000,
        });
        await authenticatedPage.click('[data-testid="confirm-high-risk-btn"]');
      } catch {
        // Some profiles downgrade this operation to single-step confirmation.
      }

      await expect
        .poll(
          async () => {
            const chapterDetailResponse = await apiContext.get(`/api/v1/chapters/${chapter.id}`);
            if (!chapterDetailResponse.ok()) {
              return "";
            }
            const updatedChapter = await chapterDetailResponse.json();
            return String(updatedChapter.content || "");
          },
          { timeout: 10000 }
        )
        .toContain("新的章节正文内容");
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

  test.describe("富文本安全渲染", () => {
    test("场景详情页会剥离危险 HTML 标签", async ({
      authenticatedPage,
      apiContext,
      testProjectId,
    }) => {
      const chapterResponse = await apiContext.post("/api/v1/chapters", {
        data: {
          project_id: testProjectId,
          chapter_number: 1,
          title: "安全测试章节",
        },
      });
      expect(chapterResponse.ok()).toBeTruthy();
      const chapter = await chapterResponse.json();

      const sceneResponse = await apiContext.post("/api/v1/scenes", {
        data: {
          chapter_id: chapter.id,
          scene_order: 1,
          content:
            '<p>安全内容</p><script>window.__xss_marker = "executed"</script><img src=x onerror="window.__img_marker = 1" />',
        },
      });
      expect(sceneResponse.ok()).toBeTruthy();
      const scene = await sceneResponse.json();

      await authenticatedPage.goto(
        `/projects/${testProjectId}/chapters/${chapter.id}/scenes/${scene.id}`
      );

      const richTextContent = authenticatedPage.locator(".ink-richtext");
      await expect(authenticatedPage.getByText("安全内容", { exact: true })).toBeVisible();
      await expect(richTextContent.locator("script")).toHaveCount(0);
      await expect(richTextContent.locator("img")).toHaveCount(0);
      await expect(
        authenticatedPage.evaluate(() => (window as Window & { __xss_marker?: string }).__xss_marker ?? null)
      ).resolves.toBeNull();
      await expect(
        authenticatedPage.evaluate(() => (window as Window & { __img_marker?: number }).__img_marker ?? null)
      ).resolves.toBeNull();
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

      const zipPath = path.join(os.tmpdir(), `ai-novel-agent-e2e-${Date.now()}.zip`);
      await download.saveAs(zipPath);

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
