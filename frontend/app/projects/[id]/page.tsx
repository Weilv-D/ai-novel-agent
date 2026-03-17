"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { AgentWorkspace } from "@/components/AgentWorkspace";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { ApiError, chapterApi, exportApi, projectPackageApi, volumeApi } from "@/lib/api-client";
import { getProjectStatusMeta } from "@/lib/presentation";
import { useProjectStore } from "@/lib/stores/projectStore";
import type { Chapter, Volume } from "@/lib/types";

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

  const toast = useToast();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [volumes, setVolumes] = useState<Volume[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);

  useEffect(() => {
    if (id) {
      fetchProject(id);
    }

    return () => {
      clearCurrentProject();
    };
  }, [id, fetchProject, clearCurrentProject]);

  useEffect(() => {
    if (!id) {
      return;
    }
    void Promise.all([
      volumeApi.list(id).then((data) => setVolumes(data as Volume[])).catch(() => setVolumes([])),
      chapterApi.list(id).then((data) => setChapters(data as Chapter[])).catch(() => setChapters([])),
    ]);
  }, [id]);

  async function handleDelete() {
    try {
      setDeleting(true);
      await deleteProject(id);
      router.push("/projects");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "删除项目失败");
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
  const chapterCountByVolume = chapters.reduce<Record<string, number>>((acc, chapter) => {
    if (chapter.volume_id) {
      acc[chapter.volume_id] = (acc[chapter.volume_id] || 0) + 1;
    }
    return acc;
  }, {});

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

        <div className="mb-8 grid grid-cols-1 gap-6 xl:grid-cols-[320px_minmax(0,1fr)] xl:items-start">
          <Card className="h-fit xl:sticky xl:top-6 xl:max-h-[calc(100vh-7rem)] xl:overflow-hidden">
            <CardHeader>
              <CardTitle className="text-lg">基本信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm xl:max-h-[calc(100vh-10rem)] xl:overflow-y-auto xl:pr-1">
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
                  <Button variant="outline" href={`/projects/${project.id}/volumes`} size="sm">
                    卷
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
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-lg">项目大纲</CardTitle>
                  <Button variant="outline" href={`/projects/${project.id}/edit`} size="sm">
                    编辑大纲
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--ink-800))]">
                  {project.story_outline || "尚未整理项目大纲。建议先明确主线目标、核心冲突与阶段推进。"}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-lg">卷细纲概览</CardTitle>
                  <Button variant="outline" href={`/projects/${project.id}/volumes`} size="sm">
                    管理卷细纲
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {volumes.length === 0 ? (
                  <div className="rounded-[1rem] border border-dashed border-[rgba(var(--line),0.18)] px-4 py-5 text-sm leading-7 text-[rgb(var(--ink-800))]">
                    还没有卷。建议先建立卷细纲，再把章节归入对应卷中。
                  </div>
                ) : (
                  volumes.map((volume) => (
                    <Link
                      key={volume.id}
                      href={`/projects/${project.id}/volumes/${volume.id}`}
                      className="block rounded-[1.15rem] border border-[rgba(var(--line),0.14)] bg-[var(--surface-elevated)] px-4 py-4 transition-colors hover:bg-[var(--surface-strong)]"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-medium text-[rgb(var(--ink-950))]">
                            第 {volume.volume_number || "?"} 卷 {volume.title || "未命名卷"}
                          </div>
                          <p className="mt-2 line-clamp-2 text-sm leading-7 text-[rgb(var(--ink-800))]">
                            {volume.outline || "尚未填写卷细纲总述。"}
                          </p>
                        </div>
                        <span className="rounded-full border border-[rgba(var(--line),0.14)] px-3 py-1 text-xs tracking-[0.08em] text-[rgb(var(--ink-800))]">
                          章节 {chapterCountByVolume[volume.id] || 0}
                        </span>
                      </div>
                    </Link>
                  ))
                )}
              </CardContent>
            </Card>

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
