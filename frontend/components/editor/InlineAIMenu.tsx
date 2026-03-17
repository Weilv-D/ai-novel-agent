"use client";

import type { Editor } from "@tiptap/core";
import { BubbleMenu } from "@tiptap/react";
import { useState } from "react";

import { agentApi, ApiError } from "@/lib/api-client";
import type { InlineEditOperation } from "@/lib/types";

const INLINE_AI_ACTIONS: Array<{ label: string; operation: InlineEditOperation }> = [
  { label: "改写", operation: "rewrite" },
  { label: "扩写", operation: "expand" },
  { label: "缩写", operation: "condense" },
  { label: "换视角", operation: "change_pov" },
];

interface InlineAIMenuProps {
  editor: Editor;
  context?: Record<string, unknown>;
  onError?: (message: string) => void;
}

export function InlineAIMenu({ editor, context = {}, onError }: InlineAIMenuProps) {
  const [activeOperation, setActiveOperation] = useState<InlineEditOperation | null>(null);

  async function handleInlineEdit(operation: InlineEditOperation) {
    const selection = editor.state.selection;
    if (selection.empty) {
      return;
    }

    const selectedText = editor.state.doc.textBetween(selection.from, selection.to, "\n\n").trim();
    if (!selectedText) {
      return;
    }

    if (selectedText.length > 3000) {
      onError?.("单次内联编辑最多处理 3000 个字符。");
      return;
    }

    const documentText = editor.state.doc.textBetween(0, editor.state.doc.content.size, "\n\n");
    let accumulated = "";
    let replaceTo = selection.to;

    setActiveOperation(operation);

    try {
      for await (const chunk of agentApi.inlineEditStream({
        text: selectedText,
        operation,
        context: {
          document_text:
            documentText.length > 4000
              ? `${documentText.slice(0, 2000)}\n...\n${documentText.slice(-2000)}`
              : documentText,
          ...context,
        },
      })) {
        accumulated += chunk;
        editor
          .chain()
          .focus()
          .insertContentAt(
            { from: selection.from, to: replaceTo },
            accumulated,
            { parseOptions: { preserveWhitespace: "full" } }
          )
          .setTextSelection({ from: selection.from, to: selection.from + accumulated.length })
          .run();
        replaceTo = selection.from + accumulated.length;
      }

      editor.chain().focus().setTextSelection(replaceTo).run();
    } catch (error) {
      editor
        .chain()
        .focus()
        .insertContentAt(
          { from: selection.from, to: replaceTo },
          selectedText,
          { parseOptions: { preserveWhitespace: "full" } }
        )
        .setTextSelection({ from: selection.from, to: selection.from + selectedText.length })
        .run();

      if (error instanceof ApiError) {
        onError?.(error.detail);
      } else {
        onError?.("AI 内联编辑失败。");
      }
    } finally {
      setActiveOperation(null);
    }
  }

  return (
    <BubbleMenu
      editor={editor}
      pluginKey="inline-ai-menu"
      shouldShow={() => activeOperation !== null || (!editor.state.selection.empty && editor.isEditable)}
      tippyOptions={{ duration: 150, maxWidth: 480 }}
    >
      <div className="ink-editor__bubble">
        {activeOperation ? (
          <span className="text-xs tracking-[0.08em] text-[rgb(var(--seal-dark))]">
            AI {INLINE_AI_ACTIONS.find((item) => item.operation === activeOperation)?.label}中...
          </span>
        ) : (
          INLINE_AI_ACTIONS.map((action) => (
            <button
              key={action.operation}
              type="button"
              onClick={() => handleInlineEdit(action.operation)}
              className="rounded-full border border-[rgba(var(--line),0.22)] px-3 py-1.5 text-xs tracking-[0.08em] text-[rgb(var(--ink-800))] transition-colors hover:bg-[rgba(var(--ink-950),0.05)]"
            >
              {action.label}
            </button>
          ))
        )}
      </div>
    </BubbleMenu>
  );
}
