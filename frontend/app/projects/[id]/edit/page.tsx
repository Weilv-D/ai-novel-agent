"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { agentWorkflowApi, ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/Loading";
import { useProjectStore } from "@/lib/stores/projectStore";
import type { AgentProfile, ProjectStatus, ProjectUpdate } from "@/lib/types";

const FALLBACK_PROFILES: AgentProfile[] = [
  {
    id: "default",
    name: "Default",
    description: "通用长篇写作 profile。",
    builtin: true,
    root: "builtin",
  },
  {
    id: "xianxia_intrigue",
    name: "仙侠权谋",
    description: "严格遵照 others/ 下的大纲、章纲与写作规范。",
    builtin: true,
    root: "builtin",
  },
];

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
    story_outline: "",
    notes: "",
    genre: "",
    target_audience: "",
    target_word_count: undefined,
    agent_profile_id: "default",
    status: undefined as ProjectStatus | undefined,
  });
  const [profiles, setProfiles] = useState<AgentProfile[]>(FALLBACK_PROFILES);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const nextProfiles = await agentWorkflowApi.listProfiles();
        if (nextProfiles.length > 0) {
          setProfiles(nextProfiles);
        }
      } catch {
        setProfiles(FALLBACK_PROFILES);
      }
    })();
  }, []);

  useEffect(() => {
    if (id) {
      fetchProject(id).catch(() => {
        // store handles errors
      });
    }

    return () => {
      clearCurrentProject();
    };
  }, [id, fetchProject, clearCurrentProject]);

  useEffect(() => {
    if (project) {
      setFormData({
        name: project.name,
        summary: project.summary || "",
        story_outline: project.story_outline || "",
        notes: project.notes || "",
        genre: project.genre || "",
        target_audience: project.target_audience || "",
        target_word_count: project.target_word_count,
        agent_profile_id: project.agent_profile_id || "default",
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

  if (loading) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-2xl px-4 py-8">
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载项目中..." />
          </div>
        </div>
      </main>
    );
  }

  if (error || !project) {
    return (
      <main className="ink-page">
        <div className="mx-auto max-w-2xl px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">
                  项目未找到
                </h3>
                <p className="mb-6 text-[rgb(var(--ink-800))]">
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
    <main className="ink-page">
      <div className="mx-auto max-w-2xl px-4 py-10">
        <div className="mb-8">
          <Link href={`/projects/${id}`} className="ink-backlink mb-4">
            ← 返回项目详情
          </Link>
          <p className="ink-kicker">Refine Project</p>
          <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">编辑项目</h1>
          <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-800))]">
            修改项目信息和创作设置，让后续章节、角色与世界观保持同一方向。
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

              <Textarea
                label="项目简介"
                placeholder="简要描述这个项目的主题和内容..."
                value={formData.summary}
                onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
                rows={3}
              />

              <Textarea
                label="项目大纲"
                placeholder="维护作品总纲、主线因果与长期推进方向..."
                value={formData.story_outline}
                onChange={(e) => setFormData({ ...formData, story_outline: e.target.value })}
                rows={8}
              />

              <Textarea
                label="备注"
                placeholder="添加任何额外的备注或想法..."
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={4}
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

              <div>
                <label className="ink-label">项目状态</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as ProjectStatus })}
                  className="ink-select"
                >
                  <option value="drafting">草稿中</option>
                  <option value="writing">写作中</option>
                  <option value="revising">修订中</option>
                  <option value="completed">已完成</option>
                </select>
              </div>

              <div>
                <label className="ink-label">Agent Profile</label>
                <select
                  value={formData.agent_profile_id || "default"}
                  onChange={(e) => setFormData({ ...formData, agent_profile_id: e.target.value })}
                  className="ink-select"
                >
                  {profiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.name}
                    </option>
                  ))}
                </select>
                <p className="mt-2 text-sm leading-6 text-[rgb(var(--ink-800))]">
                  {(profiles.find((profile) => profile.id === (formData.agent_profile_id || "default")) || profiles[0])?.description}
                </p>
              </div>

              {submitError && <div className="ink-alert ink-alert-danger">{submitError}</div>}

              <div className="flex gap-4 pt-4">
                <Button type="button" variant="outline" href={`/projects/${id}`} fullWidth>
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
