"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ApiError, worldSettingApi } from "@/lib/api-client";
import type { WorldSetting } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";

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

  const groupedSettings = settings.reduce<Record<string, WorldSetting[]>>((acc, setting) => {
    if (!acc[setting.category]) {
      acc[setting.category] = [];
    }
    acc[setting.category].push(setting);
    return acc;
  }, {});

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link href={`/projects/${projectId}`} className="ink-backlink mb-2">
              ← 返回项目
            </Link>
            <p className="ink-kicker">World Ledger</p>
            <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">世界观设定</h1>
            <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-700))]">
              管理世界观、背景信息和设定条目，让不同章节引用同一套基础规则。
            </p>
          </div>
          <Button href={`/projects/${projectId}/worldsettings/new`}>新建设定</Button>
        </div>

        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载设定中..." />
          </div>
        )}

        {error && !loading && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center">
                <p className="mb-4 text-[rgb(var(--danger))]">{error}</p>
                <Button onClick={loadSettings}>重试</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && settings.length === 0 && (
          <Card padding="lg">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">
                  还没有世界观设定
                </h3>
                <p className="mb-6 text-[rgb(var(--ink-700))]">
                  创建第一个设定，开始构建您的世界
                </p>
                <Button href={`/projects/${projectId}/worldsettings/new`}>创建设定</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && settings.length > 0 && (
          <div className="space-y-8">
            {Object.entries(groupedSettings).map(([category, items]) => (
              <div key={category}>
                <h2 className="ink-display mb-4 flex items-center gap-3 text-2xl font-semibold text-[rgb(var(--ink-950))]">
                  <span className="h-8 w-[3px] rounded-full bg-[rgb(var(--accent))]" />
                  {category}
                </h2>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {items.map((setting) => (
                    <Card key={setting.id} className="transition-transform duration-200 hover:-translate-y-1">
                      <CardContent className="p-5">
                        <div className="mb-3 flex items-start justify-between gap-3">
                          <h3 className="ink-display text-xl font-semibold text-[rgb(var(--ink-950))]">
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
                        <p className="line-clamp-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                          {setting.content}
                        </p>
                        <p className="mt-3 text-xs text-[rgb(var(--ink-700))]">
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
