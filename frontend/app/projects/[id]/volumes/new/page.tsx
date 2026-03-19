"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { ApiError, volumeApi } from "@/lib/api-client";
import { useRouteParam } from "@/lib/navigation";
import type { VolumeCreate } from "@/lib/types";

export default function NewVolumePage() {
  const router = useRouter();
  const projectId = useRouteParam("id");

  const [formData, setFormData] = useState<Omit<VolumeCreate, "project_id">>({
    volume_number: 1,
    title: "",
    outline: "",
    notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.title?.trim() && !formData.outline?.trim()) {
      setError("卷名或卷细纲至少填写一项");
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const result = await volumeApi.create({ ...formData, project_id: projectId }) as { id: string };
      router.push(`/projects/${projectId}/volumes/${result.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "创建卷失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-3xl px-4 py-10">
        <div className="mb-8">
          <Link href={`/projects/${projectId}/volumes`} className="ink-backlink mb-4">
            ← 返回卷列表
          </Link>
          <p className="ink-kicker">Create Volume</p>
          <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">新建卷</h1>
          <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-800))]">
            为这一卷定义中程目标、冲突推进和章节布局范围。
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>卷细纲</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <Input
                label="卷序号"
                type="number"
                min="1"
                value={formData.volume_number || 1}
                onChange={(e) => setFormData({ ...formData, volume_number: parseInt(e.target.value, 10) || 1 })}
              />

              <Input
                label="卷名"
                placeholder="例如：北地试锋"
                value={formData.title || ""}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              />

              <Textarea
                label="卷细纲总述"
                placeholder="描述这一卷的目标、主冲突、关键节点、支线牵引和卷末收束。"
                value={formData.outline || ""}
                onChange={(e) => setFormData({ ...formData, outline: e.target.value })}
                rows={8}
              />

              <Textarea
                label="备注"
                placeholder="记录本卷的节奏策略、伏笔回收、人物推进等。"
                value={formData.notes || ""}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={4}
              />

              {error && <div className="ink-alert ink-alert-danger">{error}</div>}

              <div className="flex gap-4 pt-4">
                <Button type="button" variant="outline" href={`/projects/${projectId}/volumes`} fullWidth>
                  取消
                </Button>
                <Button type="submit" disabled={loading} fullWidth>
                  {loading ? "创建中..." : "创建卷"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
