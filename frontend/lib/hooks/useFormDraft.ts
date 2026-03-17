/**
 * Form Draft Hook - Auto-save form data to localStorage
 *
 * Prevents data loss on page refresh or accidental navigation.
 */

import { useCallback, useMemo, useState } from "react";

const DRAFT_PREFIX = "form-draft-";

export function useFormDraft<T extends Record<string, unknown>>(
  key: string,
  initialData: T,
  options?: {
    onRestore?: (data: T) => void;
  }
): {
  data: T;
  setData: (data: T | ((prev: T) => T)) => void;
  saveDraft: () => void;
  clearDraft: () => void;
  hasDraft: boolean;
  restoreDraft: () => T | null;
} {
  const storageKey = `${DRAFT_PREFIX}${key}`;
  const [data, setDataState] = useState<T>(initialData);

  const getDraft = useCallback((): T | null => {
    if (typeof window === "undefined") return null;
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        return JSON.parse(stored) as T;
      }
    } catch {
      console.warn(`Failed to parse draft for key: ${key}`);
    }
    return null;
  }, [storageKey, key]);

  const persistDraft = useCallback(
    (dataToSave: T) => {
      if (typeof window === "undefined") return;
      try {
        localStorage.setItem(storageKey, JSON.stringify(dataToSave));
      } catch {
        console.warn(`Failed to save draft for key: ${key}`);
      }
    },
    [storageKey, key]
  );

  const clearDraft = useCallback(() => {
    if (typeof window === "undefined") return;
    localStorage.removeItem(storageKey);
  }, [storageKey]);

  const hasDraft = useMemo(() => getDraft() !== null, [getDraft]);

  const restoreDraft = useCallback((): T | null => {
    const draft = getDraft();
    if (draft) {
      setDataState(draft);
      if (options?.onRestore) {
        options.onRestore(draft);
      }
    }
    return draft;
  }, [getDraft, options]);

  const setData = useCallback((update: T | ((prev: T) => T)) => {
    setDataState(update);
  }, []);

  const saveDraft = useCallback(() => {
    persistDraft(data);
  }, [persistDraft, data]);

  return {
    data,
    setData,
    saveDraft,
    clearDraft,
    hasDraft,
    restoreDraft,
  };
}

export function useDraftRestore(
  key: string,
  onRestore: (data: Record<string, unknown>) => void
): {
  hasDraft: boolean;
  restoreDraft: () => void;
  clearDraft: () => void;
} {
  const storageKey = `${DRAFT_PREFIX}${key}`;

  const getDraft = useCallback((): Record<string, unknown> | null => {
    if (typeof window === "undefined") return null;
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      console.warn(`Failed to parse draft for key: ${key}`);
    }
    return null;
  }, [storageKey, key]);

  const clearDraft = useCallback(() => {
    if (typeof window === "undefined") return;
    localStorage.removeItem(storageKey);
  }, [storageKey]);

  const restoreDraft = useCallback(() => {
    const draft = getDraft();
    if (draft) {
      onRestore(draft);
    }
  }, [getDraft, onRestore]);

  const hasDraft = getDraft() !== null;

  return { hasDraft, restoreDraft, clearDraft };
}

export function saveFormDraft(key: string, data: Record<string, unknown>): void {
  if (typeof window === "undefined") return;
  const storageKey = `${DRAFT_PREFIX}${key}`;
  try {
    localStorage.setItem(storageKey, JSON.stringify(data));
  } catch {
    console.warn(`Failed to save draft for key: ${key}`);
  }
}

export function getFormDraft(key: string): Record<string, unknown> | null {
  if (typeof window === "undefined") return null;
  const storageKey = `${DRAFT_PREFIX}${key}`;
  try {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {
    console.warn(`Failed to parse draft for key: ${key}`);
  }
  return null;
}

export function clearFormDraft(key: string): void {
  if (typeof window === "undefined") return;
  const storageKey = `${DRAFT_PREFIX}${key}`;
  localStorage.removeItem(storageKey);
}

export function hasFormDraft(key: string): boolean {
  if (typeof window === "undefined") return false;
  const storageKey = `${DRAFT_PREFIX}${key}`;
  return localStorage.getItem(storageKey) !== null;
}
