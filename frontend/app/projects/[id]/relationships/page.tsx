"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { CharacterRelationshipGraph } from "@/components/graph/CharacterRelationshipGraph";
import { DependencyGraph } from "@/components/graph/DependencyGraph";

type RelationshipTab = "characters" | "dependencies";

export default function RelationshipGraphPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [activeTab, setActiveTab] = useState<RelationshipTab>("characters");

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-7xl px-4 py-10">
        <div className="mb-8">
          <Link href={`/projects/${projectId}`} className="ink-backlink mb-4">
            ← 返回项目
          </Link>
          <p className="ink-kicker">Relationship Atlas</p>
          <h1 className="ink-display mt-3 text-4xl font-semibold text-[rgb(var(--ink-950))]">关系图谱</h1>
          <p className="mt-3 max-w-3xl text-base leading-7 text-[rgb(var(--ink-800))]">
            用人物关系网络和依赖图谱两种视角，快速检查角色连接、设定牵引和章节引用链路。
          </p>
        </div>

        <div className="mb-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => setActiveTab("characters")}
            className={`ink-graph__tab ${activeTab === "characters" ? "ink-graph__tab--active" : ""}`}
          >
            人物关系
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("dependencies")}
            className={`ink-graph__tab ${activeTab === "dependencies" ? "ink-graph__tab--active" : ""}`}
          >
            依赖图谱
          </button>
        </div>

        {activeTab === "characters" ? (
          <CharacterRelationshipGraph projectId={projectId} />
        ) : (
          <DependencyGraph projectId={projectId} />
        )}
      </div>
    </main>
  );
}
