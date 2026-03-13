"use client";

import { useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/Loading";
import { useProjectStore } from "@/lib/stores/projectStore";

export default function ProjectDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const {
    currentProject: project,
    currentProjectLoading: loading,
    currentProjectError: error,
    fetchProject,
    clearCurrentProject,
  } = useProjectStore();

  useEffect(() => {
    if (id) {
      fetchProject(id);
    }

    return () => {
      clearCurrentProject();
    };
  }, [id, fetchProject, clearCurrentProject]);

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

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 py-8">
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载项目中..." />
          </div>
        </div>
      </main>
    );
  }

  // Error state (including 404)
  if (error || !project) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  项目未找到
                </h3>
                <p className="text-gray-600 mb-6">
                  {error || "无法加载项目信息"}
                </p>
                <Button>
                  <Link href="/projects">返回项目列表</Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/projects"
            className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-1 mb-4"
          >
            ← 返回项目列表
          </Link>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{project.title}</h1>
              <p className="mt-1 text-sm text-gray-600">{project.summary || "暂无描述"}</p>
            </div>
            <span className={`px-3 py-1 text-sm font-medium rounded-full ${getStatusColor(project.status)}`}>
              {getStatusLabel(project.status)}
            </span>
          </div>
        </div>

        {/* Project Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">基本信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">题材</span>
                <span className="font-medium">{project.genre || "未分类"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">目标受众</span>
                <span className="font-medium">{project.target_audience || "未设定"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">当前字数</span>
                <span className="font-medium">{project.current_word_count.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">目标字数</span>
                <span className="font-medium">
                  {project.target_word_count ? project.target_word_count.toLocaleString() : "-"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">创建时间</span>
                <span className="font-medium">
                  {new Date(project.created_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
            </CardContent>
          </Card>

          {project.notes && (
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">备注</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{project.notes}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Actions */}
        <Card className="mb-8">
          <CardContent className="pt-6">
            <div className="flex flex-wrap gap-4">
              <Button>
                <Link href={`/projects/${project.id}/chapters`}>章节管理</Link>
              </Button>
              <Button variant="outline">
                <Link href={`/projects/${project.id}/characters`}>人物管理</Link>
              </Button>
              <Button variant="outline">
                <Link href={`/projects/${project.id}/worldview`}>世界观</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
