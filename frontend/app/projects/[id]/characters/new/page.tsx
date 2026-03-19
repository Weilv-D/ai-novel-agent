"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { characterApi } from "@/lib/api-client";
import type { CharacterCreate } from "@/lib/types";
import { ApiError } from "@/lib/api-client";
import { useRouteParam } from "@/lib/navigation";

interface CharacterFormData {
  name: string;
  role: string;
  age: string;
  gender: string;
  appearance: string;
  personality: string;
  background: string;
  notes: string;
  profile: Record<string, string | number>;
}

export default function NewCharacterPage() {
  const router = useRouter();
  const projectId = useRouteParam("id");

  const [formData, setFormData] = useState<CharacterFormData>({
    name: "",
    role: "",
    age: "",
    gender: "",
    appearance: "",
    personality: "",
    background: "",
    notes: "",
    profile: {},
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError("人物姓名不能为空");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Convert form data to backend format
      const profile: Record<string, string | number> = {};
      if (formData.age) profile.age = parseInt(formData.age);
      if (formData.gender) profile.gender = formData.gender;
      if (formData.appearance) profile.appearance = formData.appearance;
      if (formData.personality) profile.personality = formData.personality;
      if (formData.background) profile.background = formData.background;

      const createData: CharacterCreate = {
        project_id: projectId,
        name: formData.name,
        role: formData.role || undefined,
        profile: Object.keys(profile).length > 0 ? profile : undefined,
        notes: formData.notes || undefined,
      };

      const result = await characterApi.create(createData) as { id: string };
      router.push(`/projects/${projectId}/characters/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("创建人物失败");
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
            href={`/projects/${projectId}/characters`}
            className="ink-backlink mb-4"
          >
            ← 返回人物列表
          </Link>
          <h1 className="text-3xl font-bold text-[rgb(var(--ink-950))]">新建人物</h1>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <Input
                label="姓名 *"
                placeholder="例如：张三"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />

              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="年龄"
                  type="number"
                  min="0"
                  placeholder="例如：25"
                  value={formData.age}
                  onChange={(e) => {
                    const newProfile = { ...formData.profile };
                    if (e.target.value) {
                      newProfile.age = parseInt(e.target.value);
                    } else {
                      delete newProfile.age;
                    }
                    setFormData({ ...formData, age: e.target.value, profile: newProfile });
                  }}
                />

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">性别</label>
                  <select
                    value={formData.gender}
                    onChange={(e) => {
                      const newProfile = { ...formData.profile };
                      if (e.target.value) {
                        newProfile.gender = e.target.value;
                      } else {
                        delete newProfile.gender;
                      }
                      setFormData({ ...formData, gender: e.target.value, profile: newProfile });
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">未设置</option>
                    <option value="男">男</option>
                    <option value="女">女</option>
                    <option value="其他">其他</option>
                  </select>
                </div>
              </div>

              <Input
                label="角色定位"
                placeholder="例如：主角、配角、反派..."
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              />

              <Textarea
                label="外貌描写"
                placeholder="描述人物的外貌特征..."
                value={formData.appearance}
                onChange={(e) => {
                  const newProfile = { ...formData.profile };
                  if (e.target.value) {
                    newProfile.appearance = e.target.value;
                  } else {
                    delete newProfile.appearance;
                  }
                  setFormData({ ...formData, appearance: e.target.value, profile: newProfile });
                }}
                rows={3}
              />

              <Textarea
                label="性格特点"
                placeholder="描述人物的性格特征..."
                value={formData.personality}
                onChange={(e) => {
                  const newProfile = { ...formData.profile };
                  if (e.target.value) {
                    newProfile.personality = e.target.value;
                  } else {
                    delete newProfile.personality;
                  }
                  setFormData({ ...formData, personality: e.target.value, profile: newProfile });
                }}
                rows={3}
              />

              <Textarea
                label="背景故事"
                placeholder="描述人物的过往经历..."
                value={formData.background}
                onChange={(e) => {
                  const newProfile = { ...formData.profile };
                  if (e.target.value) {
                    newProfile.background = e.target.value;
                  } else {
                    delete newProfile.background;
                  }
                  setFormData({ ...formData, background: e.target.value, profile: newProfile });
                }}
                rows={4}
              />

              <Textarea
                label="备注"
                placeholder="其他备注信息..."
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={3}
              />

              {error && <div className="ink-alert ink-alert-danger">{error}</div>}

              <div className="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  href={`/projects/${projectId}/characters`}
                  fullWidth
                >
                  取消
                </Button>
                <Button type="submit" disabled={loading} fullWidth>
                  {loading ? "创建中..." : "创建人物"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
