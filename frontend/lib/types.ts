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
  CONCEPTION = "conception",
  BUILDING = "building",
  PUBLISHING = "publishing",
  REFINING = "refining",
  COMPLETED = "completed",
}

export interface Project {
  id: string;
  title: string;
  summary?: string;
  notes?: string;
  genre?: string;
  target_audience?: string;
  target_word_count?: number;
  current_word_count: number;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  title: string;
  genre?: string;
  target_audience?: string;
  target_word_count?: number;
  status?: ProjectStatus;
}

export interface ProjectUpdate {
  title?: string;
  summary?: string;
  notes?: string;
  genre?: string;
  target_audience?: string;
  target_word_count?: number;
  status?: ProjectStatus;
  current_word_count?: number;
}

// Character types
export interface Character {
  id: string;
  project_id: string;
  name: string;
  age?: number;
  gender?: string;
  appearance?: string;
  personality?: string;
  background?: string;
  role?: string;
  created_at: string;
  updated_at: string;
}

export interface CharacterCreate {
  project_id: string;
  name: string;
  age?: number;
  gender?: string;
  appearance?: string;
  personality?: string;
  background?: string;
  role?: string;
}

export interface CharacterUpdate {
  name?: string;
  age?: number;
  gender?: string;
  appearance?: string;
  personality?: string;
  background?: string;
  role?: string;
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
export interface Chapter {
  id: string;
  project_id: string;
  volume_id?: string;
  title: string;
  summary?: string;
  notes?: string;
  order: number;
  word_count: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ChapterCreate {
  project_id: string;
  volume_id?: string;
  title: string;
  summary?: string;
  notes?: string;
  order: number;
  word_count?: number;
  status?: string;
}

export interface ChapterUpdate {
  title?: string;
  summary?: string;
  notes?: string;
  order?: number;
  word_count?: number;
  status?: string;
}

// Scene types
export interface Scene {
  id: string;
  chapter_id: string;
  title?: string;
  content?: string;
  order: number;
  pov_character_id?: string;
  location?: string;
  created_at: string;
  updated_at: string;
}

export interface SceneCreate {
  chapter_id: string;
  title?: string;
  content?: string;
  order: number;
  pov_character_id?: string;
  location?: string;
}

export interface SceneUpdate {
  title?: string;
  content?: string;
  order?: number;
  pov_character_id?: string;
  location?: string;
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
