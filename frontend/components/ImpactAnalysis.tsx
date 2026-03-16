"use client";

import { getImpactLevelClass } from "@/lib/presentation";

interface ImpactItem {
  type: string;
  id: string;
  name: string;
  impact_level: string;
}

interface ImpactAnalysisProps {
  analysis: {
    affected_objects?: ImpactItem[];
    risks?: string[];
  } | null;
}

export function ImpactAnalysis({ analysis }: ImpactAnalysisProps) {
  if (!analysis) {
    return <div className="text-sm text-[rgb(var(--ink-700))]">暂无影响分析</div>;
  }

  const objects = analysis.affected_objects || [];
  const risks = analysis.risks || [];

  return (
    <div className="space-y-3">
      {objects.length > 0 && (
        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-[rgb(var(--ink-700))]">影响范围</div>
          <div className="flex flex-wrap gap-2">
            {objects.map((obj, i) => (
              <div
                key={i}
                className={getImpactLevelClass(obj.impact_level)}
              >
                [{obj.type}] {obj.name} - {obj.impact_level}
              </div>
            ))}
          </div>
        </div>
      )}
      {risks.length > 0 && (
        <div>
          <div className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-[rgb(var(--ink-700))]">风险提示</div>
          <ul className="list-disc space-y-1 pl-5 text-sm text-[rgb(var(--danger))]">
            {risks.map((risk, i) => (
              <li key={i}>{risk}</li>
            ))}
          </ul>
        </div>
      )}
      {objects.length === 0 && risks.length === 0 && (
        <div className="text-sm text-[rgb(var(--ink-700))]">无已知影响</div>
      )}
    </div>
  );
}
