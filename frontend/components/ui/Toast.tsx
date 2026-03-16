/**
 * Toast Notification System - Global notification component
 *
 * Provides toast notifications for success, error, warning, and info messages.
 */

"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => string;
  removeToast: (id: string) => void;
  clearToasts: () => void;
  success: (title: string, message?: string) => string;
  error: (title: string, message?: string) => string;
  warning: (title: string, message?: string) => string;
  info: (title: string, message?: string) => string;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let toastIdCounter = 0;
function nextToastId() {
  return `toast-${Date.now()}-${++toastIdCounter}`;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, "id">): string => {
    const id = nextToastId();
    const newToast: Toast = { ...toast, id };

    setToasts((prev) => [...prev, newToast]);

    const duration = toast.duration ?? 5000;
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearToasts = useCallback(() => {
    setToasts([]);
  }, []);

  const success = useCallback(
    (title: string, message?: string) => addToast({ type: "success", title, message }),
    [addToast]
  );

  const error = useCallback(
    (title: string, message?: string) => addToast({ type: "error", title, message, duration: 8000 }),
    [addToast]
  );

  const warning = useCallback(
    (title: string, message?: string) => addToast({ type: "warning", title, message }),
    [addToast]
  );

  const info = useCallback(
    (title: string, message?: string) => addToast({ type: "info", title, message }),
    [addToast]
  );

  return (
    <ToastContext.Provider
      value={{ toasts, addToast, removeToast, clearToasts, success, error, warning, info }}
    >
      {children}
      <ToastContainer toasts={toasts} removeToast={removeToast} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

const TOAST_STYLES: Record<ToastType, { icon: string; bgClass: string; borderClass: string }> = {
  success: {
    icon: "✓",
    bgClass: "bg-[rgba(var(--jade),0.08)]",
    borderClass: "border-[rgba(var(--jade),0.24)]",
  },
  error: {
    icon: "✕",
    bgClass: "bg-[rgba(var(--danger),0.08)]",
    borderClass: "border-[rgba(var(--danger),0.24)]",
  },
  warning: {
    icon: "⚠",
    bgClass: "bg-[rgba(var(--amber),0.08)]",
    borderClass: "border-[rgba(var(--amber),0.24)]",
  },
  info: {
    icon: "ℹ",
    bgClass: "bg-[rgba(var(--ink-950),0.06)]",
    borderClass: "border-[rgba(var(--ink-950),0.12)]",
  },
};

function ToastContainer({ toasts, removeToast }: { toasts: Toast[]; removeToast: (id: string) => void }) {
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-[400px]"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const style = TOAST_STYLES[toast.type];

  return (
    <div
      className={`${style.bgClass} ${style.borderClass} rounded-[1rem] border p-4 shadow-lg backdrop-blur-sm animate-slide-in-right`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex-shrink-0 text-sm font-medium">{style.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[rgb(var(--ink-900))]">{toast.title}</p>
          {toast.message && (
            <p className="mt-1 text-sm text-[rgb(var(--ink-800))]">{toast.message}</p>
          )}
          {toast.action && (
            <button
              onClick={toast.action.onClick}
              className="mt-2 text-sm font-medium text-[rgb(var(--ink-900))] hover:underline"
            >
              {toast.action.label}
            </button>
          )}
        </div>
        <button
          onClick={onClose}
          className="flex-shrink-0 text-[rgb(var(--ink-800))] hover:text-[rgb(var(--ink-800))] transition-colors"
          aria-label="Close notification"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
