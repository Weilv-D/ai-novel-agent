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
import { extractCharacterRelations } from "./character-relationships";

type CharacterLayoutMode = Extract<GraphLayoutMode, "orbit" | "columns">;

interface CharacterRelationshipGraphProps {
  projectId: string;
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
        const data = await characterApi.list(projectId) as Character[];
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
      for (const relation of extractCharacterRelations(character, characters)) {
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
              style={{ width: "100%", height: "100%" }}
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
