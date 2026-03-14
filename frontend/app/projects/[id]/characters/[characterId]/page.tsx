"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Modal } from "@/components/ui/Modal";
import { characterApi } from "@/lib/api-client";
import type { Character } from "@/lib/types";
import { ApiError } from "@/lib/api-client";
import { AgentChatPanel } from "@/components/AgentChatPanel";

export default function CharacterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const characterId = params.characterId as string;

  const [character, setCharacter] = useState<Character | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadCharacter = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await characterApi.get(characterId) as Character;
      setCharacter(data);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 404) {
          setError("人物不存在");
        } else {
          setError(err.detail);
        }
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

  async function handleDelete() {
    try {
      setDeleting(true);
      await characterApi.delete(characterId);
      router.push(`/projects/${projectId}/characters`);
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.detail);
      } else {
        alert("删除人物失败");
      }
      setDeleting(false);
      setDeleteModalOpen(false);
    }
  }

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <LoadingSpinner size="lg" text="加载人物中..." />
        </div>
      </main>
    );
  }

  // Error state
  if (error || !character) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-8">
          <Card padding="lg">
            <CardContent>
              <div className="text-center py-8">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {error || "人物未找到"}
                </h3>
                <Button href={`/projects/${projectId}/characters`}>返回人物列表</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    );
  }

  // Helper functions to safely access profile values
  const getProfileValue = <T,>(key: string, defaultValue: T): T => {
    const value = character.profile?.[key];
    return value !== undefined ? (value as T) : defaultValue;
  };

  const hasProfileKey = (key: string): boolean => {
    return character.profile !== undefined && key in character.profile;
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href={`/projects/${projectId}/characters`}
            className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-1 mb-4"
          >
            ← 返回人物列表
          </Link>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-gray-900">{character.name}</h1>
                {character.role && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                    {character.role}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" href={`/projects/${projectId}/characters/${characterId}/edit`}>
                编辑
              </Button>
              <Button variant="danger" size="sm" onClick={() => setDeleteModalOpen(true)}>
                删除
              </Button>
            </div>
          </div>
        </div>

        {/* Basic Info */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">基本信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {hasProfileKey("age") && (
                <div className="flex justify-between">
                  <span className="text-gray-600">年龄</span>
                  <span className="font-medium">{getProfileValue<number>("age", 0)}</span>
                </div>
              )}
              {hasProfileKey("gender") && (
                <div className="flex justify-between">
                  <span className="text-gray-600">性别</span>
                  <span className="font-medium">{getProfileValue<string>("gender", "")}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-600">创建时间</span>
                <span className="font-medium">
                  {new Date(character.created_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">更新时间</span>
                <span className="font-medium">
                  {new Date(character.updated_at).toLocaleDateString("zh-CN")}
                </span>
              </div>
            </CardContent>
          </Card>

          {hasProfileKey("appearance") && (
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">外貌描写</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700 whitespace-pre-wrap">{getProfileValue<string>("appearance", "")}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Personality */}
        {hasProfileKey("personality") && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="text-lg">性格特点</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700 whitespace-pre-wrap">{getProfileValue<string>("personality", "")}</p>
            </CardContent>
          </Card>
        )}

        {/* Background */}
        {hasProfileKey("background") && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">背景故事</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700 whitespace-pre-wrap">{getProfileValue<string>("background", "")}</p>
            </CardContent>
          </Card>
        )}

        {/* Agent Chat */}
        <AgentChatPanel
          projectId={projectId}
          context={{ character_id: characterId, character_name: character.name }}
        />

        {/* Delete Confirmation Modal */}
        <Modal
          isOpen={deleteModalOpen}
          onClose={() => setDeleteModalOpen(false)}
          onConfirm={handleDelete}
          title="删除人物"
          message={`确定要删除人物"${character.name}"吗？此操作无法撤销。`}
          confirmText="删除"
          cancelText="取消"
          variant="danger"
          loading={deleting}
        />
      </div>
    </main>
  );
}
