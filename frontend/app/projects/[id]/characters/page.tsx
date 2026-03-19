"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { ApiError, characterApi } from "@/lib/api-client";
import type { Character } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";

function formatStructuredValue(value: unknown): string {
  if (typeof value === "string") {
    return value.trim();
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => formatStructuredValue(item))
      .filter(Boolean)
      .join("、");
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return "";
}

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

  const getProfileValue = <T,>(character: Character, key: string, defaultValue: T): T => {
    const value = character.profile?.[key];
    return value !== undefined ? (value as T) : defaultValue;
  };

  const hasProfileKey = (character: Character, key: string): boolean => {
    return character.profile !== undefined && key in character.profile;
  };

  const getCharacterSummary = (character: Character): string => {
    const preferredKeys = ["background", "personality", "appearance", "key_events", "chapter_scope"];
    for (const key of preferredKeys) {
      const value = formatStructuredValue(character.profile?.[key]);
      if (value) {
        return value;
      }
    }
    for (const value of Object.values(character.profile ?? {})) {
      const formatted = formatStructuredValue(value);
      if (formatted) {
        return formatted;
      }
    }
    if (character.relationships && Object.keys(character.relationships).length > 0) {
      return `已记录 ${Object.keys(character.relationships).length} 条人物关系。`;
    }
    return "当前只有基础条目，尚未生成更多人物细节。";
  };

  useEffect(() => {
    loadCharacters();
  }, [loadCharacters]);

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link href={`/projects/${projectId}`} className="ink-backlink mb-2">
              ← 返回项目
            </Link>
            <p className="ink-kicker">Character Atlas</p>
            <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">人物管理</h1>
            <p className="mt-3 text-base leading-7 text-[rgb(var(--ink-800))]">
              把人物角色、外貌、性格与背景整理在统一卡面里，便于创作时快速回看。
            </p>
          </div>
          <Button href={`/projects/${projectId}/characters/new`}>新建人物</Button>
        </div>

        {loading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="加载人物中..." />
          </div>
        )}

        {error && !loading && (
          <Card padding="lg">
            <CardContent>
              <div className="text-center">
                <p className="mb-4 text-[rgb(var(--danger))]">{error}</p>
                <Button onClick={loadCharacters}>重试</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && characters.length === 0 && (
          <Card padding="lg">
            <CardContent>
              <div className="py-8 text-center">
                <h3 className="ink-display mb-2 text-2xl font-semibold text-[rgb(var(--ink-950))]">
                  还没有人物
                </h3>
                <p className="mb-6 text-[rgb(var(--ink-800))]">
                  创建第一个人物，开始构建您的故事世界
                </p>
                <Button href={`/projects/${projectId}/characters/new`}>创建人物</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && !error && characters.length > 0 && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {characters.map((character) => (
              <Card key={character.id} className="transition-transform duration-200 hover:-translate-y-1">
                <CardContent className="p-6">
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <h3 className="ink-display text-2xl font-semibold text-[rgb(var(--ink-950))]">
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
                      <span className="ink-badge ink-badge-rust">{character.role}</span>
                    </div>
                  )}

                  <div className="space-y-2 text-sm text-[rgb(var(--ink-800))]">
                    {hasProfileKey(character, "age") && (
                      <div className="flex items-center gap-2">
                        <span>年龄:</span>
                        <span className="font-medium text-[rgb(var(--ink-950))]">
                          {getProfileValue<number>(character, "age", 0)}
                        </span>
                      </div>
                    )}
                    {hasProfileKey(character, "gender") && (
                      <div className="flex items-center gap-2">
                        <span>性别:</span>
                        <span className="font-medium text-[rgb(var(--ink-950))]">
                          {getProfileValue<string>(character, "gender", "")}
                        </span>
                      </div>
                    )}
                  </div>

                  <p className="mt-4 line-clamp-4 whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--ink-800))]">
                    {hasProfileKey(character, "appearance")
                      ? getProfileValue<string>(character, "appearance", "")
                      : getCharacterSummary(character)}
                  </p>

                  {character.relationships && Object.keys(character.relationships).length > 0 && (
                    <p className="mt-3 text-xs text-[rgb(var(--ink-800))]">
                      关系数 {Object.keys(character.relationships).length}
                    </p>
                  )}

                  <p className="mt-4 text-xs text-[rgb(var(--ink-800))]">
                    更新于 {new Date(character.updated_at).toLocaleDateString("zh-CN")}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
