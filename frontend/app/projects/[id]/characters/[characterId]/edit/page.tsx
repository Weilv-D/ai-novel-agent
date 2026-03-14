"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { LoadingSpinner } from "@/components/ui/Loading";
import { characterApi } from "@/lib/api-client";
import type { Character, CharacterUpdate } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

export default function EditCharacterPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const characterId = params.characterId as string;

  const [character, setCharacter] = useState<Character | null>(null);
  const [formData, setFormData] = useState<CharacterUpdate>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCharacter = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await characterApi.get(characterId) as Character;
      setCharacter(data);
      setFormData({
        name: data.name,
        role: data.role,
        profile: data.profile || {},
      });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("加载人物失败");
      }
    } finally {
      setLoading(false);
    }
  }, [characterId]);

  useEffect(() => {
    loadCharacter();
  }, [loadCharacter]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formData.name?.trim()) {
      setError("人物姓名不能为空");
      return;
    }

    try {
      setSaving(true);
      setError(null);
      await characterApi.update(characterId, formData);
      router.push(`/projects/${projectId}/characters/${characterId}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("保存人物失败");
      }
    } finally {
      setSaving(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 py-8">
          <LoadingSpinner size="lg" text="加载人物中..." />
        </div>
      </main>
    );
  }

  // Error state
  if (error && !character) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-2xl mx-auto px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">加载失败</h3>
                <p className="text-gray-600 mb-6">{error}</p>
                <Button href={`/projects/${projectId}/characters/${characterId}`}>返回人物</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/projects/${projectId}/characters/${characterId}`}
            className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-1 mb-4"
          >
            ← 返回人物
          </Link>
          <h1 className="text-3xl font-bold text-gray-900">编辑人物</h1>
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
                value={formData.name || ""}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />

              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="年龄"
                  type="number"
                  min="0"
                  placeholder="例如：25"
                  value={String((formData.profile?.age as number | undefined) ?? "")}
                  onChange={(e) => {
                    const newProfile = { ...(formData.profile || {}) };
                    if (e.target.value) {
                      newProfile.age = parseInt(e.target.value);
                    } else {
                      delete newProfile.age;
                    }
                    setFormData({
                      ...formData,
                      profile: newProfile,
                    });
                  }}
                />

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">性别</label>
                  <select
                    value={String((formData.profile?.gender as string | undefined) ?? "")}
                    onChange={(e) => {
                      const newProfile = { ...(formData.profile || {}) };
                      if (e.target.value) {
                        newProfile.gender = e.target.value;
                      } else {
                        delete newProfile.gender;
                      }
                      setFormData({
                        ...formData,
                        profile: newProfile,
                      });
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
                value={formData.role || ""}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              />

              <Textarea
                label="外貌描写"
                placeholder="描述人物的外貌特征..."
                value={String((formData.profile?.appearance as string | undefined) ?? "")}
                onChange={(e) => {
                  const newProfile = { ...(formData.profile || {}) };
                  if (e.target.value) {
                    newProfile.appearance = e.target.value;
                  } else {
                    delete newProfile.appearance;
                  }
                  setFormData({
                    ...formData,
                    profile: newProfile,
                  });
                }}
                rows={3}
              />

              <Textarea
                label="性格特点"
                placeholder="描述人物的性格特征..."
                value={String((formData.profile?.personality as string | undefined) ?? "")}
                onChange={(e) => {
                  const newProfile = { ...(formData.profile || {}) };
                  if (e.target.value) {
                    newProfile.personality = e.target.value;
                  } else {
                    delete newProfile.personality;
                  }
                  setFormData({
                    ...formData,
                    profile: newProfile,
                  });
                }}
                rows={3}
              />

              <Textarea
                label="背景故事"
                placeholder="描述人物的过往经历..."
                value={String((formData.profile?.background as string | undefined) ?? "")}
                onChange={(e) => {
                  const newProfile = { ...(formData.profile || {}) };
                  if (e.target.value) {
                    newProfile.background = e.target.value;
                  } else {
                    delete newProfile.background;
                  }
                  setFormData({
                    ...formData,
                    profile: newProfile,
                  });
                }}
                rows={4}
              />

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <div className="flex gap-4 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  href={`/projects/${projectId}/characters/${characterId}`}
                  fullWidth
                >
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
