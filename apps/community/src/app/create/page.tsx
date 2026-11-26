"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { createPost, getTrendingTags } from "@/lib/api";
import { extractHashtags, POST_FLAIRS } from "@/lib/feed";
import { isSignedIn } from "@/lib/session";

const DEFAULT_TAG_CHIPS = [
  "dubaimarina",
  "jlt",
  "difc",
  "padel",
  "hiring",
  "events",
  "housing",
];

export default function CreatePage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [flair, setFlair] = useState<string>("");
  const [trending, setTrending] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!isSignedIn()) return;
    getTrendingTags(8)
      .then((rows) => setTrending(rows.map((r) => r.tag.replace(/^#+/, "").toLowerCase())))
      .catch(() => {
        /* fallback to default chips */
      });
  }, []);

  const helperTags = useMemo(() => {
    const merged = [...trending, ...DEFAULT_TAG_CHIPS];
    return Array.from(new Set(merged)).slice(0, 10);
  }, [trending]);

  function addHashtag(tag: string) {
    const clean = tag.replace(/^#+/, "").toLowerCase();
    const existing = extractHashtags(text);
    if (existing.includes(clean)) return;
    const prefix = text.trim().length > 0 && !/\s$/.test(text) ? " " : "";
    setText(`${text}${prefix}#${clean}`);
  }

  async function submit() {
    if (!text.trim()) {
      setError("Write something first.");
      return;
    }
    if (!isSignedIn()) {
      setError("Sign in first — posts are tied to your account.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const tags = extractHashtags(text);
      await createPost(text.trim(), undefined, {
        ...(flair ? { flair } : {}),
        ...(tags.length > 0 ? { tags } : {}),
      });
      setText("");
      setFlair("");
      router.push("/");
    } catch (e) {
      setError(
        `Could not post — ${(e as Error).message || "the community service is unavailable"}. Your draft is kept here; nothing was posted.`,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1>Create</h1>
      <p className="sub">Share an update with your communities.</p>
      <div className="user-box">
        <label htmlFor="post-flair">Flair (optional)</label>
        <select
          id="post-flair"
          value={flair}
          onChange={(e) => setFlair(e.target.value)}
          style={{
            display: "block",
            width: "100%",
            marginTop: 6,
            marginBottom: 12,
            borderRadius: 12,
            border: "1px solid var(--border)",
            padding: "8px 12px",
            background: "var(--card)",
          }}
        >
          <option value="">None</option>
          {POST_FLAIRS.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>

        <label htmlFor="post-text">Your post</label>
        <textarea
          id="post-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="What's happening? Add #hashtags like #dubaimarina"
          maxLength={2000}
        />

        <div style={{ marginTop: 10 }}>
          <span className="meta">Add topic tags:</span>
          <div className="lanes" style={{ margin: "8px 0 0" }}>
            {helperTags.map((tag) => (
              <button
                key={tag}
                type="button"
                className="lane-btn"
                onClick={() => addHashtag(tag)}
              >
                #{tag}
              </button>
            ))}
          </div>
        </div>
      </div>
      <button type="button" className="primary" disabled={busy} onClick={submit}>
        {busy ? "Posting…" : "Post"}
      </button>
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      <p className="ai-text" style={{ marginTop: 16 }}>
        Posts are shared only with the audience you choose. Nothing is posted without your tap above.
      </p>
    </section>
  );
}
