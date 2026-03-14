// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiError {
  detail: string;
  status: number;
}

// Project types (aligned with backend schemas)
export enum ProjectStatus {
  DRAFTING = "drafting",
  WRITING = "writing",
  REVISING = "revising",
  COMPLETED = "completed",
}

export interface Project {
  id: string;
  name: string;
  genre?: string;
  target_audience?: string;
  target_word_count?: number;
  summary?: string;
  notes?: string;
  meta?: Record<string, unknown>;
  user_id: string;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  genre?: string;
  target_audience?: string;
  target_word_count?: number;
  summary?: string;
  notes?: string;
  meta?: Record<string, unknown>;
  status?: ProjectStatus;
}

export interface ProjectUpdate {
  name?: string;
  genre?: string;
  target_audience?: string;
  target_word_count?: number;
  summary?: string;
  notes?: string;
  meta?: Record<string, unknown>;
  status?: ProjectStatus;
}

// Character types
export interface Character {
  id: string;
  project_id: string;
  name: string;
  role?: string;
  profile?: Record<string, unknown>;
  relationships?: Record<string, unknown>;
  arc_state?: Record<string, unknown>;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface CharacterCreate {
  project_id: string;
  name: string;
  role?: string;
  profile?: Record<string, unknown>;
  relationships?: Record<string, unknown>;
  arc_state?: Record<string, unknown>;
  notes?: string;
}

export interface CharacterUpdate {
  name?: string;
  role?: string;
  profile?: Record<string, unknown>;
  relationships?: Record<string, unknown>;
  arc_state?: Record<string, unknown>;
  notes?: string;
}

// WorldSetting types
export interface WorldSetting {
  id: string;
  project_id: string;
  category: string;
  name: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface WorldSettingCreate {
  project_id: string;
  category: string;
  name: string;
  content: string;
}

export interface WorldSettingUpdate {
  category?: string;
  name?: string;
  content?: string;
}

// Chapter types
export enum ChapterStatus {
  DRAFT = "draft",
  WRITING = "writing",
  COMPLETED = "completed",
}

export interface Chapter {
  id: string;
  project_id: string;
  volume_id?: string;
  chapter_number: number;
  title?: string;
  outline?: string;
  content?: string;
  status: ChapterStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface ChapterCreate {
  project_id: string;
  volume_id?: string;
  chapter_number: number;
  title?: string;
  outline?: string;
  content?: string;
  status?: ChapterStatus;
  notes?: string;
}

export interface ChapterUpdate {
  chapter_number?: number;
  title?: string;
  outline?: string;
  content?: string;
  status?: ChapterStatus;
  notes?: string;
  volume_id?: string;
}

// Scene types
export interface Scene {
  id: string;
  chapter_id: string;
  scene_order: number;
  pov_character_id?: string;
  location?: string;
  content?: string;
  meta?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SceneCreate {
  chapter_id: string;
  scene_order: number;
  pov_character_id?: string;
  location?: string;
  content?: string;
  meta?: Record<string, unknown>;
}

export interface SceneUpdate {
  scene_order?: number;
  pov_character_id?: string;
  location?: string;
  content?: string;
  meta?: Record<string, unknown>;
}

// Memory types
export interface Memory {
  id: string;
  project_id: string;
  chapter_id?: string;
  fact_type: string;
  content: string;
  embedding?: number[];
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MemoryCreate {
  project_id: string;
  chapter_id?: string;
  fact_type: string;
  content: string;
  metadata?: Record<string, unknown>;
}

// Snapshot types
export interface Snapshot {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  created_at: string;
}

export interface SnapshotCreate {
  project_id: string;
  name: string;
  description?: string;
}

// Dependency types
export interface Dependency {
  id: string;
  source_type: string;
  source_id: string;
  target_type: string;
  target_id: string;
  dependency_type: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface DependencyCreate {
  source_type: string;
  source_id: string;
  target_type: string;
  target_id: string;
  dependency_type: string;
  metadata?: Record<string, unknown>;
}

export interface DependencyAnalysis {
  affected_objects: Array<{
    type: string;
    id: string;
    name: string;
    impact_level: string;
  }>;
  risks: string[];
}

// Suggestion types
export type SuggestionStatus = "draft" | "patched" | "committed" | "discarded";
export type SuggestionType =
  | "character_edit"
  | "world_edit"
  | "chapter_edit"
  | "scene_edit"
  | "content_gen"
  | "outline_gen"
  | "continuity_fix";

export interface Suggestion {
  id: string;
  project_id: string;
  target_type: string;
  target_id: string;
  type: SuggestionType;
  content: Record<string, unknown>;
  status: SuggestionStatus;
  impact_analysis?: Record<string, unknown>;
  committed_at?: string;
  created_at: string;
  updated_at: string;
}

// Chat types
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  suggestions?: Suggestion[];
  metadata?: Record<string, unknown>;
  timestamp: number;
}

export interface AgentChatRequest {
  project_id: string;
  message: string;
  history: Array<{ role: string; content: string }>;
  context?: Record<string, unknown>;
}

export interface AgentChatResponse {
  message: string;
  suggestions: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
}
