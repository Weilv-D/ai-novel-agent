"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/Loading";
import { sceneApi } from "@/lib/api-client";
import type { Scene, SceneUpdate } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

export default function EditScenePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const chapterId = params.chapterId as string;
  const sceneId = params.sceneId as string;

  const [scene, setScene] = useState<Scene | null>(null);
  const [formData, setFormData] = useState<SceneUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadScene = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await sceneApi.get(chapterId, sceneId) as Scene;
      setScene(data);
      setFormData({
        scene_order: data.scene_order,
        pov_character_id: data.pov_character_id,
        location: data.location,
        content: data.content,
        meta: data.meta,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    try {
      setSaving(true);
      setError(null);
      await sceneApi.update(chapterId, sceneId, formData);
      router.push(`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("保存场景失败");
      }
    } finally {
      setSaving(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-3xl mx-auto px-4 py-8">
          <LoadingSpinner size="lg" text="加载场景中..." />
        </div>
      </main>
    );
  }

  // Error state
  if (error && !scene) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-3xl mx-auto px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">加载失败</h3>
                <p className="text-gray-600 mb-6">{error}</p>
                <Button href={`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}`}>返回场景</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}`}
            className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-1 mb-4"
          >
            ← 返回场景
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">编辑场景</h1>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>场景信息</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <Input
                label="序号 *"
                type="number"
                min="1"
                value={formData.scene_order ?? 1}
                onChange={(e) => setFormData({ ...formData, scene_order: parseInt(e.target.value) || 1 })}
                required
              />

              <Input
                label="地点"
                placeholder="例如：咖啡厅、城堡大厅..."
                value={formData.location ?? ""}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              />

              <Textarea
                label="场景内容"
                placeholder="描述场景中发生的事件..."
                value={formData.content ?? ""}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                rows={12}
              />

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <div className="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  href={`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}`}
                  fullWidth
                >
                  取消
                </Button>
                <Button type="submit" disabled={saving} fullWidth>
                  {saving ? "保存中..." : "保存更改"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
