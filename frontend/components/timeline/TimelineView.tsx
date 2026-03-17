"use client";

import { TimelineEvent } from "@/components/timeline/TimelineEvent";
import type { ProjectTimelineResponse } from "@/lib/types";
import { getChapterStatusMeta } from "@/lib/presentation";

interface TimelineViewProps {
  timeline: ProjectTimelineResponse;
  projectId: string;
}

export function TimelineView({ timeline, projectId }: TimelineViewProps) {
  return (
    <div className="relative">
      <div className="pointer-events-none absolute bottom-0 left-[3.2rem] top-0 hidden w-px bg-[linear-gradient(180deg,rgba(var(--seal),0.24),rgba(var(--line),0.06))] md:block" />

      <div className="space-y-8">
        {timeline.chapters.map((chapter) => {
          const statusMeta = getChapterStatusMeta(chapter.status);
          return (
            <section
              key={chapter.id}
              className="grid gap-5 md:grid-cols-[6.5rem_minmax(0,1fr)] md:items-start"
            >
              <div className="relative z-10 flex flex-row items-center gap-4 md:flex-col md:items-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-full border border-[rgba(var(--seal),0.28)] bg-[rgba(var(--paper),0.95)] text-lg font-semibold text-[rgb(var(--seal))] shadow-[0_12px_32px_rgba(126,58,50,0.12)]">
                  {chapter.chapter_number}
                </div>
                <div className="text-left md:text-center">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[rgb(var(--ink-700))]">
                    {chapter.volume?.title || "未分卷"}
                  </div>
                  <div className="mt-1 text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
                    {chapter.volume?.volume_number ? `第 ${chapter.volume.volume_number} 卷` : "Chapter"}
                  </div>
                </div>
              </div>

              <div className="rounded-[1.7rem] border border-[rgba(var(--line),0.14)] bg-[rgba(var(--paper),0.88)] p-6 shadow-[0_24px_60px_rgba(33,33,33,0.06)] backdrop-blur-sm">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="max-w-3xl">
                    <div className="flex flex-wrap items-center gap-3">
                      <h2 className="ink-display text-3xl font-semibold text-[rgb(var(--ink-950))]">
                        {chapter.title || "未命名章节"}
                      </h2>
                      <span className={statusMeta.className}>{statusMeta.label}</span>
                      <span className="rounded-full border border-[rgba(var(--line),0.14)] px-3 py-1 text-xs tracking-[0.08em] text-[rgb(var(--ink-800))]">
                        事件 {chapter.event_count}
                      </span>
                    </div>
                    <p className="mt-4 text-sm leading-7 text-[rgb(var(--ink-800))]">
                      {chapter.outline || "该章节还没有章纲说明。"}
                    </p>
                  </div>
                  <div className="text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
                    更新于 {new Date(chapter.updated_at).toLocaleDateString("zh-CN")}
                  </div>
                </div>

                {chapter.events.length === 0 ? (
                  <div className="mt-6 rounded-[1.2rem] border border-dashed border-[rgba(var(--line),0.18)] px-4 py-5 text-sm leading-7 text-[rgb(var(--ink-800))]">
                    当前章节还没有挂接到时间线的事件记忆。
                  </div>
                ) : (
                  <div className="mt-6 space-y-4">
                    {chapter.events.map((event) => (
                      <TimelineEvent key={event.id} event={event} projectId={projectId} />
                    ))}
                  </div>
                )}
              </div>
            </section>
          );
        })}

        {timeline.unassigned_events.length > 0 ? (
          <section className="rounded-[1.7rem] border border-dashed border-[rgba(var(--amber),0.28)] bg-[rgba(var(--amber),0.08)] p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="ink-kicker text-[rgb(var(--amber-700,145_92_24))]">Loose Events</p>
                <h2 className="ink-display mt-2 text-3xl font-semibold text-[rgb(var(--ink-950))]">
                  游离事件
                </h2>
              </div>
              <span className="rounded-full border border-[rgba(var(--amber),0.26)] px-3 py-1 text-xs tracking-[0.08em] text-[rgb(var(--ink-800))]">
                {timeline.unassigned_events.length} 条
              </span>
            </div>
            <p className="mt-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
              这些事件记忆还没有明确关联到章节或场景，建议补齐 `memory.meta` 里的 `chapter_id` / `scene_id`。
            </p>
            <div className="mt-6 space-y-4">
              {timeline.unassigned_events.map((event) => (
                <TimelineEvent key={event.id} event={event} projectId={projectId} />
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
