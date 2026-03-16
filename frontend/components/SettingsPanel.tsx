/**
 * Settings Panel Component
 *
 * Provides UI for user preferences like theme, font size, etc.
 */

"use client";

import { useState } from "react";
import { usePreferencesStore, type Theme, type FontSize } from "@/lib/stores/preferencesStore";
import { Button } from "@/components/ui/Button";

interface SettingsPanelProps {
  onClose?: () => void;
}

const themeOptions: { value: Theme; label: string; description: string }[] = [
  { value: "light", label: "浅色", description: "始终使用浅色主题" },
  { value: "dark", label: "深色", description: "始终使用深色主题" },
  { value: "system", label: "跟随系统", description: "自动跟随系统设置" },
];

const fontSizeOptions: { value: FontSize; label: string; preview: string }[] = [
  { value: "small", label: "小", preview: "14px" },
  { value: "medium", label: "中", preview: "16px" },
  { value: "large", label: "大", preview: "18px" },
];

export function SettingsPanel({ onClose }: SettingsPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const theme = usePreferencesStore((state) => state.theme);
  const fontSize = usePreferencesStore((state) => state.fontSize);
  const autoSaveDraft = usePreferencesStore((state) => state.autoSaveDraft);
  const compactMode = usePreferencesStore((state) => state.compactMode);

  const setTheme = usePreferencesStore((state) => state.setTheme);
  const setFontSize = usePreferencesStore((state) => state.setFontSize);
  const toggleAutoSaveDraft = usePreferencesStore((state) => state.toggleAutoSaveDraft);
  const toggleCompactMode = usePreferencesStore((state) => state.toggleCompactMode);
  const reset = usePreferencesStore((state) => state.reset);

  const openPanel = () => setIsOpen(true);
  const closePanel = () => {
    setIsOpen(false);
    onClose?.();
  };

  return (
    <>
      {/* Settings button */}
      <button
        onClick={openPanel}
        className="flex h-10 w-10 items-center justify-center rounded-[0.75rem] text-[rgb(var(--ink-800))] transition-colors hover:bg-[rgba(var(--ink-950),0.04)] hover:text-[rgb(var(--ink-900))]"
        aria-label="Open settings"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543.94 1.543 3.17 0 4.11a1.724 1.724 0 00-1.065 2.572c.426 1.756-.917 3.17-2.573 1.066a1.724 1.724 0 00-2.573 1.066c-1.543.94-3.17-.917-3.17-2.573a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.065-2.573z"
          />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      {/* Settings panel overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 bg-[rgba(var(--ink-950),0.3)] backdrop-blur-sm"
          onClick={closePanel}
          aria-hidden="true"
        />
      )}

      {/* Settings panel */}
      <div
        className={`fixed right-0 top-0 z-50 h-full w-full max-w-md transform border-l border-[rgba(var(--line),0.2)] bg-[rgb(var(--paper))] shadow-2xl transition-transform duration-300 ease-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[rgba(var(--line),0.2)] px-6 py-4">
            <h2 className="text-lg font-medium text-[rgb(var(--ink-950))]">设置</h2>
            <button
              onClick={closePanel}
              className="flex h-8 w-8 items-center justify-center rounded-[0.5rem] text-[rgb(var(--ink-800))] transition-colors hover:bg-[rgba(var(--ink-950),0.04)]"
              aria-label="Close settings"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="space-y-8">
              {/* Theme */}
              <section>
                <h3 className="mb-3 text-sm font-medium text-[rgb(var(--ink-900))]">主题</h3>
                <div className="space-y-2">
                  {themeOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setTheme(option.value)}
                      className={`w-full rounded-[0.75rem] border p-3 text-left transition-colors ${
                        theme === option.value
                          ? "border-[rgb(var(--jade))] bg-[rgba(var(--jade),0.08)]"
                          : "border-[rgba(var(--line),0.2)] hover:border-[rgba(var(--line),0.4)]"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-[rgb(var(--ink-900))]">{option.label}</span>
                        {theme === option.value && (
                          <svg className="h-4 w-4 text-[rgb(var(--jade))]" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-[rgb(var(--ink-800))]">{option.description}</p>
                    </button>
                  ))}
                </div>
              </section>

              {/* Font Size */}
              <section>
                <h3 className="mb-3 text-sm font-medium text-[rgb(var(--ink-900))]">字体大小</h3>
                <div className="flex gap-2">
                  {fontSizeOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setFontSize(option.value)}
                      className={`flex-1 rounded-[0.75rem] border p-3 text-center transition-colors ${
                        fontSize === option.value
                          ? "border-[rgb(var(--jade))] bg-[rgba(var(--jade),0.08)]"
                          : "border-[rgba(var(--line),0.2)] hover:border-[rgba(var(--line),0.4)]"
                      }`}
                    >
                      <div className="text-sm font-medium text-[rgb(var(--ink-900))]">{option.label}</div>
                      <div className="mt-1 text-xs text-[rgb(var(--ink-800))]">{option.preview}</div>
                    </button>
                  ))}
                </div>
              </section>

              {/* Toggles */}
              <section>
                <h3 className="mb-3 text-sm font-medium text-[rgb(var(--ink-900))]">功能</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between rounded-[0.75rem] border border-[rgba(var(--line),0.2)] p-3">
                    <div>
                      <div className="text-sm font-medium text-[rgb(var(--ink-900))]">自动保存草稿</div>
                      <div className="text-xs text-[rgb(var(--ink-800))]">自动保存表单数据到本地</div>
                    </div>
                    <button
                      onClick={toggleAutoSaveDraft}
                      className={`relative h-6 w-11 rounded-full transition-colors ${
                        autoSaveDraft ? "bg-[rgb(var(--jade))]" : "bg-[rgba(var(--ink-950),0.2)]"
                      }`}
                      role="switch"
                      aria-checked={autoSaveDraft}
                    >
                      <span
                        className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                          autoSaveDraft ? "translate-x-5" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>

                  <div className="flex items-center justify-between rounded-[0.75rem] border border-[rgba(var(--line),0.2)] p-3">
                    <div>
                      <div className="text-sm font-medium text-[rgb(var(--ink-900))]">紧凑模式</div>
                      <div className="text-xs text-[rgb(var(--ink-800))]">减少界面间距</div>
                    </div>
                    <button
                      onClick={toggleCompactMode}
                      className={`relative h-6 w-11 rounded-full transition-colors ${
                        compactMode ? "bg-[rgb(var(--jade))]" : "bg-[rgba(var(--ink-950),0.2)]"
                      }`}
                      role="switch"
                      aria-checked={compactMode}
                    >
                      <span
                        className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                          compactMode ? "translate-x-5" : "translate-x-0"
                        }`}
                      />
                    </button>
                  </div>
                </div>
              </section>
            </div>
          </div>

          {/* Footer */}
          <div className="border-t border-[rgba(var(--line),0.2)] px-6 py-4">
            <Button variant="outline" fullWidth onClick={() => reset()}>
              重置为默认设置
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
