"use client";

import { useEffect, useState, useCallback, useMemo } from "react";

import { clearStoredApiKey, getStoredApiKey, healthApi, setStoredApiKey } from "@/lib/api-client";
import type { HealthResponse } from "@/lib/api-client";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

export function PersonalSetupPanel() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize data using AbortController to prevent race conditions or memory leaks
  useEffect(() => {
    setApiKey(getStoredApiKey());
    const abortController = new AbortController();

    // Minor delay to allow seamless transition for local environments
    const initData = async () => {
      try {
        const result = await healthApi.check();
        if (!abortController.signal.aborted) {
          setHealth(result);
          setLoadError(null);
        }
      } catch (error: unknown) {
        if (!abortController.signal.aborted) {
          const detail = error instanceof Error ? error.message : "无法连接后端";
          setLoadError(detail);
        }
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    void initData();

    return () => {
      abortController.abort();
    };
  }, []);

  const saveApiKey = useCallback(() => {
    setStoredApiKey(apiKey);
    setMessage(apiKey.trim() ? "API Key 已凝藏于书斋。" : "留白已落，归于初简。");
  }, [apiKey]);

  const clearApiKey = useCallback(() => {
    clearStoredApiKey();
    setApiKey("");
    setMessage("印封已去，清白如初。");
  }, []);

  // Performance: Memoize rendering elements to prevent unnecessary repaints
  const SkeletonLoader = useMemo(() => (
    <div className="space-y-4 animate-fade-in">
      <div className="h-24 w-full rounded-xl skeleton-pulse" />
      <div className="h-10 w-full rounded-lg skeleton-pulse mt-6" />
      <div className="h-10 w-48 rounded-lg skeleton-pulse" />
    </div>
  ), []);

  return (
    <Card className="overflow-hidden rounded-2xl border-none p-0 bg-white/40 shadow-xl shadow-ink-900/5 backdrop-blur-md transition-all will-change-transform">
      <CardHeader className="border-b border-line/30 bg-gradient-to-r from-paper-deep/40 to-transparent px-8 py-6">
        <p className="ink-kicker">Personal Mode</p>
        <CardTitle className="mt-2 text-2xl tracking-widest font-serif font-medium">个人的小书斋</CardTitle>
        <CardDescription className="text-ink-700 tracking-wide mt-2">
          单人沉浸式工作台。每一笔灵光，皆归于本心。
        </CardDescription>
      </CardHeader>
      <CardContent className="px-8 py-8 bg-paper-soft/40 relative min-h-[300px]">
        {isLoading ? (
          SkeletonLoader
        ) : (
          <div className="space-y-6 animate-fade-in">
            {health && (
              <div className="rounded-xl border border-seal/20 bg-seal/5 p-5 text-sm text-ink-800 tracking-wide shadow-inner">
                <div className="flex gap-2 items-center mb-2 font-medium text-seal/90">
                  <span className="w-1.5 h-1.5 rounded-full bg-seal shadow-[0_0_8px_rgba(200,70,57,0.6)]"></span>
                  砚台状态
                </div>
                <p className="mt-1 transition-opacity">气象：{health.mode === "standalone" ? "独立实例" : health.mode}</p>
                <p className="mt-1">
                  印信保护：
                  {health.auth_required
                    ? `已上栓（凭证头：${health.api_key_header || "X-API-Key"}）`
                    : "解封状态"}
                </p>
              </div>
            )}

            {loadError && (
              <div className="rounded-xl border border-red-800/20 bg-red-800/5 p-4 text-sm text-red-800 shadow-inner">
                后阁未开，墨香难达：{loadError}
              </div>
            )}

            <div className="space-y-4 pt-2">
              <Input
                label="私人印信 (API Key)"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="若后阁设下门阀，请将于此落印..."
                testId="api-key-input"
              />

              <div className="flex flex-col gap-4 sm:flex-row pt-2">
                <Button type="button" onClick={saveApiKey} className="font-serif tracking-widest min-w-[120px]" testId="save-api-key-btn">
                  落印
                </Button>
                <Button type="button" variant="ghost" onClick={clearApiKey} className="font-serif tracking-widest min-w-[120px]" testId="clear-api-key-btn">
                  拂尘
                </Button>
              </div>

              {message && (
                <p className="text-sm text-ink-600 font-serif italic tracking-wide animate-fade-in block">
                  {message}
                </p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
