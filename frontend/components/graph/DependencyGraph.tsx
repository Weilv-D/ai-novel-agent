"use client";

import {
  Background,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import { useEffect, useMemo, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/Loading";
import {
  ApiError,
  chapterApi,
  characterApi,
  dependencyApi,
  projectApi,
  sceneApi,
  suggestionApi,
  volumeApi,
  worldSettingApi,
} from "@/lib/api-client";
import type {
  Chapter,
  Dependency,
  DependencyEntityType,
  Scene,
  Suggestion,
  Volume,
  WorldSetting,
} from "@/lib/types";
import type { Character, Project } from "@/lib/types";

import { GraphControls } from "./GraphControls";
import {
  createGraphEdge,
  createGraphNode,
  ENTITY_LABELS,
  layoutNodesInColumns,
  layoutNodesInOrbit,
  type GraphLayoutMode,
  type GraphNodeData,
  type GraphNodeEntityType,
} from "./graph-styles";

type DependencyLayoutMode = Extract<GraphLayoutMode, "columns" | "radial">;

interface DependencyGraphProps {
  projectId: string;
}

function entityKey(entityType: DependencyEntityType, entityId: string): string {
  return `${entityType}:${entityId}`;
}

function volumeLabel(volume: Volume): string {
  return `第 ${volume.volume_number || "?"} 卷 ${volume.title || "未命名卷"}`;
}

function chapterLabel(chapter: Chapter): string {
  return `第 ${chapter.chapter_number} 章 ${chapter.title || "无标题"}`;
}

function sceneLabel(scene: Scene): string {
  return `场景 ${scene.scene_order}${scene.location ? ` · ${scene.location}` : ""}`;
}

function suggestionLabel(suggestion: Suggestion): string {
  return `${suggestion.type} · ${suggestion.status}`;
}

export function DependencyGraph({ projectId }: DependencyGraphProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [layoutMode, setLayoutMode] = useState<DependencyLayoutMode>("columns");
  const [dependencies, setDependencies] = useState<Dependency[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [worldSettings, setWorldSettings] = useState<WorldSetting[]>([]);
  const [volumes, setVolumes] = useState<Volume[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);

  useEffect(() => {
    let active = true;

    async function loadGraphData() {
      try {
        setLoading(true);
        setError(null);

        const [
          projectData,
          dependencyData,
          characterData,
          worldSettingData,
          volumeData,
          chapterData,
          suggestionData,
        ] = await Promise.all([
          projectApi.get(projectId) as Promise<Project>,
          dependencyApi.list(projectId) as Promise<Dependency[]>,
          characterApi.list(projectId) as Promise<Character[]>,
          worldSettingApi.list(projectId) as Promise<WorldSetting[]>,
          volumeApi.list(projectId) as Promise<Volume[]>,
          chapterApi.list(projectId) as Promise<Chapter[]>,
          suggestionApi.list(projectId, { limit: 500 }) as Promise<Suggestion[]>,
        ]);

        const needsScenes = dependencyData.some(
          (dependency) => dependency.source_type === "scene" || dependency.target_type === "scene"
        );

        const sceneData = needsScenes
          ? (
              await Promise.all(
                chapterData.map(async (chapter) => {
                  try {
                    return await sceneApi.list(chapter.id) as Scene[];
                  } catch {
                    return [];
                  }
                })
              )
            ).flat()
          : [];

        if (!active) {
          return;
        }

        setProject(projectData);
        setDependencies(dependencyData);
        setCharacters(characterData);
        setWorldSettings(worldSettingData);
        setVolumes(volumeData);
        setChapters(chapterData);
        setScenes(sceneData);
        setSuggestions(suggestionData);
      } catch (err) {
        if (!active) {
          return;
        }
        setError(err instanceof ApiError ? err.detail : "加载依赖图谱失败");
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadGraphData();

    return () => {
      active = false;
    };
  }, [projectId]);

  const graph = useMemo(() => {
    const lookup = new Map<string, { label: string; entityType: GraphNodeEntityType }>();

    if (project) {
      lookup.set(entityKey("project", project.id), {
        label: project.name,
        entityType: "project",
      });
    }

    for (const character of characters) {
      lookup.set(entityKey("character", character.id), {
        label: character.name,
        entityType: "character",
      });
    }

    for (const worldSetting of worldSettings) {
      lookup.set(entityKey("world_setting", worldSetting.id), {
        label: worldSetting.name,
        entityType: "world_setting",
      });
    }

    for (const volume of volumes) {
      lookup.set(entityKey("volume", volume.id), {
        label: volumeLabel(volume),
        entityType: "volume",
      });
    }

    for (const chapter of chapters) {
      lookup.set(entityKey("chapter", chapter.id), {
        label: chapterLabel(chapter),
        entityType: "chapter",
      });
    }

    for (const scene of scenes) {
      lookup.set(entityKey("scene", scene.id), {
        label: sceneLabel(scene),
        entityType: "scene",
      });
    }

    for (const suggestion of suggestions) {
      lookup.set(entityKey("suggestion", suggestion.id), {
        label: suggestionLabel(suggestion),
        entityType: "suggestion",
      });
    }

    const nodes = new Map<string, Node<GraphNodeData>>();
    const edges: Edge[] = [];

    for (const dependency of dependencies) {
      const sourceKey = entityKey(dependency.source_type, dependency.source_id);
      const targetKey = entityKey(dependency.target_type, dependency.target_id);
      const sourceMeta = lookup.get(sourceKey) || {
        label: `${ENTITY_LABELS[dependency.source_type]} ${dependency.source_id.slice(0, 8)}`,
        entityType: dependency.source_type,
      };
      const targetMeta = lookup.get(targetKey) || {
        label: `${ENTITY_LABELS[dependency.target_type]} ${dependency.target_id.slice(0, 8)}`,
        entityType: dependency.target_type,
      };

      if (!nodes.has(sourceKey)) {
        nodes.set(
          sourceKey,
          createGraphNode({
            id: sourceKey,
            label: sourceMeta.label,
            entityType: sourceMeta.entityType,
          }),
        );
      }

      if (!nodes.has(targetKey)) {
        nodes.set(
          targetKey,
          createGraphNode({
            id: targetKey,
            label: targetMeta.label,
            entityType: targetMeta.entityType,
          }),
        );
      }

      edges.push(
        createGraphEdge({
          id: dependency.id,
          source: sourceKey,
          target: targetKey,
          label: dependency.dependency_type || "依赖",
          dependencyType: dependency.dependency_type || null,
        }),
      );
    }

    const baseNodes = [...nodes.values()];
    const layoutedNodes =
      layoutMode === "columns" ? layoutNodesInColumns(baseNodes) : layoutNodesInOrbit(baseNodes);

    return {
      nodes: layoutedNodes,
      edges,
    };
  }, [
    chapters,
    characters,
    dependencies,
    layoutMode,
    project,
    scenes,
    suggestions,
    volumes,
    worldSettings,
  ]);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <CardTitle className="text-lg">依赖关系图谱</CardTitle>
            <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-800))]">
              根据 Dependency 模型绘制项目对象之间的引用、影响、包含和先后关系。
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
            <span className="rounded-full border border-[rgba(var(--line),0.24)] px-3 py-1">
              节点 {graph.nodes.length}
            </span>
            <span className="rounded-full border border-[rgba(var(--line),0.24)] px-3 py-1">
              边 {graph.edges.length}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex min-h-[520px] items-center justify-center">
            <LoadingSpinner size="lg" text="加载依赖图谱中..." />
          </div>
        ) : error ? (
          <div className="ink-alert ink-alert-danger">{error}</div>
        ) : dependencies.length === 0 ? (
          <div className="rounded-[1.2rem] border border-dashed border-[rgba(var(--line),0.22)] px-5 py-10 text-center text-sm leading-7 text-[rgb(var(--ink-800))]">
            当前项目还没有依赖记录，图谱暂时为空。
          </div>
        ) : (
          <div className="ink-graph">
            <ReactFlow
              nodes={graph.nodes}
              edges={graph.edges}
              style={{ width: "100%", height: "100%" }}
              fitView
              fitViewOptions={{ padding: 0.18 }}
              minZoom={0.3}
              maxZoom={1.7}
              proOptions={{ hideAttribution: true }}
            >
              <Background gap={22} color="rgba(120,120,120,0.12)" />
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
                onLayoutChange={(nextMode) => setLayoutMode(nextMode as DependencyLayoutMode)}
                layoutOptions={[
                  { value: "columns", label: "分类布局" },
                  { value: "radial", label: "辐射布局" },
                ]}
              />
            </ReactFlow>
          </div>
        )}
        <div className="mt-4 flex flex-wrap gap-2 text-xs tracking-[0.08em] text-[rgb(var(--ink-700))]">
          {(["character", "world_setting", "chapter"] as const).map((entityType) => (
            <span
              key={entityType}
              className="rounded-full border px-3 py-1"
              style={{
                borderColor:
                  entityType === "character"
                    ? "rgb(var(--seal) / 0.3)"
                    : entityType === "world_setting"
                      ? "rgb(var(--amber) / 0.34)"
                      : "rgb(var(--jade) / 0.34)",
              }}
            >
              {ENTITY_LABELS[entityType]}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
