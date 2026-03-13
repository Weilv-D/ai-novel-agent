"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Modal } from "@/components/ui/Modal";
import { chapterApi, sceneApi } from "@/lib/api-client";
import type { Chapter, Scene } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

export default function ChapterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const chapterId = params.chapterId as string;

  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadChapter = useCallback(async () => {
    try {
      setError(null);
      const data = await chapterApi.get(projectId, chapterId) as Chapter;
      setChapter(data);
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
  }, [projectId, chapterId]);

  const loadScenes = useCallback(async () => {
    try {
      const data = await sceneApi.list(chapterId) as Scene[];
      setScenes(data.sort((a, b) => a.scene_order - b.scene_order));
    } catch (err) {
      // Scenes are optional, don't show error if loading fails
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
      await chapterApi.delete(projectId, chapterId);
      router.push(`/projects/${projectId}/chapters`);
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.detail);
      } else {
        alert("删除章节失败");
      }
      setDeleting(false);
      setDeleteModalOpen(false);
    }
  }

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

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <LoadingSpinner size="lg" text="加载章节中..." />
        </div>
      </main>
    );
  }

  // Error state
  if (error || !chapter) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
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

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/projects/${projectId}/chapters`}
            className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-1 mb-4"
          >
            ← 返回章节列表
          </Link>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-sm font-medium text-gray-500">第 {chapter.chapter_number} 章</span>
                <h1 className="text-3xl font-bold text-gray-900">{chapter.title || "无标题"}</h1>
                <span className={`px-3 py-1 text-sm font-medium rounded-full ${getStatusColor(chapter.status)}`}>
                  {getStatusLabel(chapter.status)}
                </span>
              </div>
              {chapter.outline && (
                <p className="text-gray-600">{chapter.outline}</p>
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

        {/* Chapter Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">统计信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">场景数</span>
                <span className="font-medium">{scenes.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">创建时间</span>
                <span className="font-medium">
                  {new Date(chapter.created_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">更新时间</span>
                <span className="font-medium">
                  {new Date(chapter.updated_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
            </CardContent>
          </Card>

          {chapter.notes && (
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">备注</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{chapter.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Scenes */}
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
              <div className="text-center py-8 text-gray-500">
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
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-md hover:bg-gray-50"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">场景 {scene.scene_order}</span>
                        {scene.location && (
                          <span className="text-sm text-gray-600">📍 {scene.location}</span>
                        )}
                      </div>
                      {scene.content && (
                        <p className="text-sm text-gray-700 mt-1 line-clamp-2">{scene.content}</p>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      href={`/projects/${projectId}/chapters/${chapterId}/scenes/${scene.id}`}
                    >
                      查看
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Delete Confirmation Modal */}
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
