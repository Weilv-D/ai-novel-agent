"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, textImportApi } from "@/lib/api-client";
import type {
  DetectedCharacter,
  DetectedChapter,
  DetectedVolume,
  DetectedWorldSetting,
  TextImportPhase,
  TextImportJobResponse,
  TextImportPreview,
  TextImportProgress,
  TextImportResponse,
} from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";

type WizardStep = "upload" | "analysis" | "preview";
type PreviewTab = "overview" | "chapters" | "characters" | "world_settings";

interface TextImportWizardProps {
  isOpen: boolean;
  onClose: () => void;
  onImported: (result: TextImportResponse) => Promise<void> | void;
}

const PHASE_LABELS: Record<TextImportPhase, string> = {
  structure_detection: "结构检测",
  outline_extraction: "大纲提取",
  character_extraction: "角色提取",
  world_setting_extraction: "世界观提取",
  completed: "分析完成",
  error: "分析失败",
};

const WORLD_SETTING_OPTIONS = [
  { label: "魔法/修炼体系", value: "magic_system" },
  { label: "地理", value: "geography" },
  { label: "历史", value: "history" },
  { label: "组织势力", value: "organization" },
  { label: "技术", value: "technology" },
  { label: "文化", value: "culture" },
  { label: "宗教", value: "religion" },
  { label: "经济", value: "economy" },
  { label: "规则", value: "rules" },
  { label: "其他", value: "other" },
];
const MAX_TEXT_IMPORT_FILE_BYTES = 64 * 1024 * 1024;
const CHAPTERS_PER_PAGE = 20;
const ACTIVE_TEXT_IMPORT_JOB_KEY = "text-import-active-job-id";

function normalizePreview(raw: TextImportPreview): TextImportPreview {
  return {
    ...raw,
    volumes: raw.volumes || [],
    chapters: raw.chapters || [],
    characters: raw.characters || [],
    world_settings: raw.world_settings || [],
    warnings: raw.warnings || [],
    failed_phases: raw.failed_phases || [],
  };
}

function appendProgressEvent(
  currentEvents: TextImportProgress[],
  nextEvent: TextImportProgress,
): TextImportProgress[] {
  const lastEvent = currentEvents[currentEvents.length - 1];
  if (
    lastEvent
    && lastEvent.phase === nextEvent.phase
    && lastEvent.progress === nextEvent.progress
    && lastEvent.message === nextEvent.message
  ) {
    return currentEvents;
  }
  return [...currentEvents, nextEvent];
}

function normalizeJobProgress(job: TextImportJobResponse): TextImportProgress {
  const phase: TextImportPhase =
    job.phase
    || (job.status === "failed"
      ? "error"
      : job.status === "completed"
        ? "completed"
        : "structure_detection");

  return {
    phase,
    progress: job.progress,
    message:
      job.message
      || (job.status === "queued" ? "任务已排队，等待后台分析" : "后台分析进行中"),
    data: {
      warnings: job.warnings,
      failed_phases: job.failed_phases,
    },
  };
}

function getStoredTextImportJobId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(ACTIVE_TEXT_IMPORT_JOB_KEY);
}

function setStoredTextImportJobId(jobId: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(ACTIVE_TEXT_IMPORT_JOB_KEY, jobId);
}

function clearStoredTextImportJobId(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(ACTIVE_TEXT_IMPORT_JOB_KEY);
}

function waitForNextPoll(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      window.clearTimeout(timeoutId);
      signal?.removeEventListener("abort", handleAbort);
    };

    const handleAbort = () => {
      cleanup();
      reject(new DOMException("Aborted", "AbortError"));
    };

    const timeoutId = window.setTimeout(() => {
      cleanup();
      resolve();
    }, ms);

    if (signal) {
      signal.addEventListener("abort", handleAbort, { once: true });
    }
  });
}

export function TextImportWizard({
  isOpen,
  onClose,
  onImported,
}: TextImportWizardProps) {
  const [step, setStep] = useState<WizardStep>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [projectName, setProjectName] = useState("");
  const [genre, setGenre] = useState("");
  const [events, setEvents] = useState<TextImportProgress[]>([]);
  const [preview, setPreview] = useState<TextImportPreview | null>(null);
  const [activeTab, setActiveTab] = useState<PreviewTab>("overview");
  const [chapterPage, setChapterPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jsonDrafts, setJsonDrafts] = useState<Record<string, string>>({});
  const [jsonErrors, setJsonErrors] = useState<Record<string, string>>({});
  const runTokenRef = useRef(0);
  const analyzeAbortRef = useRef<AbortController | null>(null);

  const latestEvent = events[events.length - 1] || null;
  const progressPercent = Math.max(0, Math.min(100, Math.round((latestEvent?.progress || 0) * 100)));

  const tabSummary = useMemo(
    () => ({
      overview: preview?.volumes.length || 0,
      chapters: preview?.chapters.length || 0,
      characters: preview?.characters.length || 0,
      world_settings: preview?.world_settings.length || 0,
    }),
    [preview]
  );
  const chapterPageCount = Math.max(1, Math.ceil((preview?.chapters.length || 0) / CHAPTERS_PER_PAGE));
  const pagedChapters = useMemo(() => {
    if (!preview) {
      return [];
    }
    const start = (chapterPage - 1) * CHAPTERS_PER_PAGE;
    return preview.chapters.slice(start, start + CHAPTERS_PER_PAGE);
  }, [chapterPage, preview]);

  const pollBackgroundJob = useCallback(async (jobId: string, token: number, signal?: AbortSignal) => {
    setActiveJobId(jobId);
    setStoredTextImportJobId(jobId);

    while (token === runTokenRef.current) {
      const job = await textImportApi.getJob(jobId);
      if (token !== runTokenRef.current) {
        return;
      }

      setEvents((prev) => appendProgressEvent(prev, normalizeJobProgress(job)));

      if (job.status === "completed") {
        clearStoredTextImportJobId();
        setActiveJobId(null);
        const nextPreview = job.preview;
        if (!nextPreview) {
          throw new ApiError(500, "后台分析完成，但未返回预览结果");
        }
        setPreview(normalizePreview(nextPreview));
        setActiveTab("overview");
        setChapterPage(1);
        setStep("preview");
        return;
      }

      if (job.status === "failed") {
        clearStoredTextImportJobId();
        setActiveJobId(null);
        throw new ApiError(500, job.error_detail || job.message || "后台文本分析失败");
      }

      await waitForNextPoll(2000, signal);
    }
  }, []);

  useEffect(() => {
    if (!isOpen) {
      runTokenRef.current += 1;
      analyzeAbortRef.current?.abort();
      analyzeAbortRef.current = null;
      setStep("upload");
      setFile(null);
      setProjectName("");
      setGenre("");
      setEvents([]);
      setPreview(null);
      setActiveTab("overview");
      setChapterPage(1);
      setError(null);
      setIsAnalyzing(false);
      setIsConfirming(false);
      setActiveJobId(null);
      setJsonDrafts({});
      setJsonErrors({});
      document.body.style.overflow = "";
      return;
    }
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  useEffect(() => {
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isOpen && !isConfirming) {
        handleClose();
      }
    };
    document.addEventListener("keydown", onEscape);
    return () => document.removeEventListener("keydown", onEscape);
  });

  useEffect(() => {
    if (!isOpen || isAnalyzing || preview) {
      return;
    }

    const storedJobId = getStoredTextImportJobId();
    if (!storedJobId) {
      return;
    }

    const token = runTokenRef.current + 1;
    runTokenRef.current = token;
    analyzeAbortRef.current?.abort();
    const controller = new AbortController();
    analyzeAbortRef.current = controller;
    setError(null);
    setEvents([
      {
        phase: "structure_detection",
        progress: 0.15,
        message: "已恢复后台分析任务，正在同步最新进度",
        data: { mode: "background_job", job_id: storedJobId },
      },
    ]);
    setStep("analysis");
    setIsAnalyzing(true);

    void pollBackgroundJob(storedJobId, token, controller.signal)
      .catch((err) => {
        if (token !== runTokenRef.current) {
          return;
        }
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }
        setActiveJobId(null);
        clearStoredTextImportJobId();
        setError(err instanceof ApiError ? err.detail : "文本分析失败");
        setStep("upload");
      })
      .finally(() => {
        if (token === runTokenRef.current) {
          setIsAnalyzing(false);
        }
        if (analyzeAbortRef.current === controller) {
          analyzeAbortRef.current = null;
        }
      });
  }, [isOpen, isAnalyzing, pollBackgroundJob, preview]);

  function handleClose() {
    if (isConfirming) {
      return;
    }
    runTokenRef.current += 1;
    analyzeAbortRef.current?.abort();
    analyzeAbortRef.current = null;
    onClose();
  }

  function updatePreview(nextPreview: TextImportPreview | null) {
    setPreview(nextPreview ? normalizePreview(nextPreview) : null);
  }

  function appendEvent(nextEvent: TextImportProgress) {
    setEvents((prev) => appendProgressEvent(prev, nextEvent));
  }

  async function handleAnalyze() {
    if (!file) {
      setError("请选择要导入的 .txt 或 .md 文件");
      return;
    }
    if (!projectName.trim()) {
      setError("请填写导入后的项目名称");
      return;
    }
    if (file.size > MAX_TEXT_IMPORT_FILE_BYTES) {
      setError("上传文件过大，请控制在 64MB 以内");
      return;
    }

    const token = runTokenRef.current + 1;
    runTokenRef.current = token;
    analyzeAbortRef.current?.abort();
    const controller = new AbortController();
    analyzeAbortRef.current = controller;
    setError(null);
    setEvents([]);
    setPreview(null);
    setActiveJobId(null);
    clearStoredTextImportJobId();
    setJsonDrafts({});
    setJsonErrors({});
    setStep("analysis");
    setIsAnalyzing(true);

    try {
      let backgroundJobId: string | null = null;
      for await (const event of textImportApi.analyzeStream(
        file,
        projectName.trim(),
        genre.trim() || undefined,
        { signal: controller.signal }
      )) {
        if (token !== runTokenRef.current) {
          return;
        }
        appendEvent(event);

        if (event.phase === "error") {
          const detail = typeof event.data.detail === "string" ? event.data.detail : event.message;
          throw new ApiError(500, detail || "文本分析失败");
        }

        if (event.data.mode === "background_job") {
          const jobId = typeof event.data.job_id === "string" ? event.data.job_id : "";
          if (!jobId) {
            throw new ApiError(500, "后台分析任务创建失败");
          }
          backgroundJobId = jobId;
          break;
        }

        if (event.phase === "completed") {
          const nextPreview = event.data.preview as TextImportPreview | undefined;
          if (nextPreview) {
            clearStoredTextImportJobId();
            updatePreview(nextPreview);
            setActiveTab("overview");
            setChapterPage(1);
            setStep("preview");
          }
        }
      }

      if (backgroundJobId) {
        await pollBackgroundJob(backgroundJobId, token, controller.signal);
      }
    } catch (err) {
      if (token !== runTokenRef.current) {
        return;
      }
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      setActiveJobId(null);
      clearStoredTextImportJobId();
      setError(err instanceof ApiError ? err.detail : "文本分析失败");
      setStep("upload");
    } finally {
      if (token === runTokenRef.current) {
        setIsAnalyzing(false);
      }
      if (analyzeAbortRef.current === controller) {
        analyzeAbortRef.current = null;
      }
    }
  }

  async function handleConfirmImport() {
    if (!preview) {
      return;
    }
    setIsConfirming(true);
    setError(null);
    try {
      const result = await textImportApi.confirm(preview);
      clearStoredTextImportJobId();
      setActiveJobId(null);
      await onImported(result);
      handleClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "确认导入失败");
    } finally {
      setIsConfirming(false);
    }
  }

  function updateOverviewField<K extends keyof TextImportPreview>(field: K, value: TextImportPreview[K]) {
    if (!preview) {
      return;
    }
    updatePreview({ ...preview, [field]: value });
  }

  function updateVolume(index: number, patch: Partial<DetectedVolume>) {
    if (!preview) {
      return;
    }
    const nextVolumes = preview.volumes.map((volume, currentIndex) =>
      currentIndex === index ? { ...volume, ...patch } : volume
    );
    updatePreview({ ...preview, volumes: nextVolumes });
  }

  function updateChapter(index: number, patch: Partial<DetectedChapter>) {
    if (!preview) {
      return;
    }
    const nextChapters = preview.chapters.map((chapter, currentIndex) =>
      currentIndex === index ? { ...chapter, ...patch } : chapter
    );
    updatePreview({ ...preview, chapters: nextChapters });
  }

  function removeChapter(index: number) {
    if (!preview) {
      return;
    }
    const chapterNumber = preview.chapters[index]?.chapter_number;
    const nextChapters = preview.chapters.filter((_, currentIndex) => currentIndex !== index);
    const nextVolumes = preview.volumes.map((volume) => ({
      ...volume,
      chapter_numbers: volume.chapter_numbers.filter((currentNumber) => currentNumber !== chapterNumber),
    }));
    updatePreview({ ...preview, chapters: nextChapters, volumes: nextVolumes });
  }

  function updateCharacter(index: number, patch: Partial<DetectedCharacter>) {
    if (!preview) {
      return;
    }
    const nextCharacters = preview.characters.map((character, currentIndex) =>
      currentIndex === index ? { ...character, ...patch } : character
    );
    updatePreview({ ...preview, characters: nextCharacters });
  }

  function removeCharacter(index: number) {
    if (!preview) {
      return;
    }
    updatePreview({
      ...preview,
      characters: preview.characters.filter((_, currentIndex) => currentIndex !== index),
    });
  }

  function addCharacter() {
    if (!preview) {
      return;
    }
    updatePreview({
      ...preview,
      characters: [
        ...preview.characters,
        { name: "", role: "", profile: {}, relationships: {} },
      ],
    });
  }

  function updateWorldSetting(index: number, patch: Partial<DetectedWorldSetting>) {
    if (!preview) {
      return;
    }
    const nextWorldSettings = preview.world_settings.map((worldSetting, currentIndex) =>
      currentIndex === index ? { ...worldSetting, ...patch } : worldSetting
    );
    updatePreview({ ...preview, world_settings: nextWorldSettings });
  }

  function removeWorldSetting(index: number) {
    if (!preview) {
      return;
    }
    updatePreview({
      ...preview,
      world_settings: preview.world_settings.filter((_, currentIndex) => currentIndex !== index),
    });
  }

  function addWorldSetting() {
    if (!preview) {
      return;
    }
    updatePreview({
      ...preview,
      world_settings: [
        ...preview.world_settings,
        { category: "other", name: "", content: "" },
      ],
    });
  }

  function getJsonDraft(key: string, value: Record<string, unknown>) {
    return jsonDrafts[key] ?? JSON.stringify(value || {}, null, 2);
  }

  function handleJsonDraftChange(key: string, value: string) {
    setJsonDrafts((prev) => ({ ...prev, [key]: value }));
  }

  function commitJsonDraft(
    key: string,
    currentValue: Record<string, unknown>,
    onSuccess: (value: Record<string, unknown>) => void
  ) {
    const draft = jsonDrafts[key] ?? JSON.stringify(currentValue || {}, null, 2);
    try {
      const parsed = JSON.parse(draft);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("invalid");
      }
      onSuccess(parsed as Record<string, unknown>);
      setJsonDrafts((prev) => ({ ...prev, [key]: JSON.stringify(parsed, null, 2) }));
      setJsonErrors((prev) => ({ ...prev, [key]: "" }));
    } catch {
      setJsonErrors((prev) => ({ ...prev, [key]: "请输入合法 JSON 对象" }));
    }
  }

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6">
      <div
        className="absolute inset-0 bg-[rgba(var(--ink-950),0.45)] backdrop-blur-md"
        onClick={handleClose}
        aria-hidden="true"
      />

      <div className="ink-panel relative z-10 flex max-h-[min(92vh,980px)] w-full max-w-6xl flex-col overflow-hidden rounded-[2rem] p-0">
        <div className="border-b border-[rgba(var(--line),0.12)] px-8 py-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="ink-kicker">Text Import</p>
              <h2 className="ink-display mt-3 text-3xl font-semibold text-[rgb(var(--ink-950))]">
                导入文本并结构化为书籍项目
              </h2>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-[rgb(var(--ink-800))]">
                上传已有小说 TXT 或 Markdown，系统会先分析结构并生成预览。你确认后，原文会保留在章节正文里，同时补出项目总纲、章纲、角色和世界观。
              </p>
            </div>
            <Button variant="ghost" onClick={handleClose} disabled={isConfirming}>
              关闭
            </Button>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-3">
            {[
              { key: "upload", label: "1. 上传文件" },
              { key: "analysis", label: "2. 分析进度" },
              { key: "preview", label: "3. 预览确认" },
            ].map((item) => {
              const active =
                item.key === step ||
                (item.key === "upload" && step === "analysis") ||
                (item.key === "analysis" && step === "preview");
              return (
                <div
                  key={item.key}
                  className={`rounded-[1rem] border px-4 py-3 text-sm ${
                    active
                      ? "border-[rgba(var(--seal),0.32)] bg-[rgba(var(--seal),0.08)] text-[rgb(var(--ink-950))]"
                      : "border-[rgba(var(--line),0.14)] bg-[rgba(var(--ink-950),0.03)] text-[rgb(var(--ink-800))]"
                  }`}
                >
                  {item.label}
                </div>
              );
            })}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-8 py-6">
          {step === "upload" && (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(320px,0.7fr)]">
              <div className="space-y-5">
                <div className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] p-5">
                  <Input
                    label="项目名称"
                    value={projectName}
                    onChange={(event) => setProjectName(event.target.value)}
                    placeholder="例如：天门雪夜录"
                    testId="text-import-project-name"
                  />
                  <div className="mt-4">
                    <Input
                      label="题材（可选）"
                      value={genre}
                      onChange={(event) => setGenre(event.target.value)}
                      placeholder="例如：仙侠 / 悬疑 / 都市"
                    />
                  </div>
                  <div className="mt-4">
                    <label className="mb-2 block text-sm font-medium tracking-wider text-ink-800">
                      选择文件
                    </label>
                    <input
                      type="file"
                      accept=".txt,.md,.markdown,text/plain,text/markdown"
                      onChange={(event) => setFile(event.target.files?.[0] || null)}
                      className="block w-full rounded-lg border border-line/60 bg-[var(--field-surface)] px-4 py-3 text-sm text-ink-950"
                      data-testid="text-import-file-input"
                    />
                  </div>
                  {file && (
                    <div className="mt-4 rounded-[1rem] bg-[rgba(var(--ink-950),0.05)] px-4 py-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                      已选择：<span className="font-medium text-[rgb(var(--ink-950))]">{file.name}</span>
                      <br />
                      大小：{(file.size / 1024).toFixed(1)} KB
                    </div>
                  )}
                </div>
              </div>

              <div className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-strong)] p-5">
                <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                  导入说明
                </div>
                <div className="mt-2 text-lg font-medium text-[rgb(var(--ink-950))]">
                  这一步会先做预分析，不会立即入库
                </div>
                <div className="mt-4 space-y-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                  <p>支持 `.txt` 与 `.md` 文件，上传后会先做章节结构识别，再生成章纲、项目总纲、角色和世界观预览。</p>
                  <p>确认导入前，你可以修改项目摘要、章纲、角色和设定内容；原文会保留到 `chapter.content`。</p>
                  <p>如果文本没有稳定章节标记，系统会按单章或安全分段兜底，并在预览里给出警告。当前上传上限为 64MB。</p>
                  <p>超长文本会自动转后台全量分析；关闭窗口不会取消任务，重新打开后会继续恢复进度。</p>
                </div>
              </div>
            </div>
          )}

          {step === "analysis" && (
            <div className="mx-auto max-w-4xl space-y-6">
              <div className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-strong)] p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                      当前阶段
                    </div>
                    <div className="mt-2 text-2xl font-medium text-[rgb(var(--ink-950))]">
                      {latestEvent ? PHASE_LABELS[latestEvent.phase] : "等待开始"}
                    </div>
                    <p className="mt-2 text-sm leading-7 text-[rgb(var(--ink-800))]">
                      {latestEvent?.message || "正在准备分析任务..."}
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                      进度
                    </div>
                    <div className="mt-2 text-3xl font-semibold text-[rgb(var(--ink-950))]">
                      {progressPercent}%
                    </div>
                  </div>
                </div>
                <div className="mt-5 h-3 overflow-hidden rounded-full bg-[rgba(var(--ink-950),0.08)]">
                  <div
                    className="h-full rounded-full bg-[rgba(var(--seal),0.75)] transition-all duration-500"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>

              <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(280px,0.7fr)]">
                <div className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] p-5">
                  <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                    进度日志
                  </div>
                  <div className="mt-4 space-y-3">
                    {events.length === 0 && (
                      <div className="text-sm text-[rgb(var(--ink-800))]">正在建立分析流...</div>
                    )}
                    {events.slice(-8).map((event, index) => (
                      <div
                        key={`${event.phase}-${index}-${event.progress}`}
                        className="rounded-[1rem] bg-[rgba(var(--ink-950),0.04)] px-4 py-3"
                      >
                        <div className="text-xs uppercase tracking-[0.16em] text-[rgb(var(--ink-700))]">
                          {PHASE_LABELS[event.phase]}
                        </div>
                        <div className="mt-1 text-sm leading-7 text-[rgb(var(--ink-900))]">
                          {event.message}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-strong)] p-5">
                  <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                    分析提示
                  </div>
                  <div className="mt-4 space-y-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                    <p>章节越多，章纲提取耗时越长。</p>
                    <p>如果某个 AI 阶段失败，系统会保留已完成的结构结果，并在预览里标记警告。</p>
                    <p>超长文本会自动转后台全量分析；关闭弹窗不会取消任务，重新打开会自动恢复轮询。</p>
                    {activeJobId && <p>后台任务 ID：{activeJobId}</p>}
                  </div>
                  <div className="mt-6">
                    <Button variant="outline" onClick={handleAnalyze} disabled={isAnalyzing}>
                      {isAnalyzing ? "分析中..." : "重新开始分析"}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === "preview" && preview && (
            <div className="space-y-6">
              {(preview.warnings.length > 0 || preview.failed_phases.length > 0) && (
                <div className="rounded-[1.25rem] border border-[rgba(var(--amber),0.22)] bg-[rgba(var(--amber),0.08)] px-5 py-4">
                  <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                    导入警告
                  </div>
                  <div className="mt-3 space-y-2 text-sm leading-7 text-[rgb(var(--ink-900))]">
                    {preview.warnings.map((warning, index) => (
                      <p key={`${warning}-${index}`}>{warning}</p>
                    ))}
                    {preview.compact_preview && (
                      <p>当前是大文本紧凑预览模式：章节正文只展示节选，确认导入时仍会保留完整原文。</p>
                    )}
                    {preview.failed_phases.length > 0 && (
                      <p>失败阶段：{preview.failed_phases.map((phase) => PHASE_LABELS[phase]).join(" / ")}</p>
                    )}
                  </div>
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                {[
                  { key: "overview" as const, label: "大纲", count: tabSummary.overview },
                  { key: "chapters" as const, label: "章节", count: tabSummary.chapters },
                  { key: "characters" as const, label: "角色", count: tabSummary.characters },
                  { key: "world_settings" as const, label: "世界观", count: tabSummary.world_settings },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setActiveTab(tab.key)}
                    className={`rounded-[1rem] border px-4 py-3 text-sm transition-colors ${
                      activeTab === tab.key
                        ? "border-[rgba(var(--seal),0.32)] bg-[rgba(var(--seal),0.08)] text-[rgb(var(--ink-950))]"
                        : "border-[rgba(var(--line),0.14)] bg-[var(--surface-elevated)] text-[rgb(var(--ink-800))]"
                    }`}
                  >
                    {tab.label} · {tab.count}
                  </button>
                ))}
              </div>

              {activeTab === "overview" && (
                <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(320px,0.7fr)]">
                  <div className="space-y-5">
                    <div className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] p-5">
                      <Input
                        label="项目名称"
                        value={preview.project_name}
                        onChange={(event) => updateOverviewField("project_name", event.target.value)}
                      />
                      <div className="mt-4">
                        <Input
                          label="题材"
                          value={preview.genre || ""}
                          onChange={(event) => updateOverviewField("genre", event.target.value)}
                        />
                      </div>
                      <div className="mt-4">
                        <Textarea
                          label="项目摘要"
                          value={preview.summary || ""}
                          onChange={(event) => updateOverviewField("summary", event.target.value)}
                          className="min-h-[140px]"
                        />
                      </div>
                      <div className="mt-4">
                        <Textarea
                          label="项目总纲"
                          value={preview.story_outline || ""}
                          onChange={(event) => updateOverviewField("story_outline", event.target.value)}
                          className="min-h-[220px]"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-5">
                    <div className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-strong)] p-5">
                      <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                        文件信息
                      </div>
                      <div className="mt-3 space-y-2 text-sm leading-7 text-[rgb(var(--ink-800))]">
                        <p>文件：{preview.source_filename || file?.name || "未记录"}</p>
                        <p>编码：{preview.source_encoding || "未记录"}</p>
                        <p>卷数：{preview.volumes.length}</p>
                        <p>章节数：{preview.chapters.length}</p>
                        <p>预览模式：{preview.compact_preview ? "长文本紧凑预览" : "完整预览"}</p>
                      </div>
                    </div>

                    <div className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] p-5">
                      <div className="text-xs uppercase tracking-[0.18em] text-[rgb(var(--ink-800))]">
                        卷结构
                      </div>
                      <div className="mt-4 space-y-4">
                        {preview.volumes.map((volume, index) => (
                          <div key={`${volume.volume_number}-${index}`} className="rounded-[1rem] bg-[rgba(var(--ink-950),0.04)] p-4">
                            <Input
                              label={`卷 ${volume.volume_number} 标题`}
                              value={volume.title || ""}
                              onChange={(event) => updateVolume(index, { title: event.target.value })}
                            />
                            <div className="mt-3 text-xs leading-6 text-[rgb(var(--ink-800))]">
                              包含章节：{volume.chapter_numbers.join(", ") || "未关联章节"}
                            </div>
                            <div className="mt-3">
                              <Textarea
                                label="卷纲"
                                value={volume.outline || ""}
                                onChange={(event) => updateVolume(index, { outline: event.target.value })}
                                className="min-h-[140px]"
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === "chapters" && (
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3 rounded-[1rem] bg-[rgba(var(--ink-950),0.04)] px-4 py-3 text-sm text-[rgb(var(--ink-800))]">
                    <div>
                      显示第 {(chapterPage - 1) * CHAPTERS_PER_PAGE + 1} - {Math.min(chapterPage * CHAPTERS_PER_PAGE, preview.chapters.length)} 章，共 {preview.chapters.length} 章
                    </div>
                    {chapterPageCount > 1 && (
                      <div className="flex flex-wrap gap-2">
                        <Button variant="outline" onClick={() => setChapterPage((current) => Math.max(1, current - 1))} disabled={chapterPage <= 1}>
                          上一页
                        </Button>
                        <Button variant="outline" onClick={() => setChapterPage((current) => Math.min(chapterPageCount, current + 1))} disabled={chapterPage >= chapterPageCount}>
                          下一页
                        </Button>
                      </div>
                    )}
                  </div>
                  {pagedChapters.map((chapter, pageIndex) => {
                    const index = (chapterPage - 1) * CHAPTERS_PER_PAGE + pageIndex;
                    return (
                    <div
                      key={`${chapter.chapter_number}-${index}`}
                      className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] p-5"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="text-sm font-medium text-[rgb(var(--ink-950))]">
                          第 {chapter.chapter_number} 章
                        </div>
                        <Button variant="ghost" onClick={() => removeChapter(index)}>
                          删除章节
                        </Button>
                      </div>
                      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,0.65fr)_minmax(300px,0.35fr)]">
                        <div className="space-y-4">
                          <Input
                            label="章节标题"
                            value={chapter.title || ""}
                            onChange={(event) => updateChapter(index, { title: event.target.value })}
                          />
                          <Textarea
                            label="章纲"
                            value={chapter.outline || ""}
                            onChange={(event) => updateChapter(index, { outline: event.target.value })}
                            className="min-h-[180px]"
                          />
                        </div>
                        <div>
                          <Textarea
                            label={chapter.content_truncated ? "正文节选（导入会保留完整原文）" : "正文原文"}
                            value={chapter.content}
                            onChange={(event) => updateChapter(index, { content: event.target.value })}
                            className="min-h-[320px]"
                            readOnly={Boolean(chapter.content_truncated)}
                          />
                          <div className="mt-2 text-xs leading-6 text-[rgb(var(--ink-800))]">
                            {chapter.content_length
                              ? `正文长度约 ${chapter.content_length.toLocaleString()} 字符`
                              : "正文长度未记录"}
                            {chapter.content_truncated ? "，当前只展示节选。" : ""}
                          </div>
                        </div>
                      </div>
                    </div>
                    );
                  })}
                </div>
              )}

              {activeTab === "characters" && (
                <div className="space-y-4">
                  <div className="flex justify-end">
                    <Button variant="outline" onClick={addCharacter}>
                      新增角色
                    </Button>
                  </div>
                  {preview.characters.map((character, index) => {
                    const profileKey = `character-${index}-profile`;
                    const relationshipKey = `character-${index}-relationships`;
                    return (
                      <div
                        key={`${character.name || "character"}-${index}`}
                        className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] p-5"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div className="text-sm font-medium text-[rgb(var(--ink-950))]">
                            角色 {index + 1}
                          </div>
                          <Button variant="ghost" onClick={() => removeCharacter(index)}>
                            删除角色
                          </Button>
                        </div>
                        <div className="mt-4 grid gap-4 lg:grid-cols-2">
                          <div className="space-y-4">
                            <Input
                              label="名称"
                              value={character.name}
                              onChange={(event) => updateCharacter(index, { name: event.target.value })}
                            />
                            <Input
                              label="角色定位"
                              value={character.role || ""}
                              onChange={(event) => updateCharacter(index, { role: event.target.value })}
                            />
                          </div>
                          <div className="space-y-4">
                            <div>
                              <Textarea
                                label="人物 Profile(JSON)"
                                value={getJsonDraft(profileKey, character.profile)}
                                onChange={(event) => handleJsonDraftChange(profileKey, event.target.value)}
                                onBlur={() =>
                                  commitJsonDraft(profileKey, character.profile, (value) =>
                                    updateCharacter(index, { profile: value })
                                  )
                                }
                                className="min-h-[180px]"
                              />
                              {jsonErrors[profileKey] && (
                                <p className="mt-2 text-xs text-[rgb(var(--danger))]">{jsonErrors[profileKey]}</p>
                              )}
                            </div>
                            <div>
                              <Textarea
                                label="关系(JSON)"
                                value={getJsonDraft(relationshipKey, character.relationships)}
                                onChange={(event) => handleJsonDraftChange(relationshipKey, event.target.value)}
                                onBlur={() =>
                                  commitJsonDraft(relationshipKey, character.relationships, (value) =>
                                    updateCharacter(index, { relationships: value })
                                  )
                                }
                                className="min-h-[180px]"
                              />
                              {jsonErrors[relationshipKey] && (
                                <p className="mt-2 text-xs text-[rgb(var(--danger))]">{jsonErrors[relationshipKey]}</p>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {activeTab === "world_settings" && (
                <div className="space-y-4">
                  <div className="flex justify-end">
                    <Button variant="outline" onClick={addWorldSetting}>
                      新增设定
                    </Button>
                  </div>
                  {preview.world_settings.map((worldSetting, index) => (
                    <div
                      key={`${worldSetting.name || "world-setting"}-${index}`}
                      className="rounded-[1.25rem] border border-[rgba(var(--line),0.16)] bg-[var(--surface-elevated)] p-5"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="text-sm font-medium text-[rgb(var(--ink-950))]">
                          设定 {index + 1}
                        </div>
                        <Button variant="ghost" onClick={() => removeWorldSetting(index)}>
                          删除设定
                        </Button>
                      </div>
                      <div className="mt-4 grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
                        <div>
                          <label className="mb-2 block text-sm font-medium tracking-wider text-ink-800">
                            分类
                          </label>
                          <select
                            value={worldSetting.category}
                            onChange={(event) => updateWorldSetting(index, { category: event.target.value })}
                            className="ink-select"
                          >
                            {WORLD_SETTING_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="space-y-4">
                          <Input
                            label="名称"
                            value={worldSetting.name}
                            onChange={(event) => updateWorldSetting(index, { name: event.target.value })}
                          />
                          <Textarea
                            label="内容"
                            value={worldSetting.content}
                            onChange={(event) => updateWorldSetting(index, { content: event.target.value })}
                            className="min-h-[220px]"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="border-t border-[rgba(var(--line),0.12)] px-8 py-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div
              className="text-sm leading-7 text-[rgb(var(--ink-800))]"
              data-testid="text-import-status-message"
              role={error ? "alert" : undefined}
            >
              {error || (step === "preview" ? "确认后会一次性创建项目、卷、章节、角色和世界观记录。" : "上传分析完成前不会写入项目数据。")}
            </div>
            <div className="flex flex-wrap gap-3">
              {step === "analysis" && (
                <Button variant="outline" onClick={handleClose} disabled={isConfirming}>
                  稍后继续
                </Button>
              )}
              {step === "upload" && (
                <Button onClick={handleAnalyze} loading={isAnalyzing} testId="text-import-start-btn">
                  {isAnalyzing ? "分析中..." : "开始分析"}
                </Button>
              )}
              {step === "preview" && (
                <>
                  <Button
                    variant="outline"
                    onClick={() => {
                      clearStoredTextImportJobId();
                      setActiveJobId(null);
                      setStep("upload");
                    }}
                    disabled={isConfirming}
                  >
                    返回重选文件
                  </Button>
                  <Button onClick={handleConfirmImport} loading={isConfirming} testId="text-import-confirm-btn">
                    {isConfirming ? "导入中..." : "确认导入"}
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
