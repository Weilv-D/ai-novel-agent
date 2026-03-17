"use client";

import {
  Background,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";

import { characterApi, ApiError } from "@/lib/api-client";
import type { Character } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";

import { GraphControls } from "./GraphControls";
import {
  createGraphEdge,
  createGraphNode,
  ENTITY_LABELS,
  layoutNodesInColumns,
  layoutNodesInOrbit,
  type GraphLayoutMode,
  type GraphNodeData,
} from "./graph-styles";

type CharacterLayoutMode = Extract<GraphLayoutMode, "orbit" | "columns">;

interface CharacterRelationshipGraphProps {
  projectId: string;
}

interface CharacterRelation {
  targetId?: string;
  targetName?: string;
  label: string;
  note?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function looksLikeUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(value);
}

function readFirstString(source: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return undefined;
}

function relationFromRecord(
  record: Record<string, unknown>,
  fallbackLabel: string,
  fallbackName?: string,
): CharacterRelation | null {
  const targetId = readFirstString(record, ["target_id", "character_id", "id"]);
  const targetName = readFirstString(record, ["target_name", "character_name", "name", "label"]) || fallbackName;
  const label = readFirstString(record, ["relation", "relationship", "type", "kind", "role"]) || fallbackLabel;
  const note = readFirstString(record, ["note", "description", "status"]);

  if (!targetId && !targetName) {
    return null;
  }

  return {
    targetId,
    targetName,
    label,
    note,
  };
}

function extractCharacterRelations(character: Character): CharacterRelation[] {
  const relationships = character.relationships;
  if (!relationships) {
    return [];
  }

  const extracted: CharacterRelation[] = [];

  for (const [key, rawValue] of Object.entries(relationships)) {
    if (Array.isArray(rawValue)) {
      for (const item of rawValue) {
        if (typeof item === "string" && item.trim()) {
          extracted.push({ targetName: item.trim(), label: key });
        } else if (isRecord(item)) {
          const relation = relationFromRecord(item, key);
          if (relation) {
            extracted.push(relation);
          }
        }
      }
      continue;
    }

    if (typeof rawValue === "string" && rawValue.trim()) {
      if (looksLikeUuid(key)) {
        extracted.push({ targetId: key, label: rawValue.trim() });
      } else {
        extracted.push({ targetName: rawValue.trim(), label: key });
      }
      continue;
    }

    if (!isRecord(rawValue)) {
      continue;
    }

    if (key === "entries" || key === "items" || key === "links") {
      for (const item of Object.values(rawValue)) {
        if (isRecord(item)) {
          const relation = relationFromRecord(item, "关系");
          if (relation) {
            extracted.push(relation);
          }
        }
      }
      continue;
    }

    const directRelation = relationFromRecord(rawValue, key);
    if (directRelation) {
      extracted.push(directRelation);
      continue;
    }

    for (const [nestedKey, nestedValue] of Object.entries(rawValue)) {
      if (typeof nestedValue === "string" && nestedValue.trim()) {
        extracted.push({
          targetId: looksLikeUuid(nestedKey) ? nestedKey : undefined,
          targetName: looksLikeUuid(nestedKey) ? undefined : nestedKey,
          label: key,
          note: nestedValue.trim(),
        });
      } else if (isRecord(nestedValue)) {
        const relation = relationFromRecord(
          nestedValue,
          key,
          looksLikeUuid(nestedKey) ? undefined : nestedKey,
        );
        if (relation) {
          extracted.push(relation);
        }
      }
    }
  }

  return extracted;
}

export function CharacterRelationshipGraph({ projectId }: CharacterRelationshipGraphProps) {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [layoutMode, setLayoutMode] = useState<CharacterLayoutMode>("orbit");

  useEffect(() => {
    let active = true;

    async function loadCharacters() {
      try {
        setLoading(true);
        setError(null);
        const data = await characterApi.list(projectId, { limit: 500 }) as Character[];
        if (!active) {
          return;
        }
        setCharacters(data);
      } catch (err) {
        if (!active) {
          return;
        }
        setError(err instanceof ApiError ? err.detail : "加载人物关系失败");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadCharacters();

    return () => {
      active = false;
    };
  }, [projectId]);

  const graph = useMemo(() => {
    const nodes = new Map<string, Node<GraphNodeData>>();
    const edges: Edge[] = [];
    const edgeKeys = new Set<string>();
    const charactersById = new Map(characters.map((character) => [character.id, character]));
    const charactersByName = new Map(
      characters.map((character) => [character.name.trim().toLocaleLowerCase("zh-CN"), character])
    );

    for (const character of characters) {
      nodes.set(
        character.id,
        createGraphNode({
          id: character.id,
          label: `${character.name}${character.role ? `\n${character.role}` : ""}`,
          entityType: "character",
        }),
      );
    }

    for (const character of characters) {
      for (const relation of extractCharacterRelations(character)) {
        const byId = relation.targetId ? charactersById.get(relation.targetId) : undefined;
        const byName = relation.targetName
          ? charactersByName.get(relation.targetName.trim().toLocaleLowerCase("zh-CN"))
          : undefined;
        const targetCharacter = byId || byName;

        let targetNodeId = targetCharacter?.id;
        if (!targetNodeId && relation.targetName) {
          targetNodeId = `external:${relation.targetName.trim().toLocaleLowerCase("zh-CN")}`;
          if (!nodes.has(targetNodeId)) {
            nodes.set(
              targetNodeId,
              createGraphNode({
                id: targetNodeId,
                label: `${relation.targetName}\n待补人物`,
                entityType: "external_character",
                dimmed: true,
              }),
            );
          }
        }

        if (!targetNodeId || targetNodeId === character.id) {
          continue;
        }

        const pair = [character.id, targetNodeId].sort().join(":");
        const edgeKey = `${pair}:${relation.label}`;
        if (edgeKeys.has(edgeKey)) {
          continue;
        }

        edgeKeys.add(edgeKey);
        edges.push(
          createGraphEdge({
            id: `relationship:${edgeKey}`,
            source: character.id,
            target: targetNodeId,
            label: relation.note ? `${relation.label} · ${relation.note}` : relation.label,
            muted: targetNodeId.startsWith("external:"),
          }),
        );
      }
    }

    const baseNodes = [...nodes.values()];
    const layoutedNodes =
      layoutMode === "orbit" ? layoutNodesInOrbit(baseNodes) : layoutNodesInColumns(baseNodes);

    return {
      nodes: layoutedNodes,
      edges,
      relationCount: edges.length,
    };
  }, [characters, layoutMode]);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <CardTitle className="text-lg">人物关系网络</CardTitle>
            <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-800))]">
              从人物档案里的 `relationships` 字段解析关系边；未匹配到项目人物的名字会以虚线节点保留。
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
            <span className="rounded-full border border-[rgba(var(--seal),0.28)] px-3 py-1">人物 {characters.length}</span>
            <span className="rounded-full border border-[rgba(var(--line),0.24)] px-3 py-1">关系 {graph.relationCount}</span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex min-h-[520px] items-center justify-center">
            <LoadingSpinner size="lg" text="加载人物关系图谱中..." />
          </div>
        ) : error ? (
          <div className="ink-alert ink-alert-danger">{error}</div>
        ) : characters.length === 0 ? (
          <div className="rounded-[1.2rem] border border-dashed border-[rgba(var(--line),0.22)] px-5 py-10 text-center text-sm leading-7 text-[rgb(var(--ink-800))]">
            当前项目还没有人物，图谱暂时为空。
          </div>
        ) : (
          <div className="ink-graph">
            <ReactFlow
              nodes={graph.nodes}
              edges={graph.edges}
              fitView
              fitViewOptions={{ padding: 0.18 }}
              minZoom={0.35}
              maxZoom={1.6}
              proOptions={{ hideAttribution: true }}
            >
              <Background gap={24} color="rgba(120,120,120,0.12)" />
              <MiniMap
                pannable
                zoomable
                nodeStrokeWidth={3}
                maskColor="rgb(var(--paper) / 0.75)"
                style={{
                  background: "rgb(var(--paper-soft) / 0.92)",
                  border: "1px solid rgb(var(--line) / 0.22)",
                }}
              />
              <GraphControls
                layout={layoutMode}
                onLayoutChange={(nextMode) => setLayoutMode(nextMode as CharacterLayoutMode)}
                layoutOptions={[
                  { value: "orbit", label: "环形布局" },
                  { value: "columns", label: "列阵布局" },
                ]}
              />
            </ReactFlow>
          </div>
        )}
        <div className="mt-4 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
          <span className="rounded-full border border-[rgba(var(--seal),0.28)] px-3 py-1">
            {ENTITY_LABELS.character}
          </span>
          <span className="rounded-full border border-dashed border-[rgba(var(--line),0.28)] px-3 py-1">
            {ENTITY_LABELS.external_character}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
