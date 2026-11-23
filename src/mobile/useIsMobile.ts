// Phone layout switch. Keep 820px in sync with the @media queries in the screen CSS modules.
import { useSyncExternalStore } from "react";

const query = window.matchMedia("(max-width: 820px)");

export function useIsMobile(): boolean {
  return useSyncExternalStore(
    (onChange) => { query.addEventListener("change", onChange); return () => query.removeEventListener("change", onChange); },
    () => query.matches || devicePreview,
  );
}

/** `?device` — desktop preview of an iPhone 17 Pro Max (status bar, hardware island, safe areas drawn by us). */
export const devicePreview = new URLSearchParams(window.location.search).has("device");

