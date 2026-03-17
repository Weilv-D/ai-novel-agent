"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStore } from "@/lib/stores/chatStore";
import { Button } from "@/components/ui/Button";

interface AgentChatPanelProps {
  projectId: string;
  context?: Record<string, unknown>;
  className?: string;
}

export function AgentChatPanel({ projectId, context, className = "" }: AgentChatPanelProps) {
  const [input, setInput] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { messages, loading, streaming, error, sendMessageStream, clearMessages } = useChatStore();

  // Clear messages when switching to a different project context
  useEffect(() => {
    clearMessages();
  }, [projectId, clearMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const msg = input.trim();
    if (!msg || loading || streaming) return;
    setInput("");
    await sendMessageStream(projectId, msg, context);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        aria-label="Open AI writing assistant"
        className={`fixed bottom-6 right-6 z-50 flex h-16 w-16 items-center justify-center rounded-full border border-[rgba(var(--line),0.18)] bg-[linear-gradient(180deg,rgba(var(--ink-950),0.94),rgba(var(--ink-900),0.94))] text-lg font-semibold tracking-[0.2em] text-[rgb(var(--paper-soft))] shadow-[0_28px_60px_-28px_rgba(var(--shadow),0.82)] transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_32px_72px_-28px_rgba(var(--shadow),0.85)] ${className}`}
      >
        AI
      </button>
    );
  }

  return (
    <div className={`ink-panel fixed bottom-6 right-6 z-50 flex h-[540px] w-[min(26rem,calc(100vw-1.5rem))] flex-col overflow-hidden rounded-[1.75rem] ${className}`}>
      <div className="flex items-center justify-between border-b border-[rgba(var(--line),0.12)] bg-[rgba(var(--ink-950),0.94)] px-4 py-4 text-[rgb(var(--paper-soft))]">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-[rgba(255,255,255,0.78)]">Creative Agent</div>
          <span className="ink-display text-xl font-semibold">AI 写作助手</span>
        </div>
        <div className="flex gap-2">
          <button onClick={clearMessages} aria-label="Clear chat messages" className="text-sm opacity-80 transition-opacity hover:opacity-100">
            清空
          </button>
          <button onClick={() => setIsOpen(false)} aria-label="Collapse chat panel" className="text-sm opacity-80 transition-opacity hover:opacity-100">
            收起
          </button>
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="mt-8 text-center text-sm text-[rgb(var(--ink-800))]">
            <p>你好！我是 AI 写作助手。</p>
            <p className="mt-1">你可以问我关于世界观、人物、大纲、写作等问题。</p>
          </div>
        )}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                msg.role === "user"
                  ? "rounded-br-sm bg-[rgba(var(--ink-950),0.94)] text-[rgb(var(--paper-soft))]"
                  : "rounded-bl-sm border border-[rgba(var(--line),0.12)] bg-[var(--surface-elevated)] text-[rgb(var(--ink-800))]"
              }`}
            >
              {msg.content}
              {msg.role === "assistant" && streaming && msg.id === messages[messages.length - 1]?.id && (
                <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-[rgb(var(--ink-600))]" />
              )}
            </div>
          </div>
        ))}
        {error && (
          <div className="text-center text-sm text-[rgb(var(--danger))]">{error}</div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-[rgba(var(--line),0.12)] p-3">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息..."
            rows={1}
            className="min-h-[46px] flex-1 resize-none rounded-[1rem] border border-[rgba(var(--line),0.18)] bg-[var(--field-surface)] px-4 py-3 text-sm text-[rgb(var(--ink-950))] placeholder:text-[rgb(var(--ink-800))] focus:outline-none focus:ring-4 focus:ring-[rgba(var(--accent),0.08)]"
            disabled={loading || streaming}
          />
          <Button
            onClick={handleSend}
            size="sm"
            disabled={!input.trim() || loading || streaming}
          >
            {loading || streaming ? "..." : "发送"}
          </Button>
        </div>
      </div>
    </div>
  );
}
