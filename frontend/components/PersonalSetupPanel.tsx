"use client";

import { useEffect, useState } from "react";

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

  useEffect(() => {
    setApiKey(getStoredApiKey());
    void healthApi.check()
      .then((result) => {
        setHealth(result);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        const detail = error instanceof Error ? error.message : "无法连接后端";
        setLoadError(detail);
      });
  }, []);

  const saveApiKey = () => {
    setStoredApiKey(apiKey);
    setMessage(apiKey.trim() ? "API Key 已凝藏于书斋。" : "留白已落，归于初简。");
  };

  const clearApiKey = () => {
    clearStoredApiKey();
    setApiKey("");
    setMessage("印封已去，清白如初。");
  };

  return (
    <Card className="overflow-hidden rounded-2xl border-none p-0 bg-white/40 shadow-xl shadow-ink-900/5 backdrop-blur-md">
      <CardHeader className="border-b border-line/30 bg-gradient-to-r from-paper-deep/40 to-transparent px-8 py-6">
        <p className="ink-kicker">Personal Mode</p>
        <CardTitle className="mt-2 text-2xl tracking-widest font-serif font-medium">个人的小书斋</CardTitle>
        <CardDescription className="text-ink-700 tracking-wide mt-2">
          单人沉浸式工作台。每一笔灵光，皆归于本心。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 px-8 py-8 bg-paper-soft/40 relative">
        {health && (
          <div className="rounded-xl border border-seal/20 bg-seal/5 p-5 text-sm text-ink-800 tracking-wide shadow-inner">
            <div className="flex gap-2 items-center mb-2 font-medium text-seal/90">
              <span className="w-1.5 h-1.5 rounded-full bg-seal"></span>
              砚台状态
            </div>
            <p className="mt-1">气象：{health.mode === "personal" ? "个人独享" : health.mode}</p>
            <p className="mt-1">笔名：{health.personal_user_email || "未题名"}</p>
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
          />

          <div className="flex flex-col gap-4 sm:flex-row pt-2">
            <Button type="button" onClick={saveApiKey} className="font-serif tracking-widest">
              落印
            </Button>
            <Button type="button" variant="ghost" onClick={clearApiKey} className="font-serif tracking-widest">
              拂尘
            </Button>
          </div>

          {message && <p className="text-sm text-ink-600 font-serif italic tracking-wide animate-pulse">{message}</p>}
        </div>
      </CardContent>
    </Card>
  );
}
