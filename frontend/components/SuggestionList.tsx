"use client";

import { useEffect, useState, useCallback } from "react";
import { suggestionApi } from "@/lib/api-client";
import type { Suggestion } from "@/lib/types";
import { SuggestionCard } from "@/components/SuggestionCard";
import { LoadingSpinner } from "@/components/ui/Loading";

interface SuggestionListProps {
  projectId: string;
  status?: string;
  className?: string;
}

export function SuggestionList({ projectId, status, className = "" }: SuggestionListProps) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSuggestions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await suggestionApi.list(projectId, { status });
      setSuggestions(data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [projectId, status]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  function handleAction() {
    // Refresh the list after any action
    fetchSuggestions();
  }

  if (loading) {
    return <LoadingSpinner size="sm" text="加载建议..." />;
  }

  if (suggestions.length === 0) {
    return (
      <div className={`rounded-[1.2rem] border border-dashed border-[rgba(var(--line),0.18)] py-6 text-center text-sm text-[rgb(var(--ink-700))] ${className}`}>
        暂无待处理的建议
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {suggestions.map((s) => (
        <SuggestionCard key={s.id} suggestion={s} onAction={handleAction} />
      ))}
    </div>
  );
}
