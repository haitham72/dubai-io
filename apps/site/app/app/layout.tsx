import Link from "next/link";
import TabsNav from "./tabs";

export const metadata = {
  title: "Dubai-io app — Today, Chat, Services, Feed, Ask",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <header
        style={{
          borderBottom: "1px solid var(--line)",
          padding: "12px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <Link
          href="/"
          style={{ color: "var(--foreground)", textDecoration: "none", fontWeight: 700 }}
        >
          Dubai-io
        </Link>
        <span style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
          Signed-in preview · same FastAPI backend
        </span>
      </header>
      <TabsNav />
      <div className="appWrap">{children}</div>
    </>
  );
}
