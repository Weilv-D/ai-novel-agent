"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { TimelineView } from "@/components/timeline/TimelineView";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import { ApiError, timelineApi } from "@/lib/api-client";
import type { ProjectTimelineResponse } from "@/lib/types";

export default function ProjectTimelinePage() {
  const params = useParams();
  const projectId = params.id as string;

  const [timeline, setTimeline] = useState<ProjectTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTimeline = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await timelineApi.get(projectId);
      setTimeline(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("加载时间线失败");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void loadTimeline();
  }, [loadTimeline]);

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <Link href={`/projects/${projectId}`} className="ink-backlink mb-2">
              ← 返回项目
            </Link>
            <p className="ink-kicker">Project Timeline</p>
            <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">
              章节时间线
            </h1>
            <p className="mt-3 max-w-3xl text-base leading-7 text-[rgb(var(--ink-800))]">
              以章节顺序为骨架，把事件记忆穿插到对应章/场景下，方便检查推进节奏和遗漏线索。
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" href={`/projects/${projectId}/chapters`}>
              章节
            </Button>
            <Button variant="outline" href={`/projects/${projectId}/relationships`}>
              图谱
            </Button>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <LoadingSpinner size="lg" text="加载时间线中..." />
          </div>
        ) : null}

        {error && !loading ? (
          <Card padding="lg">
            <CardContent>
              <div className="py-10 text-center">
                <h2 className="ink-display text-2xl font-semibold text-[rgb(var(--ink-950))]">
                  时间线暂不可用
                </h2>
                <p className="mt-3 text-sm leading-7 text-[rgb(var(--ink-800))]">{error}</p>
                <div className="mt-6 flex justify-center gap-3">
                  <Button onClick={() => void loadTimeline()}>重试</Button>
                  <Button variant="outline" href={`/projects/${projectId}`}>
                    返回项目
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {!loading && !error && timeline ? (
          <>
            <div className="mb-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-[1.5rem] border border-[rgba(var(--line),0.14)] bg-[rgba(var(--paper),0.84)] px-5 py-4">
                <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-700))]">
                  Chapters
                </div>
                <div className="mt-2 text-3xl font-semibold text-[rgb(var(--ink-950))]">
                  {timeline.chapters.length}
                </div>
              </div>
              <div className="rounded-[1.5rem] border border-[rgba(var(--line),0.14)] bg-[rgba(var(--paper),0.84)] px-5 py-4">
                <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-700))]">
                  Events
                </div>
                <div className="mt-2 text-3xl font-semibold text-[rgb(var(--ink-950))]">
                  {timeline.total_events}
                </div>
              </div>
              <div className="rounded-[1.5rem] border border-[rgba(var(--line),0.14)] bg-[rgba(var(--paper),0.84)] px-5 py-4">
                <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-700))]">
                  Loose
                </div>
                <div className="mt-2 text-3xl font-semibold text-[rgb(var(--ink-950))]">
                  {timeline.unassigned_events.length}
                </div>
              </div>
            </div>

            <TimelineView timeline={timeline} projectId={projectId} />
          </>
        ) : null}
      </div>
    </main>
  );
}
