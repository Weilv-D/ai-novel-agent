import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      <div className="max-w-4xl mx-auto px-4 py-16 sm:px-6 sm:py-24">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-900 mb-4">
            AI Novel Agent
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            AI 驱动的超长篇小说创作系统
          </p>
          <p className="mt-4 text-sm text-gray-500">
            对象级 AI 协作 · 修改传播 · 一致性维护
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
          <Button size="lg">
            <Link href="/projects">查看项目</Link>
          </Button>
          <Button size="lg" variant="outline">
            <Link href="/projects/new">新建项目</Link>
          </Button>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">项目管理</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                创建和管理您的小说项目，设定题材、受众和目标字数
              </CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">人物与设定</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                构建丰富的人物档案和世界观，AI 帮助维护一致性
              </CardDescription>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">智能创作</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                基于大纲和设定生成场景，支持局部改写和风格调整
              </CardDescription>
            </CardContent>
          </Card>
        </div>

        {/* API Docs Link */}
        <div className="mt-12 text-center text-sm text-gray-500">
          <span>后端 API 文档: </span>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            /docs
          </a>
          <span> (开发环境)</span>
        </div>
      </div>
    </main>
  );
}
