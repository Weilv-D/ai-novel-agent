/**
 * API Client for AI Novel Agent Backend
 * Handles HTTP requests to the FastAPI backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY_STORAGE_KEY = "api_key";
const API_KEY_HEADER_STORAGE_KEY = "api_key_header";
const DEFAULT_API_KEY_HEADER = "X-API-Key";

export function getStoredApiKey(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return localStorage.getItem(API_KEY_STORAGE_KEY) || "";
}

export function setStoredApiKey(apiKey: string): void {
  if (typeof window === "undefined") {
    return;
  }
  const trimmed = apiKey.trim();
  if (!trimmed) {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
    return;
  }
  localStorage.setItem(API_KEY_STORAGE_KEY, trimmed);
}

export function clearStoredApiKey(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem(API_KEY_STORAGE_KEY);
}

export function getStoredApiKeyHeader(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return localStorage.getItem(API_KEY_HEADER_STORAGE_KEY) || "";
}

export function setStoredApiKeyHeader(headerName: string | null | undefined): void {
  if (typeof window === "undefined") {
    return;
  }
  const trimmed = headerName?.trim();
  if (!trimmed) {
    localStorage.removeItem(API_KEY_HEADER_STORAGE_KEY);
    return;
  }
  localStorage.setItem(API_KEY_HEADER_STORAGE_KEY, trimmed);
}

/**
 * Custom error class for API errors
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public data?: unknown
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

/**
 * Helper function to build query strings from parameters
 */
function buildQueryString(params: Record<string, string | number | boolean | undefined>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined) {
      searchParams.append(key, String(value));
    }
  });
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

export interface HealthResponse {
  status: string;
  version: string;
  mode: string;
  auth_required: boolean;
  api_key_header?: string | null;
}

function cacheHealthApiHeader(health: Partial<HealthResponse> | null): void {
  if (!health?.api_key_header) {
    return;
  }
  setStoredApiKeyHeader(health.api_key_header);
}

async function resolveApiKeyHeader(): Promise<string> {
  const storedHeader = getStoredApiKeyHeader();
  if (storedHeader) {
    return storedHeader;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`);
    if (!response.ok) {
      return DEFAULT_API_KEY_HEADER;
    }

    const health = (await response.json()) as Partial<HealthResponse>;
    cacheHealthApiHeader(health);
    return health.api_key_header?.trim() || DEFAULT_API_KEY_HEADER;
  } catch {
    return DEFAULT_API_KEY_HEADER;
  }
}

/**
 * Core fetch wrapper with error handling and authentication
 */
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const apiKey = getStoredApiKey();
  const apiKeyHeader = apiKey ? await resolveApiKeyHeader() : DEFAULT_API_KEY_HEADER;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (apiKey) {
    headers[apiKeyHeader] = apiKey;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle empty responses (e.g., 204 No Content)
  const contentType = response.headers.get("content-type");
  const hasJsonBody = contentType?.includes("application/json");
  const data = hasJsonBody ? await response.json() : null;

  if (!response.ok) {
    const errorPayload = data as {
      detail?: string;
      message?: string;
      error?: { message?: string };
    } | null;
    throw new ApiError(
      response.status,
      errorPayload?.detail
        || errorPayload?.message
        || errorPayload?.error?.message
        || "An error occurred",
      data
    );
  }

  if (endpoint === "/api/v1/health" && data && typeof data === "object") {
    cacheHealthApiHeader(data as Partial<HealthResponse>);
  }

  return data as T;
}

// ============================================================================
// Health API
// ============================================================================

export const healthApi = {
  check: () => fetchApi<HealthResponse>("/api/v1/health"),
};

// ============================================================================
// Project API
// ============================================================================

export const projectApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    fetchApi<unknown[]>(
      `/api/v1/projects${buildQueryString(params || {})}`
    ),

  getById: (id: string) =>
    fetchApi<unknown>(`/api/v1/projects/${id}`),

  get: (id: string) =>
    fetchApi<unknown>(`/api/v1/projects/${id}`),

  create: (data: unknown) =>
    fetchApi<unknown>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: unknown) =>
    fetchApi<unknown>(`/api/v1/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/v1/projects/${id}`, {
      method: "DELETE",
    }),
};

// ============================================================================
// Character API
// ============================================================================

export const characterApi = {
  list: (projectId: string, params?: { skip?: number; limit?: number }) =>
    fetchApi<unknown[]>(
      `/api/v1/characters/project/${projectId}${buildQueryString(params || {})}`
    ),

  get: (id: string) =>
    fetchApi<unknown>(`/api/v1/characters/${id}`),

  create: (data: unknown) =>
    fetchApi<unknown>("/api/v1/characters", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: unknown) =>
    fetchApi<unknown>(`/api/v1/characters/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/v1/characters/${id}`, {
      method: "DELETE",
    }),
};

// ============================================================================
// WorldSetting API
// ============================================================================

export const worldSettingApi = {
  list: (projectId: string, params?: { skip?: number; limit?: number }) =>
    fetchApi<unknown[]>(
      `/api/v1/world-settings/project/${projectId}${buildQueryString(params || {})}`
    ),

  getByCategory: (projectId: string, category: string, params?: { skip?: number; limit?: number }) =>
    fetchApi<unknown[]>(
      `/api/v1/world-settings/project/${projectId}/category/${category}${buildQueryString(params || {})}`
    ),

  get: (id: string) =>
    fetchApi<unknown>(`/api/v1/world-settings/${id}`),

  create: (data: unknown) =>
    fetchApi<unknown>("/api/v1/world-settings", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: unknown) =>
    fetchApi<unknown>(`/api/v1/world-settings/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/v1/world-settings/${id}`, {
      method: "DELETE",
    }),
};

// ============================================================================
// Chapter API
// ============================================================================

export const chapterApi = {
  list: (projectId: string, params?: { skip?: number; limit?: number }) =>
    fetchApi<unknown[]>(
      `/api/v1/chapters/project/${projectId}${buildQueryString(params || {})}`
    ),

  listByVolume: (volumeId: string, params?: { skip?: number; limit?: number }) =>
    fetchApi<unknown[]>(
      `/api/v1/chapters/volume/${volumeId}${buildQueryString(params || {})}`
    ),

  get: (id: string) =>
    fetchApi<unknown>(`/api/v1/chapters/${id}`),

  create: (data: unknown) =>
    fetchApi<unknown>("/api/v1/chapters", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: unknown) =>
    fetchApi<unknown>(`/api/v1/chapters/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/v1/chapters/${id}`, {
      method: "DELETE",
    }),
};

// ============================================================================
// Volume API
// ============================================================================

export const volumeApi = {
  list: (projectId: string, params?: { skip?: number; limit?: number }) =>
    fetchApi<unknown[]>(
      `/api/v1/volumes/project/${projectId}${buildQueryString(params || {})}`
    ),

  get: (id: string) =>
    fetchApi<unknown>(`/api/v1/volumes/${id}`),

  create: (data: unknown) =>
    fetchApi<unknown>("/api/v1/volumes", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: unknown) =>
    fetchApi<unknown>(`/api/v1/volumes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/v1/volumes/${id}`, {
      method: "DELETE",
    }),
};

// ============================================================================
// Scene API
// ============================================================================

export const sceneApi = {
  list: (chapterId: string, params?: { skip?: number; limit?: number }) =>
    fetchApi<unknown[]>(
      `/api/v1/scenes/chapter/${chapterId}${buildQueryString(params || {})}`
    ),

  get: (id: string) =>
    fetchApi<unknown>(`/api/v1/scenes/${id}`),

  create: (data: unknown) =>
    fetchApi<unknown>("/api/v1/scenes", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: unknown) =>
    fetchApi<unknown>(`/api/v1/scenes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    fetchApi<void>(`/api/v1/scenes/${id}`, {
      method: "DELETE",
    }),
};

// ============================================================================
// Memory API
// ============================================================================

export const memoryApi = {
  list: (projectId: string, params?: { skip?: number; limit?: number }) =>
    fetchApi<unknown[]>(
      `/api/v1/memories${buildQueryString({ project_id: projectId, ...params })}`
    ),

  get: (id: string) =>
    fetchApi<unknown>(`/api/v1/memories/${id}`),

  create: (data: unknown) =>
    fetchApi<unknown>("/api/v1/memories", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  search: (params: { project_id: string; query: string; limit?: number }) =>
    fetchApi<unknown[]>(
      `/api/v1/memories/search${buildQueryString(params)}`
    ),

  delete: (id: string) =>
    fetchApi<void>(`/api/v1/memories/${id}`, {
      method: "DELETE",
    }),
};

// ============================================================================
// Snapshot API
// ============================================================================

export const snapshotApi = {
  list: (projectId: string) =>
    fetchApi<unknown[]>(`/api/v1/snapshots?project_id=${projectId}`),

  get: (id: string) =>
    fetchApi<unknown>(`/api/v1/snapshots/${id}`),

  create: (data: unknown) =>
    fetchApi<unknown>("/api/v1/snapshots", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  rollback: (id: string) =>
    fetchApi<unknown>(`/api/v1/snapshots/${id}/rollback`, {
      method: "POST",
    }),
};

// ============================================================================
// Dependency API
// ============================================================================

export const dependencyApi = {
  list: (projectId: string) =>
    fetchApi<unknown[]>(`/api/v1/dependencies?project_id=${projectId}`),

  get: (id: string) =>
    fetchApi<unknown>(`/api/v1/dependencies/${id}`),

  create: (data: unknown) =>
    fetchApi<unknown>("/api/v1/dependencies", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  analyze: (params: { object_type: string; object_id: string }) =>
    fetchApi<unknown>(
      `/api/v1/dependencies/analysis${buildQueryString(params)}`
    ),
};

// ============================================================================
// Agent API
// ============================================================================

import type {
  AgentChatRequest,
  AgentChatResponse,
  AgentProfile,
  AgentRiskPolicyRegistry,
  AgentRun,
  AgentSkillCatalog,
  AgentStreamEvent,
  AgentThread,
  AgentThreadMessageRequest,
  AgentThreadMessageResponse,
  AgentThreadState,
  Suggestion,
} from "@/lib/types";

async function buildAuthenticatedHeaders(
  initialHeaders: Record<string, string> = {}
): Promise<Record<string, string>> {
  const headers = { ...initialHeaders };
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("api_key") : null;
  if (!apiKey) {
    return headers;
  }
  const headerName = await resolveApiKeyHeader();
  headers[headerName] = apiKey;
  return headers;
}

export const agentApi = {
  chat: (data: AgentChatRequest) =>
    fetchApi<AgentChatResponse>("/api/v1/agent/chat", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  chatStream: async function* (data: AgentChatRequest): AsyncGenerator<string, void, unknown> {
    const url = `${API_BASE_URL}/api/v1/agent/chat/stream`;
    const headers = await buildAuthenticatedHeaders({
      "Content-Type": "application/json",
    });

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new ApiError(response.status, "Stream request failed");
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") return;
          try {
            const parsed = JSON.parse(data);
            if (parsed.content) {
              yield parsed.content;
            }
          } catch {
            // skip malformed data
          }
        }
      }
    }
  },

  autoSummarize: (data: { project_id: string; chapter_id: string; content: string }) =>
    fetchApi<{ memories: unknown[]; count: number }>("/api/v1/agent/auto-summarize", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  continuityCheck: (data: { project_id: string; content: string }) =>
    fetchApi<AgentChatResponse>("/api/v1/agent/continuity-check", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

export const agentWorkflowApi = {
  listProfiles: () =>
    fetchApi<AgentProfile[]>("/api/v1/agent/profiles"),

  getRiskPolicies: () =>
    fetchApi<AgentRiskPolicyRegistry>("/api/v1/agent/risk-policies"),

  getSkills: (projectId?: string) =>
    fetchApi<AgentSkillCatalog>(`/api/v1/agent/skills${buildQueryString({ project_id: projectId })}`),

  createThread: (projectId: string) =>
    fetchApi<AgentThread>("/api/v1/agent/threads", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId }),
    }),

  getThread: (threadId: string) =>
    fetchApi<AgentThreadState>(`/api/v1/agent/threads/${threadId}`),

  sendMessage: (threadId: string, data: AgentThreadMessageRequest) =>
    fetchApi<AgentThreadMessageResponse>(`/api/v1/agent/threads/${threadId}/messages`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  sendMessageStream: async function* (
    threadId: string,
    data: AgentThreadMessageRequest
  ): AsyncGenerator<AgentStreamEvent, void, unknown> {
    const url = `${API_BASE_URL}/api/v1/agent/threads/${threadId}/messages`;
    const headers = await buildAuthenticatedHeaders({
      "Content-Type": "application/json",
    });

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({ ...data, stream: true }),
    });

    if (!response.ok) {
      throw new ApiError(response.status, "Stream request failed");
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") return;
          try {
            const parsed = JSON.parse(data) as AgentStreamEvent;
            yield parsed;
          } catch {
            // skip malformed data
          }
        }
      }
    }
  },

  getRun: (runId: string) =>
    fetchApi<AgentRun>(`/api/v1/agent/runs/${runId}`),

  confirmRun: (runId: string) =>
    fetchApi<{ run: AgentRun }>(`/api/v1/agent/runs/${runId}/confirm`, {
      method: "POST",
    }),

  confirmHighRiskRun: (runId: string) =>
    fetchApi<{ run: AgentRun }>(`/api/v1/agent/runs/${runId}/confirm-high-risk`, {
      method: "POST",
    }),

  cancelRun: (runId: string) =>
    fetchApi<{ run: AgentRun }>(`/api/v1/agent/runs/${runId}/cancel`, {
      method: "POST",
    }),
};

// ============================================================================
// Suggestion API (enhanced)
// ============================================================================

export const suggestionApi = {
  list: (projectId: string, params?: { status?: string; skip?: number; limit?: number }) =>
    fetchApi<Suggestion[]>(
      `/api/v1/suggestions${buildQueryString({ project_id: projectId, ...params })}`
    ),

  get: (id: string) =>
    fetchApi<Suggestion>(`/api/v1/suggestions/${id}`),

  action: (id: string, action: "confirm" | "discard" | "commit") =>
    fetchApi<{ success: boolean; message: string }>(
      `/api/v1/suggestions/${id}/action`,
      {
        method: "POST",
        body: JSON.stringify({ action }),
      }
    ),

  pendingCount: (projectId: string) =>
    fetchApi<{ count: number }>(
      `/api/v1/suggestions/pending/count${buildQueryString({ project_id: projectId })}`
    ),
};

// ============================================================================
// Export API
// ============================================================================

export const exportApi = {
  download: async (projectId: string, format: "txt" | "markdown" = "txt") => {
    const url = `${API_BASE_URL}/api/v1/projects/${projectId}/export?format=${format}`;
    const headers = await buildAuthenticatedHeaders();

    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new ApiError(response.status, "Export failed");
    }

    const blob = await response.blob();
    const filename = format === "txt" ? "novel.txt" : "novel.md";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  },
};

export interface ProjectImportWarning {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ProjectImportResponse {
  project_id: string;
  project_name: string;
  imported_counts: Record<string, number>;
  warnings: ProjectImportWarning[];
}

export const projectPackageApi = {
  downloadPackage: async (projectId: string, projectName: string) => {
    const url = `${API_BASE_URL}/api/v1/projects/${projectId}/package`;
    const headers = await buildAuthenticatedHeaders();

    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new ApiError(response.status, "Package export failed");
    }

    const blob = await response.blob();
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const filename = `${projectName}_package_${timestamp}.zip`;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  },

  importPackage: async (file: File, newName?: string): Promise<ProjectImportResponse> => {
    const url = `${API_BASE_URL}/api/v1/projects/import${newName ? `?new_name=${encodeURIComponent(newName)}` : ""}`;
    const headers = await buildAuthenticatedHeaders();
    delete headers["Content-Type"];

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        errorData?.detail || "Package import failed"
      );
    }

    return response.json();
  },
};
