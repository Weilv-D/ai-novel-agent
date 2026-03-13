"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/Loading";
import { useProjectStore } from "@/lib/stores/projectStore";
import { ApiError } from "@/lib/api-client";
import type { ProjectUpdate, ProjectStatus } from "@/lib/types";

export default function EditProjectPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const {
    currentProject: project,
    currentProjectLoading: loading,
    currentProjectError: error,
    fetchProject,
    clearCurrentProject,
    updateProject,
  } = useProjectStore();

  const [formData, setFormData] = useState<ProjectUpdate>({
    name: "",
    summary: "",
    notes: "",
    genre: "",
    target_audience: "",
    target_word_count: undefined,
    status: undefined as ProjectStatus | undefined,
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Load project data on mount
  useEffect(() => {
    if (id) {
      fetchProject(id).catch(() => {
        // Error is handled by the store
      });
    }

    return () => {
      clearCurrentProject();
    };
  }, [id, fetchProject, clearCurrentProject]);

  // Update form data when project is loaded
  useEffect(() => {
    if (project) {
      setFormData({
        name: project.name,
        summary: project.summary || "",
        notes: project.notes || "",
        genre: project.genre || "",
        target_audience: project.target_audience || "",
        target_word_count: project.target_word_count,
        status: project.status,
      });
    }
  }, [project]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.name?.trim()) {
      setSubmitError("项目名称不能为空");
      return;
    }

    try {
      setSubmitting(true);
      setSubmitError(null);
      await updateProject(id, formData);
      // Redirect to project detail page
      router.push(`/projects/${id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setSubmitError(err.detail);
      } else {
        setSubmitError("更新项目失败");
      }
    } finally {
      setSubmitting(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 py-8">
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载项目中..." />
          </div>
        </div>
      </main>
    );
  }

  // Error state
  if (error || !project) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  项目未找到
                </h3>
                <p className="text-gray-600 mb-6">
                  {error || "无法加载项目信息"}
                </p>
                <div className="flex justify-center gap-4">
                  <Button variant="outline" href="/projects">返回项目列表</Button>
                  <Button onClick={() => fetchProject(id)}>重试</Button>
                </div>
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
            href={`/projects/${id}`}
            className="text-sm text-blue-600 hover:text-blue-700 mb-4 inline-block"
          >
            ← 返回项目详情
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">编辑项目</h1>
          <p className="mt-1 text-sm text-gray-600">
            修改项目信息和设置
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

              {/* Summary */}
              <Textarea
                label="项目简介"
                placeholder="简要描述这个项目的主题和内容..."
                value={formData.summary}
                onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
                rows={3}
              />

              {/* Notes */}
              <Textarea
                label="备注"
                placeholder="添加任何额外的备注或想法..."
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={4}
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

              {/* Status */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  项目状态
                </label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as ProjectStatus })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="drafting">草稿中</option>
                  <option value="writing">写作中</option>
                  <option value="revising">修订中</option>
                  <option value="completed">已完成</option>
                </select>
              </div>

              {/* Error Message */}
              {submitError && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {submitError}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  href={`/projects/${id}`}
                  fullWidth
                >
                  取消
                </Button>
                <Button type="submit" disabled={submitting} fullWidth>
                  {submitting ? "保存中..." : "保存更改"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
