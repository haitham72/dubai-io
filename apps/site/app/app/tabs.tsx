"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/app", label: "Home" },
  { href: "/app/chat", label: "Chat" },
  { href: "/app/services", label: "Services" },
  { href: "/app/feed", label: "Feed" },
  { href: "/app/ask", label: "Ask" },
  { href: "/app/map", label: "Maps" },
];

export default function TabsNav() {
  const path = usePathname();
  const active = (href: string) =>
    href === "/app" ? path === "/app" : path === href || path.startsWith(`${href}/`);
  return (
    <nav className="tabbar" aria-label="App">
      <div className="tabbarInner">
        {tabs.map((tab) => (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active(tab.href) ? "page" : undefined}
          >
            {tab.label}
          </Link>
        ))}
        <span style={{ flex: 1 }} />
        <Link href="/app/profile" aria-current={path === "/app/profile" ? "page" : undefined}>
          Me
        </Link>
      </div>
    </nav>
  );
}
