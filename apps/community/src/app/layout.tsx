import type { Metadata } from "next";
import type { ReactNode } from "react";
import Nav from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dubai-io Community",
  description: "Community preview — staged for founder visual review.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <header className="topbar">
            <span className="brand">Dubai-io</span>
            <span className="brand-note">Community</span>
          </header>
          <main>{children}</main>
          <Nav />
        </div>
      </body>
    </html>
  );
}
