"use client";
import { useState } from "react";
import { createPost } from "@/lib/api";

export default function CreatePage() {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!text.trim()) { setError("Write something first."); return; }
    setBusy(true); setError(null); setStatus(null);
    try {
      await createPost(text.trim());
      setStatus("Posted to your feed.");
      setText("");
    } catch {
      setError("Could not post — the community service is unavailable. Your draft is kept here; nothing was posted.");
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
      {status && <div className="notice" role="status">{status}</div>}
      {error && <div className="error" role="alert">{error}</div>}
      <p className="ai-text" style={{ marginTop: 16 }}>Posts are shared only with the audience you choose. Nothing is posted without your tap above.</p>
    </section>
  );
}
