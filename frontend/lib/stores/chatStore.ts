/**
 * Chat Store - Zustand state management for agent chat
 */

import { create } from "zustand";
import { agentApi } from "@/lib/api-client";
import type { ChatMessage } from "@/lib/types";

interface ChatState {
  messages: ChatMessage[];
  loading: boolean;
  streaming: boolean;
  error: string | null;

  sendMessage: (projectId: string, message: string, context?: Record<string, unknown>) => Promise<void>;
  sendMessageStream: (projectId: string, message: string, context?: Record<string, unknown>) => Promise<void>;
  clearMessages: () => void;
  clearError: () => void;
}

let messageIdCounter = 0;
function nextId() {
  return `msg-${Date.now()}-${++messageIdCounter}`;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  loading: false,
  streaming: false,
  error: null,

  sendMessage: async (projectId, message, context) => {
    const userMsg: ChatMessage = {
      id: nextId(),
      role: "user",
      content: message,
      timestamp: Date.now(),
    };

    set((s) => ({
      messages: [...s.messages, userMsg],
      loading: true,
      error: null,
    }));

    const history = get()
      .messages.filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-10)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const response = await agentApi.chat({
        project_id: projectId,
        message,
        history,
        context,
      });

      const assistantMsg: ChatMessage = {
        id: nextId(),
        role: "assistant",
        content: response.message,
        metadata: response.metadata,
        timestamp: Date.now(),
      };

      set((s) => ({
        messages: [...s.messages, assistantMsg],
        loading: false,
      }));
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "发送消息失败",
      });
    }
  },

  sendMessageStream: async (projectId, message, context) => {
    const userMsg: ChatMessage = {
      id: nextId(),
      role: "user",
      content: message,
      timestamp: Date.now(),
    };

    const assistantMsgId = nextId();
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    };

    set((s) => ({
      messages: [...s.messages, userMsg, assistantMsg],
      streaming: true,
      error: null,
    }));

    const history = get()
      .messages.filter((m) => m.role === "user" || m.role === "assistant")
      .slice(-10)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      for await (const chunk of agentApi.chatStream({
        project_id: projectId,
        message,
        history,
        context,
      })) {
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === assistantMsgId
              ? { ...m, content: m.content + chunk }
              : m
          ),
        }));
      }
      set({ streaming: false });
    } catch (err) {
      set({
        streaming: false,
        error: err instanceof Error ? err.message : "流式响应失败",
      });
    }
  },

  clearMessages: () => set({ messages: [], error: null }),
  clearError: () => set({ error: null }),
}));
