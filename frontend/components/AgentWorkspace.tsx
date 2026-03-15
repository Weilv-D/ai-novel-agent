"use client";

import { useEffect, useState, useTransition } from "react";

import { agentWorkflowApi, ApiError } from "@/lib/api-client";
import type { AgentOperation, AgentRun, AgentThread, AgentThreadMessage } from "@/lib/types";
import { getRunStatusMeta } from "@/lib/presentation";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import { Textarea } from "@/components/ui/Input";
import { DiffPreview } from "@/components/DiffPreview";

interface AgentWorkspaceProps {
  projectId: string;
  projectName: string;
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

function OperationCard({ operation }: { operation: AgentOperation }) {
  const toolLabel = TOOL_LABELS[operation.tool_name] || operation.tool_name;
  const preview = operation.preview;
  return (
    <div className="rounded-[1.4rem] border border-[rgba(var(--line),0.14)] bg-[rgba(255,255,255,0.58)] p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-600))]">
            Step {operation.position}
          </div>
          <div className="mt-1 text-base font-medium text-[rgb(var(--ink-950))]">{toolLabel}</div>
        </div>
        {operation.target_display && (
          <span className="rounded-full border border-[rgba(var(--line),0.18)] px-3 py-1 text-xs text-[rgb(var(--ink-700))]">
            {operation.target_display}
          </span>
        )}
      </div>
      <p className="text-sm leading-7 text-[rgb(var(--ink-800))]">{operation.description}</p>
      {operation.reason && (
        <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-600))]">原因：{operation.reason}</p>
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
      {operation.error_message && (
        <p className="mt-3 text-sm text-[rgb(var(--danger))]">{operation.error_message}</p>
      )}
    </div>
  );
}

export function AgentWorkspace({
  projectId,
  projectName,
  className = "",
  onProjectRefresh,
}: AgentWorkspaceProps) {
  const [thread, setThread] = useState<AgentThread | null>(null);
  const [messages, setMessages] = useState<AgentThreadMessage[]>([]);
  const [recentRuns, setRecentRuns] = useState<AgentRun[]>([]);
  const [currentRun, setCurrentRun] = useState<AgentRun | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

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

  async function handleRunAction(action: "confirm" | "cancel") {
    if (!currentRun || isPending) {
      return;
    }
    setError(null);
    startTransition(async () => {
      try {
        if (action === "confirm") {
          await agentWorkflowApi.confirmRun(currentRun.id);
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
            />
            <div className="mt-4 flex items-center justify-between gap-3">
              <p className="text-sm text-[rgb(var(--ink-600))]">
                Agent 会先生成完整计划和预览，确认后才真正写入数据。
              </p>
              <Button onClick={handleSend} disabled={!input.trim() || isPending}>
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
                {currentRun.error_message && (
                  <div className="rounded-[1.2rem] bg-[rgba(var(--danger),0.08)] px-4 py-3 text-sm leading-7 text-[rgb(var(--danger))]">
                    {currentRun.error_message}
                  </div>
                )}
                <div className="space-y-3">
                  {currentRun.operations.map((operation) => (
                    <OperationCard key={operation.id} operation={operation} />
                  ))}
                </div>
                {currentRun.status === "awaiting_confirmation" && (
                  <div className="flex gap-3 pt-2">
                    <Button onClick={() => handleRunAction("confirm")} disabled={isPending}>
                      确认执行
                    </Button>
                    <Button variant="outline" onClick={() => handleRunAction("cancel")} disabled={isPending}>
                      取消计划
                    </Button>
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
