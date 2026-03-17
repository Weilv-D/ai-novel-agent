"use client";

import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  type DragEndEvent,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import type { ReactNode } from "react";

import { SortableItem } from "./SortableItem";

interface SortableListProps<T extends { id: string }> {
  items: T[];
  onReorder: (items: T[]) => void | Promise<void>;
  renderItem: (item: T, index: number) => ReactNode;
  disabled?: boolean;
  className?: string;
  getItemLabel?: (item: T, index: number) => string;
}

export function SortableList<T extends { id: string }>({
  items,
  onReorder,
  renderItem,
  disabled = false,
  className = "",
  getItemLabel,
}: SortableListProps<T>) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  async function handleDragEnd(event: DragEndEvent) {
    if (disabled || !event.over || event.active.id === event.over.id) {
      return;
    }

    const oldIndex = items.findIndex((item) => item.id === event.active.id);
    const newIndex = items.findIndex((item) => item.id === event.over?.id);
    if (oldIndex < 0 || newIndex < 0 || oldIndex === newIndex) {
      return;
    }

    await onReorder(arrayMove(items, oldIndex, newIndex));
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={items.map((item) => item.id)} strategy={verticalListSortingStrategy}>
        <div className={className}>
          {items.map((item, index) => (
            <SortableItem
              key={item.id}
              id={item.id}
              disabled={disabled || items.length < 2}
              handleLabel={getItemLabel?.(item, index) || "拖拽排序"}
            >
              {renderItem(item, index)}
            </SortableItem>
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}
