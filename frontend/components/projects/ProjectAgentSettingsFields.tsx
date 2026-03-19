"use client";

import { Input, Textarea } from "@/components/ui/Input";
import {
  joinMultilineList,
  parseMultilineList,
} from "@/lib/project-agent-settings";
import type { ProjectAgentSettings } from "@/lib/types";

interface ProjectAgentSettingsFieldsProps {
  value: ProjectAgentSettings;
  onChange: (next: ProjectAgentSettings) => void;
}

function updateListField(
  value: ProjectAgentSettings,
  field: "tone_keywords" | "voice_constraints" | "forbidden_patterns" | "terminology_glossary",
  raw: string,
): ProjectAgentSettings {
  return {
    ...value,
    [field]: parseMultilineList(raw),
  };
}

export function ProjectAgentSettingsFields({
  value,
  onChange,
}: ProjectAgentSettingsFieldsProps) {
  return (
    <div className="space-y-6 rounded-[1.1rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-strong)] px-4 py-5">
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
          Agent Settings
        </div>
        <p className="mt-2 text-sm leading-6 text-[rgb(var(--ink-800))]">
          这些配置会覆盖 profile 的默认风格，并统一作用于写作 brief、draft、polish 和连续性检查。
        </p>
      </div>

      <Textarea
        label="风格目标"
        placeholder="例如：冷峻、克制、强调政治博弈中的压迫感。"
        value={value.style_goal || ""}
        onChange={(event) =>
          onChange({
            ...value,
            style_goal: event.target.value.trim() ? event.target.value : null,
          })
        }
        rows={4}
      />

      <div className="grid gap-6 md:grid-cols-2">
        <Textarea
          label="语气关键词"
          placeholder="每行一个，例如：克制&#10;压迫感&#10;古典"
          value={joinMultilineList(value.tone_keywords)}
          onChange={(event) => onChange(updateListField(value, "tone_keywords", event.target.value))}
          rows={6}
        />
        <Textarea
          label="叙述约束"
          placeholder="每行一个，例如：优先第三人称限知&#10;句子不要过分口语化"
          value={joinMultilineList(value.voice_constraints)}
          onChange={(event) => onChange(updateListField(value, "voice_constraints", event.target.value))}
          rows={6}
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Textarea
          label="禁忌模式"
          placeholder="每行一个，例如：不要现代网络流行语&#10;不要总结式结尾"
          value={joinMultilineList(value.forbidden_patterns)}
          onChange={(event) => onChange(updateListField(value, "forbidden_patterns", event.target.value))}
          rows={6}
        />
        <Textarea
          label="术语表"
          placeholder="每行一个，例如：玄甲卫&#10;镇岳司&#10;九州历"
          value={joinMultilineList(value.terminology_glossary)}
          onChange={(event) => onChange(updateListField(value, "terminology_glossary", event.target.value))}
          rows={6}
        />
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Input
          label="章节目标字数"
          type="number"
          min={1}
          value={value.chapter_target_chars || ""}
          onChange={(event) =>
            onChange({
              ...value,
              chapter_target_chars: event.target.value ? parseInt(event.target.value, 10) : null,
            })
          }
        />
        <Input
          label="场景目标字数"
          type="number"
          min={1}
          value={value.scene_target_chars || ""}
          onChange={(event) =>
            onChange({
              ...value,
              scene_target_chars: event.target.value ? parseInt(event.target.value, 10) : null,
            })
          }
        />
        <div>
          <label className="ink-label">连续性模式</label>
          <select
            value={value.continuity_mode}
            onChange={(event) =>
              onChange({
                ...value,
                continuity_mode: event.target.value as ProjectAgentSettings["continuity_mode"],
              })
            }
            className="ink-select"
          >
            <option value="strict">严格</option>
            <option value="standard">标准</option>
          </select>
          <p className="mt-2 text-sm leading-6 text-[rgb(var(--ink-800))]">
            严格模式会更积极阻断事实、时间线和风格冲突。
          </p>
        </div>
      </div>
    </div>
  );
}
