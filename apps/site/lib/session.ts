"use client";

import { apiGet } from "./api";

let session: Promise<unknown> | null = null;

/**
 * Open the anonymous cookie session the backend requires before any
 * owner-scoped read. Cached per page load; failures surface through the
 * caller's own error state (the page still renders, with retry).
 */
export function ensureSession(): Promise<unknown> {
  if (!session) {
    session = apiGet("/api/session").catch((err: unknown) => {
      session = null;
      throw err;
    });
  }
  return session;
}
