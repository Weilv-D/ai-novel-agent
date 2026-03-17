"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { AgentChatPanel } from "@/components/AgentChatPanel";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { ApiError, chapterApi, sceneApi, volumeApi } from "@/lib/api-client";
import { getChapterStatusMeta } from "@/lib/presentation";
import type { Chapter, Scene, Volume } from "@/lib/types";

export default function ChapterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const chapterId = params.chapterId as string;

  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [volume, setVolume] = useState<Volume | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadChapter = useCallback(async () => {
    try {
      setError(null);
      const data = await chapterApi.get(chapterId) as Chapter;
      setChapter(data);
      if (data.volume_id) {
        const volumeData = await volumeApi.get(data.volume_id) as Volume;
        setVolume(volumeData);
      } else {
        setVolume(null);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setError("章节不存在");
        } else {
          setError(err.detail);
        }
      } else {
        setError("加载章节失败");
      }
    } finally {
      setLoading(false);
    }
  }, [chapterId]);

  const loadScenes = useCallback(async () => {
    try {
      const data = await sceneApi.list(chapterId) as Scene[];
      setScenes(data.sort((a, b) => a.scene_order - b.scene_order));
    } catch (err) {
      console.error("Failed to load scenes:", err);
    }
  }, [chapterId]);

  useEffect(() => {
    loadChapter();
    loadScenes();
  }, [loadChapter, loadScenes]);

  async function handleDelete() {
    try {
      setDeleting(true);
      await chapterApi.delete(chapterId);
      router.push(`/projects/${projectId}/chapters`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "删除章节失败");
      setDeleting(false);
      setDeleteModalOpen(false);
    }
  }

  if (loading) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-4xl px-4 py-8">
          <LoadingSpinner size="lg" text="加载章节中..." />
        </div>
      </main>
    );
  }

  if (error || !chapter) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-4xl px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">
                  {error || "章节未找到"}
                </h3>
                <Button href={`/projects/${projectId}/chapters`}>返回章节列表</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  const statusMeta = getChapterStatusMeta(chapter.status);

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-4xl px-4 py-10">
        <div className="mb-8">
          <Link href={`/projects/${projectId}/chapters`} className="ink-backlink mb-4">
            ← 返回章节列表
          </Link>
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex-1">
              <p className="ink-kicker">Chapter Detail</p>
              <div className="mb-2 mt-3 flex flex-wrap items-center gap-3">
                <span className="text-sm font-medium text-[rgb(var(--ink-800))]">
                  第 {chapter.chapter_number} 章
                </span>
                <h1 className="ink-display text-4xl font-semibold text-[rgb(var(--ink-950))]">
                  {chapter.title || "无标题"}
                </h1>
                <span className={statusMeta.className}>{statusMeta.label}</span>
              </div>
              {volume && (
                <Link
                  href={`/projects/${projectId}/volumes/${volume.id}`}
                  className="inline-flex rounded-full border border-[rgba(var(--line),0.14)] px-3 py-1 text-xs tracking-[0.08em] text-[rgb(var(--ink-800))] transition-colors hover:bg-[rgba(var(--ink-950),0.05)]"
                >
                  所属卷：第 {volume.volume_number || "?"} 卷 {volume.title || "未命名卷"}
                </Link>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" href={`/projects/${projectId}/chapters/${chapterId}/edit`}>
                编辑
              </Button>
              <Button variant="danger" size="sm" onClick={() => setDeleteModalOpen(true)}>
                删除
              </Button>
            </div>
          </div>
        </div>

        <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-3">
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg">章纲</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--ink-800))]">
                {chapter.outline || "尚未填写章纲。"}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">统计信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                <span className="text-[rgb(var(--ink-800))]">场景数</span>
                <span className="font-medium text-[rgb(var(--ink-950))]">{scenes.length}</span>
              </div>
              <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                <span className="text-[rgb(var(--ink-800))]">创建时间</span>
                <span className="font-medium text-[rgb(var(--ink-950))]">
                  {new Date(chapter.created_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
              <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                <span className="text-[rgb(var(--ink-800))]">更新时间</span>
                <span className="font-medium text-[rgb(var(--ink-950))]">
                  {new Date(chapter.updated_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
              {volume && (
                <div className="rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-4">
                  <div className="mb-2 text-[rgb(var(--ink-800))]">卷细纲归属</div>
                  <Link
                    href={`/projects/${projectId}/volumes/${volume.id}`}
                    className="text-sm font-medium text-[rgb(var(--ink-950))] hover:underline"
                  >
                    第 {volume.volume_number || "?"} 卷 {volume.title || "未命名卷"}
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          {chapter.notes && (
            <Card className="md:col-span-3">
              <CardHeader>
                <CardTitle className="text-lg">备注</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--ink-800))]">
                  {chapter.notes}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>场景列表</CardTitle>
              <Button size="sm" href={`/projects/${projectId}/chapters/${chapterId}/scenes/new`}>
                新建场景
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {scenes.length === 0 ? (
              <div className="py-8 text-center text-[rgb(var(--ink-800))]">
                <p>暂无场景</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  href={`/projects/${projectId}/chapters/${chapterId}/scenes/new`}
                >
                  创建第一个场景
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {scenes.map((scene) => (
                  <div
                    key={scene.id}
                    className="flex items-center justify-between rounded-[1.15rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-subtle)] p-4 transition-colors hover:bg-[var(--surface-elevated)]"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-[rgb(var(--ink-800))]">场景 {scene.scene_order}</span>
                        {scene.location && (
                          <span className="text-sm text-[rgb(var(--ink-800))]">📍 {scene.location}</span>
                        )}
                      </div>
                      {scene.content && (
                        <p className="mt-1 line-clamp-2 text-sm leading-7 text-[rgb(var(--ink-800))]">
                          {scene.content}
                        </p>
                      )}
                    </div>
                    <Button variant="outline" size="sm" href={`/projects/${projectId}/chapters/${chapterId}/scenes/${scene.id}`}>
                      查看
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <AgentChatPanel
          projectId={projectId}
          context={{ chapter_id: chapterId, chapter_number: chapter.chapter_number }}
        />

        <Modal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          onConfirm={handleDelete}
          title="删除章节"
          message={`确定要删除章节"${chapter.title}"吗？此操作无法撤销。`}
          confirmText="删除"
          cancelText="取消"
          variant="danger"
          loading={deleting}
        />
      </div>
    </main>
  );
}
