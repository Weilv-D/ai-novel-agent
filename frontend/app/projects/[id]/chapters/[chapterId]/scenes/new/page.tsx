"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { sceneApi } from "@/lib/api-client";
import type { SceneCreate } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

export default function NewScenePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const chapterId = params.chapterId as string;

  const [formData, setFormData] = useState<Omit<SceneCreate, "chapter_id">>({
    scene_order: 1,
    pov_character_id: undefined,
    location: "",
    content: "",
    meta: undefined,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    try {
      setLoading(true);
      setError(null);
      const result = await sceneApi.create({ ...formData, chapter_id: chapterId }) as { id: string };
      router.push(`/projects/${projectId}/chapters/${chapterId}/scenes/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("创建场景失败");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="ink-page">
      <div className="max-w-3xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/projects/${projectId}/chapters/${chapterId}`}
            className="ink-backlink mb-4"
          >
            ← 返回章节
          </Link>
          <h1 className="text-3xl font-bold text-[rgb(var(--ink-950))]">新建场景</h1>
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
                value={formData.scene_order}
                onChange={(e) => setFormData({ ...formData, scene_order: parseInt(e.target.value) || 1 })}
                required
              />

              <Input
                label="地点"
                placeholder="例如：咖啡厅、城堡大厅..."
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              />

              <Textarea
                label="场景内容"
                placeholder="描述场景中发生的事件..."
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                rows={10}
              />

              {error && <div className="ink-alert ink-alert-danger">{error}</div>}

              <div className="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  href={`/projects/${projectId}/chapters/${chapterId}`}
                  fullWidth
                >
                  取消
                </Button>
                <Button type="submit" disabled={loading} fullWidth>
                  {loading ? "创建中..." : "创建场景"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
