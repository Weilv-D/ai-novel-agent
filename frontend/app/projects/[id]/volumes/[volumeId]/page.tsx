"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { ApiError, chapterApi, volumeApi } from "@/lib/api-client";
import { useRouteParam } from "@/lib/navigation";
import type { Chapter, Volume } from "@/lib/types";

export default function VolumeDetailPage() {
  const router = useRouter();
  const projectId = useRouteParam("id");
  const volumeId = useRouteParam("volumeId");

  const [volume, setVolume] = useState<Volume | null>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [volumeData, chapterData] = await Promise.all([
        volumeApi.get(volumeId) as Promise<Volume>,
        chapterApi.listByVolume(volumeId) as Promise<Chapter[]>,
      ]);
      setVolume(volumeData);
      setChapters(chapterData.sort((a, b) => a.chapter_number - b.chapter_number));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "加载卷细纲失败");
    } finally {
      setLoading(false);
    }
  }, [volumeId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleDelete() {
    try {
      setDeleting(true);
      await volumeApi.delete(volumeId);
      router.push(`/projects/${projectId}/volumes`);
    } catch (err) {
      setDeleting(false);
      setDeleteModalOpen(false);
      toast.error(err instanceof ApiError ? err.detail : "删除卷失败");
    }
  }

  if (loading) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-5xl px-4 py-10">
          <LoadingSpinner size="lg" text="加载卷细纲中..." />
        </div>
      </main>
    );
  }

  if (error || !volume) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-5xl px-4 py-10">
          <Card padding="lg">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">卷未找到</h3>
                <p className="mb-6 text-[rgb(var(--ink-800))]">{error || "无法加载卷信息"}</p>
                <Button href={`/projects/${projectId}/volumes`}>返回卷列表</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-5xl px-4 py-10">
        <div className="mb-8">
          <Link href={`/projects/${projectId}/volumes`} className="ink-backlink mb-4">
            ← 返回卷列表
          </Link>
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex-1">
              <p className="ink-kicker">Volume Detail</p>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <span className="text-sm font-medium text-[rgb(var(--ink-800))]">
                  第 {volume.volume_number || "?"} 卷
                </span>
                <h1 className="ink-display text-4xl font-semibold text-[rgb(var(--ink-950))]">
                  {volume.title || "未命名卷"}
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" href={`/projects/${projectId}/volumes/${volumeId}/edit`}>
                编辑
              </Button>
              <Button variant="danger" size="sm" onClick={() => setDeleteModalOpen(true)}>
                删除
              </Button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <Card>
            <CardHeader>
              <CardTitle>卷细纲总述</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--ink-800))]">
                {volume.outline || "尚未填写卷细纲总述。"}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">基本信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                <span className="text-[rgb(var(--ink-800))]">章节数</span>
                <span className="font-medium text-[rgb(var(--ink-950))]">{chapters.length}</span>
              </div>
              <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                <span className="text-[rgb(var(--ink-800))]">创建时间</span>
                <span className="font-medium text-[rgb(var(--ink-950))]">
                  {new Date(volume.created_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
              <div className="rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-4">
                <div className="mb-2 text-[rgb(var(--ink-800))]">快捷操作</div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" href={`/projects/${projectId}/chapters/new?volumeId=${volume.id}`}>
                    新建章节
                  </Button>
                  <Button variant="outline" size="sm" href={`/projects/${projectId}/chapters`}>
                    查看所有章节
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {volume.notes && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="text-lg">备注</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--ink-800))]">
                {volume.notes}
              </p>
            </CardContent>
          </Card>
        )}

        <Card className="mt-6">
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>卷下章纲</CardTitle>
              <Button size="sm" href={`/projects/${projectId}/chapters/new?volumeId=${volume.id}`}>
                新建章节
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {chapters.length === 0 ? (
              <div className="py-8 text-center text-sm leading-7 text-[rgb(var(--ink-800))]">
                当前卷还没有章节。
              </div>
            ) : (
              <div className="space-y-3">
                {chapters.map((chapter) => (
                  <div
                    key={chapter.id}
                    className="rounded-[1.15rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] px-4 py-4"
                  >
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div className="flex-1">
                        <div className="text-sm font-medium text-[rgb(var(--ink-950))]">
                          第 {chapter.chapter_number} 章 {chapter.title || "无标题"}
                        </div>
                        <p className="mt-2 line-clamp-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                          {chapter.outline || "尚未填写章纲。"}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" href={`/projects/${projectId}/chapters/${chapter.id}`}>
                          查看
                        </Button>
                        <Button variant="outline" size="sm" href={`/projects/${projectId}/chapters/${chapter.id}/edit`}>
                          编辑
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Modal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          onConfirm={handleDelete}
          title="删除卷"
          message={`确定要删除卷「${volume.title || `第${volume.volume_number || "?"}卷`}」吗？只有空卷才能删除。`}
          confirmText="删除"
          cancelText="取消"
          variant="danger"
          loading={deleting}
        />
      </div>
    </main>
  );
}
