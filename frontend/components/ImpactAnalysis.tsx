"use client";

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

const LEVEL_COLORS: Record<string, string> = {
  high: "text-red-600 bg-red-50",
  medium: "text-yellow-600 bg-yellow-50",
  low: "text-green-600 bg-green-50",
};

export function ImpactAnalysis({ analysis }: ImpactAnalysisProps) {
  if (!analysis) {
    return <div className="text-sm text-gray-400">暂无影响分析</div>;
  }

  const objects = analysis.affected_objects || [];
  const risks = analysis.risks || [];

  return (
    <div className="space-y-3">
      {objects.length > 0 && (
        <div>
          <div className="text-xs font-medium text-gray-500 mb-1">影响范围</div>
          <div className="space-y-1">
            {objects.map((obj, i) => (
              <div
                key={i}
                className={`text-sm px-2 py-1 rounded ${LEVEL_COLORS[obj.impact_level] || "text-gray-600 bg-gray-50"}`}
              >
                [{obj.type}] {obj.name} - {obj.impact_level}
              </div>
            ))}
          </div>
        </div>
      )}
      {risks.length > 0 && (
        <div>
          <div className="text-xs font-medium text-gray-500 mb-1">风险提示</div>
          <ul className="text-sm text-red-600 list-disc list-inside space-y-1">
            {risks.map((risk, i) => (
              <li key={i}>{risk}</li>
            ))}
          </ul>
        </div>
      )}
      {objects.length === 0 && risks.length === 0 && (
        <div className="text-sm text-gray-400">无已知影响</div>
      )}
    </div>
  );
}
