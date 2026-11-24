import type { Metadata } from "next";
import type { ReactNode } from "react";
import Frame from "@/components/Frame";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dubai-io Community",
  description: "Community preview — staged for founder visual review.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Frame>{children}</Frame>
      </body>
    </html>
  );
}
