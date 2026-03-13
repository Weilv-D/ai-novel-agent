"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/Loading";
import { chapterApi } from "@/lib/api-client";
import type { Chapter } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

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
      // Sort by chapter_number
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

  function getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      draft: "草稿",
      writing: "写作中",
      completed: "已完成",
    };
    return labels[status] || status;
  }

  function getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      draft: "bg-gray-100 text-gray-800",
      writing: "bg-blue-100 text-blue-800",
      completed: "bg-green-100 text-green-800",
    };
    return colors[status] || "bg-gray-100 text-gray-800";
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Link
              href={`/projects/${projectId}`}
              className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-1 mb-2"
            >
              ← 返回项目
            </Link>
            <h1 className="text-3xl font-bold text-gray-900">章节管理</h1>
            <p className="mt-1 text-sm text-gray-600">
              管理小说章节和场景
            </p>
          </div>
          <Button href={`/projects/${projectId}/chapters/new`}>
            新建章节
          </Button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载章节中..." />
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center">
                <p className="text-red-600 mb-4">{error}</p>
                <Button onClick={loadChapters}>重试</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {!loading && !error && chapters.length === 0 && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  还没有章节
                </h3>
                <p className="text-gray-600 mb-6">
                  创建第一章，开始构建您的故事
                </p>
                <Button href={`/projects/${projectId}/chapters/new`}>
                  创建第一章
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Chapters List */}
        {!loading && !error && chapters.length > 0 && (
          <div className="space-y-4">
            {chapters.map((chapter) => (
              <Card key={chapter.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-sm font-medium text-gray-500">
                          第 {chapter.chapter_number} 章
                        </span>
                        <h3 className="text-xl font-semibold text-gray-900">
                          {chapter.title || "无标题"}
                        </h3>
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(chapter.status)}`}>
                          {getStatusLabel(chapter.status)}
                        </span>
                      </div>
                      {chapter.outline && (
                        <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                          {chapter.outline}
                        </p>
                      )}
                      <div className="flex items-center gap-4 text-sm text-gray-500">
                        {chapter.updated_at && (
                          <span>
                            更新于 {new Date(chapter.updated_at).toLocaleDateString("zh-CN")}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
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
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
