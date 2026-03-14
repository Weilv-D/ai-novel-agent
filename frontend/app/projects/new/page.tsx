"use client";

import { useState } from "react";
import Link from "next/link";

import { ApiError, projectApi } from "@/lib/api-client";
import type { ProjectCreate } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

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
    <main className="ink-page">
      <div className="mx-auto max-w-2xl px-4 py-10">
        <div className="mb-8">
          <Link href="/projects" className="ink-backlink mb-4">
            ← 返回项目列表
          </Link>
          <p className="ink-kicker">New Project</p>
          <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">新建项目</h1>
          <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-700))]">
            先定义作品的基本边界，再逐步扩展章节、角色和世界观。
          </p>
        </div>

        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>项目信息</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <Input
                label="项目名称 *"
                placeholder="输入小说名称"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />

              <Input
                label="题材"
                placeholder="例如：奇幻、科幻、都市..."
                value={formData.genre}
                onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
              />

              <Input
                label="目标受众"
                placeholder="例如：青少年、成人..."
                value={formData.target_audience}
                onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
              />

              <Input
                label="目标字数"
                type="number"
                placeholder="例如：100000"
                value={formData.target_word_count || ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    target_word_count: e.target.value ? parseInt(e.target.value, 10) : undefined,
                  })
                }
              />

              {error && <div className="ink-alert ink-alert-danger">{error}</div>}

              <div className="flex gap-4 pt-4">
                <Button type="button" variant="outline" href="/projects" fullWidth>
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
