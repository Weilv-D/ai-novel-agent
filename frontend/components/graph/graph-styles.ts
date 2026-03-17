import type { CSSProperties } from "react";

import { MarkerType, type Edge, type Node, type XYPosition } from "@xyflow/react";

import type { DependencyEntityType, DependencyType } from "@/lib/types";

export type GraphLayoutMode = "orbit" | "columns" | "radial";
export type GraphNodeEntityType = DependencyEntityType | "external_character";

export interface GraphNodeData extends Record<string, unknown> {
  label: string;
  entityType: GraphNodeEntityType;
}

interface GraphNodeOptions {
  id: string;
  label: string;
  entityType: GraphNodeEntityType;
  position?: XYPosition;
  dimmed?: boolean;
}

interface GraphEdgeOptions {
  id: string;
  source: string;
  target: string;
  label?: string;
  dependencyType?: DependencyType | null;
  muted?: boolean;
}

const ENTITY_ORDER: GraphNodeEntityType[] = [
  "project",
  "character",
  "world_setting",
  "volume",
  "chapter",
  "scene",
  "suggestion",
  "external_character",
];

export const ENTITY_LABELS: Record<GraphNodeEntityType, string> = {
  project: "项目",
  character: "人物",
  world_setting: "设定",
  volume: "卷",
  chapter: "章节",
  scene: "场景",
  suggestion: "建议",
  external_character: "关系名",
};

function getNodeTheme(entityType: GraphNodeEntityType, dimmed = false): CSSProperties {
  const base = {
    color: "rgb(var(--ink-950))",
    background: "linear-gradient(145deg, rgb(255 255 255 / 0.94), rgb(var(--paper-soft) / 0.9))",
    border: "1px solid rgb(var(--line) / 0.28)",
    boxShadow: "0 20px 44px -30px rgb(var(--shadow) / 0.2)",
  } satisfies CSSProperties;

  if (entityType === "character") {
    return {
      ...base,
      border: "2px solid rgb(var(--seal) / 0.55)",
      boxShadow: "0 22px 40px -28px rgb(var(--seal) / 0.24)",
    };
  }

  if (entityType === "world_setting") {
    return {
      ...base,
      border: "2px solid rgb(var(--amber) / 0.58)",
      boxShadow: "0 22px 40px -28px rgb(var(--amber) / 0.2)",
    };
  }

  if (entityType === "chapter") {
    return {
      ...base,
      border: "2px solid rgb(var(--jade) / 0.58)",
      boxShadow: "0 22px 40px -28px rgb(var(--jade) / 0.2)",
    };
  }

  if (entityType === "volume") {
    return {
      ...base,
      border: "2px solid rgb(var(--ink-700) / 0.45)",
    };
  }

  if (entityType === "scene") {
    return {
      ...base,
      border: "1px solid rgb(var(--jade) / 0.4)",
      background: "linear-gradient(145deg, rgb(255 255 255 / 0.86), rgb(var(--jade) / 0.08))",
    };
  }

  if (entityType === "project") {
    return {
      ...base,
      border: "2px solid rgb(var(--ink-950) / 0.72)",
      background: "linear-gradient(145deg, rgb(var(--paper-soft) / 0.96), rgb(var(--paper-deep) / 0.88))",
    };
  }

  if (entityType === "suggestion") {
    return {
      ...base,
      border: "1px solid rgb(var(--amber) / 0.4)",
      background: "linear-gradient(145deg, rgb(255 255 255 / 0.88), rgb(var(--amber) / 0.08))",
    };
  }

  if (dimmed) {
    return {
      ...base,
      opacity: 0.78,
      borderStyle: "dashed",
      borderWidth: "1px",
    };
  }

  return base;
}

export function createGraphNode({
  id,
  label,
  entityType,
  position = { x: 0, y: 0 },
  dimmed = false,
}: GraphNodeOptions): Node<GraphNodeData> {
  return {
    id,
    position,
    data: { label, entityType },
    draggable: true,
    style: {
      ...getNodeTheme(entityType, dimmed),
      minWidth: 170,
      maxWidth: 240,
      borderRadius: 22,
      padding: "14px 18px",
      fontFamily: "var(--font-serif)",
      fontSize: 14,
      lineHeight: 1.5,
      letterSpacing: "0.03em",
      whiteSpace: "pre-wrap",
    },
  };
}

export function createGraphEdge({
  id,
  source,
  target,
  label,
  dependencyType,
  muted = false,
}: GraphEdgeOptions): Edge {
  const stroke =
    dependencyType === "influences"
      ? "rgb(var(--amber))"
      : dependencyType === "contains"
        ? "rgb(var(--jade))"
        : dependencyType === "precedes"
          ? "rgb(var(--seal-dark))"
          : "rgb(var(--ink-700))";

  return {
    id,
    source,
    target,
    label,
    type: "smoothstep",
    animated: dependencyType === "influences",
    style: {
      stroke,
      strokeOpacity: muted ? 0.45 : 0.78,
      strokeWidth: dependencyType === "contains" ? 1.8 : 1.6,
    },
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 18,
      height: 18,
      color: stroke,
    },
    labelStyle: {
      fill: "rgb(var(--ink-900))",
      fontSize: 11,
      letterSpacing: "0.06em",
    },
    labelBgStyle: {
      fill: "rgb(var(--paper-soft))",
      fillOpacity: 0.92,
    },
    labelBgPadding: [8, 4],
    labelBgBorderRadius: 10,
  };
}

function sortNodes(nodes: Array<Node<GraphNodeData>>): Array<Node<GraphNodeData>> {
  return [...nodes].sort((left, right) => {
    const orderDelta = ENTITY_ORDER.indexOf(left.data.entityType) - ENTITY_ORDER.indexOf(right.data.entityType);
    if (orderDelta !== 0) {
      return orderDelta;
    }
    return left.data.label.localeCompare(right.data.label, "zh-CN");
  });
}

export function layoutNodesInOrbit(nodes: Array<Node<GraphNodeData>>): Array<Node<GraphNodeData>> {
  const sorted = sortNodes(nodes);
  if (sorted.length === 0) {
    return sorted;
  }

  const centerX = 520;
  const centerY = 320;
  const radius = Math.max(190, sorted.length * 34);

  return sorted.map((node, index) => {
    if (sorted.length === 1) {
      return { ...node, position: { x: centerX, y: centerY } };
    }

    const angle = (-Math.PI / 2) + (index / sorted.length) * Math.PI * 2;
    return {
      ...node,
      position: {
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
      },
    };
  });
}

export function layoutNodesInColumns(nodes: Array<Node<GraphNodeData>>): Array<Node<GraphNodeData>> {
  const sorted = sortNodes(nodes);
  const grouped = new Map<GraphNodeEntityType, Array<Node<GraphNodeData>>>();

  for (const node of sorted) {
    const bucket = grouped.get(node.data.entityType) || [];
    bucket.push(node);
    grouped.set(node.data.entityType, bucket);
  }

  const columnGap = 250;
  const rowGap = 132;
  let columnIndex = 0;

  return ENTITY_ORDER.flatMap((entityType) => {
    const bucket = grouped.get(entityType);
    if (!bucket?.length) {
      return [];
    }

    const positioned = bucket.map((node, index) => ({
      ...node,
      position: {
        x: 60 + columnIndex * columnGap,
        y: 80 + index * rowGap,
      },
    }));

    columnIndex += 1;
    return positioned;
  });
}
