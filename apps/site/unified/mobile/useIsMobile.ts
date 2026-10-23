"use client";
// Phone layout switch (<= 820 px). Client-only snapshot; false during any server render.
import { useSyncExternalStore } from "react";

const QUERY = "(max-width: 820px)";

export function useIsMobile(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const q = window.matchMedia(QUERY);
      q.addEventListener("change", onChange);
      return () => q.removeEventListener("change", onChange);
    },
    () => window.matchMedia(QUERY).matches,
    () => false,
  );
}
