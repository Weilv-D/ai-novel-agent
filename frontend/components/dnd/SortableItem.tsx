"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { ReactNode } from "react";

interface SortableItemProps {
  id: string;
  children: ReactNode;
  disabled?: boolean;
  handleLabel?: string;
}

export function SortableItem({
  id,
  children,
  disabled = false,
  handleLabel = "拖拽排序",
}: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
    disabled,
  });

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
      }}
      className={[
        "flex items-start gap-3",
        isDragging ? "z-20 opacity-95" : "",
      ].join(" ")}
    >
      <button
        type="button"
        aria-label={handleLabel}
        disabled={disabled}
        {...attributes}
        {...listeners}
        className="mt-3 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[rgba(var(--line),0.22)] bg-[rgba(255,255,255,0.72)] text-sm text-[rgb(var(--ink-800))] shadow-sm transition-colors hover:bg-[rgba(var(--ink-950),0.05)] disabled:cursor-not-allowed disabled:opacity-45"
      >
        ⋮⋮
      </button>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
