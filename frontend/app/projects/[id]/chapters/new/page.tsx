"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/Loading";
import { ApiError, chapterApi, volumeApi } from "@/lib/api-client";
import type { ChapterCreate, ChapterStatus, Volume } from "@/lib/types";

export default function NewChapterPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = params.id as string;

  const [volumes, setVolumes] = useState<Volume[]>([]);
  const [volumeLoading, setVolumeLoading] = useState(true);
  const [formData, setFormData] = useState<Omit<ChapterCreate, "project_id">>({
    volume_id: searchParams.get("volumeId") || "",
    chapter_number: 1,
    title: "",
    outline: "",
    content: "",
    notes: "",
    status: "draft" as ChapterStatus,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const data = await volumeApi.list(projectId) as Volume[];
        const sorted = data.sort((a, b) => (a.volume_number || 0) - (b.volume_number || 0));
        setVolumes(sorted);
        if (!searchParams.get("volumeId") && sorted[0]?.id) {
          setFormData((prev) => ({ ...prev, volume_id: prev.volume_id || sorted[0].id }));
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "加载卷列表失败");
      } finally {
        setVolumeLoading(false);
      }
    })();
  }, [projectId, searchParams]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.volume_id) {
      setError("请选择所属卷");
      return;
    }
    if (!formData.title?.trim() && !formData.outline?.trim() && !formData.content?.trim()) {
      setError("章节标题、章纲或正文至少填写一项");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const result = await chapterApi.create({
        ...formData,
        project_id: projectId,
      }) as { id: string };
      router.push(`/projects/${projectId}/chapters/${result.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "创建章节失败");
    } finally {
      setLoading(false);
    }
  }

  if (volumeLoading) {
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
          <Link href={`/projects/${projectId}/chapters`} className="ink-backlink mb-4">
            ← 返回章节列表
          </Link>
          <p className="ink-kicker">Create Chapter</p>
          <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">新建章节</h1>
          <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-800))]">
            章节属于卷细纲下的章纲条目，先确定所属卷，再写入本章目标和推进内容。
          </p>
        </div>

        {volumes.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center">
              <h2 className="ink-display text-2xl font-semibold text-[rgb(var(--ink-950))]">当前还没有卷</h2>
              <p className="mt-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                新建章节前，请先创建至少一个卷细纲。
              </p>
              <div className="mt-6 flex justify-center gap-3">
                <Button variant="outline" href={`/projects/${projectId}/chapters`}>返回</Button>
                <Button href={`/projects/${projectId}/volumes/new`}>创建卷细纲</Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>章纲信息</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label className="ink-label">所属卷 *</label>
                  <select
                    value={formData.volume_id || ""}
                    onChange={(e) => setFormData({ ...formData, volume_id: e.target.value })}
                    className="ink-select"
                  >
                    {volumes.map((volume) => (
                      <option key={volume.id} value={volume.id}>
                        第{volume.volume_number || "?"}卷 {volume.title || "未命名卷"}
                      </option>
                    ))}
                  </select>
                </div>

                <Input
                  label="章节号 *"
                  type="number"
                  min="1"
                  value={formData.chapter_number}
                  onChange={(e) => setFormData({ ...formData, chapter_number: parseInt(e.target.value, 10) || 1 })}
                  required
                />

                <Input
                  label="章节标题"
                  placeholder="例如：雨夜追索"
                  value={formData.title || ""}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                />

                <Textarea
                  label="章纲"
                  placeholder="描述本章的目标、冲突、转折与收束压力。"
                  value={formData.outline || ""}
                  onChange={(e) => setFormData({ ...formData, outline: e.target.value })}
                  rows={5}
                />

                <Textarea
                  label="正文草稿"
                  placeholder="如果已经有初稿，可以直接填写。"
                  value={formData.content || ""}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  rows={10}
                />

                <Textarea
                  label="备注"
                  placeholder="记录节奏提醒、伏笔、待补细节等。"
                  value={formData.notes || ""}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={4}
                />

                <div>
                  <label className="ink-label">状态</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as ChapterStatus })}
                    className="ink-select"
                  >
                    <option value="draft">草稿</option>
                    <option value="writing">写作中</option>
                    <option value="completed">已完成</option>
                  </select>
                </div>

                {error && <div className="ink-alert ink-alert-danger">{error}</div>}

                <div className="flex gap-4 pt-4">
                  <Button type="button" variant="outline" href={`/projects/${projectId}/chapters`} fullWidth>
                    取消
                  </Button>
                  <Button type="submit" disabled={loading} fullWidth>
                    {loading ? "创建中..." : "创建章节"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}
      </div>
    </main>
  );
}
