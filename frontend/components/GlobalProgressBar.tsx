/**
 * Global Progress Bar Component
 *
 * Shows a loading progress bar at the top of the page during navigation.
 */

"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

export function GlobalProgressBar() {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const pathname = usePathname();

  useEffect(() => {
    setLoading(true);
    setProgress(20);

    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return prev;
        return prev + 10;
      });
    }, 100);

    const completeTimer = setTimeout(() => {
      setProgress(100);
      setTimeout(() => {
        setLoading(false);
        setProgress(0);
      }, 200);
    }, 300);

    return () => {
      clearInterval(progressInterval);
      clearTimeout(completeTimer);
    };
  }, [pathname]);

  if (!loading) return null;

  return (
    <div className="fixed left-0 right-0 top-0 z-[100] h-1 bg-transparent">
      <div
        className="h-full bg-[rgb(var(--jade))] transition-all duration-200 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}
