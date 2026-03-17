"use client";

import Link from "next/link";

import type { ProjectTimelineEvent } from "@/lib/types";

const memoryTypeLabel: Record<string, string> = {
  episode: "事件",
  fact: "事实",
  semantic: "设定",
};

interface TimelineEventProps {
  event: ProjectTimelineEvent;
  projectId: string;
}

export function TimelineEvent({ event, projectId }: TimelineEventProps) {
  const targetHref = event.scene_id && event.chapter_id
    ? `/projects/${projectId}/chapters/${event.chapter_id}/scenes/${event.scene_id}`
    : event.chapter_id
      ? `/projects/${projectId}/chapters/${event.chapter_id}`
      : null;

  return (
    <article className="rounded-[1.4rem] border border-[rgba(var(--line),0.14)] bg-[rgba(var(--paper),0.9)] p-5 shadow-[0_18px_40px_rgba(33,33,33,0.06)] backdrop-blur-sm">
      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-full border border-[rgba(var(--seal),0.28)] bg-[rgba(var(--seal),0.08)] px-3 py-1 text-[11px] tracking-[0.16em] text-[rgb(var(--seal))]">
          {memoryTypeLabel[event.memory_type] || event.memory_type}
        </span>
        {event.scene_order ? (
          <span className="text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
            场景 {event.scene_order}
            {event.location ? ` · ${event.location}` : ""}
          </span>
        ) : event.chapter_number ? (
          <span className="text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
            第 {event.chapter_number} 章
          </span>
        ) : null}
      </div>

      <h3 className="mt-4 text-xl font-semibold text-[rgb(var(--ink-950))]">{event.title}</h3>
      <p className="mt-3 text-sm leading-7 text-[rgb(var(--ink-800))]">{event.summary}</p>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <div className="text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
          {new Date(event.created_at).toLocaleString("zh-CN", {
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
        {targetHref ? (
          <Link
            href={targetHref}
            className="inline-flex items-center gap-2 rounded-full border border-[rgba(var(--line),0.16)] px-3 py-1.5 text-xs tracking-[0.08em] text-[rgb(var(--ink-900))] transition-colors hover:bg-[rgba(var(--ink-950),0.05)]"
          >
            查看原文
            <span aria-hidden="true">↗</span>
          </Link>
        ) : null}
      </div>
    </article>
  );
}
