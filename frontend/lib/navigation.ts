"use client";

import { useParams } from "next/navigation";

type RouteParams = Record<string, string | string[]>;

export function useRouteParam(name: string): string {
  const params = useParams<RouteParams>();
  const value = params?.[name];
  if (Array.isArray(value)) {
    return value[0] || "";
  }
  return value || "";
}
