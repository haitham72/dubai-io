// /api/photos — photo collection + annotation work queue + hybrid search (Postgres + pgvector).
// Images live as static files in public/photos/ (Vercel CDN in production, Vite static locally).
// Postgres holds METADATA ONLY (file, meta, result, doc, embedding) — never image bytes, never base64.
// Two databases, same code:
//   local dev  (`npm run dev`, DATABASE_URL in .env → Docker `mirsal-pg`) — the annotation queue
//   production (Vercel, DATABASE_URL → Supabase) — only finished rows, migrated with `node scripts/photos.mjs migrate`; serves search
// Workers reach Postgres only through this route (HTTP), so firewalls don't matter.
//
//   POST ?action=setup                      (token) create table/extension (idempotent; also drops the legacy image/mime bytea columns)
//   POST ?action=seed      {file, meta, collection?}   (token) add metadata for an image; the file itself
//                                                     must already exist in public/photos/
//   POST ?action=claim     {worker, n}       (token) atomically claim n pending images (stale claims > 10 min return to the pool)
//   POST ?action=complete  {file, worker, model, result | error}  (token) store the annotation (or release / fail after 3 tries)
//   POST ?action=embed                      (token) embed annotated rows that have no vector yet (OpenAI, text only)
//   POST ?action=import    {file, meta, collection, result, model}  (token) upsert a finished row (migration target)
//   GET  ?action=export&after=<file>&n=20    (token) finished rows (metadata only) for migration (paged by file name)
//   GET  ?action=status                     counts by status and worker
//   GET  ?action=list&limit=24&offset=0     one page of finished rows, newest first ({total} = all finished rows)
//   GET  ?action=search&q=...&k=12[&year=..&event=..]  hybrid keyword + semantic search over annotations
//   GET  ?action=image&file=...             302 redirect to the static file (images live on the CDN, not in Postgres)
import postgres from "postgres";
import { body, env, fail, json, openai, route } from "../lib/http.js";

type Sql = ReturnType<typeof postgres>;
let db: Sql | null = null;
function sql(): Sql {
  const url = env("DATABASE_URL") || env("supabase_transactionpooler");
  if (!url) throw fail(503, "Database not configured");
  // Supabase transaction pooler: no prepared statements, TLS; the local Docker database: plain TCP.
  const local = /@(localhost|127\.0\.0\.1)[:/]/.test(url);
  db ??= postgres(url, { prepare: false, ssl: local ? false : "require", max: local ? 4 : 1, idle_timeout: 20 });
  return db;
}

function requireToken(req: Request) {
  const token = env("PHOTOS_TOKEN");
  if (!token || req.headers.get("authorization") !== `Bearer ${token}`) throw fail(401, "Worker token required");
}

interface Annotation { caption: string; caption_ar: string; people: string[]; objects: string[]; scene: string; text_in_image: string; tags: string[] }
interface Meta { account?: string; year?: number | null; event?: string; date?: string | null; extra?: string }

/** The text that gets embedded for search: filename context + annotation, both languages. */
const docText = (m: Meta, a: Annotation) => [
  `${m.event ?? ""} ${m.date ?? ""} (${m.account ?? ""})`, a.caption, a.caption_ar, a.scene,
  (a.people ?? []).join(", "), (a.objects ?? []).join(", "), a.text_in_image, (a.tags ?? []).join(", "), m.extra,
].filter(Boolean).join("\n");

/** Absolute CDN URL for a photo file. Prefers the Host header because the local dev
 *  plugin builds req.url without a port (Vercel requests carry the real host). */
const photoUrl = (req: Request, file: string) => {
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? new URL(req.url).host;
  const proto = req.headers.get("x-forwarded-proto") ?? new URL(req.url).protocol.replace(":", "") ?? "https";
  return `${proto}://${host}/photos/${file.split("/").map(encodeURIComponent).join("/")}`;
};

async function embed(texts: string[]): Promise<string[]> {
  const r = await openai<{ data: { embedding: number[] }[] }>("embeddings", { model: "text-embedding-3-small", input: texts });
  return r.data.map((d) => `[${d.embedding.map((x) => x.toFixed(6)).join(",")}]`);
}

const STALE = "10 minutes";

export const POST = route(async (req) => {
  requireToken(req);
  const action = new URL(req.url).searchParams.get("action");
  const q = sql();

  if (action === "setup") {
    await q`create extension if not exists vector`;
    await q`create table if not exists photo_jobs (
      file text primary key, collection text not null default 'default', meta jsonb not null default '{}',
      status text not null default 'pending', worker text, model text, claimed_at timestamptz, attempts int not null default 0,
      result jsonb, error text, doc text, embedding vector(1536),
      created_at timestamptz not null default now(), updated_at timestamptz not null default now())`;
    await q`create index if not exists photo_jobs_status_idx on photo_jobs (status)`;
    // Migration from the old bytea design: images now live in public/photos/, so drop the byte columns.
    await q`alter table photo_jobs drop column if exists image`;
    await q`alter table photo_jobs drop column if exists mime`;
    return json({ ok: true });
  }

  if (action === "seed") {
    const b = await body<{ file: string; meta: Meta; collection?: string }>(req);
    if (!b.file) return fail(400, "file is required");
    const rows = await q`insert into photo_jobs (file, collection, meta)
      values (${b.file}, ${b.collection ?? "default"}, ${q.json(b.meta as never)})
      on conflict (file) do nothing returning file`;
    return json({ added: rows.length === 1 });
  }

  if (action === "claim") {
    const b = await body<{ worker: string; n?: number }>(req);
    const n = Math.max(1, Math.min(25, b.n ?? 10));
    const rows = await q`with picked as (
        select file from photo_jobs
        where status = 'pending' or (status = 'claimed' and claimed_at < now() - ${STALE}::interval)
        order by file limit ${n} for update skip locked)
      update photo_jobs p set status = 'claimed', worker = ${b.worker}, claimed_at = now(), attempts = p.attempts + 1, updated_at = now()
      from picked where p.file = picked.file
      returning p.file, p.meta`;
    return json(rows.map((r) => ({ file: r.file as string, meta: r.meta as Meta, url: photoUrl(req, r.file as string) })));
  }

  if (action === "complete") {
    const b = await body<{ file: string; worker: string; model?: string; result?: Annotation; error?: string }>(req);
    // Only the worker that currently holds the claim may write: a late worker whose claim expired and was handed to
    // someone else can't overwrite their work, and a finished image is never overwritten.
    const [row] = await q`select meta, status, worker from photo_jobs where file = ${b.file}`;
    if (!row) return fail(404, "Unknown file");
    if (row.status !== "claimed" || row.worker !== b.worker) {
      return json({ ok: false, reason: row.status === "done" ? "already done" : "not your claim (it expired and was reassigned)" }, 409);
    }
    if (b.result) {
      await q`update photo_jobs set status = 'done', result = ${q.json(b.result as never)}, model = ${b.model ?? null},
        doc = ${docText(row.meta as Meta, b.result)}, embedding = null, error = null, updated_at = now()
        where file = ${b.file} and status = 'claimed' and worker = ${b.worker}`;
    } else {
      await q`update photo_jobs set status = case when attempts >= 3 then 'failed' else 'pending' end,
        error = ${(b.error ?? "unknown").slice(0, 500)}, updated_at = now()
        where file = ${b.file} and status = 'claimed' and worker = ${b.worker}`;
    }
    return json({ ok: true });
  }

  if (action === "import") {
    const b = await body<{ file: string; meta: Meta; collection?: string; result: Annotation; model?: string; worker?: string }>(req);
    if (!b.file || !b.result) return fail(400, "file and result are required");
    await q`insert into photo_jobs (file, collection, meta, status, result, model, worker, doc)
      values (${b.file}, ${b.collection ?? "default"}, ${q.json(b.meta as never)},
              'done', ${q.json(b.result as never)}, ${b.model ?? null}, ${b.worker ?? "migration"}, ${docText(b.meta, b.result)})
      on conflict (file) do update set meta = excluded.meta, collection = excluded.collection,
        status = 'done', result = excluded.result, model = excluded.model, worker = excluded.worker, doc = excluded.doc,
        embedding = null, error = null, updated_at = now()`;
    return json({ ok: true });
  }

  if (action === "embed") {
    let total = 0;
    for (;;) {
      const rows = await q`select file, doc from photo_jobs where status = 'done' and embedding is null and doc is not null limit 64`;
      if (!rows.length) break;
      const vectors = await embed(rows.map((r) => r.doc as string));
      for (const [i, r] of rows.entries()) await q`update photo_jobs set embedding = ${vectors[i]}::vector where file = ${r.file}`;
      total += rows.length;
    }
    return json({ embedded: total });
  }

  return fail(400, "Unknown action");
});

export const GET = route(async (req) => {
  const p = new URL(req.url).searchParams;
  const action = p.get("action");
  const q = sql();

  if (action === "export") {
    requireToken(req);
    const n = Math.max(1, Math.min(50, Number(p.get("n")) || 20));
    const rows = await q`select file, collection, meta, result, model, worker
      from photo_jobs where status = 'done' and file > ${p.get("after") ?? ""} order by file limit ${n}`;
    return json(rows);
  }

  if (action === "status") {
    const rows = await q`select status, coalesce(worker, '-') as worker, count(*)::int as n,
      count(embedding)::int as embedded from photo_jobs group by 1, 2 order by 1, 2`;
    return json(rows);
  }

  if (action === "search") {
    const text = (p.get("q") ?? "").trim();
    if (!text) return fail(400, "q is required");
    const k = Math.max(1, Math.min(48, Number(p.get("k")) || 12));
    // Optional metadata filters.
    const year = p.get("year") ? Number(p.get("year")) : null;
    const event = (p.get("event") ?? "").trim();

    // Keyword terms: Unicode letters/numbers, length ≥ 2 (keeps Arabic words, drops noise).
    const terms = [...new Set(
      text.toLowerCase().split(/[^\p{L}\p{N}]+/u).filter((t) => t.length >= 2).map((t) => t.replace(/[\\%_]/g, "\\$&")),
    )].slice(0, 12);

    type Hit = { file: string; meta: Meta; caption: string; caption_ar: string; tags: unknown; hits?: number; dist?: number };
    let kw: Hit[] = [];
    if (terms.length) {
      kw = await q`select file, meta, result->>'caption' as caption, result->>'caption_ar' as caption_ar, result->'tags' as tags,
          (select count(*)::int from unnest(${terms}::text[]) as t(term)
            where lower(file || ' ' || coalesce(doc, '')) like '%' || term || '%' escape '\\') as hits
        from photo_jobs
        where status = 'done'
        ${year ? q`and (meta->>'year')::int = ${year}` : q``}
        ${event ? q`and meta->>'event' ilike ${"%" + event + "%"}` : q``}
        and exists (select 1 from unnest(${terms}::text[]) as t(term)
          where lower(file || ' ' || coalesce(doc, '')) like '%' || term || '%' escape '\\')
        order by hits desc, file limit ${k * 2}`;
    }

    // Semantic list (skipped when nothing is embedded yet — keyword results still work).
    const [{ n: embedded }] = await q`select count(*)::int as n from photo_jobs where status = 'done' and embedding is not null`;
    let vec: Hit[] = [];
    if ((embedded as number) > 0) {
      const [vector] = await embed([text]);
      vec = await q`select file, meta, result->>'caption' as caption, result->>'caption_ar' as caption_ar, result->'tags' as tags,
          (embedding <=> ${vector}::vector) as dist
        from photo_jobs where status = 'done' and embedding is not null
        ${year ? q`and (meta->>'year')::int = ${year}` : q``}
        ${event ? q`and meta->>'event' ilike ${"%" + event + "%"}` : q``}
        order by embedding <=> ${vector}::vector limit ${k}`;
    }

    // Reciprocal Rank Fusion. When keyword hits exist the query names something concrete
    // ("zayed", "oman national day") → restrict to keyword-matching rows, ranked by RRF
    // over both lists (semantic order still refines ties). Otherwise fall back to pure vector.
    const rank = (list: Hit[]) => new Map(list.map((r, i) => [r.file, i]));
    const kr = rank(kw), vr = rank(vec);
    const pool = kw.length ? kw : vec;
    const byFile = new Map<string, Hit>([...kw, ...vec].map((r) => [r.file, r]));
    const results = pool
      .map((r) => {
        const score = (kr.has(r.file) ? 1 / (60 + (kr.get(r.file) as number)) : 0)
          + (vr.has(r.file) ? 1 / (60 + (vr.get(r.file) as number)) : 0);
        const why = [...(kr.has(r.file) ? ["keyword"] : []), ...(vr.has(r.file) ? ["semantic"] : [])];
        const full = byFile.get(r.file) as Hit;
        return { file: full.file, meta: full.meta, caption: full.caption, caption_ar: full.caption_ar, tags: full.tags, score: Math.round(score * 1000) / 1000, why, url: photoUrl(req, full.file) };
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, k);
    return json({ mode: "hybrid", count: results.length, results });
  }

  if (action === "image") {
    // Legacy endpoint: images are static files now — redirect to the CDN instead of reading Postgres.
    const file = p.get("file") ?? "";
    if (!file) return fail(400, "file is required");
    return Response.redirect(photoUrl(req, file), 302);
  }

  if (action === "list") {
    // Annotated photos, newest first (filename-parsed year, then day, then filename), one page at a
    // time so the first screen paints fast. Meta comes from the filename convention, so rows always carry a date.
    const limit = Math.min(Math.max(Number(p.get("limit")) || 24, 1), 200);
    const offset = Math.max(Number(p.get("offset")) || 0, 0);
    const rows = await q`select file, meta, result->>'caption' as caption, result->'tags' as tags, count(*) over() as total
      from photo_jobs where status = 'done'
      order by (meta->>'year')::int desc nulls last,
        case when meta->>'date' ~ '^[0-9]{1,2} [A-Z][a-z]{2} [0-9]{4}$' then to_date(meta->>'date', 'DD Mon YYYY') end desc nulls last,
        file desc
      limit ${limit} offset ${offset}`;
    // Past the end the window count is gone with the rows — count separately (rare).
    const total = rows.length ? Number(rows[0].total)
      : offset ? ((await q`select count(*)::int as n from photo_jobs where status = 'done'`)[0].n as number) : 0;
    return json({
      mode: "list",
      count: rows.length,
      total,
      offset,
      results: rows.map((r) => ({
        file: r.file as string, meta: r.meta as Meta,
        caption: (r.caption as string) ?? "", tags: (r.tags as string[]) ?? [],
        url: photoUrl(req, r.file as string),
      })),
    });
  }

  return fail(400, "Unknown action");
});
