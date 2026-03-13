"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Modal } from "@/components/ui/Modal";
import { sceneApi } from "@/lib/api-client";
import type { Scene } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

export default function SceneDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const chapterId = params.chapterId as string;
  const sceneId = params.sceneId as string;

  const [scene, setScene] = useState<Scene | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadScene = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await sceneApi.get(chapterId, sceneId) as Scene;
      setScene(data);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setError("场景不存在");
        } else {
          setError(err.detail);
        }
      } else {
        setError("加载场景失败");
      }
    } finally {
      setLoading(false);
    }
  }, [chapterId, sceneId]);

  useEffect(() => {
    loadScene();
  }, [loadScene]);

  async function handleDelete() {
    try {
      setDeleting(true);
      await sceneApi.delete(chapterId, sceneId);
      router.push(`/projects/${projectId}/chapters/${chapterId}`);
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.detail);
      } else {
        alert("删除场景失败");
      }
      setDeleting(false);
      setDeleteModalOpen(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <LoadingSpinner size="lg" text="加载场景中..." />
        </div>
      </main>
    );
  }

  // Error state
  if (error || !scene) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {error || "场景未找到"}
                </h3>
                <Button href={`/projects/${projectId}/chapters/${chapterId}`}>返回章节</Button>
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
            href={`/projects/${projectId}/chapters/${chapterId}`}
            className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-1 mb-4"
          >
            ← 返回章节
          </Link>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-sm font-medium text-gray-500">场景 {scene.scene_order}</span>
                <h1 className="text-3xl font-bold text-gray-900">场景详情</h1>
              </div>
              {scene.location && (
                <p className="text-gray-600">📍 {scene.location}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" href={`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}/edit`}>
                编辑
              </Button>
              <Button variant="danger" size="sm" onClick={() => setDeleteModalOpen(true)}>
                删除
              </Button>
            </div>
          </div>
        </div>

        {/* Scene Content */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">序号</span>
                <span className="font-medium">{scene.scene_order}</span>
              </div>
              {scene.pov_character_id && (
                <div className="flex justify-between">
                  <span className="text-gray-600">POV 角色 ID</span>
                  <span className="font-medium">{scene.pov_character_id}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-600">创建时间</span>
                <span className="font-medium">
                  {new Date(scene.created_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">更新时间</span>
                <span className="font-medium">
                  {new Date(scene.updated_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
            </CardContent>
          </Card>

          {scene.location && (
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">地点</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700">{scene.location}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Content */}
        {scene.content && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">场景内容</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                {scene.content}
              </p>
            </CardContent>
          </Card>
        )}

        {/* Delete Confirmation Modal */}
        <Modal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          onConfirm={handleDelete}
          title="删除场景"
          message={`确定要删除场景 ${scene.scene_order} 吗？此操作无法撤销。`}
          confirmText="删除"
          cancelText="取消"
          variant="danger"
          loading={deleting}
        />
      </div>
    </main>
  );
}
