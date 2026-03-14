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
        className={`fixed bottom-6 right-6 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 flex items-center justify-center text-2xl z-50 ${className}`}
      >
        AI
      </button>
    );
  }

  return (
    <div className={`fixed bottom-6 right-6 w-96 h-[500px] bg-white rounded-lg shadow-xl border border-gray-200 flex flex-col z-50 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-blue-600 text-white rounded-t-lg">
        <span className="font-medium">AI 写作助手</span>
        <div className="flex gap-2">
          <button onClick={clearMessages} className="text-sm opacity-80 hover:opacity-100">
            清空
          </button>
          <button onClick={() => setIsOpen(false)} className="text-sm opacity-80 hover:opacity-100">
            收起
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-8 text-sm">
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
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {msg.content}
              {msg.role === "assistant" && streaming && msg.id === messages[messages.length - 1]?.id && (
                <span className="inline-block w-1 h-4 bg-gray-400 ml-1 animate-pulse" />
              )}
            </div>
          </div>
        ))}
        {error && (
          <div className="text-center text-red-500 text-sm">{error}</div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-3">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息..."
            rows={1}
            className="flex-1 resize-none rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
