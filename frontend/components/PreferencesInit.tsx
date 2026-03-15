/**
 * Preferences Init Component
 *
 * Initializes user preferences (theme, font size) on app load.
 */

"use client";

import { useEffect } from "react";
import { usePreferencesStore, applyTheme, applyFontSize } from "@/lib/stores/preferencesStore";

export function PreferencesInit() {
  const theme = usePreferencesStore((state) => state.theme);
  const fontSize = usePreferencesStore((state) => state.fontSize);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    applyFontSize(fontSize);
  }, [fontSize]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    
    const handleChange = () => {
      if (theme === "system") {
        applyTheme("system");
      }
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, [theme]);

  return null;
}
