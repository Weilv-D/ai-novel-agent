"use client";

import { useEffect, useState } from "react";
import { Button } from "./Button";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "primary";
  loading?: boolean;
}

export function Modal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = "落定",
  cancelText = "暂留",
  variant = "primary",
  loading = false,
}: ModalProps) {
  const [shouldRender, setShouldRender] = useState(false);
  const [isRenderedOpen, setIsRenderedOpen] = useState(false);

  // Mount/Unmount logic for smooth animation
  useEffect(() => {
    if (isOpen) {
      setShouldRender(true);
      // Small timeout to allow the browser to paint before adding the 'open' classes
      const timeoutId = setTimeout(() => setIsRenderedOpen(true), 10);
      return () => clearTimeout(timeoutId);
    } else {
      setIsRenderedOpen(false);
      // Wait for exit animation to complete before removing from DOM
      const timeoutId = setTimeout(() => setShouldRender(false), 300);
      return () => clearTimeout(timeoutId);
    }
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !loading) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose, loading]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!shouldRender) return null;

  const handleConfirm = () => {
    if (!loading) {
      onConfirm();
    }
  };

  const handleClose = () => {
    if (!loading) {
      onClose();
    }
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center transition-opacity duration-300 ${isRenderedOpen ? 'opacity-100' : 'opacity-0'}`}>
      <div
        className="fixed inset-0 bg-ink-950/40 backdrop-blur-md transition-all duration-300 will-change-transform"
        onClick={handleClose}
        aria-hidden="true"
      />

      <div className={`ink-panel relative mx-4 w-full max-w-md rounded-2xl p-8 bg-paper-soft shadow-2xl transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] will-change-transform ${isRenderedOpen ? 'scale-100 translate-y-0 opacity-100' : 'scale-95 translate-y-4 opacity-0'}`}>
        <h3 className="ink-display mb-3 text-2xl font-medium tracking-wide text-ink-950 border-b border-line/30 pb-3">{title}</h3>
        <p className="mb-8 text-md leading-relaxed text-ink-700 font-serif">{message}</p>

        <div className="flex justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={loading}
            fullWidth={false}
            className="font-serif tracking-widest px-6"
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            variant={variant === "danger" ? "danger" : "primary"}
            onClick={handleConfirm}
            disabled={loading}
            fullWidth={false}
            className="font-serif tracking-widest px-6"
          >
            {loading ? "引墨..." : confirmText}
          </Button>
        </div>
      </div>
    </div>
  );
}
