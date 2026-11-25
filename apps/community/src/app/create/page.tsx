"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createPost } from "@/lib/api";
import { isSignedIn } from "@/lib/session";

export default function CreatePage() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!text.trim()) { setError("Write something first."); return; }
    if (!isSignedIn()) { setError("Sign in first — posts are tied to your account."); return; }
    setBusy(true); setError(null);
    try {
      await createPost(text.trim());
      setText("");
      router.push("/"); // feed refetches; the new post is at the top
    } catch (e) {
      setError(`Could not post — ${(e as Error).message || "the community service is unavailable"}. Your draft is kept here; nothing was posted.`);
    } finally { setBusy(false); }
  }

  return (
    <section>
      <h1>Create</h1>
      <p className="sub">Share an update with your communities.</p>
      <div className="user-box">
        <label htmlFor="post-text">Your post</label>
        <textarea id="post-text" value={text} onChange={(e) => setText(e.target.value)} placeholder="What's happening?" maxLength={2000} />
      </div>
      <button type="button" className="primary" disabled={busy} onClick={submit}>{busy ? "Posting…" : "Post"}</button>
      {error && <div className="error" role="alert">{error}</div>}
      <p className="ai-text" style={{ marginTop: 16 }}>Posts are shared only with the audience you choose. Nothing is posted without your tap above.</p>
    </section>
  );
}
