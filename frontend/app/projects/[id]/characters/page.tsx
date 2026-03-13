"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/Loading";
import { characterApi } from "@/lib/api-client";
import type { Character } from "@/lib/types";
import { ApiError } from "@/lib/api-client";

export default function CharactersPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCharacters = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await characterApi.list(projectId) as Character[];
      setCharacters(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Failed to load characters");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadCharacters();
  }, [loadCharacters]);

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Link
              href={`/projects/${projectId}`}
              className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-1 mb-2"
            >
              ← 返回项目
            </Link>
            <h1 className="text-3xl font-bold text-gray-900">人物管理</h1>
            <p className="mt-1 text-sm text-gray-600">
              管理小说中的人物角色
            </p>
          </div>
          <Button href={`/projects/${projectId}/characters/new`}>
            新建人物
          </Button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载人物中..." />
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center">
                <p className="text-red-600 mb-4">{error}</p>
                <Button onClick={loadCharacters}>重试</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {!loading && !error && characters.length === 0 && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  还没有人物
                </h3>
                <p className="text-gray-600 mb-6">
                  创建第一个人物，开始构建您的故事世界
                </p>
                <Button href={`/projects/${projectId}/characters/new`}>
                  创建人物
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Characters List */}
        {!loading && !error && characters.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {characters.map((character) => (
              <Card key={character.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <h3 className="text-xl font-semibold text-gray-900">
                      {character.name}
                    </h3>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" size="sm" href={`/projects/${projectId}/characters/${character.id}`}>
                        查看
                      </Button>
                      <Button variant="outline" size="sm" href={`/projects/${projectId}/characters/${character.id}/edit`}>
                        编辑
                      </Button>
                    </div>
                  </div>

                  {character.role && (
                    <div className="mb-3">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {character.role}
                      </span>
                    </div>
                  )}

                  <div className="space-y-2 text-sm text-gray-600">
                    {character.age !== undefined && (
                      <div className="flex items-center gap-2">
                        <span>年龄:</span>
                        <span className="font-medium text-gray-900">{character.age}</span>
                      </div>
                    )}
                    {character.gender && (
                      <div className="flex items-center gap-2">
                        <span>性别:</span>
                        <span className="font-medium text-gray-900">{character.gender}</span>
                      </div>
                    )}
                  </div>

                  {character.appearance && (
                    <p className="mt-4 text-sm text-gray-700 line-clamp-2">
                      {character.appearance}
                    </p>
                  )}

                  {character.updated_at && (
                    <p className="mt-4 text-xs text-gray-500">
                      更新于 {new Date(character.updated_at).toLocaleDateString("zh-CN")}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
