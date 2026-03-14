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
    setMessage(apiKey.trim() ? "API Key 已保存到当前浏览器。" : "空值已视为清除。");
  };

  const clearApiKey = () => {
    clearStoredApiKey();
    setApiKey("");
    setMessage("已清除本地 API Key。");
  };

  return (
    <Card className="border-blue-100 bg-white/90 backdrop-blur">
      <CardHeader>
        <CardTitle className="text-lg">个人模式设置</CardTitle>
        <CardDescription>
          当前项目已按单用户使用方式收口。后端会把数据归属到固定个人账户。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {health && (
          <div className="rounded-md bg-blue-50 p-4 text-sm text-gray-700">
            <p>运行模式：{health.mode}</p>
            <p>个人账号：{health.personal_user_email || "未配置"}</p>
            <p>
              API Key 保护：
              {health.auth_required
                ? `已启用（请求头：${health.api_key_header || "X-API-Key"}）`
                : "未启用"}
            </p>
          </div>
        )}

        {loadError && (
          <div className="rounded-md bg-red-50 p-4 text-sm text-red-700">
            无法读取后端健康状态：{loadError}
          </div>
        )}

        <Input
          label="本地 API Key"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          placeholder="如果后端配置了 ADMIN_API_KEY，就把它保存到这里"
        />

        <div className="flex flex-col gap-3 sm:flex-row">
          <Button type="button" onClick={saveApiKey}>
            保存到浏览器
          </Button>
          <Button type="button" variant="outline" onClick={clearApiKey}>
            清除本地 Key
          </Button>
        </div>

        {message && <p className="text-sm text-gray-600">{message}</p>}
      </CardContent>
    </Card>
  );
}
