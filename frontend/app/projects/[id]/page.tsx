"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { AgentWorkspace } from "@/components/AgentWorkspace";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Modal } from "@/components/ui/Modal";
import { ApiError, exportApi, projectPackageApi } from "@/lib/api-client";
import { getProjectStatusMeta } from "@/lib/presentation";
import { useProjectStore } from "@/lib/stores/projectStore";

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    currentProject: project,
    currentProjectLoading: loading,
    currentProjectError: error,
    fetchProject,
    clearCurrentProject,
    deleteProject,
  } = useProjectStore();

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (id) {
      fetchProject(id);
    }

    return () => {
      clearCurrentProject();
    };
  }, [id, fetchProject, clearCurrentProject]);

  async function handleDelete() {
    try {
      setDeleting(true);
      await deleteProject(id);
      router.push("/projects");
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.detail);
      } else {
        alert("删除项目失败");
      }
      setDeleting(false);
      setDeleteModalOpen(false);
    }
  }

  if (loading) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-5xl px-4 py-8">
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载项目中..." />
          </div>
        </div>
      </main>
    );
  }

  if (error || !project) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-5xl px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">
                  项目未找到
                </h3>
                <p className="mb-6 text-[rgb(var(--ink-800))]">
                  {error || "无法加载项目信息"}
                </p>
                <Button href="/projects">返回项目列表</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  const statusMeta = getProjectStatusMeta(project.status);

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-7xl px-4 py-10">
        <div className="mb-10">
          <Link href="/projects" className="ink-backlink mb-5">
            ← 返回项目列表
          </Link>
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <p className="ink-kicker">Project Detail</p>
              <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">
                {project.name}
              </h1>
              <p className="mt-4 text-base leading-7 text-[rgb(var(--ink-800))]">
                {project.summary || "暂无描述"}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <span className={statusMeta.className}>{statusMeta.label}</span>
              <Button variant="outline" href={`/projects/${project.id}/edit`} size="sm">
                编辑
              </Button>
              <Button variant="danger" onClick={() => setDeleteModalOpen(true)} size="sm">
                删除
              </Button>
            </div>
          </div>
        </div>

        <div className="mb-8 grid grid-cols-1 gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="text-lg">基本信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                <span className="text-[rgb(var(--ink-800))]">题材</span>
                <span className="font-medium text-[rgb(var(--ink-950))]">{project.genre || "未分类"}</span>
              </div>
              <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                <span className="text-[rgb(var(--ink-800))]">目标受众</span>
                <span className="font-medium text-[rgb(var(--ink-950))]">
                  {project.target_audience || "未设定"}
                </span>
              </div>
              <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                <span className="text-[rgb(var(--ink-800))]">目标字数</span>
                <span className="font-medium text-[rgb(var(--ink-950))]">
                  {project.target_word_count ? project.target_word_count.toLocaleString() : "-"}
                </span>
              </div>
              <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                <span className="text-[rgb(var(--ink-800))]">创建时间</span>
                <span className="font-medium text-[rgb(var(--ink-950))]">
                  {new Date(project.created_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
              <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                <span className="text-[rgb(var(--ink-800))]">Agent Profile</span>
                <span className="font-medium text-[rgb(var(--ink-950))]">{project.agent_profile_id}</span>
              </div>
              <div className="rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-4">
                <div className="mb-2 text-[rgb(var(--ink-800))]">辅助入口</div>
                <div className="flex flex-wrap gap-2">
                  <Button href={`/projects/${project.id}/chapters`} size="sm">
                    章节
                  </Button>
                  <Button variant="outline" href={`/projects/${project.id}/characters`} size="sm">
                    人物
                  </Button>
                  <Button variant="outline" href={`/projects/${project.id}/worldsettings`} size="sm">
                    设定
                  </Button>
                </div>
              </div>
              <div className="rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-4">
                <div className="mb-2 text-[rgb(var(--ink-800))]">导出</div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" onClick={() => exportApi.download(project.id, "txt")} size="sm" testId="export-txt-btn">
                    TXT
                  </Button>
                  <Button variant="outline" onClick={() => exportApi.download(project.id, "markdown")} size="sm" testId="export-markdown-btn">
                    Markdown
                  </Button>
                  <Button variant="outline" onClick={() => projectPackageApi.downloadPackage(project.id, project.name)} size="sm" testId="export-package-btn">
                    项目包
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-6">
            {project.notes && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">备注</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--ink-800))]">
                    {project.notes}
                  </p>
                </CardContent>
              </Card>
            )}

            <AgentWorkspace
              projectId={project.id}
              projectName={project.name}
              agentProfileId={project.agent_profile_id}
              onProjectRefresh={() => fetchProject(project.id)}
            />
          </div>
        </div>

        <Modal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          onConfirm={handleDelete}
          title="删除项目"
          message={`确定要删除项目"${project.name}"吗？此操作无法撤销，所有相关数据将被永久删除。`}
          confirmText="删除"
          cancelText="取消"
          variant="danger"
          loading={deleting}
        />
      </div>
    </main>
  );
}
