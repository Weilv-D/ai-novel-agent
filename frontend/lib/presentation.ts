import type { ChapterStatus, ProjectStatus } from "@/lib/types";

interface StatusMeta {
  label: string;
  className: string;
}

const DEFAULT_STATUS_META: StatusMeta = {
  label: "未定义",
  className: "ink-badge ink-badge-smoke",
};

const PROJECT_STATUS_META: Record<string, StatusMeta> = {
  drafting: { label: "草稿中", className: "ink-badge ink-badge-ash" },
  writing: { label: "写作中", className: "ink-badge ink-badge-rust" },
  revising: { label: "修订中", className: "ink-badge ink-badge-amber" },
  completed: { label: "已完成", className: "ink-badge ink-badge-jade" },
};

const CHAPTER_STATUS_META: Record<string, StatusMeta> = {
  draft: { label: "草稿", className: "ink-badge ink-badge-ash" },
  writing: { label: "写作中", className: "ink-badge ink-badge-rust" },
  completed: { label: "已完成", className: "ink-badge ink-badge-jade" },
};

const SUGGESTION_STATUS_META: Record<string, StatusMeta> = {
  draft: { label: "待确认", className: "ink-badge ink-badge-amber" },
  patched: { label: "已确认", className: "ink-badge ink-badge-rust" },
  committed: { label: "已应用", className: "ink-badge ink-badge-jade" },
  discarded: { label: "已丢弃", className: "ink-badge ink-badge-smoke" },
};

const IMPACT_LEVEL_CLASS: Record<string, string> = {
  high: "ink-badge ink-badge-rust",
  medium: "ink-badge ink-badge-amber",
  low: "ink-badge ink-badge-jade",
};

export function getProjectStatusMeta(status: ProjectStatus | string): StatusMeta {
  return PROJECT_STATUS_META[status] || {
    label: status,
    className: DEFAULT_STATUS_META.className,
  };
}

export function getChapterStatusMeta(status: ChapterStatus | string): StatusMeta {
  return CHAPTER_STATUS_META[status] || {
    label: status,
    className: DEFAULT_STATUS_META.className,
  };
}

export function getSuggestionStatusMeta(status: string): StatusMeta {
  return SUGGESTION_STATUS_META[status] || {
    label: status,
    className: DEFAULT_STATUS_META.className,
  };
}

export function getImpactLevelClass(level: string): string {
  return IMPACT_LEVEL_CLASS[level] || DEFAULT_STATUS_META.className;
}
