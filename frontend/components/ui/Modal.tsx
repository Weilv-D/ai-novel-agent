"use client";

import { useEffect } from "react";
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
  confirmText = "确认",
  cancelText = "取消",
  variant = "primary",
  loading = false,
}: ModalProps) {
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

  if (!isOpen) return null;

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
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 mb-6">{message}</p>

        <div className="flex justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={loading}
            fullWidth={false}
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            variant={variant === "danger" ? "danger" : "primary"}
            onClick={handleConfirm}
            disabled={loading}
            fullWidth={false}
          >
            {loading ? "处理中..." : confirmText}
          </Button>
        </div>
      </div>
    </div>
  );
}
