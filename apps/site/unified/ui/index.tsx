// Shared primitives (ported from Mirsal, recoloured). Build every screen from these.
import type { ComponentType, ReactNode } from "react";
import type { LucideProps } from "lucide-react";
import { Search } from "lucide-react";
import s from "./ui.module.css";

type Icon = ComponentType<LucideProps>;
const cx = (...c: (string | false | undefined)[]) => c.filter(Boolean).join(" ");

/** Icon size and stroke used everywhere. */
export const ICON = { size: 20, strokeWidth: 1.75 } as const;

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

/** Round avatar: an image when `src` is given, else the first letters on the accent tint. */
export function Avatar({ src, label, icon: I, size = 40, tone }: {
  src?: string; label?: string; icon?: Icon; size?: number; tone?: string;
}) {
  return (
    <span className={s.avatar} style={{ width: size, height: size, background: tone }}>
      {src ? <img src={src} alt="" /> : I ? <I size={Math.round(size * 0.5)} strokeWidth={2} /> : <b>{(label ?? "?").slice(0, 2)}</b>}
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

export function Button({ children, icon: I, variant = "secondary", onClick, disabled, type = "button" }: {
  children: ReactNode; icon?: Icon; variant?: "primary" | "secondary" | "ghost";
  onClick?: () => void; disabled?: boolean; type?: "button" | "submit";
}) {
  return (
    <button type={type} className={cx(s.btn, s[variant])} onClick={onClick} disabled={disabled}>
      {I && <I size={16} strokeWidth={2} />}
      {children}
    </button>
  );
}

export function Badge({ children, tone = "accent" }: { children: ReactNode; tone?: "accent" | "muted" }) {
  return <span className={cx(s.badge, tone === "muted" && s.badgeMuted)}>{children}</span>;
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

export function Card({ children, className, onClick }: { children: ReactNode; className?: string; onClick?: () => void }) {
  return <div className={cx(s.card, className)} onClick={onClick}>{children}</div>;
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

/** Marks fixture/demo content (root rule 2). */
export function DemoPill({ label = "Demo" }: { label?: string }) {
  return <span className={s.demo} data-testid="demo-pill">{label}</span>;
}

export function Placeholder({ title, plan }: { title: string; plan: number }) {
  return (
    <Card className={s.placeholder}>
      <strong>{title}</strong>
      <span>Coming in plan {plan}</span>
    </Card>
  );
}
