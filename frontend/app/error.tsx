"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Unhandled error:", error);
  }, [error]);

  return (
    <main className="ink-page">
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <p className="ink-kicker mb-2">Error</p>
        <h1 className="ink-display text-4xl font-semibold text-[rgb(var(--ink-950))]">
          出现了问题
        </h1>
        <p className="mt-4 text-base leading-7 text-[rgb(var(--ink-800))]">
          页面加载时发生了错误，请尝试重新加载。
        </p>
        <div className="mt-8">
          <button
            onClick={reset}
            className="inline-flex items-center rounded-[1rem] border border-[rgba(var(--line),0.18)] bg-[rgba(var(--ink-950),0.94)] px-6 py-3 text-sm font-medium text-[rgb(var(--paper-soft))] transition-all hover:bg-[rgba(var(--ink-950),1)]"
          >
            重新加载
          </button>
        </div>
      </div>
    </main>
  );
}
