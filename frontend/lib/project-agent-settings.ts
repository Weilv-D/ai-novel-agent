import type { ProjectAgentSettings } from "@/lib/types";

export const DEFAULT_PROJECT_AGENT_SETTINGS: ProjectAgentSettings = {
  style_goal: null,
  tone_keywords: [],
  voice_constraints: [],
  forbidden_patterns: [],
  terminology_glossary: [],
  chapter_target_chars: 6000,
  scene_target_chars: null,
  continuity_mode: "strict",
};

export function parseMultilineList(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinMultilineList(value: string[] | undefined | null): string {
  return (value || []).join("\n");
}

export function normalizeProjectAgentSettings(
  value?: Partial<ProjectAgentSettings> | null,
): ProjectAgentSettings {
  return {
    ...DEFAULT_PROJECT_AGENT_SETTINGS,
    ...(value || {}),
    tone_keywords: [...(value?.tone_keywords || [])],
    voice_constraints: [...(value?.voice_constraints || [])],
    forbidden_patterns: [...(value?.forbidden_patterns || [])],
    terminology_glossary: [...(value?.terminology_glossary || [])],
  };
}
