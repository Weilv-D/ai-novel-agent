"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { SortableList } from "@/components/dnd/SortableList";
import { ApiError, chapterApi, volumeApi } from "@/lib/api-client";
import { getChapterStatusMeta } from "@/lib/presentation";
import type { Chapter, Volume } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import { useToast } from "@/components/ui/Toast";

export default function ChaptersPage() {
  const params = useParams();
  const projectId = params.id as string;
  const toast = useToast();

  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [volumes, setVolumes] = useState<Volume[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reorderingVolumeId, setReorderingVolumeId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [chapterData, volumeData] = await Promise.all([
        chapterApi.list(projectId) as Promise<Chapter[]>,
        volumeApi.list(projectId) as Promise<Volume[]>,
      ]);
      setChapters(chapterData.sort((a, b) => a.chapter_number - b.chapter_number));
      setVolumes(volumeData.sort((a, b) => (a.volume_number || 0) - (b.volume_number || 0)));
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Failed to load chapters");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const groupedVolumes = useMemo(() => {
    const chapterMap = new Map<string, Chapter[]>();
    for (const chapter of chapters) {
      const key = chapter.volume_id || "__unassigned__";
      const bucket = chapterMap.get(key) || [];
      bucket.push(chapter);
      chapterMap.set(key, bucket);
    }
    return volumes.map((volume) => ({
      volume,
      chapters: (chapterMap.get(volume.id) || []).sort((a, b) => a.chapter_number - b.chapter_number),
    }));
  }, [chapters, volumes]);

  async function handleChapterReorder(volumeId: string, nextVolumeChapters: Chapter[]) {
    const previousChapters = chapters;
    const optimisticChapters = nextVolumeChapters.map((chapter, index) => ({
      ...chapter,
      chapter_number: index + 1,
    }));

    setReorderingVolumeId(volumeId);
    setChapters((currentChapters) => [
      ...currentChapters.filter((chapter) => chapter.volume_id !== volumeId),
      ...optimisticChapters,
    ]);

    try {
      const persistedChapters = await chapterApi.reorder({
        project_id: projectId,
        volume_id: volumeId,
        chapter_ids: optimisticChapters.map((chapter) => chapter.id),
      }) as Chapter[];

      setChapters((currentChapters) => [
        ...currentChapters.filter((chapter) => chapter.volume_id !== volumeId),
        ...persistedChapters,
      ]);
    } catch (err) {
      setChapters(previousChapters);
      toast.error(err instanceof ApiError ? err.detail : "章节排序保存失败");
    } finally {
      setReorderingVolumeId(null);
    }
  }

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link href={`/projects/${projectId}`} className="ink-backlink mb-2">
              ← 返回项目
            </Link>
            <p className="ink-kicker">Outline Structure</p>
            <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">章节与章纲</h1>
            <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-800))]">
              先按卷细纲组织章节，再在每章内部继续拆分场景与正文执行。
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" href={`/projects/${projectId}/volumes`}>管理卷细纲</Button>
            <Button href={`/projects/${projectId}/chapters/new`}>新建章节</Button>
          </div>
        </div>

        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载章节中..." />
          </div>
        )}

        {error && !loading && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center">
                <p className="mb-4 text-[rgb(var(--danger))]">{error}</p>
                <Button onClick={loadData}>重试</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && volumes.length === 0 && (
          <Card padding="lg">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">
                  还没有卷细纲
                </h3>
                <p className="mb-6 text-[rgb(var(--ink-800))]">
                  先建立卷，再把章节作为卷细纲下的章纲条目组织起来。
                </p>
                <Button href={`/projects/${projectId}/volumes/new`}>创建第一卷</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && volumes.length > 0 && (
          <div className="space-y-6">
            {groupedVolumes.map(({ volume, chapters: volumeChapters }) => (
              <Card key={volume.id}>
                <CardContent className="p-6">
                  <div className="flex flex-col gap-4 border-b border-[rgba(var(--line),0.12)] pb-5 lg:flex-row lg:items-start lg:justify-between">
                    <div className="max-w-3xl">
                      <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-800))]">
                        第 {volume.volume_number || "?"} 卷
                      </div>
                      <h2 className="ink-display mt-2 text-3xl font-semibold text-[rgb(var(--ink-950))]">
                        {volume.title || "未命名卷"}
                      </h2>
                      <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--ink-800))]">
                        {volume.outline || "尚未填写卷细纲总述。"}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="outline" size="sm" href={`/projects/${projectId}/volumes/${volume.id}`}>
                        查看卷细纲
                      </Button>
                      <Button size="sm" href={`/projects/${projectId}/chapters/new?volumeId=${volume.id}`}>
                        在此卷新建章节
                      </Button>
                    </div>
                  </div>

                  {volumeChapters.length === 0 ? (
                    <div className="py-8 text-center text-sm leading-7 text-[rgb(var(--ink-800))]">
                      当前卷还没有章纲。
                    </div>
                  ) : (
                    <div className="mt-5">
                      <div className="mb-3 flex items-center justify-between text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
                        <span>拖拽左侧手柄调整章序</span>
                        {reorderingVolumeId === volume.id ? <span>正在保存顺序...</span> : null}
                      </div>
                      <SortableList
                        items={volumeChapters}
                        className="space-y-4"
                        disabled={reorderingVolumeId !== null}
                        onReorder={(items) => handleChapterReorder(volume.id, items)}
                        getItemLabel={(chapter) => `拖拽排序 ${chapter.title || `第 ${chapter.chapter_number} 章`}`}
                        renderItem={(chapter) => {
                        const statusMeta = getChapterStatusMeta(chapter.status);
                        return (
                          <div
                            className="rounded-[1.2rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] p-5 transition-transform duration-200 hover:-translate-y-1"
                          >
                            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                              <div className="flex-1">
                                <div className="mb-2 flex flex-wrap items-center gap-3">
                                  <span className="text-sm font-medium text-[rgb(var(--ink-800))]">
                                    第 {chapter.chapter_number} 章
                                  </span>
                                  <h3 className="ink-display text-2xl font-semibold text-[rgb(var(--ink-950))]">
                                    {chapter.title || "无标题"}
                                  </h3>
                                  <span className={statusMeta.className}>{statusMeta.label}</span>
                                </div>
                                <p className="mb-2 line-clamp-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                                  {chapter.outline || "尚未填写章纲。"}
                                </p>
                                <div className="text-sm text-[rgb(var(--ink-800))]">
                                  更新于 {new Date(chapter.updated_at).toLocaleDateString("zh-CN")}
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <Button variant="outline" size="sm" href={`/projects/${projectId}/chapters/${chapter.id}`}>
                                  查看
                                </Button>
                                <Button variant="outline" size="sm" href={`/projects/${projectId}/chapters/${chapter.id}/edit`}>
                                  编辑
                                </Button>
                              </div>
                            </div>
                          </div>
                        );
                        }}
                      />
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
