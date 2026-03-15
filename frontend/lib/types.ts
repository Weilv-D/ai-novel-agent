// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiErrorResponse {
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
  agent_profile_id: string;
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
  agent_profile_id?: string;
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
  agent_profile_id?: string;
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

// Volume types
export interface Volume {
  id: string;
  project_id: string;
  volume_number?: number;
  title?: string;
  outline?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface VolumeCreate {
  project_id: string;
  volume_number?: number;
  title?: string;
  outline?: string;
  notes?: string;
}

export interface VolumeUpdate {
  volume_number?: number;
  title?: string;
  outline?: string;
  notes?: string;
}

// Memory types
export type MemoryType = "episode" | "semantic" | "fact";

export interface Memory {
  id: string;
  project_id: string;
  memory_type: MemoryType;
  content: string;
  meta: Record<string, unknown>;
  embedding?: number[] | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryCreate {
  project_id: string;
  memory_type: MemoryType;
  content: string;
  meta?: Record<string, unknown>;
  embedding?: number[] | null;
  auto_embed?: boolean;
}

export interface MemoryUpdate {
  memory_type?: MemoryType;
  content?: string;
  meta?: Record<string, unknown>;
  embedding?: number[] | null;
  auto_embed?: boolean;
}

export interface MemoryMatch {
  id: string;
  memory_type: MemoryType;
  content: string;
  meta: Record<string, unknown>;
  similarity: number;
}

export interface VectorSearchResponse {
  matches: MemoryMatch[];
  total_count: number;
  search_summary?: string | null;
}

// Snapshot types
export type SnapshotTargetType =
  | "project"
  | "character"
  | "world_setting"
  | "volume"
  | "chapter"
  | "scene"
  | "suggestion";

export interface Snapshot {
  id: string;
  project_id: string;
  target_type: SnapshotTargetType;
  target_id: string;
  data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface SnapshotCreate {
  project_id: string;
  target_type: SnapshotTargetType;
  target_id: string;
  data: Record<string, unknown>;
}

export interface SnapshotUpdate {
  data?: Record<string, unknown>;
}

export interface RollbackResponse {
  snapshot_id: string;
  target_type: SnapshotTargetType;
  target_id: string;
  rolled_back_at: string;
  message: string;
}

// Dependency types
export type DependencyEntityType =
  | "project"
  | "character"
  | "world_setting"
  | "volume"
  | "chapter"
  | "scene"
  | "suggestion";

export type DependencyType = "references" | "influences" | "contains" | "precedes";

export interface Dependency {
  id: string;
  project_id: string;
  source_type: DependencyEntityType;
  source_id: string;
  target_type: DependencyEntityType;
  target_id: string;
  dependency_type?: DependencyType | null;
  created_at: string;
  updated_at: string;
}

export interface DependencyCreate {
  project_id: string;
  source_type: DependencyEntityType;
  source_id: string;
  target_type: DependencyEntityType;
  target_id: string;
  dependency_type?: DependencyType | null;
}

export interface DependencyUpdate {
  dependency_type?: DependencyType | null;
}

export interface ImpactDetail {
  target_type: DependencyEntityType;
  target_id: string;
  dependency_type?: DependencyType | null;
  description?: string | null;
}

export interface ImpactAnalysisResponse {
  source_type: DependencyEntityType;
  source_id: string;
  impacted_objects: ImpactDetail[];
  total_count: number;
  analysis_summary?: string | null;
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

export type SuggestionTargetType = "character" | "world_setting" | "chapter" | "scene";
export type SuggestionAction = "confirm" | "discard" | "commit";

export interface Suggestion {
  id: string;
  project_id: string;
  target_type: SuggestionTargetType;
  target_id: string;
  type: SuggestionType;
  content: Record<string, unknown>;
  status: SuggestionStatus;
  impact_analysis?: Record<string, unknown> | null;
  committed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SuggestionCreate {
  project_id: string;
  target_type: SuggestionTargetType;
  target_id: string;
  type: SuggestionType;
  content: Record<string, unknown>;
  status?: SuggestionStatus;
}

export interface SuggestionActionRequest {
  action: SuggestionAction;
  impact_analysis?: Record<string, unknown> | null;
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

// Agent workflow types
export type AgentMessageRole = "user" | "assistant" | "system";
export type RunStatus =
  | "draft"
  | "awaiting_confirmation"
  | "awaiting_high_risk_confirmation"
  | "executing"
  | "completed"
  | "failed"
  | "cancelled"
  | "superseded";
export type OperationStatus = "planned" | "executed" | "failed" | "cancelled";
export type AgentSubtaskRole = "planner" | "researcher" | "writer" | "editor" | "continuity";
export type AgentSubtaskStatus = "planned" | "completed" | "failed" | "skipped";
export type AgentPermissionLevel = "read_search" | "standard_write" | "high_risk_write";
export type AgentRiskLevel = "low" | "medium" | "high";
export type AgentVerificationStatus = "pending" | "passed" | "failed" | "skipped";
export type AgentHookName = "PreCompact" | "PrePlan" | "SubagentStop" | "RunStop";

export interface OperationPreview {
  changed_fields: string[];
  before_summary?: string | null;
  after_summary?: string | null;
  diff?: string | null;
  reason?: string | null;
}

export interface AgentThread {
  id: string;
  project_id: string;
  title: string;
  is_default: boolean;
  meta: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AgentThreadMessage {
  id: string;
  thread_id: string;
  role: AgentMessageRole;
  content: string;
  meta: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AgentOperation {
  id: string;
  run_id: string;
  position: number;
  tool_name: string;
  target_type?: string | null;
  target_id?: string | null;
  target_display?: string | null;
  description: string;
  reason?: string | null;
  payload: Record<string, unknown>;
  preview: OperationPreview;
  permission_level: AgentPermissionLevel;
  risk_level: AgentRiskLevel;
  requires_secondary_confirmation: boolean;
  status: OperationStatus;
  verification_status: AgentVerificationStatus;
  verification_summary?: string | null;
  execution_result?: Record<string, unknown> | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentSubtask {
  id: string;
  run_id: string;
  position: number;
  role: AgentSubtaskRole;
  title: string;
  status: AgentSubtaskStatus;
  summary?: string | null;
  error_message?: string | null;
  meta: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AgentThreadCheckpoint {
  id: string;
  thread_id: string;
  profile_id: string;
  thread_summary: string;
  active_object_bundle: Record<string, unknown>;
  recent_run_digest: Record<string, unknown>;
  source_message_count: number;
  source_run_count: number;
  total_context_characters: number;
  created_at: string;
  updated_at: string;
}

export interface AgentHookTraceEntry {
  hook_name: AgentHookName;
  status: AgentSubtaskStatus;
  summary?: string | null;
  meta: Record<string, unknown>;
}

export interface AgentRun {
  id: string;
  thread_id: string;
  project_id: string;
  user_message_id?: string | null;
  assistant_message_id?: string | null;
  revision_of_run_id?: string | null;
  status: RunStatus;
  summary?: string | null;
  error_message?: string | null;
  warning_message?: string | null;
  verification_status: AgentVerificationStatus;
  verification_summary?: string | null;
  meta: Record<string, unknown>;
  confirmed_at?: string | null;
  secondary_confirmed_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  operations: AgentOperation[];
  subtasks: AgentSubtask[];
}

export interface AgentThreadState {
  thread: AgentThread;
  messages: AgentThreadMessage[];
  recent_runs: AgentRun[];
  current_run?: AgentRun | null;
  latest_checkpoint?: AgentThreadCheckpoint | null;
}

export interface AgentThreadMessageRequest {
  content: string;
  context?: Record<string, unknown>;
  stream?: boolean;
}

export interface AgentThreadMessageResponse {
  thread: AgentThread;
  user_message: AgentThreadMessage;
  assistant_message: AgentThreadMessage;
  run?: AgentRun | null;
}

export interface AgentProfile {
  id: string;
  name: string;
  description: string;
  builtin: boolean;
  root: string;
}

export interface AgentSkillSummary {
  name: string;
  description: string;
  kind: string;
  tool_name?: string | null;
  source: string;
  payload_contract?: string | null;
  references: string[];
}

export interface AgentSkillCatalog {
  profile_id: string;
  profile_name: string;
  builtin: boolean;
  source_roots: string[];
  planner: AgentSkillSummary;
  operations: AgentSkillSummary[];
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
