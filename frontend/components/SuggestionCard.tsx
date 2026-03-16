"use client";

import { useState } from "react";
import { suggestionApi } from "@/lib/api-client";
import type { Suggestion } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { getSuggestionStatusMeta } from "@/lib/presentation";

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
  const statusMeta = getSuggestionStatusMeta(suggestion.status);

  return (
    <div className="rounded-[1.4rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.54)] p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="text-xs font-medium uppercase tracking-[0.14em] text-[rgb(var(--ink-700))]">
          {TYPE_LABELS[suggestion.type] || suggestion.type}
        </span>
        <span className={statusMeta.className}>{statusMeta.label}</span>
      </div>

      <p className="mb-4 whitespace-pre-wrap text-sm leading-7 text-[rgb(var(--ink-800))]">{summary}</p>

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
