"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { TipTapEditor } from "@/components/editor";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/Loading";
import { ApiError, agentApi, chapterApi, volumeApi } from "@/lib/api-client";
import { useRouteParam } from "@/lib/navigation";
import { hasRichTextContent, normalizeRichTextContent, richTextToPlainText } from "@/lib/rich-text";
import type { Chapter, ChapterStatus, ChapterUpdate, Volume } from "@/lib/types";

export default function EditChapterPage() {
  const router = useRouter();
  const projectId = useRouteParam("id");
  const chapterId = useRouteParam("chapterId");

  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [volumes, setVolumes] = useState<Volume[]>([]);
  const [formData, setFormData] = useState<ChapterUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPage = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [chapterData, volumeData] = await Promise.all([
        chapterApi.get(chapterId) as Promise<Chapter>,
        volumeApi.list(projectId) as Promise<Volume[]>,
      ]);
      setChapter(chapterData);
      setVolumes(volumeData.sort((a, b) => (a.volume_number || 0) - (b.volume_number || 0)));
      setFormData({
        volume_id: chapterData.volume_id,
        chapter_number: chapterData.chapter_number,
        title: chapterData.title,
        outline: chapterData.outline,
        content: chapterData.content,
        notes: chapterData.notes,
        status: chapterData.status,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "加载章节失败");
    } finally {
      setLoading(false);
    }
  }, [chapterId, projectId]);

  useEffect(() => {
    loadPage();
  }, [loadPage]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const plainContent = richTextToPlainText(formData.content);

    if (!formData.volume_id) {
      setError("请选择所属卷");
      return;
    }
    if (!formData.title?.trim() && !formData.outline?.trim() && !plainContent) {
      setError("章节标题、章纲或正文至少填写一项");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      const payload: ChapterUpdate = {
        ...formData,
        content: hasRichTextContent(formData.content) ? normalizeRichTextContent(formData.content) : "",
      };

      await chapterApi.update(chapterId, payload);
      if (plainContent.length > 100) {
        agentApi.autoSummarize({
          project_id: projectId,
          chapter_id: chapterId,
          content: plainContent,
        }).catch(() => {});
      }
      router.push(`/projects/${projectId}/chapters/${chapterId}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "保存章节失败");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-3xl px-4 py-10">
          <LoadingSpinner size="lg" text="加载章节中..." />
        </div>
      </main>
    );
  }

  if (error && !chapter) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-3xl px-4 py-10">
          <Card padding="lg">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">加载失败</h3>
                <p className="mb-6 text-[rgb(var(--ink-800))]">{error}</p>
                <Button href={`/projects/${projectId}/chapters/${chapterId}`}>返回章节</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-3xl px-4 py-10">
        <div className="mb-8">
          <Link href={`/projects/${projectId}/chapters/${chapterId}`} className="ink-backlink mb-4">
            ← 返回章节
          </Link>
          <p className="ink-kicker">Edit Chapter</p>
          <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">编辑章节</h1>
          <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-800))]">
            调整所属卷、章纲与正文，使章节继续保持在卷细纲的推进路径上。
          </p>
        </div>

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
                value={formData.chapter_number ?? 1}
                onChange={(e) => setFormData({ ...formData, chapter_number: parseInt(e.target.value, 10) || 1 })}
                required
              />

              <Input
                label="章节标题"
                placeholder="例如：山门夜审"
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

              <TipTapEditor
                label="正文草稿"
                placeholder="维护章节正文。"
                value={formData.content || ""}
                onChange={(content) => setFormData({ ...formData, content })}
                projectId={projectId}
                aiContext={{
                  chapter_id: chapterId,
                  chapter_number: formData.chapter_number,
                  chapter_title: formData.title,
                  chapter_outline: formData.outline,
                  volume_id: formData.volume_id,
                }}
                onAiError={(message) => setError(message)}
              />

              <Textarea
                label="备注"
                placeholder="记录伏笔、修订点或写作提醒。"
                value={formData.notes || ""}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={4}
              />

              <div>
                <label className="ink-label">状态</label>
                <select
                  value={formData.status || "draft"}
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
                <Button type="button" variant="outline" href={`/projects/${projectId}/chapters/${chapterId}`} fullWidth>
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
