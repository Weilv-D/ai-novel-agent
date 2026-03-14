/**
 * API Client for AI Novel Agent Backend
 * Handles HTTP requests to the FastAPI backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

/**
 * Core fetch wrapper with error handling and authentication
 */
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const apiKey = typeof window !== "undefined" ? localStorage.getItem("api_key") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (apiKey) {
    headers["X-API-Key"] = apiKey;
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
    throw new ApiError(
      response.status,
      (data as { detail?: string; message?: string })?.detail
        || (data as { detail?: string; message?: string })?.message
        || "An error occurred",
      data
    );
  }

  return data as T;
}

// ============================================================================
// Health API
// ============================================================================

export interface HealthResponse {
  status: string;
  version: string;
}

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
