"use client";

import type { Editor } from "@tiptap/core";
import CharacterCount from "@tiptap/extension-character-count";
import Highlight from "@tiptap/extension-highlight";
import Placeholder from "@tiptap/extension-placeholder";
import StarterKit from "@tiptap/starter-kit";
import { EditorContent, useEditor } from "@tiptap/react";
import { useEffect, useId } from "react";

import { richTextToPlainText, normalizeRichTextContent } from "@/lib/rich-text";

import { EditorToolbar } from "./EditorToolbar";
import { InlineAIMenu } from "./InlineAIMenu";

interface TipTapEditorProps {
  label?: string;
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  error?: string;
  disabled?: boolean;
  projectId?: string;
  aiContext?: Record<string, unknown>;
  minHeightClassName?: string;
  onAiError?: (message: string) => void;
}

export function TipTapEditor({
  label,
  value = "",
  onChange,
  placeholder = "开始输入...",
  error,
  disabled = false,
  projectId,
  aiContext,
  minHeightClassName = "min-h-[320px]",
  onAiError,
}: TipTapEditorProps) {
  const editorId = useId();
  const normalizedContent = normalizeRichTextContent(value);

  const editor = useEditor({
    editable: !disabled,
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [2, 3],
        },
      }),
      Placeholder.configure({
        placeholder,
      }),
      CharacterCount.configure(),
      Highlight,
    ],
    editorProps: {
      attributes: {
        id: editorId,
        class: `ink-editor__content ${minHeightClassName}`.trim(),
      },
    },
    content: normalizedContent,
    onUpdate: ({ editor: currentEditor }: { editor: Editor }) => {
      onChange(currentEditor.getHTML());
    },
  });

  useEffect(() => {
    if (!editor) {
      return;
    }
    editor.setEditable(!disabled);
  }, [disabled, editor]);

  useEffect(() => {
    if (!editor) {
      return;
    }

    if (editor.getHTML() !== normalizedContent) {
      editor.commands.setContent(normalizedContent, false);
    }
  }, [editor, normalizedContent]);

  const characterCount =
    editor?.storage.characterCount?.characters() ?? richTextToPlainText(normalizedContent).length;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={editorId} className="ink-label">
          {label}
        </label>
      )}

      <div className={`ink-editor ${error ? "ink-editor--error" : ""}`}>
        <EditorToolbar editor={editor} characterCount={characterCount} />
        <EditorContent editor={editor} className="ink-editor__surface" />
        {editor && projectId ? (
          <InlineAIMenu
            editor={editor}
            context={{ project_id: projectId, ...aiContext }}
            onError={onAiError}
          />
        ) : null}
      </div>

      {error ? (
        <p className="mt-2 text-xs tracking-[0.05em] text-[rgb(var(--danger))]">{error}</p>
      ) : null}
    </div>
  );
}
