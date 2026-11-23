// Small iOS building blocks shared by the mobile pages.
import type { ComponentType, ReactNode } from "react";
import type { LucideProps } from "lucide-react";
import { useStore } from "../store";
import { ICON } from "../ui";
import s from "./mobile.module.css";

export const ORB = "/mirsal-logo.png";

/** Round Liquid Glass control (toolbar button). */
export function GlassButton({ icon: I, label, onClick, primary }: {
  icon: ComponentType<LucideProps>; label: string; onClick?: () => void; primary?: boolean;
}) {
  return (
    <button className={`${s.gbtn} ${primary ? s.gbtnPrimary : ""}`} aria-label={label} title={label} onClick={onClick}>
      <I {...ICON} size={22} />
    </button>
  );
}

/** Mirsal Updates entry inside toolbars: the orb with the unread count. */
export function OrbButton({ onClick }: { onClick: () => void }) {
  const unread = useStore((st) => st.tasks.filter((t) => t.unread && !t.dismissed).length);
  return (
    <button className={`${s.gbtn} ${s.orbBtn}`} aria-label={`Mirsal Updates${unread ? `, ${unread} new` : ""}`} onClick={onClick}>
      <img src={ORB} alt="" />
      {unread > 0 && <span className={s.orbBadge}>{unread}</span>}
    </button>
  );
}

/** Floating toolbar row over content (conversation, AI). */
export function NavBar({ children }: { children: ReactNode }) {
  return <div className={s.navbar}>{children}</div>;
}

export function LargeTitle({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className={s.head}>
      <h1 className={s.largeTitle}>{title}</h1>
      <div className={s.headActions}>{children}</div>
    </div>
  );
}
