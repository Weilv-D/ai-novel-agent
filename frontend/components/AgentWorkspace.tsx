"use client";

import { useEffect, useState, useTransition } from "react";

import { agentWorkflowApi, ApiError } from "@/lib/api-client";
import type {
  AgentExecutionChildUnit,
  AgentAppliedRiskPolicy,
  AgentExecutionContractPhase,
  AgentHookTraceEntry,
  AgentOperation,
  AgentRun,
  AgentRunRiskSummary,
  AgentSubtask,
  AgentThread,
  AgentThreadCheckpoint,
  AgentThreadMessage,
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
  create_character: "创建人物",
  update_character: "修改人物",
  create_world_setting: "创建设定",
  update_world_setting: "修改设定",
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

function MessageBubble({ message }: { message: AgentThreadMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-[1.25rem] px-4 py-3 text-sm leading-7 shadow-sm ${
          isUser
            ? "bg-[rgba(var(--ink-950),0.95)] text-[rgb(var(--paper-soft))]"
            : "border border-[rgba(var(--line),0.16)] bg-[rgba(255,255,255,0.62)] text-[rgb(var(--ink-900))]"
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
    <div className="rounded-[1.1rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.46)] px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-600))]">{subtask.role}</div>
          <div className="mt-1 text-sm font-medium text-[rgb(var(--ink-900))]">{subtask.title}</div>
        </div>
        <span className={verificationMeta.className}>{verificationMeta.label}</span>
      </div>
      {subtask.summary && (
        <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-700))]">{subtask.summary}</p>
      )}
      {(source || validationStatus || attemptCount !== null || retryStrategy) && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
          {source && (
            <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
              source:{source}
            </span>
          )}
          {validationStatus && (
            <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
              validation:{validationStatus}
            </span>
          )}
          {attemptCount !== null && (
            <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
              attempts:{attemptCount}/{maxAttempts ?? attemptCount}
            </span>
          )}
          {retryStrategy && (
            <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
              strategy:{retryStrategy}
            </span>
          )}
        </div>
      )}
      {dependencyList.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
          {dependencyList.map((dependency) => (
            <span key={dependency} className="rounded-full border border-[rgba(var(--line),0.14)] px-3 py-1">
              depends:{dependency}
            </span>
          ))}
        </div>
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
    <div className="rounded-[1.4rem] border border-[rgba(var(--line),0.14)] bg-[rgba(255,255,255,0.58)] p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-600))]">
            Step {operation.position}
          </div>
          <div className="mt-1 text-base font-medium text-[rgb(var(--ink-950))]">{toolLabel}</div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <span className={riskMeta.className}>{riskMeta.label}</span>
          <span className={verificationMeta.className}>{verificationMeta.label}</span>
          {operation.target_display && (
            <span className="rounded-full border border-[rgba(var(--line),0.18)] px-3 py-1 text-xs text-[rgb(var(--ink-700))]">
              {operation.target_display}
            </span>
          )}
        </div>
      </div>
      <p className="text-sm leading-7 text-[rgb(var(--ink-800))]">{operation.description}</p>
      {operation.reason && (
        <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-600))]">原因：{operation.reason}</p>
      )}
      {operation.requires_secondary_confirmation && (
        <p className="mt-2 text-sm leading-7 text-[rgb(var(--danger))]">此步骤会触发二次确认，适用于高风险正文覆盖。</p>
      )}
      {preview.changed_fields.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {preview.changed_fields.map((field) => (
            <span
              key={field}
              className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1 text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]"
            >
              {field}
            </span>
          ))}
        </div>
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
        <p className="mt-3 text-sm leading-7 text-[rgb(var(--ink-600))]">校验：{operation.verification_summary}</p>
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
    <div className="rounded-[1.2rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.48)] px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-600))]">Run Risk</div>
          <div className="mt-1 text-base font-medium text-[rgb(var(--ink-950))]">执行风险摘要</div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className={riskMeta.className}>{riskMeta.label}</span>
          <span className="rounded-full border border-[rgba(var(--line),0.16)] px-3 py-1 text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
            gate:{riskSummary.confirmation_gate}
          </span>
          <span className="rounded-full border border-[rgba(var(--line),0.16)] px-3 py-1 text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
            policy:{riskSummary.policy_version}
          </span>
        </div>
      </div>
      <p className="mt-3 text-sm leading-7 text-[rgb(var(--ink-800))]">{riskSummary.summary}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
        <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
          total:{riskSummary.total_operations}
        </span>
        <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
          low:{riskSummary.low_risk_operation_count}
        </span>
        <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
          medium:{riskSummary.medium_risk_operation_count}
        </span>
        <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
          high:{riskSummary.high_risk_operation_count}
        </span>
      </div>
      {riskSummary.applied_policies.length > 0 && (
        <div className="mt-3 space-y-2">
          {riskSummary.applied_policies.map((policy: AgentAppliedRiskPolicy) => (
            <div
              key={`${policy.policy_id}-${policy.matched_operation_positions.join("-")}`}
              className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[rgba(var(--ink-950),0.03)] px-3 py-3"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-[rgb(var(--ink-900))]">{policy.name}</div>
                <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-600))]">
                  {policy.scope} / {policy.risk_level} / gate:{policy.confirmation_gate}
                </div>
              </div>
              <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-700))]">{policy.description}</p>
              {policy.matched_operation_positions.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
                  <span className="rounded-full border border-[rgba(var(--line),0.14)] px-3 py-1">
                    steps:{policy.matched_operation_positions.join(", ")}
                  </span>
                  {policy.requires_secondary_confirmation && (
                    <span className="rounded-full bg-[rgba(var(--danger),0.08)] px-3 py-1 text-[rgb(var(--danger))]">
                      二次确认
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      {(riskSummary.high_risk_operation_positions.length > 0 ||
        riskSummary.secondary_confirmation_operation_positions.length > 0) && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
          {riskSummary.high_risk_operation_positions.length > 0 && (
            <span className="rounded-full bg-[rgba(var(--danger),0.08)] px-3 py-1 text-[rgb(var(--danger))]">
              高风险步骤:{riskSummary.high_risk_operation_positions.join(", ")}
            </span>
          )}
          {riskSummary.secondary_confirmation_operation_positions.length > 0 && (
            <span className="rounded-full bg-[rgba(var(--amber),0.12)] px-3 py-1">
              二次确认步骤:{riskSummary.secondary_confirmation_operation_positions.join(", ")}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function ChildUnitCard({ childUnit }: { childUnit: AgentExecutionChildUnit }) {
  return (
    <div className="rounded-[1rem] border border-[rgba(var(--line),0.12)] bg-[rgba(var(--ink-950),0.03)] px-3 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-medium text-[rgb(var(--ink-900))]">{childUnit.title}</div>
        <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-600))]">
          {childUnit.role} / {childUnit.stage}
        </div>
      </div>
      <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-700))]">{childUnit.description}</p>
      <div className="mt-2 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
        <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
          gate:{childUnit.confirmation_gate}
        </span>
        <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
          mode:{childUnit.mode}
        </span>
        {childUnit.requires_confirmation && (
          <span className="rounded-full bg-[rgba(var(--amber),0.12)] px-3 py-1">requires-confirmation</span>
        )}
      </div>
      {(childUnit.depends_on.length > 0 || childUnit.operation_positions.length > 0) && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
          {childUnit.depends_on.map((dependency) => (
            <span key={dependency} className="rounded-full border border-[rgba(var(--line),0.14)] px-3 py-1">
              depends:{dependency}
            </span>
          ))}
          {childUnit.operation_positions.length > 0 && (
            <span className="rounded-full border border-[rgba(var(--line),0.14)] px-3 py-1">
              steps:{childUnit.operation_positions.join(", ")}
            </span>
          )}
        </div>
      )}
      {(childUnit.capability_ids.length > 0 || childUnit.tool_scope.length > 0) && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
          {childUnit.capability_ids.map((capabilityId) => (
            <span key={capabilityId} className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
              capability:{capabilityId}
            </span>
          ))}
          {childUnit.tool_scope.slice(0, 4).map((tool) => (
            <span key={tool} className="rounded-full border border-[rgba(var(--line),0.14)] px-3 py-1">
              {tool}
            </span>
          ))}
        </div>
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
  const [thread, setThread] = useState<AgentThread | null>(null);
  const [messages, setMessages] = useState<AgentThreadMessage[]>([]);
  const [recentRuns, setRecentRuns] = useState<AgentRun[]>([]);
  const [currentRun, setCurrentRun] = useState<AgentRun | null>(null);
  const [latestCheckpoint, setLatestCheckpoint] = useState<AgentThreadCheckpoint | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const hookTrace = getHookTrace(currentRun);
  const permissionMatrix = currentRun?.execution_contract?.phases || [];

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
    // projectId change means a different workspace.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function refreshAfterMutation() {
    if (thread?.id) {
      await loadThreadState(thread.id);
    }
    if (onProjectRefresh) {
      await onProjectRefresh();
    }
  }

  async function handleSend() {
    const content = input.trim();
    if (!thread?.id || !content || isPending) {
      return;
    }
    setError(null);
    setInput("");
    startTransition(async () => {
      try {
        const response = await agentWorkflowApi.sendMessage(thread.id, {
          content,
          context: {},
        });
        setMessages((prev) => [...prev, response.user_message, response.assistant_message]);
        if (response.run) {
          setCurrentRun(response.run);
          setRecentRuns((prev) => [response.run!, ...prev.filter((run) => run.id !== response.run!.id)].slice(0, 8));
        }
      } catch (err) {
        const message = err instanceof ApiError ? err.detail : "发送指令失败";
        setError(message);
      }
    });
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
    <div className={`grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)] ${className}`}>
      <Card className="overflow-hidden">
        <CardHeader className="border-b border-[rgba(var(--line),0.12)] pb-4">
          <p className="ink-kicker">Agent Workspace</p>
          <CardTitle className="mt-3 text-3xl">以自然语言驱动 {projectName}</CardTitle>
          <CardDescription>
            直接说出你的目标，例如“创建一个冷静克制的女主角”“把第三章改成雨夜追逐”“新增一个宗教设定并补进世界观”。
          </CardDescription>
        </CardHeader>
        <CardContent className="flex min-h-[780px] flex-col gap-4 pt-6">
          <div className="flex-1 space-y-4 overflow-y-auto pr-1">
            {messages.length === 0 ? (
              <div className="rounded-[1.4rem] border border-dashed border-[rgba(var(--line),0.18)] bg-[rgba(255,255,255,0.38)] px-6 py-12 text-center text-sm leading-7 text-[rgb(var(--ink-600))]">
                还没有对话。先告诉 Agent 你要修改什么，或者直接给出写作任务。
              </div>
            ) : (
              messages.map((message) => <MessageBubble key={message.id} message={message} />)
            )}
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
              <p className="text-sm text-[rgb(var(--ink-600))]">
                Agent 会先生成完整计划和预览，确认后才真正写入数据。
              </p>
              <Button onClick={handleSend} disabled={!input.trim() || isPending} testId="agent-send-btn">
                {isPending ? "处理中..." : "生成计划"}
              </Button>
            </div>
            {error && <p className="mt-3 text-sm text-[rgb(var(--danger))]">{error}</p>}
          </div>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="ink-kicker">Current Run</p>
                <CardTitle className="mt-3 text-2xl">当前待执行计划</CardTitle>
                {agentProfileId && (
                  <p className="mt-3 text-sm leading-6 text-[rgb(var(--ink-600))]">
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
          <CardContent className="space-y-4">
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
                {(currentRun.planner_window || currentRun.compact_policy || currentRun.retained_window || currentRun.active_bundle_contract) && (
                  <div className="rounded-[1.2rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.48)] px-4 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-600))]">
                          Planner Window
                        </div>
                        <div className="mt-1 text-base font-medium text-[rgb(var(--ink-950))]">当前规划输入窗口</div>
                      </div>
                      {currentRun.planner_window && (
                        <span className="rounded-full border border-[rgba(var(--line),0.16)] px-3 py-1 text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
                          mode:{currentRun.planner_window.history_mode}
                        </span>
                      )}
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
                      {currentRun.planner_window && (
                        <>
                          <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                            history:{currentRun.planner_window.history_message_count}
                          </span>
                          <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                            retained:{currentRun.planner_window.retained_message_limit}
                          </span>
                          {currentRun.planner_window.checkpoint_id && (
                            <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                              checkpoint:attached
                            </span>
                          )}
                        </>
                      )}
                      {currentRun.compact_policy && (
                        <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                          policy:{currentRun.compact_policy.policy_version}
                        </span>
                      )}
                      {currentRun.retained_window && (
                        <>
                          <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                            retained-msgs:{currentRun.retained_window.message_count}
                          </span>
                          <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                            retained-chars:{currentRun.retained_window.character_count}
                          </span>
                          {currentRun.retained_window.roles.length > 0 && (
                            <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                              roles:{currentRun.retained_window.roles.join("/")}
                            </span>
                          )}
                        </>
                      )}
                      {currentRun.active_bundle_contract && (
                        <>
                          <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                            bundle:{currentRun.active_bundle_contract.source}
                          </span>
                          <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                            sections:{currentRun.active_bundle_contract.included_sections.length}
                          </span>
                          <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                            chars:{currentRun.active_bundle_contract.collections.characters_count}/{currentRun.active_bundle_contract.collections.characters_limit}
                          </span>
                          <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                            chapters:{currentRun.active_bundle_contract.collections.chapters_count}/{currentRun.active_bundle_contract.collections.chapters_limit}
                          </span>
                        </>
                      )}
                    </div>
                    {currentRun.active_bundle_contract?.focused_object_types.length ? (
                      <div className="mt-3 text-sm leading-7 text-[rgb(var(--ink-700))]">
                        当前聚焦对象：{currentRun.active_bundle_contract.focused_object_types.join(" / ")}
                      </div>
                    ) : null}
                  </div>
                )}
                {currentRun.subtasks.length > 0 && (
                  <div className="space-y-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-600))]">
                      Internal Subtasks
                    </div>
                    {currentRun.subtasks.map((subtask) => (
                      <SubtaskCard key={subtask.id} subtask={subtask} />
                    ))}
                  </div>
                )}
                {permissionMatrix.length > 0 && (
                  <div className="space-y-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-600))]">
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
                          className="rounded-[1.1rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.44)] px-4 py-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="text-sm font-medium text-[rgb(var(--ink-900))]">
                              {phaseName.toUpperCase()} / {mode}
                            </div>
                            <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-600))]">
                              {`${phase.operation_count} ops / gate:${phase.confirmation_gate} / registry:${currentRun.execution_contract?.registry_version ?? "n/a"}`}
                            </div>
                          </div>
                          {levels.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
                              {levels.map((level) => (
                                <span key={level} className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                                  level:{level}
                                </span>
                              ))}
                            </div>
                          )}
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
                                    <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-600))]">
                                      {capability.execution_record
                                        ? `${capability.execution_record.status} / ${capability.execution_record.source_role}`
                                        : capability.kind}
                                    </div>
                                  </div>
                                  <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-700))]">
                                    {capability.description}
                                  </p>
                                  <div className="mt-2 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
                                    <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                                      policy:{capability.policy.execution_phase}/{capability.policy.source_role}
                                    </span>
                                    <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                                      gate:{capability.policy.confirmation_gate}
                                    </span>
                                  </div>
                                  {capability.execution_record?.output_summary && (
                                    <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-600))]">
                                      {capability.execution_record.output_summary}
                                    </p>
                                  )}
                                  <div className="mt-3 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
                                    <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                                      capability:{capability.capability_id}
                                    </span>
                                    {capability.execution_record && (
                                      <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                                        attempts:{capability.execution_record.attempt_count}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                          {tools.length > 0 && (
                            <div className="mt-3 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
                              {tools.slice(0, 5).map((tool) => (
                                <span key={tool} className="rounded-full border border-[rgba(var(--line),0.14)] px-3 py-1">
                                  {tool}
                                </span>
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
                    <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-600))]">
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
                          className="rounded-[1.1rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.44)] px-4 py-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="text-sm font-medium text-[rgb(var(--ink-900))]">{entry.hook_name}</div>
                            <span className={meta.className}>{meta.label}</span>
                          </div>
                          {entry.summary && (
                            <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-700))]">{entry.summary}</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
                <div className="space-y-3">
                  {currentRun.operations.map((operation) => (
                    <OperationCard key={operation.id} operation={operation} />
                  ))}
                </div>
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
              <div className="rounded-[1.3rem] border border-dashed border-[rgba(var(--line),0.18)] px-5 py-8 text-sm leading-7 text-[rgb(var(--ink-600))]">
                暂无计划。先给 Agent 一个明确目标，再回来确认执行。
              </div>
            )}
          </CardContent>
        </Card>

        {latestCheckpoint && (
          <Card>
            <CardHeader>
              <p className="ink-kicker">Context Checkpoint</p>
              <CardTitle className="mt-3 text-2xl">最新线程压缩摘要</CardTitle>
              <CardDescription>
                长线程达到阈值后，系统会生成 checkpoint，后续 planning 会优先参考这里的摘要与对象上下文。
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                  <div className="text-xs uppercase tracking-[0.14em] text-[rgb(var(--ink-600))]">Profile</div>
                  <div className="mt-2 text-sm font-medium text-[rgb(var(--ink-950))]">{latestCheckpoint.profile_id}</div>
                </div>
                <div className="rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                  <div className="text-xs uppercase tracking-[0.14em] text-[rgb(var(--ink-600))]">Messages</div>
                  <div className="mt-2 text-sm font-medium text-[rgb(var(--ink-950))]">{latestCheckpoint.source_message_count}</div>
                </div>
                <div className="rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3">
                  <div className="text-xs uppercase tracking-[0.14em] text-[rgb(var(--ink-600))]">Runs</div>
                  <div className="mt-2 text-sm font-medium text-[rgb(var(--ink-950))]">{latestCheckpoint.source_run_count}</div>
                </div>
              </div>
              {(latestCheckpoint.compact_policy || latestCheckpoint.compaction_boundary || latestCheckpoint.active_bundle_contract) && (
                <div className="flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-600))]">
                  {latestCheckpoint.compact_policy && (
                    <>
                      <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                        policy:{latestCheckpoint.compact_policy.policy_version}
                      </span>
                      <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                        recent:{latestCheckpoint.compact_policy.recent_window_limit}
                      </span>
                      <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                        delta:{latestCheckpoint.compact_policy.checkpoint_delta_limit}
                      </span>
                    </>
                  )}
                  {latestCheckpoint.compaction_boundary && (
                    <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                      boundary:{latestCheckpoint.compaction_boundary.history_mode}
                    </span>
                  )}
                  {latestCheckpoint.active_bundle_contract && (
                    <>
                      <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                        bundle:{latestCheckpoint.active_bundle_contract.source}
                      </span>
                      <span className="rounded-full bg-[rgba(var(--ink-950),0.06)] px-3 py-1">
                        digest:{latestCheckpoint.active_bundle_contract.collections.recent_run_digest_count}/
                        {latestCheckpoint.active_bundle_contract.collections.recent_run_digest_limit}
                      </span>
                    </>
                  )}
                </div>
              )}
              {latestCheckpoint.active_bundle_contract?.focused_object_types.length ? (
                <div className="text-sm leading-7 text-[rgb(var(--ink-700))]">
                  压缩时的聚焦对象：{latestCheckpoint.active_bundle_contract.focused_object_types.join(" / ")}
                </div>
              ) : null}
              <div className="rounded-[1.1rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.44)] px-4 py-4">
                <div className="mb-2 text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-600))]">Summary</div>
                <p className="text-sm leading-7 text-[rgb(var(--ink-800))]">{latestCheckpoint.thread_summary}</p>
              </div>
              <div className="text-xs tracking-[0.12em] text-[rgb(var(--ink-600))]">
                生成时间：{formatTimestamp(latestCheckpoint.created_at)}
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <p className="ink-kicker">Recent Runs</p>
            <CardTitle className="mt-3 text-2xl">最近执行记录</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {recentRuns.length === 0 ? (
              <div className="rounded-[1.2rem] border border-dashed border-[rgba(var(--line),0.18)] px-4 py-6 text-sm text-[rgb(var(--ink-600))]">
                还没有任何执行记录。
              </div>
            ) : (
              recentRuns.map((run) => {
                const meta = getRunStatusMeta(run.status);
                return (
                  <div
                    key={run.id}
                    className="rounded-[1.2rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.44)] px-4 py-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-medium text-[rgb(var(--ink-900))]">
                        {run.summary || "未命名计划"}
                      </div>
                      <span className={meta.className}>{meta.label}</span>
                    </div>
                    <div className="mt-2 text-xs tracking-[0.12em] text-[rgb(var(--ink-600))]">
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
  );
}
