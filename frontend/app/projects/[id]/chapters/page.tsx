"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ApiError, chapterApi } from "@/lib/api-client";
import { getChapterStatusMeta } from "@/lib/presentation";
import type { Chapter } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";

export default function ChaptersPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadChapters = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await chapterApi.list(projectId) as Chapter[];
      setChapters(data.sort((a, b) => a.chapter_number - b.chapter_number));
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
    loadChapters();
  }, [loadChapters]);

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link href={`/projects/${projectId}`} className="ink-backlink mb-2">
              ← 返回项目
            </Link>
            <p className="ink-kicker">Chapter Workflow</p>
            <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">章节管理</h1>
            <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-700))]">
              以章节为主线安排故事推进，再把场景拆解到更细的创作颗粒度。
            </p>
          </div>
          <Button href={`/projects/${projectId}/chapters/new`}>新建章节</Button>
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
                <Button onClick={loadChapters}>重试</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && chapters.length === 0 && (
          <Card padding="lg">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">
                  还没有章节
                </h3>
                <p className="mb-6 text-[rgb(var(--ink-700))]">
                  创建第一章，开始构建您的故事
                </p>
                <Button href={`/projects/${projectId}/chapters/new`}>创建第一章</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && chapters.length > 0 && (
          <div className="space-y-4">
            {chapters.map((chapter) => {
              const statusMeta = getChapterStatusMeta(chapter.status);

              return (
                <Card key={chapter.id} className="transition-transform duration-200 hover:-translate-y-1">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="mb-2 flex items-center gap-3">
                          <span className="text-sm font-medium text-[rgb(var(--ink-600))]">
                            第 {chapter.chapter_number} 章
                          </span>
                          <h3 className="ink-display text-2xl font-semibold text-[rgb(var(--ink-950))]">
                            {chapter.title || "无标题"}
                          </h3>
                          <span className={statusMeta.className}>{statusMeta.label}</span>
                        </div>
                        {chapter.outline && (
                          <p className="mb-2 line-clamp-2 text-sm leading-7 text-[rgb(var(--ink-700))]">
                            {chapter.outline}
                          </p>
                        )}
                        <div className="flex items-center gap-4 text-sm text-[rgb(var(--ink-600))]">
                          <span>更新于 {new Date(chapter.updated_at).toLocaleDateString("zh-CN")}</span>
                        </div>
                      </div>
                      <div className="ml-4 flex items-center gap-2">
                        <Button variant="outline" size="sm" href={`/projects/${projectId}/chapters/${chapter.id}`}>
                          查看
                        </Button>
                        <Button variant="outline" size="sm" href={`/projects/${projectId}/chapters/${chapter.id}/edit`}>
                          编辑
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
