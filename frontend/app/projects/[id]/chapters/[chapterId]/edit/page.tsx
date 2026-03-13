"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/Loading";
import { chapterApi } from "@/lib/api-client";
import type { Chapter, ChapterUpdate, ChapterStatus } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

export default function EditChapterPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const chapterId = params.chapterId as string;

  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [formData, setFormData] = useState<ChapterUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadChapter = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await chapterApi.get(projectId, chapterId) as Chapter;
      setChapter(data);
      setFormData({
        chapter_number: data.chapter_number,
        title: data.title,
        outline: data.outline,
        content: data.content,
        notes: data.notes,
        status: data.status,
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("加载章节失败");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId, chapterId]);

  useEffect(() => {
    loadChapter();
  }, [loadChapter]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.title?.trim() && !formData.content?.trim()) {
      setError("章节标题或内容不能为空");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      await chapterApi.update(projectId, chapterId, formData);
      router.push(`/projects/${projectId}/chapters/${chapterId}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("保存章节失败");
      }
    } finally {
      setSaving(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 py-8">
          <LoadingSpinner size="lg" text="加载章节中..." />
        </div>
      </main>
    );
  }

  // Error state
  if (error && !chapter) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">加载失败</h3>
                <p className="text-gray-600 mb-6">{error}</p>
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
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/projects/${projectId}/chapters/${chapterId}`}
            className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-1 mb-4"
          >
            ← 返回章节
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">编辑章节</h1>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>章节信息</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <Input
                label="章节号 *"
                type="number"
                min="1"
                value={formData.chapter_number ?? 1}
                onChange={(e) => setFormData({ ...formData, chapter_number: parseInt(e.target.value) || 1 })}
                required
              />

              <Input
                label="章节标题"
                placeholder="例如：第一章 开始"
                value={formData.title || ""}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              />

              <Textarea
                label="大纲"
                placeholder="简要描述本章节的主要内容..."
                value={formData.outline || ""}
                onChange={(e) => setFormData({ ...formData, outline: e.target.value })}
                rows={3}
              />

              <Textarea
                label="内容"
                placeholder="章节正文..."
                value={formData.content || ""}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                rows={8}
              />

              <Textarea
                label="备注"
                placeholder="写作笔记、待办事项等..."
                value={formData.notes || ""}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={3}
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">状态</label>
                <select
                  value={formData.status || "draft"}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as ChapterStatus })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="draft">草稿</option>
                  <option value="writing">写作中</option>
                  <option value="completed">已完成</option>
                </select>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <div className="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  href={`/projects/${projectId}/chapters/${chapterId}`}
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
