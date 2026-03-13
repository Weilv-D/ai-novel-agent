"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/Loading";
import { useProjectStore } from "@/lib/stores/projectStore";

export default function ProjectsPage() {
  const { projects, loading, error, fetchProjects } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  function getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      conception: "构思中",
      building: "搭建中",
      publishing: "连载中",
      refining: "精修中",
      completed: "已完成",
    };
    return labels[status] || status;
  }

  function getStatusColor(status: string): string {
    const colors: Record<string, string> = {
      conception: "bg-gray-100 text-gray-800",
      building: "bg-blue-100 text-blue-800",
      publishing: "bg-green-100 text-green-800",
      refining: "bg-yellow-100 text-yellow-800",
      completed: "bg-purple-100 text-purple-800",
    };
    return colors[status] || "bg-gray-100 text-gray-800";
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">我的项目</h1>
            <p className="mt-1 text-sm text-gray-600">
              管理您的小说创作项目
            </p>
          </div>
          <Button href="/projects/new">新建项目</Button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载项目中..." />
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center">
                <p className="text-red-600 mb-4">{error}</p>
                <Button onClick={() => fetchProjects()}>重试</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {!loading && !error && projects.length === 0 && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  还没有项目
                </h3>
                <p className="text-gray-600 mb-6">
                  创建您的第一个小说项目，开始 AI 辅助创作之旅
                </p>
                <Button href="/projects/new">创建项目</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Projects Grid */}
        {!loading && !error && projects.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <Link key={project.id} href={`/projects/${project.id}`}>
                <Card className="h-full transition-shadow hover:shadow-md cursor-pointer">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-xl truncate">
                        {project.title}
                      </CardTitle>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(project.status)}`}>
                        {getStatusLabel(project.status)}
                      </span>
                    </div>
                    <CardDescription>
                      {project.genre || "未分类"} · {project.target_audience || "未设定受众"}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm text-gray-600">
                      <div className="flex justify-between">
                        <span>当前字数</span>
                        <span className="font-medium">{project.current_word_count.toLocaleString()}</span>
                      </div>
                      {project.target_word_count && (
                        <div className="flex justify-between">
                          <span>目标字数</span>
                          <span className="font-medium">{project.target_word_count.toLocaleString()}</span>
                        </div>
                      )}
                      <div className="pt-2 text-xs text-gray-500">
                        更新于 {new Date(project.updated_at).toLocaleDateString("zh-CN")}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
