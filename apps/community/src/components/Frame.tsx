"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import Nav from "./Nav";

export default function Frame({ children }: { children: ReactNode }) {
  const path = usePathname();
  if (path === "/") return <div className="feed-root">{children}</div>;
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">Dubai-io</span>
        <span className="brand-note">Community</span>
      </header>
      <main>{children}</main>
      <Nav />
    </div>
  );
}
