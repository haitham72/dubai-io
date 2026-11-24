"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Feed" },
  { href: "/communities", label: "Communities" },
  { href: "/create", label: "Create" },
  { href: "/inbox", label: "Inbox" },
  { href: "/profile", label: "Profile" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <nav className="dock" aria-label="Primary">
      {links.map((l) => (
        <Link key={l.href} href={l.href} className={pathname === l.href ? "dock-link active" : "dock-link"}>
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
