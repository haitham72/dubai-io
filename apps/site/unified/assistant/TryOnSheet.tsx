"use client";
import { useEffect, useState } from "react";
import type { ChatProduct } from "../state";
import s from "./assistant.module.css";

type Status = { ready?: boolean; vertex?: boolean; openai?: boolean; fixture?: boolean };

export function TryOnSheet({
  product,
  onClose,
}: {
  product: ChatProduct;
  onClose: () => void;
}) {
  const [status, setStatus] = useState<Status | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [adult, setAdult] = useState(false);
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ src: string; caption: string; provenance: string; demo?: boolean } | null>(null);

  useEffect(() => {
    let alive = true;
    fetch("/api/tryon/status", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => { if (alive) setStatus(d); })
      .catch(() => { if (alive) setStatus({ ready: false }); });
    return () => { alive = false; };
  }, []);

  const run = async () => {
    if (!file || !adult || !approved) return;
    setBusy(true);
    setError(null);
    setPreview(null);
    try {
      const body = new FormData();
      body.set("person", file);
      body.set("title", product.title || "item");
      body.set("confirmed_adult", "1");
      if (product.thumbnail?.startsWith("https://")) {
        body.set("product_image_url", product.thumbnail);
      }
      const res = await fetch("/api/tryon", { method: "POST", body, credentials: "include" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : "Couldn't make a preview");
        return;
      }
      const mime = data.media_type || "image/png";
      setPreview({
        src: `data:${mime};base64,${data.image_base64}`,
        caption: data.caption || "AI preview",
        provenance: data.provenance || "inferred",
        demo: Boolean(data.demo),
      });
    } catch {
      setError("Couldn't make a preview");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={s.tryonBackdrop} role="dialog" aria-modal="true" aria-labelledby="tryon-title" data-testid="tryon-sheet">
      <div className={s.tryonSheet}>
        <header className={s.tryonHead}>
          <h2 id="tryon-title">Try it on</h2>
          <button type="button" className={s.tryonClose} onClick={onClose} aria-label="Close">Close</button>
        </header>
        <p className={s.tryonLede}>
          Full body · Front facing · Bright light. Your photo + this item → AI preview.
          Not shared with shops. Deleted after the preview unless you keep it later.
        </p>
        <div className={s.tryonProduct}>
          {product.thumbnail?.startsWith("https://") ? (
            <img src={product.thumbnail} alt="" width={72} height={72} />
          ) : null}
          <div>
            <strong>{product.title || "Item"}</strong>
            <p>{product.price || "Price unknown"}{product.source ? ` · ${product.source}` : ""}</p>
          </div>
        </div>

        {!status?.ready && status !== null && (
          <p className={s.err} role="alert" data-testid="tryon-blocker">
            Try-on needs a provider key (Google Vertex Virtual Try-On or OpenAI image). Preview kept as draft only — nothing invented.
          </p>
        )}

        <label className={s.tryonUpload}>
          <span>Your photo (18+)</span>
          <input
            data-testid="tryon-file"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <label className={s.tryonCheck}>
          <input type="checkbox" checked={adult} onChange={(e) => setAdult(e.target.checked)} data-testid="tryon-adult" />
          I confirm I am 18+ and this is my photo
        </label>

        <div className={s.tryonApproval} data-testid="tryon-approval">
          <p>
            Approval: share <strong>your photo</strong> + <strong>1 product image</strong> with the try-on model
            ({status?.vertex ? "Google Virtual Try-On" : status?.openai ? "OpenAI image" : "provider TBD"}).
            Not sent to {product.source || "the shop"}.
          </p>
          <label className={s.tryonCheck}>
            <input type="checkbox" checked={approved} onChange={(e) => setApproved(e.target.checked)} data-testid="tryon-approve" />
            I approve this exact side effect
          </label>
        </div>

        <div className={s.tryonActions}>
          <button
            type="button"
            className={s.tryonPrimary}
            data-testid="tryon-run"
            disabled={!file || !adult || !approved || busy || status?.ready === false}
            onClick={() => void run()}
          >
            {busy ? "Making preview…" : "Try it on"}
          </button>
          {product.link?.startsWith("https://") && (
            <a className={s.tryonSecondary} href={product.link} target="_blank" rel="noopener noreferrer">
              Open store
            </a>
          )}
        </div>

        {error && <p className={s.err} role="alert">{error}</p>}
        {preview && (
          <figure className={s.tryonResult} data-testid="tryon-result">
            <img src={preview.src} alt="AI try-on preview" />
            <figcaption>
              {preview.demo ? "Demo data · " : ""}
              {preview.caption} · {preview.provenance}
            </figcaption>
          </figure>
        )}
      </div>
    </div>
  );
}
