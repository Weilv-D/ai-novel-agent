"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import Link from "next/link";
import { useState } from "react";
import { projectApi } from "@/lib/api-client";
import { ApiError } from "@/lib/api-client";
import type { ProjectCreate } from "@/lib/types";

export default function NewProjectPage() {
  const [formData, setFormData] = useState<ProjectCreate>({
    name: "",
    genre: "",
    target_audience: "",
    target_word_count: undefined,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError("项目标题不能为空");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const result = await projectApi.create(formData) as { id: string };
      // Redirect to project detail page
      window.location.href = `/projects/${result.id}`;
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("创建项目失败");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/projects"
            className="text-sm text-blue-600 hover:text-blue-700 mb-4 inline-block"
          >
            ← 返回项目列表
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">新建项目</h1>
          <p className="mt-1 text-sm text-gray-600">
            创建一个新的小说创作项目
          </p>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>项目信息</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Name */}
              <Input
                label="项目名称 *"
                placeholder="输入小说名称"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />

              {/* Genre */}
              <Input
                label="题材"
                placeholder="例如：奇幻、科幻、都市..."
                value={formData.genre}
                onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
              />

              {/* Target Audience */}
              <Input
                label="目标受众"
                placeholder="例如：青少年、成人..."
                value={formData.target_audience}
                onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
              />

              {/* Target Word Count */}
              <Input
                label="目标字数"
                type="number"
                placeholder="例如：100000"
                value={formData.target_word_count || ""}
                onChange={(e) => setFormData({
                  ...formData,
                  target_word_count: e.target.value ? parseInt(e.target.value) : undefined,
                })}
              />

              {/* Error Message */}
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  href="/projects"
                  fullWidth
                >
                  取消
                </Button>
                <Button type="submit" disabled={loading} fullWidth>
                  {loading ? "创建中..." : "创建项目"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
