"use client";

import { useState } from "react";
import { suggestionApi } from "@/lib/api-client";
import type { Suggestion } from "@/lib/types";
import { Button } from "@/components/ui/Button";

interface SuggestionCardProps {
  suggestion: Suggestion;
  onAction?: (id: string, action: "confirm" | "discard" | "commit") => void;
}

const TYPE_LABELS: Record<string, string> = {
  character_edit: "人物修改",
  world_edit: "世界观修改",
  chapter_edit: "章节修改",
  scene_edit: "场景修改",
  content_gen: "内容生成",
  outline_gen: "大纲生成",
  continuity_fix: "连续性修复",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "待确认",
  patched: "已确认",
  committed: "已应用",
  discarded: "已丢弃",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-yellow-100 text-yellow-800",
  patched: "bg-blue-100 text-blue-800",
  committed: "bg-green-100 text-green-800",
  discarded: "bg-gray-100 text-gray-500",
};

export function SuggestionCard({ suggestion, onAction }: SuggestionCardProps) {
  const [acting, setActing] = useState(false);

  async function handleAction(action: "confirm" | "discard" | "commit") {
    setActing(true);
    try {
      await suggestionApi.action(suggestion.id, action);
      onAction?.(suggestion.id, action);
    } catch (err) {
      alert(err instanceof Error ? err.message : "操作失败");
    } finally {
      setActing(false);
    }
  }

  const content = suggestion.content;
  const summary =
    (content.reason as string) ||
    (content.suggested_content as string) ||
    (content.suggested_value as string) ||
    (content.suggested_fix as string) ||
    (content.issue as string) ||
    JSON.stringify(content).slice(0, 150);

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-gray-500">
          {TYPE_LABELS[suggestion.type] || suggestion.type}
        </span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[suggestion.status] || ""}`}>
          {STATUS_LABELS[suggestion.status] || suggestion.status}
        </span>
      </div>

      <p className="text-sm text-gray-700 mb-3 whitespace-pre-wrap">{summary}</p>

      {suggestion.status === "draft" && (
        <div className="flex gap-2">
          <Button size="sm" onClick={() => handleAction("confirm")} disabled={acting}>
            接受
          </Button>
          <Button size="sm" variant="outline" onClick={() => handleAction("discard")} disabled={acting}>
            拒绝
          </Button>
        </div>
      )}
      {suggestion.status === "patched" && (
        <div className="flex gap-2">
          <Button size="sm" onClick={() => handleAction("commit")} disabled={acting}>
            应用
          </Button>
          <Button size="sm" variant="outline" onClick={() => handleAction("discard")} disabled={acting}>
            丢弃
          </Button>
        </div>
      )}
    </div>
  );
}
