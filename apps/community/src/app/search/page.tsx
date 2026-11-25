"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import RealPostCard from "@/components/RealPostCard";
import * as api from "@/lib/api";
import type { SearchResults } from "@/lib/api";
import { isSignedIn } from "@/lib/session";

export default function SearchPage() {
  return (
    <Suspense fallback={<section><h1>Search</h1><p className="empty">Loading…</p></section>}>
      <SearchInner />
    </Suspense>
  );
}

function SearchInner() {
  const router = useRouter();
  const params = useSearchParams();
  const q = params.get("q") ?? "";
  const [query, setQuery] = useState(q);
  const [results, setResults] = useState<SearchResults | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "live" | "empty" | "error" | "signedout">(q ? "loading" : "idle");
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (term: string) => {
    if (!term.trim()) { setResults(null); setState("idle"); return; }
    if (!isSignedIn()) { setState("signedout"); return; }
    setState("loading"); setError(null);
    try {
      const r = await api.searchCommunity(term.trim());
      setResults(r);
      setState((r.groups.length + r.profiles.length + r.posts.length) === 0 ? "empty" : "live");
    } catch (e) {
      setError((e as Error).message || "Search failed");
      setState("error");
    }
  }, []);

  useEffect(() => { void run(q); }, [q, run]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const term = query.trim();
    if (term) router.push(`/search?q=${encodeURIComponent(term)}`);
  };

  return (
    <section>
      <h1>Search</h1>
      <p className="sub">Groups, people and posts.</p>
      <form onSubmit={submit} role="search">
        <div className="user-box" style={{ display: "flex", gap: 8 }}>
          <input aria-label="Search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search communities, people, posts…" maxLength={100} style={{ flex: 1 }} />
          <button type="submit" className="primary" style={{ marginTop: 0 }}>Search</button>
        </div>
      </form>

      {state === "signedout" && <div className="notice" role="status">Sign in to search. <Link href="/signin">Sign in</Link></div>}
      {state === "error" && <div className="error" role="alert">{error ?? "Search is unavailable right now."}</div>}
      {state === "empty" && <p className="empty">No results for “{q}”.</p>}
      {state === "idle" && <p className="empty">Type to search groups, people and posts.</p>}

      {results && (results.groups.length > 0 || results.profiles.length > 0 || results.posts.length > 0) && (
        <>
          {results.groups.length > 0 && (
            <>
              <h2>Communities</h2>
              {results.groups.map((g) => (
                <article key={g.id} className="card">
                  <h2><Link href={`/communities/${encodeURIComponent(g.id)}`}>{g.name}</Link></h2>
                  <p>{g.description}</p>
                  <p className="meta">{g.member_count ?? g.members ?? 0} members · {g.visibility}</p>
                </article>
              ))}
            </>
          )}
          {results.profiles.length > 0 && (
            <>
              <h2>People</h2>
              {results.profiles.map((p) => (
                <article key={p.handle} className="card">
                  <h2><Link href={`/u/${encodeURIComponent(p.handle)}`}>{p.display_name || p.handle}</Link> <span className="handle">@{p.handle}</span></h2>
                  <p className="meta">{p.area}{p.interests?.length ? ` · ${p.interests.join(", ")}` : ""}</p>
                </article>
              ))}
            </>
          )}
          {results.posts.length > 0 && (
            <>
              <h2>Posts</h2>
              <div className="feed-v2">
                {results.posts.map((p) => <RealPostCard key={p.id} post={p} />)}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}
