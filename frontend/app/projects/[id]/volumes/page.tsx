"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { ApiError, chapterApi, volumeApi } from "@/lib/api-client";
import { useRouteParam } from "@/lib/navigation";
import type { Chapter, Volume } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";

export default function VolumesPage() {
  const projectId = useRouteParam("id");

  const [volumes, setVolumes] = useState<Volume[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [volumeData, chapterData] = await Promise.all([
        volumeApi.list(projectId) as Promise<Volume[]>,
        chapterApi.list(projectId) as Promise<Chapter[]>,
      ]);
      setVolumes(volumeData.sort((a, b) => (a.volume_number || 0) - (b.volume_number || 0)));
      setChapters(chapterData);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "加载卷细纲失败");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const chapterCountByVolume = useMemo(
    () =>
      chapters.reduce<Record<string, number>>((acc, chapter) => {
        if (chapter.volume_id) {
          acc[chapter.volume_id] = (acc[chapter.volume_id] || 0) + 1;
        }
        return acc;
      }, {}),
    [chapters],
  );

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link href={`/projects/${projectId}`} className="ink-backlink mb-2">
              ← 返回项目
            </Link>
            <p className="ink-kicker">Volume Outline</p>
            <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">卷细纲管理</h1>
            <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-800))]">
              用卷细纲承载中程目标、因果链和章节排列，再让章节成为卷下的章纲节点。
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" href={`/projects/${projectId}/chapters`}>查看章节</Button>
            <Button href={`/projects/${projectId}/volumes/new`}>新建卷</Button>
          </div>
        </div>

        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载卷细纲中..." />
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
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">还没有卷</h3>
                <p className="mb-6 text-[rgb(var(--ink-800))]">
                  创建第一卷，开始搭建卷细纲与章节路径。
                </p>
                <Button href={`/projects/${projectId}/volumes/new`}>创建第一卷</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && volumes.length > 0 && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {volumes.map((volume) => (
              <Link key={volume.id} href={`/projects/${projectId}/volumes/${volume.id}`}>
                <Card className="h-full cursor-pointer transition-transform duration-200 hover:-translate-y-1">
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="text-xs uppercase tracking-[0.14em] text-[rgb(var(--ink-800))]">
                          第 {volume.volume_number || "?"} 卷
                        </div>
                        <h2 className="ink-display mt-2 text-3xl font-semibold text-[rgb(var(--ink-950))]">
                          {volume.title || "未命名卷"}
                        </h2>
                      </div>
                      <span className="rounded-full border border-[rgba(var(--line),0.14)] px-3 py-1 text-xs tracking-[0.08em] text-[rgb(var(--ink-800))]">
                        章节 {chapterCountByVolume[volume.id] || 0}
                      </span>
                    </div>
                    <p className="mt-4 line-clamp-4 whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--ink-800))]">
                      {volume.outline || "尚未填写卷细纲总述。"}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
