// Shared primitives. Build every screen from these.
// Need a new primitive? Build it locally in your folder first; promote it here once a second screen needs it.
import { useEffect, useRef, type ComponentType, type ReactNode } from "react";
import type { LucideProps } from "lucide-react";
import { Search } from "lucide-react";
import s from "./ui.module.css";

type Icon = ComponentType<LucideProps>;
const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");

/** Icon size and stroke used everywhere. */
export const ICON = { size: 20, strokeWidth: 1.75 } as const;

export function SidebarHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className={s.sidebarHeader}>
      <h1 className={s.sidebarTitle}>{title}</h1>
      <div className={s.row}>{children}</div>
    </div>
  );
}

export function PageHeader({ title, subtitle, leading, children }: {
  title: ReactNode; subtitle?: ReactNode; leading?: ReactNode; children?: ReactNode;
}) {
  return (
    <header className={s.pageHeader}>
      {leading}
      <div>
        <h2 className={s.pageHeaderTitle}>{title}</h2>
        {subtitle && <div className={s.pageHeaderSub}>{subtitle}</div>}
      </div>
      <div className={s.spacer} />
      <div className={s.row}>{children}</div>
    </header>
  );
}

export function SearchField({ placeholder, value, onChange, onSubmit }: {
  placeholder: string; value?: string; onChange?: (v: string) => void; onSubmit?: (v: string) => void;
}) {
  return (
    <label className={s.search}>
      <Search size={16} strokeWidth={ICON.strokeWidth} />
      <input
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSubmit?.((e.target as HTMLInputElement).value)}
      />
    </label>
  );
}

export function Avatar({ src, size = 44, online }: { src: string; size?: number; online?: boolean }) {
  return (
    <span className={s.avatar} style={{ width: size, height: size }}>
      <img src={src} alt="" />
      {online && <span className={s.dot} />}
    </span>
  );
}

export function IconButton({ icon: I, label, onClick }: { icon: Icon; label: string; onClick?: () => void }) {
  return (
    <button className={s.iconBtn} aria-label={label} title={label} onClick={onClick}>
      <I {...ICON} />
    </button>
  );
}

export function Button({ children, icon: I, variant = "secondary", onClick, style, disabled }: {
  children: ReactNode; icon?: Icon; variant?: "primary" | "secondary" | "ghost" | "purple";
  onClick?: () => void; style?: React.CSSProperties; disabled?: boolean;
}) {
  return (
    <button className={cx(s.btn, s[variant])} onClick={onClick} style={style} disabled={disabled}>
      {I && <I size={16} strokeWidth={2} />}
      {children}
    </button>
  );
}

export function Badge({ children, tone = "blue" }: { children: ReactNode; tone?: "blue" | "purple" | "muted" }) {
  return <span className={cx(s.badge, tone === "purple" && s.badgePurple, tone === "muted" && s.badgeMuted)}>{children}</span>;
}

export function ListRow({ leading, title, subtitle, trailing, selected, onClick }: {
  leading?: ReactNode; title: ReactNode; subtitle?: ReactNode; trailing?: ReactNode;
  selected?: boolean; onClick?: () => void;
}) {
  return (
    <button className={cx(s.listRow, selected && s.listRowSelected)} onClick={onClick}>
      {leading}
      <div className={s.listRowBody}>
        <div className={s.listRowTitle}>{title}</div>
        {subtitle && <div className={s.listRowSub}>{subtitle}</div>}
      </div>
      {trailing && <div className={s.listRowTrail}>{trailing}</div>}
    </button>
  );
}

export function Card({ children, className, style, onClick }: {
  children: ReactNode; className?: string; style?: React.CSSProperties; onClick?: () => void;
}) {
  return <div className={cx(s.card, className)} style={style} onClick={onClick}>{children}</div>;
}

export function Glass({ children, className, style }: { children: ReactNode; className?: string; style?: React.CSSProperties }) {
  return <div className={cx(s.glass, className)} style={style}>{children}</div>;
}

export function SectionTitle({ children, action, onAction }: { children: ReactNode; action?: string; onAction?: () => void }) {
  return (
    <h3 className={s.sectionTitle}>
      {children}
      {action && <button className={s.sectionLink} onClick={onAction}>{action}</button>}
    </h3>
  );
}

export function Segmented<T extends string>({ options, value, onChange }: {
  options: { value: T; label: string }[]; value: T; onChange: (v: T) => void;
}) {
  return (
    <div className={s.segmented} role="tablist">
      {options.map((o) => (
        <button key={o.value} role="tab" aria-selected={o.value === value}
          className={cx(s.segment, o.value === value && s.segmentActive)} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Photo card with title over a soft gradient. `ratio` = width/height. */
export function ImageCard({ src, title, subtitle, ratio = 4 / 3, onClick }: {
  src: string; title?: string; subtitle?: string; ratio?: number; onClick?: () => void;
}) {
  return (
    <div className={s.imageCard} style={{ aspectRatio: String(ratio), cursor: onClick ? "pointer" : undefined }} onClick={onClick}>
      <img src={src} alt={title ?? ""} loading="lazy" />
      {(title || subtitle) && (
        <div className={s.imageCardShade}>
          {title && <div className={s.imageCardTitle}>{title}</div>}
          {subtitle && <div className={s.imageCardSub}>{subtitle}</div>}
        </div>
      )}
    </div>
  );
}

export const Spinner = () => <span className={s.spinner} role="status" aria-label="Loading" />;

/** Shared modal chrome: backdrop click + Escape to close. The frame keeps its
 *  own `role="dialog"` and visuals — pass the screen's backdrop class so
 *  nothing moves. (Not for the calendar editor: its focus trap needs
 *  mousedown-outside semantics instead of click-to-close.) */
export function Backdrop({ backdrop, onClose, children }: {
  backdrop: string; onClose: () => void; children: ReactNode;
}) {
  const latest = useRef(onClose);
  latest.current = onClose;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") latest.current(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return <div className={backdrop} onClick={onClose}>{children}</div>;
}

/** Temporary content for a slot that a session has not built yet. */
export function Placeholder({ title, owner }: { title: string; owner: string }) {
  return (
    <div className={s.placeholder}>
      <div><strong>{title}</strong>Built by {owner}</div>
    </div>
  );
}

const DEMO_SCENES = new Set([
  "photo-1512453979798-5ea266f8880c",
  "photo-1507525428034-b723cf961d3e",
  "photo-1511895426328-dc8714191300",
  "photo-1542751371-adc38448a05e",
  "photo-1522202176988-66273c2fd55f",
  "photo-1436491865332-7a61a109cc05",
  "photo-1537996194471-e657df975ab4",
  "photo-1498837167922-ddd27525d352",
  "photo-1486406146926-c627a92ad1ab",
  "photo-1495616811223-4d98c6e9c869",
  "photo-1555400038-63f5ba517a47",
  "photo-1504674900247-0877df9cc836",
  "photo-1511512578047-dfb367046420",
  "photo-1519046904884-53103b34b206",
  "photo-1434030216411-0b793f4b4173",
  "photo-1556909114-f6e7ad7d3136",
  "photo-1586724237569-f3d0c1dee8c6",
  "photo-1503177119275-0aa32b3a9368",
  "photo-1513635269975-59663e0ac1ad",
  "photo-1497366754035-f200968a6e72",
  "photo-1516321318423-f06f85e504b3",
  "photo-1519389950473-47ba0277781c",
]);

/** Local demo scene photo path. Unknown IDs fall back to a local scene; remote hosts are not used. */
export const img = (id: string, _w = 800) =>
  `/demo/scenes/${DEMO_SCENES.has(id) ? id : "photo-1512453979798-5ea266f8880c"}.jpg`;
/** Local demo avatar path. Remote portrait hosts are not used. */
export const avatar = (n: number) =>
  `/demo/avatars/avatar-${String((Math.abs(Math.floor(n || 0)) % 10) + 1).padStart(2, "0")}.jpg`;
