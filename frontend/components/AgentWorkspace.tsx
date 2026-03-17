"use client";

import { type ReactNode, useEffect, useRef, useState, useTransition } from "react";

import { agentWorkflowApi, ApiError, chapterApi, projectApi, volumeApi } from "@/lib/api-client";
import type {
  AgentExecutionChildUnit,
  AgentAppliedRiskPolicy,
  AgentExecutionContractPhase,
  AgentHookTraceEntry,
  AgentOperation,
  Chapter,
  AgentRun,
  AgentRunRiskSummary,
  AgentStreamEvent,
  AgentSubtask,
  AgentThread,
  AgentThreadCheckpoint,
  AgentThreadMessage,
  Project,
  Volume,
} from "@/lib/types";
import { getRunStatusMeta } from "@/lib/presentation";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Textarea } from "@/components/ui/Input";
import { DiffPreview } from "@/components/DiffPreview";

interface AgentWorkspaceProps {
  projectId: string;
  projectName: string;
  agentProfileId?: string;
  className?: string;
  onProjectRefresh?: () => Promise<void> | void;
}

const TOOL_LABELS: Record<string, string> = {
  update_project_outline: "修改项目大纲",
  create_character: "创建人物",
  update_character: "修改人物",
  create_world_setting: "创建设定",
  update_world_setting: "修改设定",
  create_volume: "创建卷",
  update_volume: "修改卷细纲",
  create_chapter: "创建章节",
  update_chapter: "修改章节",
  write_chapter_content: "写章节正文",
  create_scene: "创建场景",
  update_scene: "修改场景",
  write_scene_content: "写场景正文",
};

const RISK_META: Record<string, { label: string; className: string }> = {
  low: { label: "低风险", className: "ink-badge ink-badge-jade" },
  medium: { label: "标准写入", className: "ink-badge ink-badge-amber" },
  high: { label: "高风险", className: "ink-badge ink-badge-rust" },
};

const VERIFICATION_META: Record<string, { label: string; className: string }> = {
  pending: { label: "待校验", className: "ink-badge ink-badge-ash" },
  passed: { label: "已校验", className: "ink-badge ink-badge-jade" },
  failed: { label: "校验失败", className: "ink-badge ink-badge-rust" },
  skipped: { label: "已跳过", className: "ink-badge ink-badge-smoke" },
};

function getHookTrace(run: AgentRun | null): AgentHookTraceEntry[] {
  if (!run) {
    return [];
  }
  const raw = run.meta["hook_trace"];
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter((entry): entry is AgentHookTraceEntry => {
    if (!entry || typeof entry !== "object") {
      return false;
    }
    const hook = (entry as Record<string, unknown>).hook_name;
    const status = (entry as Record<string, unknown>).status;
    return typeof hook === "string" && typeof status === "string";
  });
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    month: "numeric",
    day: "numeric",
  });
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function extractPreviewAfterText(operation: AgentOperation): string | null {
  return asString(operation.preview.after_summary) || asString(operation.preview.diff);
}

function getRequestContext(run: AgentRun | null): Record<string, unknown> {
  return asRecord(run?.meta.request_context) || {};
}

function excerpt(value: string | null | undefined, fallback: string, max = 150): string {
  const text = value?.trim();
  if (!text) {
    return fallback;
  }
  if (text.length <= max) {
    return text;
  }
  return `${text.slice(0, max)}...`;
}

interface MetaItem {
  label: string;
  value: ReactNode | null | undefined;
  tone?: "default" | "danger" | "accent";
}

function CompactMetaGrid({
  items,
  columns = 2,
  className = "",
}: {
  items: MetaItem[];
  columns?: 2 | 3 | 4;
  className?: string;
}) {
  const visibleItems = items.filter((item) => item.value !== null && item.value !== undefined && item.value !== "");
  if (visibleItems.length === 0) {
    return null;
  }

  const columnClass =
    columns === 4
      ? "sm:grid-cols-2 2xl:grid-cols-4"
      : columns === 3
        ? "sm:grid-cols-3"
        : "sm:grid-cols-2";

  return (
    <div className={`grid grid-cols-1 gap-3 ${columnClass} ${className}`}>
      {visibleItems.map((item, index) => {
        const toneClass =
          item.tone === "danger"
            ? "text-[rgb(var(--danger))]"
            : item.tone === "accent"
              ? "text-[rgb(var(--ink-950))]"
              : "text-[rgb(var(--ink-900))]";
        return (
          <div
            key={`${item.label}-${index}`}
            className="rounded-[0.95rem] bg-[rgba(var(--ink-950),0.05)] px-3 py-3"
          >
            <div className="text-[11px] uppercase tracking-[0.16em] text-[rgb(var(--ink-700))]">
              {item.label}
            </div>
            <div className={`mt-1 text-sm leading-6 ${toneClass}`}>{item.value}</div>
          </div>
        );
      })}
    </div>
  );
}

function CompactMetaLine({
  items,
  className = "",
}: {
  items: MetaItem[];
  className?: string;
}) {
  const visibleItems = items.filter((item) => item.value !== null && item.value !== undefined && item.value !== "");
  if (visibleItems.length === 0) {
    return null;
  }

  return (
    <div className={`flex flex-wrap gap-x-4 gap-y-1 text-xs leading-6 text-[rgb(var(--ink-800))] ${className}`}>
      {visibleItems.map((item, index) => {
        const toneClass =
          item.tone === "danger"
            ? "text-[rgb(var(--danger))]"
            : item.tone === "accent"
              ? "text-[rgb(var(--ink-950))]"
              : "text-[rgb(var(--ink-900))]";
        return (
          <span key={`${item.label}-${index}`}>
            <span className="text-[rgb(var(--ink-700))]">{item.label}</span>
            <span className={`ml-1 ${toneClass}`}>{item.value}</span>
          </span>
        );
      })}
    </div>
  );
}

function DisclosureSection({
  kicker,
  title,
  description,
  children,
  defaultOpen = false,
}: {
  kicker: string;
  title: string;
  description?: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details
      className="rounded-[1.15rem] border border-[rgba(var(--line),0.14)] bg-[var(--surface-strong)] px-4 py-4"
      open={defaultOpen || undefined}
    >
      <summary className="flex cursor-pointer list-none items-start justify-between gap-4 [&::-webkit-details-marker]:hidden">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">{kicker}</div>
          <div className="mt-1 text-base font-medium text-[rgb(var(--ink-950))]">{title}</div>
          {description && (
            <p className="mt-2 text-sm leading-6 text-[rgb(var(--ink-800))]">{description}</p>
          )}
        </div>
        <span className="shrink-0 text-xs tracking-[0.12em] text-[rgb(var(--ink-700))]">
          查看细节
        </span>
      </summary>
      <div className="mt-4 border-t border-[rgba(var(--line),0.12)] pt-4">{children}</div>
    </details>
  );
}

type FocusVolumeSummary = {
  id?: string;
  title: string;
  outline: string | null;
  badge: string;
};

function getProjectOutlinePreview(run: AgentRun | null, project: Project | null): string | null {
  const pendingUpdate = run?.operations.find((operation) => operation.tool_name === "update_project_outline");
  if (pendingUpdate) {
    const updates = asRecord(pendingUpdate.payload.updates) || asRecord(pendingUpdate.payload);
    return (
      asString(updates?.story_outline) ||
      asString(updates?.outline) ||
      extractPreviewAfterText(pendingUpdate) ||
      project?.story_outline ||
      null
    );
  }
  return project?.story_outline || null;
}

function getFocusedVolumeSummary(
  run: AgentRun | null,
  volumes: Volume[],
  chapters: Chapter[],
): FocusVolumeSummary | null {
  const requestContext = getRequestContext(run);
  const operationVolume =
    run?.operations.find((operation) => operation.target_type === "volume") ||
    run?.operations.find((operation) => operation.tool_name === "create_volume") ||
    run?.operations.find((operation) => {
      const payload = asRecord(operation.payload);
      const updates = asRecord(payload?.updates);
      return (
        asString(payload?.volume_id) ||
        asString(payload?.target_volume_id) ||
        asString(updates?.volume_id)
      );
    });

  const focusedVolumeId =
    asString(requestContext.volume_id) ||
    asString(operationVolume?.target_id) ||
    asString(asRecord(operationVolume?.payload)?.volume_id) ||
    asString(asRecord(asRecord(operationVolume?.payload)?.updates)?.volume_id);

  if (focusedVolumeId) {
    const matched = volumes.find((volume) => volume.id === focusedVolumeId);
    if (matched) {
      return {
        id: matched.id,
        title: matched.title || `第 ${matched.volume_number || "?"} 卷`,
        outline: matched.outline || null,
        badge: `第 ${matched.volume_number || "?"} 卷`,
      };
    }
  }

  const chapterId =
    asString(requestContext.chapter_id) ||
    asString(run?.operations.find((operation) => operation.target_type === "chapter")?.target_id);
  if (chapterId) {
    const matchedChapter = chapters.find((chapter) => chapter.id === chapterId);
    if (matchedChapter?.volume_id) {
      const matchedVolume = volumes.find((volume) => volume.id === matchedChapter.volume_id);
      if (matchedVolume) {
        return {
          id: matchedVolume.id,
          title: matchedVolume.title || `第 ${matchedVolume.volume_number || "?"} 卷`,
          outline: matchedVolume.outline || null,
          badge: `第 ${matchedVolume.volume_number || "?"} 卷`,
        };
      }
    }
  }

  const pendingVolumeOperation = run?.operations.find(
    (operation) => operation.tool_name === "create_volume" || operation.tool_name === "update_volume",
  );
  if (pendingVolumeOperation) {
    const payload = asRecord(pendingVolumeOperation.payload);
    const updates = asRecord(payload?.updates);
    const volumeNumber =
      asNumber(payload?.volume_number) ||
      asNumber(updates?.volume_number);
    return {
      title:
        asString(payload?.title) ||
        asString(updates?.title) ||
        pendingVolumeOperation.target_display ||
        "待更新卷细纲",
      outline:
        asString(payload?.outline) ||
        asString(updates?.outline) ||
        extractPreviewAfterText(pendingVolumeOperation),
      badge: `第 ${volumeNumber || "?"} 卷`,
    };
  }

  return null;
}

function getRelatedChapterOutlines(run: AgentRun | null, chapters: Chapter[], focusVolume: FocusVolumeSummary | null): Chapter[] {
  const requestContext = getRequestContext(run);
  const relatedChapterIds = new Set<string>();

  const contextChapterId = asString(requestContext.chapter_id);
  if (contextChapterId) {
    relatedChapterIds.add(contextChapterId);
  }

  for (const operation of run?.operations || []) {
    if (operation.target_type === "chapter" && operation.target_id) {
      relatedChapterIds.add(operation.target_id);
    }
    const payload = asRecord(operation.payload);
    const updates = asRecord(payload?.updates);
    for (const value of [payload?.chapter_id, updates?.chapter_id]) {
      const chapterId = asString(value);
      if (chapterId) {
        relatedChapterIds.add(chapterId);
      }
    }
  }

  let related = chapters.filter((chapter) => relatedChapterIds.has(chapter.id));

  if (related.length === 0 && focusVolume?.id) {
    related = chapters.filter((chapter) => chapter.volume_id === focusVolume.id);
  }

  return related
    .sort((left, right) => left.chapter_number - right.chapter_number)
    .slice(0, 4);
}

function MessageBubble({ message }: { message: AgentThreadMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-[1.25rem] px-4 py-3 text-sm leading-7 shadow-sm ${
          isUser
            ? "bg-[rgba(var(--ink-950),0.95)] text-[rgb(var(--paper-soft))]"
            : "border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] text-[rgb(var(--ink-900))]"
        }`}
      >
        <div className="mb-1 text-[11px] uppercase tracking-[0.18em] opacity-60">
          {isUser ? "You" : "Agent"}
        </div>
        <div className="whitespace-pre-wrap">{message.content}</div>
      </div>
    </div>
  );
}

function SubtaskCard({ subtask }: { subtask: AgentSubtask }) {
  const verificationMeta = VERIFICATION_META[subtask.status === "failed" ? "failed" : subtask.status === "completed" ? "passed" : subtask.status === "skipped" ? "skipped" : "pending"];
  const validationStatus = typeof subtask.meta.validation_status === "string" ? subtask.meta.validation_status : null;
  const source = typeof subtask.meta.source === "string" ? subtask.meta.source : null;
  const attemptCount = typeof subtask.meta.attempt_count === "number" ? subtask.meta.attempt_count : null;
  const maxAttempts = typeof subtask.meta.max_attempts === "number" ? subtask.meta.max_attempts : null;
  const retryStrategy = typeof subtask.meta.retry_strategy === "string" ? subtask.meta.retry_strategy : null;
  const childTrace = subtask.child_trace;
  const dependencyList = childTrace?.depends_on || [];
  return (
    <div className="rounded-[1.1rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">{subtask.role}</div>
          <div className="mt-1 text-sm font-medium text-[rgb(var(--ink-900))]">{subtask.title}</div>
        </div>
        <span className={verificationMeta.className}>{verificationMeta.label}</span>
      </div>
      {subtask.summary && (
        <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-800))]">{subtask.summary}</p>
      )}
      {(source || validationStatus || attemptCount !== null || retryStrategy) && (
        <CompactMetaLine
          className="mt-3"
          items={[
            { label: "来源", value: source },
            { label: "校验", value: validationStatus },
            { label: "尝试", value: attemptCount !== null ? `${attemptCount}/${maxAttempts ?? attemptCount}` : null },
            { label: "重试策略", value: retryStrategy },
          ]}
        />
      )}
      {dependencyList.length > 0 && (
        <p className="mt-3 text-xs leading-6 text-[rgb(var(--ink-800))]">
          依赖：{dependencyList.join(" / ")}
        </p>
      )}
      {subtask.error_message && (
        <p className="mt-2 text-sm leading-7 text-[rgb(var(--danger))]">{subtask.error_message}</p>
      )}
    </div>
  );
}

function OperationCard({ operation }: { operation: AgentOperation }) {
  const toolLabel = TOOL_LABELS[operation.tool_name] || operation.tool_name;
  const preview = operation.preview;
  const riskMeta = RISK_META[operation.risk_level] || RISK_META.medium;
  const verificationMeta = VERIFICATION_META[operation.verification_status] || VERIFICATION_META.pending;
  return (
    <div className="rounded-[1.4rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
            Step {operation.position}
          </div>
          <div className="mt-1 text-base font-medium text-[rgb(var(--ink-950))]">{toolLabel}</div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <span className={riskMeta.className}>{riskMeta.label}</span>
          <span className={verificationMeta.className}>{verificationMeta.label}</span>
        </div>
      </div>
      <CompactMetaLine
        className="mb-2"
        items={[
          { label: "目标", value: operation.target_display },
          {
            label: "涉及字段",
            value: preview.changed_fields.length > 0 ? preview.changed_fields.join(" / ") : null,
          },
        ]}
      />
      <p className="text-sm leading-7 text-[rgb(var(--ink-800))]">{operation.description}</p>
      {operation.reason && (
        <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-800))]">原因：{operation.reason}</p>
      )}
      {operation.requires_secondary_confirmation && (
        <p className="mt-2 text-sm leading-7 text-[rgb(var(--danger))]">此步骤会触发二次确认，适用于高风险正文覆盖。</p>
      )}
      {(preview.before_summary || preview.after_summary) && (
        <div className="mt-4">
          <DiffPreview
            title="预览"
            before={preview.before_summary || ""}
            after={preview.after_summary || ""}
          />
        </div>
      )}
      {preview.diff && (
        <pre className="mt-4 overflow-x-auto rounded-[1rem] bg-[rgba(var(--ink-950),0.92)] p-4 text-xs leading-6 text-[rgb(var(--paper-soft))]">
          {preview.diff}
        </pre>
      )}
      {operation.verification_summary && (
        <p className="mt-3 text-sm leading-7 text-[rgb(var(--ink-800))]">校验：{operation.verification_summary}</p>
      )}
      {operation.error_message && (
        <p className="mt-3 text-sm text-[rgb(var(--danger))]">{operation.error_message}</p>
      )}
    </div>
  );
}

function RiskSummaryCard({ riskSummary }: { riskSummary: AgentRunRiskSummary }) {
  const riskMeta = RISK_META[riskSummary.overall_risk_level] || RISK_META.medium;
  return (
    <div className="rounded-[1.2rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-strong)] px-4 py-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">Run Risk</div>
          <div className="mt-1 text-base font-medium text-[rgb(var(--ink-950))]">执行风险摘要</div>
        </div>
        <span className={riskMeta.className}>{riskMeta.label}</span>
      </div>
      <CompactMetaLine
        className="mt-2"
        items={[
          { label: "确认门槛", value: riskSummary.confirmation_gate },
          { label: "策略版本", value: riskSummary.policy_version },
        ]}
      />
      <p className="mt-3 text-sm leading-7 text-[rgb(var(--ink-800))]">{riskSummary.summary}</p>
      <CompactMetaGrid
        className="mt-3"
        items={[
          { label: "总步骤", value: riskSummary.total_operations, tone: "accent" },
          { label: "低风险", value: riskSummary.low_risk_operation_count },
          { label: "标准写入", value: riskSummary.medium_risk_operation_count },
          { label: "高风险", value: riskSummary.high_risk_operation_count, tone: "danger" },
        ]}
        columns={4}
      />
      {riskSummary.applied_policies.length > 0 && (
        <div className="mt-3 space-y-2">
          {riskSummary.applied_policies.map((policy: AgentAppliedRiskPolicy) => (
            <div
              key={`${policy.policy_id}-${policy.matched_operation_positions.join("-")}`}
              className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[rgba(var(--ink-950),0.03)] px-3 py-3"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-[rgb(var(--ink-900))]">{policy.name}</div>
                <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-800))]">
                  {policy.scope} / {policy.risk_level} / gate:{policy.confirmation_gate}
                </div>
              </div>
              <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-800))]">{policy.description}</p>
              <CompactMetaLine
                className="mt-2"
                items={[
                  {
                    label: "命中步骤",
                    value: policy.matched_operation_positions.length > 0 ? policy.matched_operation_positions.join(", ") : null,
                  },
                  {
                    label: "附加要求",
                    value: policy.requires_secondary_confirmation ? "需要二次确认" : null,
                    tone: policy.requires_secondary_confirmation ? "danger" : "default",
                  },
                ]}
              />
            </div>
          ))}
        </div>
      )}
      {(riskSummary.high_risk_operation_positions.length > 0 ||
        riskSummary.secondary_confirmation_operation_positions.length > 0) && (
        <CompactMetaLine
          className="mt-3"
          items={[
            {
              label: "高风险步骤",
              value: riskSummary.high_risk_operation_positions.length > 0 ? riskSummary.high_risk_operation_positions.join(", ") : null,
              tone: riskSummary.high_risk_operation_positions.length > 0 ? "danger" : "default",
            },
            {
              label: "二次确认步骤",
              value:
                riskSummary.secondary_confirmation_operation_positions.length > 0
                  ? riskSummary.secondary_confirmation_operation_positions.join(", ")
                  : null,
            },
          ]}
        />
      )}
    </div>
  );
}

function ChildUnitCard({ childUnit }: { childUnit: AgentExecutionChildUnit }) {
  return (
    <div className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[rgba(var(--ink-950),0.03)] px-3 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-medium text-[rgb(var(--ink-900))]">{childUnit.title}</div>
        <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-800))]">
          {childUnit.role} / {childUnit.stage}
        </div>
      </div>
      <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-800))]">{childUnit.description}</p>
      <CompactMetaLine
        className="mt-2"
        items={[
          { label: "确认门槛", value: childUnit.confirmation_gate },
          { label: "模式", value: childUnit.mode },
          { label: "附加要求", value: childUnit.requires_confirmation ? "需要人工确认" : null },
        ]}
      />
      {(childUnit.depends_on.length > 0 || childUnit.operation_positions.length > 0) && (
        <CompactMetaLine
          className="mt-3"
          items={[
            { label: "依赖", value: childUnit.depends_on.length > 0 ? childUnit.depends_on.join(" / ") : null },
            {
              label: "关联步骤",
              value: childUnit.operation_positions.length > 0 ? childUnit.operation_positions.join(", ") : null,
            },
          ]}
        />
      )}
      {(childUnit.capability_ids.length > 0 || childUnit.tool_scope.length > 0) && (
        <CompactMetaLine
          className="mt-3"
          items={[
            {
              label: "能力",
              value: childUnit.capability_ids.length > 0 ? childUnit.capability_ids.join(" / ") : null,
            },
            {
              label: "工具",
              value: childUnit.tool_scope.length > 0 ? Array.from(new Set(childUnit.tool_scope.slice(0, 4))).join(" / ") : null,
            },
          ]}
        />
      )}
    </div>
  );
}

export function AgentWorkspace({
  projectId,
  projectName,
  agentProfileId,
  className = "",
  onProjectRefresh,
}: AgentWorkspaceProps) {
  const [project, setProject] = useState<Project | null>(null);
  const [volumes, setVolumes] = useState<Volume[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [thread, setThread] = useState<AgentThread | null>(null);
  const [messages, setMessages] = useState<AgentThreadMessage[]>([]);
  const [recentRuns, setRecentRuns] = useState<AgentRun[]>([]);
  const [currentRun, setCurrentRun] = useState<AgentRun | null>(null);
  const [latestCheckpoint, setLatestCheckpoint] = useState<AgentThreadCheckpoint | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [streamingEvents, setStreamingEvents] = useState<AgentStreamEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const hookTrace = getHookTrace(currentRun);
  const permissionMatrix = currentRun?.execution_contract?.phases || [];
  const projectOutlinePreview = getProjectOutlinePreview(currentRun, project);
  const focusedVolume = getFocusedVolumeSummary(currentRun, volumes, chapters);
  const relatedChapters = getRelatedChapterOutlines(currentRun, chapters, focusedVolume);
  const relatedChapterPreviews = relatedChapters.slice(0, 2);
  const hasRunDiagnostics = Boolean(
    currentRun &&
      (currentRun.planner_window ||
        currentRun.compact_policy ||
        currentRun.retained_window ||
        currentRun.active_bundle_contract ||
        currentRun.subtasks.length > 0 ||
        permissionMatrix.length > 0 ||
        hookTrace.length > 0),
  );
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingEvents]);

  async function loadOutlineHierarchy() {
    try {
      const [projectData, volumeData, chapterData] = await Promise.all([
        projectApi.get(projectId) as Promise<Project>,
        volumeApi.list(projectId) as Promise<Volume[]>,
        chapterApi.list(projectId) as Promise<Chapter[]>,
      ]);
      setProject(projectData);
      setVolumes(volumeData.sort((left, right) => (left.volume_number || 0) - (right.volume_number || 0)));
      setChapters(chapterData.sort((left, right) => left.chapter_number - right.chapter_number));
    } catch (err) {
      console.error("Failed to load outline hierarchy:", err);
    }
  }

  async function loadThreadState(existingThreadId?: string) {
    setError(null);
    setLoading(true);
    try {
      const threadRecord = existingThreadId
        ? thread
        : await agentWorkflowApi.createThread(projectId);
      const activeThread = existingThreadId
        ? thread
        : threadRecord;
      const threadId = existingThreadId || activeThread?.id;
      if (!threadId || !activeThread) {
        throw new Error("无法初始化 Agent 线程");
      }
      const state = await agentWorkflowApi.getThread(threadId);
      setThread(state.thread);
      setMessages(state.messages);
      setRecentRuns(state.recent_runs);
      setCurrentRun(state.current_run || null);
      setLatestCheckpoint(state.latest_checkpoint || null);
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : "加载 Agent 工作台失败";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadThreadState();
    loadOutlineHierarchy();
    // projectId change means a different workspace.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function refreshAfterMutation() {
    if (thread?.id) {
      await loadThreadState(thread.id);
    }
    await loadOutlineHierarchy();
    if (onProjectRefresh) {
      await onProjectRefresh();
    }
  }

  async function handleSend() {
    const content = input.trim();
    if (!thread?.id || !content || isPending || isStreaming) {
      return;
    }
    setError(null);
    setInput("");
    setStreamingEvents([]);
    setIsStreaming(true);

    try {
      const userMessage: AgentThreadMessage = {
        id: `temp-${Date.now()}`,
        thread_id: thread.id,
        role: "user",
        content,
        meta: {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      for await (const event of agentWorkflowApi.sendMessageStream(thread.id, {
        content,
        context: {},
      })) {
        setStreamingEvents((prev) => [...prev, event]);

        if (event.type === "error") {
          setError(event.message || "处理过程中发生错误");
          break;
        }

        if (event.type === "result") {
          const detail = event.detail as {
            thread: AgentThread;
            user_message: AgentThreadMessage;
            assistant_message: AgentThreadMessage;
            run?: AgentRun;
          };
          setMessages((prev) => [
            ...prev.filter((m) => m.id !== userMessage.id),
            detail.user_message,
            detail.assistant_message,
          ]);
          if (detail.run) {
            setCurrentRun(detail.run);
            setRecentRuns((prev) =>
              [detail.run!, ...prev.filter((run) => run.id !== detail.run!.id)].slice(0, 8)
            );
          }
        }
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : "发送指令失败";
      setError(message);
    } finally {
      setIsStreaming(false);
    }
  }

  async function handleRunAction(action: "confirm" | "confirm_high_risk" | "cancel") {
    if (!currentRun || isPending) {
      return;
    }
    setError(null);
    startTransition(async () => {
      try {
        if (action === "confirm") {
          await agentWorkflowApi.confirmRun(currentRun.id);
        } else if (action === "confirm_high_risk") {
          await agentWorkflowApi.confirmHighRiskRun(currentRun.id);
        } else {
          await agentWorkflowApi.cancelRun(currentRun.id);
        }
        await refreshAfterMutation();
      } catch (err) {
        const message = err instanceof ApiError ? err.detail : "执行操作失败";
        setError(message);
      }
    });
  }

  if (loading) {
    return (
      <div className={className}>
        <div className="flex justify-center py-16">
          <LoadingSpinner size="lg" text="初始化 Agent 工作台..." />
        </div>
      </div>
    );
  }

  return (
    <div className={`grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)] lg:items-stretch ${className}`}>
      <Card className="flex min-h-[680px] flex-col overflow-hidden lg:h-[clamp(720px,calc(100vh-9rem),980px)]">
        <CardHeader className="border-b border-[rgba(var(--line),0.12)] pb-4">
          <p className="ink-kicker">Agent Workspace</p>
          <CardTitle className="mt-3 text-3xl">以自然语言驱动 {projectName}</CardTitle>
          <CardDescription>
            直接说出你的目标，例如“先补项目大纲，再拆第一卷细纲”“把第三章章纲改成雨夜追逐”“新增一个宗教设定并补进世界观”。
          </CardDescription>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-1 flex-col gap-4 pt-6">
          <div className="rounded-[1.15rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-strong)] px-4 py-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">Workspace Context</div>
                <div className="mt-1 text-base font-medium text-[rgb(var(--ink-950))]">当前规划层级</div>
              </div>
              <p className="max-w-lg text-xs leading-6 text-[rgb(var(--ink-800))]">
                对话上方只保留当前写作焦点摘要，避免在消息区还没开始前就占用过多垂直空间。
              </p>
            </div>
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
              <div className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] px-4 py-3">
                <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-800))]">项目大纲</div>
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-[rgb(var(--ink-900))]">
                  {excerpt(projectOutlinePreview, "尚未填写项目大纲。可以直接让 Agent 先补一版项目总纲。", 140)}
                </p>
              </div>
              <div className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] px-4 py-3">
                <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-800))]">卷细纲</div>
                <p className="mt-2 text-sm font-medium text-[rgb(var(--ink-950))]">
                  {focusedVolume?.title || "当前没有聚焦到具体卷"}
                </p>
                <CompactMetaLine
                  className="mt-1"
                  items={[
                    { label: "卷标识", value: focusedVolume?.badge },
                    { label: "关联章纲", value: relatedChapters.length > 0 ? `${relatedChapters.length} 个` : null },
                  ]}
                />
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-[rgb(var(--ink-900))]">
                  {excerpt(focusedVolume?.outline, "发送“创建卷”或在运行计划里选定卷后，这里会显示卷细纲焦点。", 120)}
                </p>
              </div>
            </div>
          </div>
          <div className="flex-1 space-y-4 overflow-y-auto overscroll-contain pr-1">
            {messages.length === 0 ? (
              <div className="rounded-[1.4rem] border border-dashed border-[rgba(var(--line),0.18)] bg-[var(--surface-subtle)] px-6 py-12 text-center text-sm leading-7 text-[rgb(var(--ink-800))]">
                还没有对话。先告诉 Agent 你要修改什么，或者直接给出写作任务。
              </div>
            ) : (
              messages.map((message) => <MessageBubble key={message.id} message={message} />)
            )}
            {isStreaming && streamingEvents.length > 0 && (
              <div className="rounded-[1.4rem] border border-[rgba(var(--line),0.2)] bg-[var(--surface-strong)] px-5 py-4 shadow-sm">
                <div className="mb-3 flex items-center gap-2">
                  <div className="h-2 w-2 animate-pulse rounded-full bg-[rgb(var(--jade))]" />
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                    Agent 思考过程
                  </span>
                </div>
                <div className="space-y-2">
                  {streamingEvents.map((event, index) => (
                    <div key={index} className="flex items-start gap-3 text-sm">
                      <span
                        className={`mt-0.5 inline-block h-1.5 w-1.5 flex-shrink-0 rounded-full ${
                          event.type === "thinking"
                            ? "bg-[rgb(var(--jade))]"
                            : event.type === "status"
                              ? "bg-[rgb(var(--ink-800))]"
                              : event.type === "operation_progress"
                                ? "bg-[rgb(var(--amber))]"
                                : event.type === "error"
                                  ? "bg-[rgb(var(--danger))]"
                                  : "bg-[rgb(var(--ink-800))]"
                        }`}
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-[rgb(var(--ink-900))]">
                            {event.stage || event.type}
                          </span>
                          {event.message && (
                            <span className="text-[rgb(var(--ink-800))]">{event.message}</span>
                          )}
                        </div>
                        {event.type === "thinking" && typeof event.detail.operations === "object" && (
                          <div className="mt-2 space-y-1">
                            {Array.isArray(event.detail.operations) && (event.detail.operations as Array<{tool_name: string; description: string}>).map((op, opIndex) => (
                              <div key={opIndex} className="text-xs text-[rgb(var(--ink-800))]">
                                • {TOOL_LABELS[op.tool_name as string] || op.tool_name}: {op.description}
                              </div>
                            ))}
                          </div>
                        )}
                        {event.type === "operation_progress" && typeof event.detail.target_display === "string" && (
                          <div className="mt-1 text-xs text-[rgb(var(--ink-800))]">
                            目标: {event.detail.target_display as string}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <div className="border-t border-[rgba(var(--line),0.12)] pt-4">
            <Textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="例如：创建一个在第 3 章登场的反派人物，身份是皇城密探，性格冷静，顺便把第三章标题改得更紧张一些。"
              className="min-h-[140px]"
              disabled={isPending}
              testId="agent-input"
            />
            <div className="mt-4 flex items-center justify-between gap-3">
              <p className="text-sm text-[rgb(var(--ink-800))]">
                {isStreaming ? "Agent 正在思考，请稍候..." : "Agent 会先生成完整计划和预览，确认后才真正写入数据。"}
              </p>
              <Button onClick={handleSend} disabled={!input.trim() || isPending || isStreaming} testId="agent-send-btn">
                {isStreaming ? "思考中..." : isPending ? "处理中..." : "生成计划"}
              </Button>
            </div>
            {error && <p className="mt-3 text-sm text-[rgb(var(--danger))]">{error}</p>}
          </div>
        </CardContent>
      </Card>

      <div className="grid min-h-0 gap-6 lg:h-[clamp(720px,calc(100vh-9rem),980px)] lg:grid-rows-[minmax(0,1.3fr)_minmax(240px,0.82fr)]">
        <Card className="flex min-h-[560px] flex-col overflow-hidden lg:min-h-0">
          <CardHeader className="border-b border-[rgba(var(--line),0.12)] pb-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="ink-kicker">Current Run</p>
                <CardTitle className="mt-3 text-2xl">当前待执行计划</CardTitle>
                {agentProfileId && (
                  <p className="mt-3 text-sm leading-6 text-[rgb(var(--ink-800))]">
                    当前项目 profile：<span className="font-medium text-[rgb(var(--ink-900))]">{agentProfileId}</span>
                  </p>
                )}
              </div>
              {currentRun && <span className={getRunStatusMeta(currentRun.status).className}>{getRunStatusMeta(currentRun.status).label}</span>}
            </div>
            <CardDescription>
              {currentRun?.summary || "当前没有待确认计划。发送一条明确指令，Agent 会生成可执行步骤。"}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto overscroll-contain pr-1">
            {currentRun ? (
              <>
                {currentRun.warning_message && (
                  <div className="rounded-[1.2rem] bg-[rgba(var(--amber),0.08)] px-4 py-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                    {currentRun.warning_message}
                  </div>
                )}
                {currentRun.verification_summary && (
                  <div className="rounded-[1.2rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                    校验状态：{currentRun.verification_summary}
                  </div>
                )}
                {currentRun.error_message && (
                  <div className="rounded-[1.2rem] bg-[rgba(var(--danger),0.08)] px-4 py-3 text-sm leading-7 text-[rgb(var(--danger))]">
                    {currentRun.error_message}
                  </div>
                )}
                {currentRun.risk_summary && <RiskSummaryCard riskSummary={currentRun.risk_summary} />}
                <div className="rounded-[1.15rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-strong)] px-4 py-4 shadow-sm">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                        Outline Focus
                      </div>
                      <div className="mt-1 text-base font-medium text-[rgb(var(--ink-950))]">本次计划聚焦层级</div>
                    </div>
                    <p className="max-w-xs text-xs leading-6 text-[rgb(var(--ink-800))]">
                      只展示会直接影响这次写入的上下文，辅助你快速判断计划是否对准对象。
                    </p>
                  </div>
                  <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] px-4 py-3">
                      <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-800))]">项目大纲</div>
                      <p className="mt-2 line-clamp-4 text-sm leading-6 text-[rgb(var(--ink-900))]">
                        {excerpt(projectOutlinePreview, "当前项目还没有完整项目大纲。", 120)}
                      </p>
                    </div>
                    <div className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] px-4 py-3">
                      <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-800))]">卷细纲</div>
                      <p className="mt-2 text-sm font-medium text-[rgb(var(--ink-950))]">
                        {focusedVolume?.title || "未锁定具体卷"}
                      </p>
                      <CompactMetaLine
                        className="mt-1"
                        items={[
                          { label: "卷标识", value: focusedVolume?.badge },
                          { label: "关联章纲", value: relatedChapters.length > 0 ? `${relatedChapters.length} 个` : null },
                        ]}
                      />
                      <p className="mt-2 line-clamp-4 text-sm leading-6 text-[rgb(var(--ink-900))]">
                        {excerpt(focusedVolume?.outline, "本次运行暂时没有卷级焦点。", 110)}
                      </p>
                    </div>
                    <div className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] px-4 py-3 md:col-span-2">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-800))]">相关章纲</div>
                        {relatedChapters.length > relatedChapterPreviews.length && (
                          <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-700))]">
                            另有 {relatedChapters.length - relatedChapterPreviews.length} 个关联章纲
                          </div>
                        )}
                      </div>
                      {relatedChapters.length > 0 ? (
                        <div className="mt-3 space-y-2">
                          {relatedChapterPreviews.map((chapter) => (
                            <div key={chapter.id} className="rounded-[0.9rem] bg-[rgba(var(--ink-950),0.05)] px-3 py-3">
                              <div className="text-sm font-medium text-[rgb(var(--ink-950))]">
                                第 {chapter.chapter_number} 章 {chapter.title || "无标题"}
                              </div>
                              <p className="mt-2 line-clamp-2 text-sm leading-6 text-[rgb(var(--ink-900))]">
                                {excerpt(chapter.outline, "尚未填写章纲。", 92)}
                              </p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-900))]">
                          当前运行还没有锁定具体章纲。
                        </p>
                      )}
                    </div>
                  </div>
                </div>
                <div className="space-y-3">
                  {currentRun.operations.map((operation) => (
                    <OperationCard key={operation.id} operation={operation} />
                  ))}
                </div>
                {hasRunDiagnostics && (
                  <DisclosureSection
                    kicker="Run Diagnostics"
                    title="运行上下文与诊断"
                    description="保留 planner window、权限矩阵和 hook trace 等系统级细节，默认收起以降低干扰。"
                  >
                    <div className="space-y-4">
                      {(currentRun.planner_window || currentRun.compact_policy || currentRun.retained_window || currentRun.active_bundle_contract) && (
                        <div className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] px-4 py-4">
                          <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-800))]">
                            Planner Window
                          </div>
                          <div className="mt-1 text-sm font-medium text-[rgb(var(--ink-950))]">当前规划输入窗口</div>
                          <CompactMetaGrid
                            className="mt-3"
                            items={[
                              { label: "历史模式", value: currentRun.planner_window?.history_mode },
                              { label: "历史消息", value: currentRun.planner_window?.history_message_count },
                              { label: "保留消息", value: currentRun.planner_window?.retained_message_limit },
                              {
                                label: "Checkpoint",
                                value: currentRun.planner_window?.checkpoint_id ? "已附带" : currentRun.planner_window ? "未附带" : null,
                              },
                              { label: "策略版本", value: currentRun.compact_policy?.policy_version },
                              {
                                label: "保留窗口",
                                value:
                                  currentRun.retained_window
                                    ? `${currentRun.retained_window.message_count} 条 / ${currentRun.retained_window.character_count} 字`
                                    : null,
                              },
                              { label: "Bundle 来源", value: currentRun.active_bundle_contract?.source },
                              {
                                label: "聚焦对象",
                                value:
                                  currentRun.active_bundle_contract?.focused_object_types.length
                                    ? currentRun.active_bundle_contract.focused_object_types.join(" / ")
                                    : null,
                              },
                            ]}
                          />
                          <CompactMetaLine
                            className="mt-3"
                            items={[
                              {
                                label: "Bundle 收录",
                                value:
                                  currentRun.active_bundle_contract
                                    ? `人物 ${currentRun.active_bundle_contract.collections.characters_count}/${currentRun.active_bundle_contract.collections.characters_limit} · 卷 ${currentRun.active_bundle_contract.collections.volumes_count}/${currentRun.active_bundle_contract.collections.volumes_limit} · 章 ${currentRun.active_bundle_contract.collections.chapters_count}/${currentRun.active_bundle_contract.collections.chapters_limit}`
                                    : null,
                              },
                              {
                                label: "保留角色",
                                value:
                                  currentRun.retained_window?.roles.length
                                    ? currentRun.retained_window.roles.join(" / ")
                                    : null,
                              },
                            ]}
                          />
                        </div>
                      )}
                      {currentRun.subtasks.length > 0 && (
                        <div className="space-y-3">
                          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                            Internal Subtasks
                          </div>
                          {currentRun.subtasks.map((subtask) => (
                            <SubtaskCard key={subtask.id} subtask={subtask} />
                          ))}
                        </div>
                      )}
                      {permissionMatrix.length > 0 && (
                        <div className="space-y-3">
                          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                            Permission Matrix
                          </div>
                          {permissionMatrix.map((phase: AgentExecutionContractPhase) => {
                            const phaseName = phase.phase;
                            const mode = phase.mode;
                            const levels = phase.allowed_permission_levels;
                            const tools = phase.tool_scope;
                            return (
                              <div
                                key={phaseName}
                                className="rounded-[1.1rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] px-4 py-3"
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <div className="text-sm font-medium text-[rgb(var(--ink-900))]">
                                    {phaseName.toUpperCase()} / {mode}
                                  </div>
                                  <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-800))]">
                                    {`${phase.operation_count} ops / gate:${phase.confirmation_gate} / registry:${currentRun.execution_contract?.registry_version ?? "n/a"}`}
                                  </div>
                                </div>
                                <CompactMetaLine
                                  className="mt-3"
                                  items={[
                                    { label: "权限级别", value: levels.length > 0 ? levels.join(" / ") : null },
                                    { label: "工具范围", value: tools.length > 0 ? Array.from(new Set(tools.slice(0, 5))).join(" / ") : null },
                                  ]}
                                />
                                {phase.child_units.length > 0 && (
                                  <div className="mt-3 space-y-3">
                                    {phase.child_units.map((childUnit: AgentExecutionChildUnit) => (
                                      <ChildUnitCard key={childUnit.unit_id} childUnit={childUnit} />
                                    ))}
                                  </div>
                                )}
                                {phase.capabilities.length > 0 && (
                                  <div className="mt-3 space-y-3">
                                    {phase.capabilities.map((capability) => (
                                      <div
                                        key={capability.capability_id}
                                        className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[rgba(var(--ink-950),0.03)] px-3 py-3"
                                      >
                                        <div className="flex items-center justify-between gap-3">
                                          <div className="text-sm font-medium text-[rgb(var(--ink-900))]">
                                            {capability.name}
                                          </div>
                                          <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-800))]">
                                            {capability.execution_record
                                              ? `${capability.execution_record.status} / ${capability.execution_record.source_role}`
                                              : capability.kind}
                                          </div>
                                        </div>
                                        <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-800))]">
                                          {capability.description}
                                        </p>
                                        <CompactMetaLine
                                          className="mt-2"
                                          items={[
                                            {
                                              label: "策略",
                                              value: `${capability.policy.execution_phase}/${capability.policy.source_role}`,
                                            },
                                            { label: "确认门槛", value: capability.policy.confirmation_gate },
                                            { label: "能力 ID", value: capability.capability_id },
                                            {
                                              label: "尝试次数",
                                              value: capability.execution_record?.attempt_count ?? null,
                                            },
                                          ]}
                                        />
                                        {capability.execution_record?.output_summary && (
                                          <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-800))]">
                                            {capability.execution_record.output_summary}
                                          </p>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                      {hookTrace.length > 0 && (
                        <div className="space-y-3">
                          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                            Hook Trace
                          </div>
                          {hookTrace.map((entry) => {
                            const meta = VERIFICATION_META[
                              entry.status === "completed"
                                ? "passed"
                                : entry.status === "failed"
                                  ? "failed"
                                  : entry.status === "skipped"
                                    ? "skipped"
                                    : "pending"
                            ];
                            return (
                              <div
                                key={entry.hook_name}
                                className="rounded-[1.1rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] px-4 py-3"
                              >
                                <div className="flex items-center justify-between gap-3">
                                  <div className="text-sm font-medium text-[rgb(var(--ink-900))]">{entry.hook_name}</div>
                                  <span className={meta.className}>{meta.label}</span>
                                </div>
                                {entry.summary && (
                                  <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-800))]">{entry.summary}</p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </DisclosureSection>
                )}
                {currentRun.status === "awaiting_confirmation" && (
                  <div className="flex gap-3 pt-2">
                    <Button onClick={() => handleRunAction("confirm")} disabled={isPending} testId="confirm-run-btn">
                      确认执行
                    </Button>
                    <Button variant="outline" onClick={() => handleRunAction("cancel")} disabled={isPending} testId="cancel-run-btn">
                      取消计划
                    </Button>
                  </div>
                )}
                {currentRun.status === "awaiting_high_risk_confirmation" && (
                  <div className="space-y-3 pt-2">
                    <div className="rounded-[1.2rem] bg-[rgba(var(--danger),0.08)] px-4 py-3 text-sm leading-7 text-[rgb(var(--danger))]">
                      当前计划包含高风险正文覆盖。请复核预览 diff 后再次确认。
                    </div>
                    <div className="flex gap-3">
                      <Button onClick={() => handleRunAction("confirm_high_risk")} disabled={isPending} testId="confirm-high-risk-btn">
                        二次确认并执行
                      </Button>
                      <Button variant="outline" onClick={() => handleRunAction("cancel")} disabled={isPending} testId="cancel-run-btn">
                        取消计划
                      </Button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="rounded-[1.3rem] border border-dashed border-[rgba(var(--line),0.18)] px-5 py-8 text-sm leading-7 text-[rgb(var(--ink-800))]">
                暂无计划。先给 Agent 一个明确目标，再回来确认执行。
              </div>
            )}
          </CardContent>
        </Card>

        <div className={`grid min-h-0 gap-6 ${latestCheckpoint ? "sm:grid-cols-2 lg:grid-cols-1 2xl:grid-cols-2" : "grid-cols-1"}`}>
          {latestCheckpoint && (
            <Card className="flex h-full min-h-0 flex-col overflow-hidden">
              <CardHeader className="border-b border-[rgba(var(--line),0.12)] pb-4">
                <p className="ink-kicker">Context Checkpoint</p>
                <CardTitle className="mt-3 text-xl">最新线程压缩摘要</CardTitle>
                <CardDescription>
                  长线程达到阈值后，系统会生成 checkpoint，后续 planning 会优先参考这里的摘要与对象上下文。
                </CardDescription>
              </CardHeader>
              <CardContent className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto overscroll-contain pr-1">
                <div className="rounded-[1.1rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] px-4 py-4">
                  <div className="mb-2 text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-800))]">Summary</div>
                  <p className="text-sm leading-7 text-[rgb(var(--ink-800))]">{latestCheckpoint.thread_summary}</p>
                </div>
                <CompactMetaGrid
                  items={[
                    { label: "Profile", value: latestCheckpoint.profile_id, tone: "accent" },
                    { label: "Messages", value: latestCheckpoint.source_message_count },
                    { label: "Runs", value: latestCheckpoint.source_run_count },
                  ]}
                />
                {latestCheckpoint.active_bundle_contract?.focused_object_types.length ? (
                  <p className="text-sm leading-7 text-[rgb(var(--ink-800))]">
                    压缩时的聚焦对象：{latestCheckpoint.active_bundle_contract.focused_object_types.join(" / ")}
                  </p>
                ) : null}
                {(latestCheckpoint.compact_policy || latestCheckpoint.compaction_boundary || latestCheckpoint.active_bundle_contract) && (
                  <DisclosureSection
                    kicker="Checkpoint Policy"
                    title="压缩策略与上下文收录"
                    description="常用摘要默认前置展示，细节折叠在这里。"
                  >
                    <CompactMetaGrid
                      items={[
                        { label: "策略版本", value: latestCheckpoint.compact_policy?.policy_version },
                        { label: "Recent Window", value: latestCheckpoint.compact_policy?.recent_window_limit },
                        { label: "Checkpoint Delta", value: latestCheckpoint.compact_policy?.checkpoint_delta_limit },
                        { label: "Boundary", value: latestCheckpoint.compaction_boundary?.history_mode },
                        { label: "Bundle 来源", value: latestCheckpoint.active_bundle_contract?.source },
                        {
                          label: "Digest",
                          value:
                            latestCheckpoint.active_bundle_contract
                              ? `${latestCheckpoint.active_bundle_contract.collections.recent_run_digest_count}/${latestCheckpoint.active_bundle_contract.collections.recent_run_digest_limit}`
                              : null,
                        },
                      ]}
                    />
                  </DisclosureSection>
                )}
                <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-800))]">
                  生成时间：{formatTimestamp(latestCheckpoint.created_at)}
                </div>
              </CardContent>
            </Card>
          )}

          <Card className="flex h-full min-h-0 flex-col overflow-hidden">
            <CardHeader className="border-b border-[rgba(var(--line),0.12)] pb-4">
              <p className="ink-kicker">Recent Runs</p>
              <CardTitle className="mt-3 text-xl">最近执行记录</CardTitle>
              <CardDescription>
                这里保留最近生成和执行过的计划，便于回看状态变化。
              </CardDescription>
            </CardHeader>
            <CardContent className="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain pr-1">
              {recentRuns.length === 0 ? (
                <div className="rounded-[1.2rem] border border-dashed border-[rgba(var(--line),0.18)] px-4 py-6 text-sm text-[rgb(var(--ink-800))]">
                  还没有任何执行记录。
                </div>
              ) : (
                recentRuns.map((run) => {
                  const meta = getRunStatusMeta(run.status);
                  return (
                    <div
                      key={run.id}
                      className="rounded-[1.1rem] border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] px-4 py-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="text-sm font-medium leading-6 text-[rgb(var(--ink-900))]">
                          {run.summary || "未命名计划"}
                        </div>
                        <span className={meta.className}>{meta.label}</span>
                      </div>
                      <div className="mt-2 text-xs tracking-[0.12em] text-[rgb(var(--ink-800))]">
                        {formatTimestamp(run.updated_at)}
                      </div>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
