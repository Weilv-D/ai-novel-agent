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

export type ProjectContinuityMode = "standard" | "strict";

export interface ProjectAgentSettings {
  style_goal?: string | null;
  tone_keywords: string[];
  voice_constraints: string[];
  forbidden_patterns: string[];
  terminology_glossary: string[];
  chapter_target_chars?: number | null;
  scene_target_chars?: number | null;
  continuity_mode: ProjectContinuityMode;
}

export interface Project {
  id: string;
  name: string;
  genre?: string;
  target_audience?: string;
  target_word_count?: number;
  summary?: string;
  story_outline?: string;
  notes?: string;
  agent_profile_id: string;
  agent_settings: ProjectAgentSettings;
  meta?: Record<string, unknown>;
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
  story_outline?: string;
  notes?: string;
  agent_profile_id?: string;
  agent_settings?: ProjectAgentSettings;
  meta?: Record<string, unknown>;
  status?: ProjectStatus;
}

export interface ProjectUpdate {
  name?: string;
  genre?: string;
  target_audience?: string;
  target_word_count?: number;
  summary?: string;
  story_outline?: string;
  notes?: string;
  agent_profile_id?: string;
  agent_settings?: ProjectAgentSettings | null;
  meta?: Record<string, unknown>;
  status?: ProjectStatus;
}

export interface ProjectTreeScene {
  id: string;
  chapter_id: string;
  scene_order: number;
  location?: string | null;
  pov_character_id?: string | null;
}

export interface ProjectTreeChapter {
  id: string;
  project_id: string;
  volume_id?: string | null;
  chapter_number: number;
  title?: string | null;
  outline?: string | null;
  status: string;
  scenes: ProjectTreeScene[];
}

export interface ProjectTreeVolume {
  id: string;
  project_id: string;
  volume_number?: number | null;
  title?: string | null;
  outline?: string | null;
  chapters: ProjectTreeChapter[];
}

export interface ProjectTree {
  project_id: string;
  volumes: ProjectTreeVolume[];
  ungrouped_chapters: ProjectTreeChapter[];
}

export interface ProjectWorkspaceSummary {
  volume_count: number;
  chapter_count: number;
  scene_count: number;
  character_count: number;
  world_setting_count: number;
  latest_run_status?: string | null;
  context_source: string;
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

export interface ChapterReorderRequest {
  project_id: string;
  volume_id: string;
  chapter_ids: string[];
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

export interface SceneReorderRequest {
  chapter_id: string;
  scene_ids: string[];
}

export type InlineEditOperation = "rewrite" | "expand" | "condense" | "change_pov";

export interface InlineEditRequest {
  text: string;
  operation: InlineEditOperation;
  context?: Record<string, unknown>;
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

export interface ProjectTimelineVolume {
  id: string;
  volume_number?: number | null;
  title?: string | null;
}

export interface ProjectTimelineEvent {
  id: string;
  memory_type: MemoryType | string;
  title: string;
  summary: string;
  content: string;
  meta: Record<string, unknown>;
  chapter_id?: string | null;
  chapter_number?: number | null;
  chapter_title?: string | null;
  scene_id?: string | null;
  scene_order?: number | null;
  location?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectTimelineChapter {
  id: string;
  volume?: ProjectTimelineVolume | null;
  chapter_number: number;
  title?: string | null;
  status: ChapterStatus;
  outline?: string | null;
  event_count: number;
  events: ProjectTimelineEvent[];
  created_at: string;
  updated_at: string;
}

export interface ProjectTimelineResponse {
  project_id: string;
  chapters: ProjectTimelineChapter[];
  unassigned_events: ProjectTimelineEvent[];
  total_events: number;
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

export type SuggestionTargetType = "project" | "character" | "world_setting" | "volume" | "chapter" | "scene";
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
export type AgentExecutionPhase = "plan" | "build";
export type AgentExecutionMode = "restricted" | "gated";
export type AgentRetryStrategy = "service_only" | "planner_then_service_fallback";
export type AgentConfirmationGate = "none" | "single" | "double";
export type AgentCapabilityKind = "read_search" | "planning" | "writing" | "editing" | "verification";
export type AgentCapabilitySourceRole = AgentSubtaskRole | "executor";
export type AgentChildUnitRole = AgentSubtaskRole | "executor";
export type AgentChildUnitStage = "preview" | "pre_execution" | "execution";
export type AgentRiskPolicyId =
  | "create_only"
  | "standard_updates"
  | "content_append"
  | "content_rewrite"
  | "long_form_overwrite"
  | "multi_object_write";
export type AgentRiskPolicyScope = "operation" | "run";
export type AgentPipelineStage = "research" | "brief" | "draft" | "polish" | "continuity_precheck" | "plan_ready";
export type AgentPipelineStepStatus = "planned" | "completed" | "failed" | "skipped" | "warning";

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
  child_trace?: AgentSubtaskTrace | null;
  pipeline_steps: AgentPipelineStep[];
  meta: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AgentPipelineStep {
  id: string;
  role: AgentSubtaskRole;
  stage: AgentPipelineStage;
  status: AgentPipelineStepStatus;
  summary: string;
  warnings: string[];
  facts_used: string[];
}

export interface AgentSubtaskAttempt {
  attempt_number: number;
  source: string;
  accepted: boolean;
  validation_status: "passed" | "recovered" | "failed";
  summary: string;
}

export interface AgentSubtaskTrace {
  unit_id: string;
  role: AgentSubtaskRole;
  execution_phase: "plan" | "build_validation";
  retry_strategy: AgentRetryStrategy;
  depends_on: string[];
  operation_positions: number[];
  tool_scope: string[];
  input_summary?: string | null;
  output_summary?: string | null;
  attempts: AgentSubtaskAttempt[];
}

export interface AgentCapability {
  capability_id: string;
  name: string;
  kind: AgentCapabilityKind;
  description: string;
  tool_scope: string[];
  policy: AgentCapabilityPolicy;
  execution_record?: AgentCapabilityExecutionRecord | null;
}

export interface AgentCapabilityExecutionRecord {
  record_id: string;
  source_role: AgentCapabilitySourceRole;
  status: "planned" | "completed" | "failed" | "skipped";
  tool_scope: string[];
  input_summary?: string | null;
  output_summary?: string | null;
  attempt_count: number;
}

export interface AgentCapabilityPolicy {
  execution_phase: AgentExecutionPhase;
  source_role: AgentCapabilitySourceRole;
  confirmation_gate: AgentConfirmationGate;
  internal_only: boolean;
  requires_confirmation: boolean;
}

export interface AgentExecutionChildUnit {
  unit_id: string;
  role: AgentChildUnitRole;
  phase: AgentExecutionPhase;
  stage: AgentChildUnitStage;
  mode: AgentExecutionMode;
  title: string;
  description: string;
  tool_scope: string[];
  capability_ids: string[];
  depends_on: string[];
  operation_positions: number[];
  confirmation_gate: AgentConfirmationGate;
  requires_confirmation: boolean;
  internal_only: boolean;
}

export interface AgentExecutionContractPhase {
  phase: AgentExecutionPhase;
  mode: AgentExecutionMode;
  allowed_permission_levels: AgentPermissionLevel[];
  tool_scope: string[];
  role_scope: AgentSubtaskRole[];
  confirmation_gate: AgentConfirmationGate;
  requires_confirmation: boolean;
  requires_secondary_confirmation: boolean;
  operation_count: number;
  child_units: AgentExecutionChildUnit[];
  capabilities: AgentCapability[];
}

export interface AgentExecutionContract {
  registry_version: string;
  phases: AgentExecutionContractPhase[];
}

export interface AgentCapabilityRegistry {
  registry_version: string;
  capabilities: AgentCapability[];
}

export interface AgentRiskPolicy {
  policy_id: AgentRiskPolicyId;
  name: string;
  scope: AgentRiskPolicyScope;
  description: string;
  risk_level: AgentRiskLevel;
  confirmation_gate: AgentConfirmationGate;
  requires_secondary_confirmation: boolean;
  tool_scope: string[];
}

export interface AgentAppliedRiskPolicy {
  policy_id: AgentRiskPolicyId;
  name: string;
  scope: AgentRiskPolicyScope;
  description: string;
  risk_level: AgentRiskLevel;
  confirmation_gate: AgentConfirmationGate;
  requires_secondary_confirmation: boolean;
  matched_operation_positions: number[];
}

export interface AgentRiskPolicyRegistry {
  policy_version: string;
  policies: AgentRiskPolicy[];
}

export interface AgentRunRiskSummary {
  policy_version: string;
  overall_risk_level: AgentRiskLevel;
  confirmation_gate: AgentConfirmationGate;
  requires_confirmation: boolean;
  requires_secondary_confirmation: boolean;
  total_operations: number;
  low_risk_operation_count: number;
  medium_risk_operation_count: number;
  high_risk_operation_count: number;
  high_risk_operation_positions: number[];
  secondary_confirmation_operation_positions: number[];
  applied_policies: AgentAppliedRiskPolicy[];
  summary: string;
}

export type AgentPlannerHistoryMode = "recent_window" | "checkpoint_delta";

export interface AgentCompactPolicy {
  policy_version: string;
  message_threshold: number;
  run_threshold: number;
  char_threshold: number;
  recent_window_limit: number;
  checkpoint_delta_limit: number;
}

export interface AgentRetainedWindow {
  history_mode: AgentPlannerHistoryMode;
  message_count: number;
  character_count: number;
  retained_message_limit: number;
  oldest_message_id?: string | null;
  newest_message_id?: string | null;
  checkpoint_id?: string | null;
  compact_policy_version?: string | null;
  roles: string[];
}

export interface AgentCompactionBoundary {
  history_mode: AgentPlannerHistoryMode;
  source_message_count: number;
  source_run_count: number;
}

export interface AgentActiveBundleCollections {
  characters_count: number;
  characters_limit: number;
  world_settings_count: number;
  world_settings_limit: number;
  volumes_count: number;
  volumes_limit: number;
  chapters_count: number;
  chapters_limit: number;
  current_scenes_count: number;
  current_scenes_limit: number;
  recent_run_digest_count: number;
  recent_run_digest_limit: number;
}

export interface AgentActiveBundleContract {
  contract_version: string;
  source: "live_context" | "checkpoint_plus_live_context" | "checkpoint_snapshot";
  included_sections: string[];
  focused_object_types: string[];
  checkpoint_id?: string | null;
  includes_thread_summary: boolean;
  includes_recent_run_digest: boolean;
  collections: AgentActiveBundleCollections;
}

export interface AgentPlannerWindow {
  history_mode: AgentPlannerHistoryMode;
  history_message_count: number;
  retained_message_limit: number;
  checkpoint_id?: string | null;
  checkpoint_available: boolean;
  compact_policy_version?: string | null;
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
  compact_policy?: AgentCompactPolicy | null;
  compaction_boundary?: AgentCompactionBoundary | null;
  active_bundle_contract?: AgentActiveBundleContract | null;
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
  execution_contract?: AgentExecutionContract | null;
  risk_summary?: AgentRunRiskSummary | null;
  compact_policy?: AgentCompactPolicy | null;
  planner_window?: AgentPlannerWindow | null;
  retained_window?: AgentRetainedWindow | null;
  active_bundle_contract?: AgentActiveBundleContract | null;
  plan_expires_at?: string | null;
  plan_basis?: AgentPlanBasis | null;
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

export interface AgentPlanBasisEntityVersion {
  entity_type: string;
  entity_id: string;
  updated_at: string;
}

export interface AgentPlanBasis {
  entity_versions: AgentPlanBasisEntityVersion[];
  context_fingerprint: string;
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

export type AgentStreamEventType =
  | "status"
  | "thinking"
  | "operation_progress"
  | "pipeline_stage"
  | "verification"
  | "message_chunk"
  | "result"
  | "error";

export interface AgentStreamEvent {
  type: AgentStreamEventType;
  timestamp: string;
  stage: string | null;
  message: string | null;
  detail: Record<string, unknown>;
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

export interface ProjectWorkspace {
  project: Project;
  agent_settings: ProjectAgentSettings;
  tree: ProjectTree;
  default_thread?: AgentThread | null;
  latest_checkpoint?: AgentThreadCheckpoint | null;
  current_run?: AgentRun | null;
  recent_runs: AgentRun[];
  workspace_summary: ProjectWorkspaceSummary;
}

export type TextImportPhase =
  | "structure_detection"
  | "outline_extraction"
  | "character_extraction"
  | "world_setting_extraction"
  | "completed"
  | "error";

export interface TextImportProgress {
  phase: TextImportPhase;
  progress: number;
  message: string;
  data: Record<string, unknown>;
}

export interface DetectedChapter {
  chapter_number: number;
  title?: string | null;
  content: string;
  outline?: string | null;
  content_length?: number | null;
  content_truncated?: boolean;
}

export interface DetectedVolume {
  volume_number: number;
  title?: string | null;
  outline?: string | null;
  chapter_numbers: number[];
}

export interface DetectedCharacter {
  name: string;
  role?: string | null;
  profile: Record<string, unknown>;
  relationships: Record<string, unknown>;
}

export interface DetectedWorldSetting {
  category: string;
  name: string;
  content: string;
}

export interface TextImportPreview {
  preview_id?: string | null;
  compact_preview?: boolean;
  project_name: string;
  genre?: string | null;
  summary?: string | null;
  story_outline?: string | null;
  volumes: DetectedVolume[];
  chapters: DetectedChapter[];
  characters: DetectedCharacter[];
  world_settings: DetectedWorldSetting[];
  warnings: string[];
  failed_phases: TextImportPhase[];
  source_filename?: string | null;
  source_encoding?: string | null;
}

export interface TextImportResponse {
  project_id: string;
  project_name: string;
  imported_counts: Record<string, number>;
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
