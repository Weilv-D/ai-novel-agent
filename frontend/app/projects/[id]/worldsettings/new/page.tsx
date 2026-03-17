"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { worldSettingApi } from "@/lib/api-client";
import type { WorldSettingCreate } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

const COMMON_CATEGORIES = [
  "地理",
  "历史",
  "魔法/科技",
  "种族/势力",
  "文化/习俗",
  "宗教/信仰",
  "经济/货币",
  "语言/文字",
  "其他",
];

export default function NewWorldSettingPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [formData, setFormData] = useState<Omit<WorldSettingCreate, "project_id">>({
    category: "",
    name: "",
    content: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.name.trim() || !formData.category.trim() || !formData.content.trim()) {
      setError("请填写所有必填项");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const result = await worldSettingApi.create({ ...formData, project_id: projectId }) as { id: string };
      router.push(`/projects/${projectId}/worldsettings/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("创建设定失败");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="ink-page">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/projects/${projectId}/worldsettings`}
            className="ink-backlink mb-4"
          >
            ← 返回世界观设定
          </Link>
          <h1 className="text-3xl font-bold text-[rgb(var(--ink-950))]">新建世界观设定</h1>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>设定信息</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  分类 *
                </label>
                <input
                  list="category-suggestions"
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="选择或输入分类"
                  required
                />
                <datalist id="category-suggestions">
                  {COMMON_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat} />
                  ))}
                </datalist>
              </div>

              <Input
                label="名称 *"
                placeholder="例如：中土大陆、霍格沃茨"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />

              <Textarea
                label="详细内容 *"
                placeholder="描述该设定的详细信息..."
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                rows={10}
                required
              />

              {error && <div className="ink-alert ink-alert-danger">{error}</div>}

              <div className="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  href={`/projects/${projectId}/worldsettings`}
                  fullWidth
                >
                  取消
                </Button>
                <Button type="submit" disabled={loading} fullWidth>
                  {loading ? "创建中..." : "创建设定"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
