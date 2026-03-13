"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/Loading";
import { worldSettingApi } from "@/lib/api-client";
import type { WorldSetting } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

export default function WorldSettingsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [settings, setSettings] = useState<WorldSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await worldSettingApi.list(projectId) as WorldSetting[];
      setSettings(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Failed to load world settings");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Group settings by category
  const groupedSettings = settings.reduce((acc, setting) => {
    if (!acc[setting.category]) {
      acc[setting.category] = [];
    }
    acc[setting.category].push(setting);
    return acc;
  }, {} as Record<string, WorldSetting[]>);

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
            <h1 className="text-3xl font-bold text-gray-900">世界观设定</h1>
            <p className="mt-1 text-sm text-gray-600">
              管理小说的世界观、设定和背景信息
            </p>
          </div>
          <Button href={`/projects/${projectId}/worldsettings/new`}>
            新建设定
          </Button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载设定中..." />
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center">
                <p className="text-red-600 mb-4">{error}</p>
                <Button onClick={loadSettings}>重试</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {!loading && !error && settings.length === 0 && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  还没有世界观设定
                </h3>
                <p className="text-gray-600 mb-6">
                  创建第一个设定，开始构建您的世界
                </p>
                <Button href={`/projects/${projectId}/worldsettings/new`}>
                  创建设定
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Settings List by Category */}
        {!loading && !error && settings.length > 0 && (
          <div className="space-y-8">
            {Object.entries(groupedSettings).map(([category, items]) => (
              <div key={category}>
                <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <span className="w-2 h-8 bg-blue-600 rounded"></span>
                  {category}
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map((setting) => (
                    <Card key={setting.id} className="hover:shadow-md transition-shadow">
                      <CardContent className="p-5">
                        <div className="flex items-start justify-between mb-3">
                          <h3 className="text-lg font-semibold text-gray-900">
                            {setting.name}
                          </h3>
                          <div className="flex items-center gap-1">
                            <Button variant="outline" size="sm" href={`/projects/${projectId}/worldsettings/${setting.id}`}>
                              查看
                            </Button>
                            <Button variant="outline" size="sm" href={`/projects/${projectId}/worldsettings/${setting.id}/edit`}>
                              编辑
                            </Button>
                          </div>
                        </div>
                        <p className="text-sm text-gray-700 line-clamp-3">
                          {setting.content}
                        </p>
                        <p className="mt-3 text-xs text-gray-500">
                          更新于 {new Date(setting.updated_at).toLocaleDateString("zh-CN")}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
