/**
 * Network Status Indicator Component
 *
 * Shows a banner when the user is offline or has connectivity issues.
 */

"use client";

import { useOnline } from "@/lib/hooks/usePerformance";

export function NetworkStatusIndicator() {
  const isOnline = useOnline();

  if (isOnline) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-[rgb(var(--danger))] px-4 py-2 text-center text-sm font-medium text-white">
      <div className="flex items-center justify-center gap-2">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M18.364 5.636a9 9 0 010 12.728m-3.536-3.536a4 4 0 010-5.656m-3.536 3.536a1 1 0 010-1.414M5.636 18.364a9 9 0 010-12.728m3.536 3.536a4 4 0 010 5.656"
          />
        </svg>
        <span>网络连接已断开，部分功能可能不可用</span>
      </div>
    </div>
  );
}
