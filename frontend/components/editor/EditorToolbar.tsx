"use client";

import type { Editor } from "@tiptap/core";

interface EditorToolbarProps {
  editor: Editor | null;
  characterCount: number;
}

interface ToolbarButtonProps {
  label: string;
  title: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

function ToolbarButton({
  label,
  title,
  active = false,
  disabled = false,
  onClick,
}: ToolbarButtonProps) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      className={[
        "rounded-full border px-3 py-1.5 text-xs tracking-[0.08em] transition-colors",
        active
          ? "border-[rgba(var(--seal),0.45)] bg-[rgba(var(--seal),0.12)] text-[rgb(var(--seal-dark))]"
          : "border-[rgba(var(--line),0.22)] bg-[rgba(255,255,255,0.72)] text-[rgb(var(--ink-800))] hover:bg-[rgba(var(--ink-950),0.05)]",
        disabled ? "cursor-not-allowed opacity-45" : "",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

export function EditorToolbar({ editor, characterCount }: EditorToolbarProps) {
  return (
    <div className="ink-editor__toolbar">
      <div className="flex flex-wrap items-center gap-2">
        <ToolbarButton
          label="B"
          title="加粗"
          active={editor?.isActive("bold")}
          disabled={!editor?.can().chain().focus().toggleBold().run()}
          onClick={() => editor?.chain().focus().toggleBold().run()}
        />
        <ToolbarButton
          label="I"
          title="斜体"
          active={editor?.isActive("italic")}
          disabled={!editor?.can().chain().focus().toggleItalic().run()}
          onClick={() => editor?.chain().focus().toggleItalic().run()}
        />
        <ToolbarButton
          label="H2"
          title="二级标题"
          active={editor?.isActive("heading", { level: 2 })}
          onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
        />
        <ToolbarButton
          label="H3"
          title="三级标题"
          active={editor?.isActive("heading", { level: 3 })}
          onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()}
        />
        <ToolbarButton
          label="重点"
          title="高亮"
          active={editor?.isActive("highlight")}
          onClick={() => editor?.chain().focus().toggleHighlight().run()}
        />
        <ToolbarButton
          label="撤销"
          title="撤销"
          disabled={!editor?.can().chain().focus().undo().run()}
          onClick={() => editor?.chain().focus().undo().run()}
        />
        <ToolbarButton
          label="重做"
          title="重做"
          disabled={!editor?.can().chain().focus().redo().run()}
          onClick={() => editor?.chain().focus().redo().run()}
        />
      </div>
      <div className="text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
        字数 {characterCount}
      </div>
    </div>
  );
}
