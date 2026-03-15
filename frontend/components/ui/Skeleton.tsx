/**
 * Skeleton Components - Loading placeholders for better perceived performance
 */

import React from "react";

interface SkeletonProps {
  className?: string;
  animate?: boolean;
}

export function Skeleton({ className = "", animate = true }: SkeletonProps) {
  return (
    <div
      className={`bg-[rgba(var(--ink-950),0.08)] ${animate ? "animate-pulse" : ""} rounded-[0.5rem] ${className}`}
      aria-hidden="true"
    />
  );
}

export function SkeletonText({ lines = 3, className = "" }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={`h-4 ${i === lines - 1 ? "w-3/4" : "w-full"}`}
        />
      ))}
    </div>
  );
}

export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div className={`rounded-[1.4rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.58)] p-4 ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-1/3" />
          <Skeleton className="h-4 w-2/3" />
        </div>
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
      <div className="mt-4 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-4/5" />
      </div>
    </div>
  );
}

export function SkeletonList({ count = 3, className = "" }: { count?: number; className?: string }) {
  return (
    <div className={`space-y-4 ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4, className = "" }: { rows?: number; cols?: number; className?: string }) {
  return (
    <div className={`overflow-hidden rounded-[1rem] border border-[rgba(var(--line),0.12)] ${className}`}>
      <div className="bg-[rgba(var(--ink-950),0.03)] px-4 py-3">
        <div className="flex gap-4">
          {Array.from({ length: cols }).map((_, i) => (
            <Skeleton key={i} className="h-4 flex-1" />
          ))}
        </div>
      </div>
      <div className="divide-y divide-[rgba(var(--line),0.08)]">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="px-4 py-3">
            <div className="flex gap-4">
              {Array.from({ length: cols }).map((_, colIndex) => (
                <Skeleton key={colIndex} className="h-4 flex-1" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonProjectCard({ className = "" }: { className?: string }) {
  return (
    <div className={`rounded-[1.4rem] border border-[rgba(var(--line),0.14)] bg-[rgba(255,255,255,0.62)] p-5 ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <Skeleton className="mt-3 h-4 w-full" />
      <Skeleton className="mt-2 h-4 w-3/4" />
      <div className="mt-4 flex gap-2">
        <Skeleton className="h-6 w-16 rounded-full" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <div className="mt-4 flex items-center justify-between">
        <Skeleton className="h-3 w-24" />
        <div className="flex gap-2">
          <Skeleton className="h-8 w-8 rounded-[0.75rem]" />
          <Skeleton className="h-8 w-8 rounded-[0.75rem]" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonCharacterCard({ className = "" }: { className?: string }) {
  return (
    <div className={`rounded-[1.2rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.58)] p-4 ${className}`}>
      <div className="flex items-center gap-3">
        <Skeleton className="h-12 w-12 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-1/2" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      </div>
      <div className="mt-3 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    </div>
  );
}

export function SkeletonChapterCard({ className = "" }: { className?: string }) {
  return (
    <div className={`rounded-[1.2rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.58)] p-4 ${className}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-[0.75rem]" />
          <div className="space-y-2">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
        </div>
        <Skeleton className="h-6 w-16 rounded-full" />
      </div>
    </div>
  );
}

export function SkeletonAgentWorkspace({ className = "" }: { className?: string }) {
  return (
    <div className={`space-y-6 ${className}`}>
      <div className="rounded-[1.4rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.62)] p-5">
        <div className="space-y-4">
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-32 w-full rounded-[1rem]" />
          <div className="flex justify-end">
            <Skeleton className="h-10 w-24 rounded-[0.75rem]" />
          </div>
        </div>
      </div>
      <div className="rounded-[1.4rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.62)] p-5">
        <Skeleton className="h-6 w-1/3" />
        <div className="mt-4 space-y-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    </div>
  );
}
