"use client";
import { useApp } from "../state";

/** Draft lives in app state so it survives the desktop/phone layout swap. Sending is wired in Task 5. */
export function Composer() {
  const { draft, setDraft } = useApp();
  return (
    <textarea
      data-testid="composer-input"
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      placeholder="Ask Dubai-io anything"
      rows={2}
    />
  );
}
