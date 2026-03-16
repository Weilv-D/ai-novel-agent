"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/Loading";
import { ApiError, volumeApi } from "@/lib/api-client";
import type { Volume, VolumeUpdate } from "@/lib/types";

export default function EditVolumePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const volumeId = params.volumeId as string;

  const [formData, setFormData] = useState<VolumeUpdate>({
    volume_number: 1,
    title: "",
    outline: "",
    notes: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadVolume = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const volume = await volumeApi.get(volumeId) as Volume;
      setFormData({
        volume_number: volume.volume_number || 1,
        title: volume.title || "",
        outline: volume.outline || "",
        notes: volume.notes || "",
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "加载卷失败");
    } finally {
      setLoading(false);
    }
  }, [volumeId]);

  useEffect(() => {
    loadVolume();
  }, [loadVolume]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!formData.title?.trim() && !formData.outline?.trim()) {
      setError("卷名或卷细纲至少填写一项");
      return;
    }
    try {
      setSaving(true);
      setError(null);
      await volumeApi.update(volumeId, formData);
      router.push(`/projects/${projectId}/volumes/${volumeId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "更新卷失败");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-3xl px-4 py-10">
          <LoadingSpinner size="lg" text="加载卷细纲中..." />
        </div>
      </main>
    );
  }

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-3xl px-4 py-10">
        <div className="mb-8">
          <Link href={`/projects/${projectId}/volumes/${volumeId}`} className="ink-backlink mb-4">
            ← 返回卷详情
          </Link>
          <p className="ink-kicker">Edit Volume</p>
          <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">编辑卷细纲</h1>
          <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-800))]">
            调整卷目标、推进链路和章纲编排范围，让项目大纲与卷细纲保持一致。
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
                onChange={(event) =>
                  setFormData({
                    ...formData,
                    volume_number: parseInt(event.target.value, 10) || 1,
                  })}
              />

              <Input
                label="卷名"
                placeholder="例如：北地试锋"
                value={formData.title || ""}
                onChange={(event) => setFormData({ ...formData, title: event.target.value })}
              />

              <Textarea
                label="卷细纲总述"
                placeholder="描述这一卷的目标、主冲突、关键节点、支线牵引和卷末收束。"
                value={formData.outline || ""}
                onChange={(event) => setFormData({ ...formData, outline: event.target.value })}
                rows={8}
              />

              <Textarea
                label="备注"
                placeholder="记录本卷的节奏策略、伏笔回收、人物推进等。"
                value={formData.notes || ""}
                onChange={(event) => setFormData({ ...formData, notes: event.target.value })}
                rows={4}
              />

              {error && <div className="ink-alert ink-alert-danger">{error}</div>}

              <div className="flex gap-4 pt-4">
                <Button type="button" variant="outline" href={`/projects/${projectId}/volumes/${volumeId}`} fullWidth>
                  取消
                </Button>
                <Button type="submit" disabled={saving} fullWidth>
                  {saving ? "保存中..." : "保存卷细纲"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
