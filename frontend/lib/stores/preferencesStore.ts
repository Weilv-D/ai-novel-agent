/**
 * User Preferences Store - Zustand state management for user preferences
 *
 * Handles theme, font size, language, and UI state with localStorage persistence.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "system";
export type FontSize = "small" | "medium" | "large";

interface UserPreferences {
  theme: Theme;
  fontSize: FontSize;
  language: "zh-CN" | "en-US";
  sidebarCollapsed: boolean;
  chatPanelOpen: boolean;
  lastVisitedProjectId: string | null;
  autoSaveDraft: boolean;
  compactMode: boolean;
}

interface UserPreferencesState extends UserPreferences {
  setTheme: (theme: Theme) => void;
  setFontSize: (fontSize: FontSize) => void;
  setLanguage: (language: "zh-CN" | "en-US") => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleChatPanel: () => void;
  setChatPanelOpen: (open: boolean) => void;
  setLastVisitedProject: (projectId: string | null) => void;
  toggleAutoSaveDraft: () => void;
  toggleCompactMode: () => void;
  reset: () => void;
}

const defaultPreferences: UserPreferences = {
  theme: "system",
  fontSize: "medium",
  language: "zh-CN",
  sidebarCollapsed: false,
  chatPanelOpen: false,
  lastVisitedProjectId: null,
  autoSaveDraft: true,
  compactMode: false,
};

export const usePreferencesStore = create<UserPreferencesState>()(
  persist(
    (set) => ({
      ...defaultPreferences,

      setTheme: (theme) => set({ theme }),
      setFontSize: (fontSize) => set({ fontSize }),
      setLanguage: (language) => set({ language }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleChatPanel: () => set((state) => ({ chatPanelOpen: !state.chatPanelOpen })),
      setChatPanelOpen: (open) => set({ chatPanelOpen: open }),
      setLastVisitedProject: (projectId) => set({ lastVisitedProjectId: projectId }),
      toggleAutoSaveDraft: () => set((state) => ({ autoSaveDraft: !state.autoSaveDraft })),
      toggleCompactMode: () => set((state) => ({ compactMode: !state.compactMode })),
      reset: () => set(defaultPreferences),
    }),
    {
      name: "user-preferences",
      partialize: (state) => ({
        theme: state.theme,
        fontSize: state.fontSize,
        language: state.language,
        sidebarCollapsed: state.sidebarCollapsed,
        lastVisitedProjectId: state.lastVisitedProjectId,
        autoSaveDraft: state.autoSaveDraft,
        compactMode: state.compactMode,
      }),
    }
  )
);

export function getFontSizeValue(fontSize: FontSize): string {
  const values: Record<FontSize, string> = {
    small: "14px",
    medium: "16px",
    large: "18px",
  };
  return values[fontSize];
}

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else if (theme === "light") {
    root.classList.remove("dark");
  } else {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (prefersDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }
}

export function applyFontSize(fontSize: FontSize): void {
  document.documentElement.style.fontSize = getFontSizeValue(fontSize);
}
