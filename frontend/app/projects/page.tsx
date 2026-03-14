"use client";

import { useEffect } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import { getProjectStatusMeta } from "@/lib/presentation";
import { useProjectStore } from "@/lib/stores/projectStore";

export default function ProjectsPage() {
  const { projects, loading, error, fetchProjects } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="ink-kicker">Project Desk</p>
            <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">
              我的项目
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-[rgb(var(--ink-700))]">
              管理小说创作项目，保持题材、受众、字数目标和当前状态在一个视图内。
            </p>
          </div>
          <Button href="/projects/new">新建项目</Button>
        </div>

        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载项目中..." />
          </div>
        )}

        {error && !loading && (
          <Card padding="lg" className="max-w-2xl">
            <CardContent>
              <div className="text-center">
                <p className="mb-4 text-[rgb(var(--danger))]">{error}</p>
                <Button onClick={() => fetchProjects()}>重试</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && projects.length === 0 && (
          <Card padding="lg" className="max-w-3xl">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">
                  还没有项目
                </h3>
                <p className="mb-6 text-[rgb(var(--ink-700))]">
                  创建您的第一个小说项目，开始 AI 辅助创作之旅
                </p>
                <Button href="/projects/new">创建项目</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && projects.length > 0 && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => {
              const statusMeta = getProjectStatusMeta(project.status);

              return (
                <Link key={project.id} href={`/projects/${project.id}`}>
                  <Card className="ink-grid-card h-full cursor-pointer transition-transform duration-200 hover:-translate-y-1">
                    <CardHeader className="mb-5">
                      <div className="flex items-start justify-between gap-4">
                        <CardTitle className="truncate pr-2 text-2xl">
                          {project.name}
                        </CardTitle>
                        <span className={statusMeta.className}>{statusMeta.label}</span>
                      </div>
                      <CardDescription className="mt-3">
                        {project.genre || "未分类"} · {project.target_audience || "未设定受众"}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3 text-sm text-[rgb(var(--ink-700))]">
                        {project.target_word_count && (
                          <div className="flex justify-between rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                            <span>目标字数</span>
                            <span className="font-medium text-[rgb(var(--ink-950))]">
                              {project.target_word_count.toLocaleString()}
                            </span>
                          </div>
                        )}
                        <div className="pt-2 text-xs text-[rgb(var(--ink-600))]">
                          更新于 {new Date(project.updated_at).toLocaleDateString("zh-CN")}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
