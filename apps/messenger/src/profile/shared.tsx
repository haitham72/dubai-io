// Shared pieces of the Profile and Settings modals: the frosted shell, grouped rows, toggles, toast.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronRight, X, type LucideIcon } from "lucide-react";
import { Backdrop, ICON, IconButton } from "../ui";
import s from "./profile.module.css";

export interface Tab { id: string; label: string; icon: LucideIcon }

/** Centered frosted modal (~1000×680): left tab nav, right header + scrolling body. Backdrop click closes. */
export function Shell({ title, tabs, active, onTab, onClose, heading, subheading, toast, children }: {
  title: string; tabs: Tab[]; active: string; onTab: (id: string) => void; onClose: () => void;
  heading: string; subheading?: string; toast?: string | null; children: ReactNode;
}) {
  const body = useRef<HTMLDivElement>(null);
  useEffect(() => { body.current?.scrollTo({ top: 0 }); }, [active]);
  return (
    <Backdrop backdrop={s.backdrop} onClose={onClose}>
      <div className={s.dialog} role="dialog" aria-modal aria-label={title} onClick={(e) => e.stopPropagation()}>
        <nav className={s.nav} aria-label={`${title} sections`}>
          <h2 className={s.navTitle}>{title}</h2>
          {tabs.map((t) => (
            <button key={t.id} className={`${s.navItem} ${t.id === active ? s.navActive : ""}`}
              aria-current={t.id === active ? "page" : undefined} onClick={() => onTab(t.id)}>
              <t.icon {...ICON} />{t.label}
            </button>
          ))}
        </nav>
        <section className={s.content}>
          <header className={s.header}>
            <div>
              <h3 className={s.heading}>{heading}</h3>
              {subheading && <p className={s.subheading}>{subheading}</p>}
            </div>
            <IconButton icon={X} label="Close" onClick={onClose} />
          </header>
          <div className={s.body} ref={body}>{children}</div>
          {toast && <div className={s.toast} role="status">{toast}</div>}
        </section>
      </div>
    </Backdrop>
  );
}

/** A white rounded card that groups rows. */
export function Group({ title, children }: { title?: string; children: ReactNode }) {
  return <div className={s.groupWrap}>
    {title && <h4 className={s.groupTitle}>{title}</h4>}
    <div className={s.group}>{children}</div>
  </div>;
}

/** Icon · label · value · (action text or chevron). Clickable when onClick is given. */
export function Row({ icon: I, label, value, action, onClick, children }: {
  icon?: LucideIcon; label: ReactNode; value?: ReactNode; action?: string; onClick?: () => void; children?: ReactNode;
}) {
  const inner = <>
    {I && <I {...ICON} className={s.rowIcon} />}
    <span className={s.rowLabel}>{label}</span>
    {value !== undefined && <span className={s.rowValue}>{value}</span>}
    {children}
    {onClick && (action ? <span className={s.rowAction}>{action}</span> : <ChevronRight {...ICON} className={s.rowChevron} />)}
  </>;
  return onClick
    ? <button className={`${s.row} ${s.rowButton}`} onClick={onClick}>{inner}</button>
    : <div className={s.row}>{inner}</div>;
}

export function Toggle({ on, onChange, label }: { on: boolean; onChange: (on: boolean) => void; label: string }) {
  return <button role="switch" aria-checked={on} aria-label={label} className={`${s.toggle} ${on ? s.toggleOn : ""}`}
    onClick={() => onChange(!on)}><span className={s.knob} /></button>;
}

/** Label + one-line detail on the left, a switch on the right. */
export function ToggleRow({ label, detail, on, onChange }: { label: string; detail?: string; on: boolean; onChange: (on: boolean) => void }) {
  return <div className={s.row}>
    <span className={s.toggleText}><span className={s.rowLabel}>{label}</span>{detail && <span className={s.rowDetail}>{detail}</span>}</span>
    <Toggle on={on} onChange={onChange} label={label} />
  </div>;
}

/** A short-lived status message shown at the bottom of the modal. */
export function useToast(ms = 2400): [string | null, (text: string) => void] {
  const [text, setText] = useState<string | null>(null);
  const timer = useRef<number>();
  useEffect(() => () => window.clearTimeout(timer.current), []);
  return [text, (t: string) => { setText(t); window.clearTimeout(timer.current); timer.current = window.setTimeout(() => setText(null), ms); }];
}
