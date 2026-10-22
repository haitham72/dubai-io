import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/chrome";

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main
        style={{
          margin: "0 auto",
          maxWidth: "var(--max-width)",
          padding: "96px 24px",
          textAlign: "center",
        }}
      >
        <h1>That page isn&apos;t here.</h1>
        <p style={{ color: "var(--muted)" }}>
          It may have moved — or it never existed.
        </p>
        <p>
          <Link href="/">Back home</Link> · <Link href="/app">Open the app</Link>
        </p>
      </main>
      <SiteFooter />
    </>
  );
}
