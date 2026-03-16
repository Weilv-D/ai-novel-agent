"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Modal } from "@/components/ui/Modal";
import { ApiError, projectPackageApi, type ProjectImportResponse } from "@/lib/api-client";
import { getProjectStatusMeta } from "@/lib/presentation";
import { useProjectStore } from "@/lib/stores/projectStore";

export default function ProjectsPage() {
  const router = useRouter();
  const { projects, loading, error, fetchProjects } = useProjectStore();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<ProjectImportResponse | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  async function handleImportClick() {
    fileInputRef.current?.click();
  }

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".zip")) {
      setImportError("请选择 .zip 格式的项目包文件");
      setImportModalOpen(true);
      return;
    }

    setImporting(true);
    setImportError(null);
    setImportResult(null);

    try {
      const result = await projectPackageApi.importPackage(file);
      setImportResult(result);
      setImportModalOpen(true);
      await fetchProjects();
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : "导入项目包失败";
      setImportError(message);
      setImportModalOpen(true);
    } finally {
      setImporting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  function handleImportModalClose() {
    setImportModalOpen(false);
    if (importResult) {
      router.push(`/projects/${importResult.project_id}`);
    }
  }

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="ink-kicker">Project Desk</p>
            <h1 className="ink-display mt-3 text-4xl font-semibold text-ink-950">
              我的项目
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-ink-700">
              管理小说创作项目，保持题材、受众、字数目标和当前状态在一个视图内。
            </p>
          </div>
          <div className="flex gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              onChange={handleFileChange}
              className="hidden"
              data-testid="import-package-input"
            />
            <Button
              variant="outline"
              onClick={handleImportClick}
              disabled={importing}
              testId="import-package-btn"
            >
              {importing ? "导入中..." : "导入项目包"}
            </Button>
            <Button href="/projects/new" testId="new-project-btn">新建项目</Button>
          </div>
        </div>

        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载项目中..." />
          </div>
        )}

        {error && !loading && (
          <Card padding="lg" className="max-w-2xl">
            <CardContent>
              <div className="text-center">
                <p className="mb-4 text-red-800">{error}</p>
                <Button onClick={() => fetchProjects()}>重试</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && projects.length === 0 && (
          <Card padding="lg" className="max-w-3xl">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-ink-950">
                  还没有项目
                </h3>
                <p className="mb-6 text-ink-700">
                  创建您的第一个小说项目，开始 AI 辅助创作之旅
                </p>
                <Button href="/projects/new">创建项目</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && projects.length > 0 && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => {
              const statusMeta = getProjectStatusMeta(project.status);

              return (
                <Link key={project.id} href={`/projects/${project.id}`}>
                  <Card className="ink-grid-card h-full cursor-pointer transition-transform duration-200 hover:-translate-y-1">
                    <CardContent className="pt-6">
                      <div className="mb-3 flex items-start justify-between gap-4">
                        <h3 className="truncate pr-2 text-xl font-semibold text-ink-950">
                          {project.name}
                        </h3>
                        <span className={statusMeta.className}>{statusMeta.label}</span>
                      </div>
                      <p className="text-sm text-ink-700">
                        {project.genre || "未分类"} · {project.target_audience || "未设定受众"}
                      </p>
                      {project.target_word_count && (
                        <div className="mt-4 flex justify-between rounded-[1rem] bg-ink-950/8 px-4 py-3 text-sm text-ink-700">
                          <span>目标字数</span>
                          <span className="font-medium text-ink-950">
                            {project.target_word_count.toLocaleString()}
                          </span>
                        </div>
                      )}
                      <div className="mt-4 pt-2 text-xs text-ink-700">
                        更新于 {new Date(project.updated_at).toLocaleDateString("zh-CN")}
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      <Modal
        isOpen={importModalOpen}
        onClose={handleImportModalClose}
        onConfirm={handleImportModalClose}
        title={importResult ? "导入成功" : "导入失败"}
        message={
          importError ||
          (importResult
            ? `项目「${importResult.project_name}」已成功导入。共导入 ${Object.entries(importResult.imported_counts).map(([k, v]) => `${v} 个${k === "characters" ? "人物" : k === "world_settings" ? "设定" : k === "chapters" ? "章节" : k === "scenes" ? "场景" : k === "volumes" ? "卷" : k === "dependencies" ? "依赖" : k === "snapshots" ? "快照" : k === "memories" ? "记忆" : k}`).join("、")}。${importResult.warnings.length > 0 ? " 存在警告信息，请查看详情。" : ""}`
            : "")
        }
        confirmText="确定"
        cancelText=""
        variant={importResult ? "primary" : "danger"}
      >
        {importResult && importResult.warnings.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-sm font-medium text-ink-900">警告信息：</p>
            {importResult.warnings.map((warning, index) => (
              <div
                key={index}
                className="rounded-lg bg-amber/12 px-3 py-2 text-sm text-ink-800"
              >
                <span className="font-medium">{warning.code}：</span>
                {warning.message}
              </div>
            ))}
          </div>
        )}
      </Modal>
    </main>
  );
}
