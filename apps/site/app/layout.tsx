import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dubai-io — your everyday assistant for Dubai",
  description:
    "Dubai-io keeps tasks, decisions, communities, services and maps in one calm place.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
