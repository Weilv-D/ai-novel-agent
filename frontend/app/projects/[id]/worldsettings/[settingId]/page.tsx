"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { ApiError, worldSettingApi } from "@/lib/api-client";
import type { WorldSetting } from "@/lib/types";

export default function WorldSettingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const settingId = params.settingId as string;

  const [setting, setSetting] = useState<WorldSetting | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadSetting = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await worldSettingApi.get(settingId) as WorldSetting;
      setSetting(data);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setError("设定不存在");
        } else {
          setError(err.detail);
        }
      } else {
        setError("加载设定失败");
      }
    } finally {
      setLoading(false);
    }
  }, [settingId]);

  useEffect(() => {
    loadSetting();
  }, [loadSetting]);

  async function handleDelete() {
    try {
      setDeleting(true);
      await worldSettingApi.delete(settingId);
      router.push(`/projects/${projectId}/worldsettings`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "删除设定失败");
      setDeleting(false);
      setDeleteModalOpen(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <main className="ink-page">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <LoadingSpinner size="lg" text="加载设定中..." />
        </div>
      </main>
    );
  }

  // Error state
  if (error || !setting) {
    return (
      <main className="ink-page">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-[rgb(var(--ink-950))] mb-2">
                  {error || "设定未找到"}
                </h3>
                <Button href={`/projects/${projectId}/worldsettings`}>返回列表</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="ink-page">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/projects/${projectId}/worldsettings`}
            className="ink-backlink mb-4"
          >
            ← 返回世界观设定
          </Link>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <span className="px-3 py-1 text-sm font-medium rounded-full bg-blue-100 text-blue-800">
                  {setting.category}
                </span>
                <h1 className="text-3xl font-bold text-[rgb(var(--ink-950))]">{setting.name}</h1>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" href={`/projects/${projectId}/worldsettings/${settingId}/edit`}>
                编辑
              </Button>
              <Button variant="danger" size="sm" onClick={() => setDeleteModalOpen(true)}>
                删除
              </Button>
            </div>
          </div>
        </div>

        {/* Content */}
        <Card>
          <CardContent className="p-8">
            <div className="prose prose-gray max-w-none">
              <p className="text-gray-700 whitespace-pre-wrap leading-relaxed text-base">
                {setting.content}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Metadata */}
        <div className="mt-6 flex items-center gap-6 text-sm text-gray-500">
          <span>创建于 {new Date(setting.created_at).toLocaleDateString("zh-CN")}</span>
          <span>更新于 {new Date(setting.updated_at).toLocaleDateString("zh-CN")}</span>
        </div>

        {/* Delete Confirmation Modal */}
        <Modal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          onConfirm={handleDelete}
          title="删除世界观设定"
          message={`确定要删除设定"${setting.name}"吗？此操作无法撤销。`}
          confirmText="删除"
          cancelText="取消"
          variant="danger"
          loading={deleting}
        />
      </div>
    </main>
  );
}
