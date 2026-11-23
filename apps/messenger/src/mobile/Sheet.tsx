// iOS bottom sheet: dimmed backdrop, grabber, rounded top. Closes on backdrop tap.
import type { ReactNode } from "react";
import s from "./mobile.module.css";

/** Taps on a list row inside `children` close the sheet (tabs, inputs and selects don't). */
export function closeOnRowTap(onClose: () => void) {
  return (e: React.MouseEvent) => {
    const el = (e.target as HTMLElement).closest("button, a, [role='button']");
    if (!el || el.getAttribute("role") === "tab" || el.closest("[role='tablist']")) return;
    window.setTimeout(onClose, 120);
  };
}

export function Sheet({ children, onClose, label, tall = true }: {
  children: ReactNode; onClose: () => void; label: string; tall?: boolean;
}) {
  return (
    <div className={s.sheetLayer}>
      <button className={s.dim} aria-label="Close" onClick={onClose} />
      <section className={`${s.sheet} ${tall ? s.sheetTall : ""}`} role="dialog" aria-modal="true" aria-label={label}>
        <div className={s.grabber} />
        {children}
      </section>
    </div>
  );
}
