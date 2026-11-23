import { defineConfig, loadEnv, type Plugin, type ViteDevServer } from "vite";
import react from "@vitejs/plugin-react";
import { existsSync } from "node:fs";
import { relative, resolve } from "node:path";

/** Runs api/*.ts (the same Web-standard handlers Vercel deploys) inside the dev server — no Python, no proxy.
 *  /api/chat → api/chat.ts · /api/images/abc → api/images.ts?id=abc (same rewrite as vercel.json) · method = exported GET/POST. */
function apiRoutes(): Plugin {
  return {
    name: "mirsal-api-routes",
    configureServer(server: ViteDevServer) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url?.startsWith("/api/")) return next();
        const url = new URL(req.url, "http://localhost");
        const [name, id] = url.pathname.slice(5).split("/").filter(Boolean);
        const file = `api/${name}.ts`;
        if (id) url.searchParams.set("id", decodeURIComponent(id));
        if (!name || !existsSync(resolve(file))) { res.statusCode = 404; return res.end("Not found"); }
        try {
          const mod = await server.ssrLoadModule(`/${file}`);
          const handler = mod[req.method ?? "GET"] as ((r: Request) => Promise<Response>) | undefined;
          if (!handler) { res.statusCode = 405; return res.end("Method not allowed"); }
          const chunks: Buffer[] = [];
          for await (const c of req) chunks.push(c as Buffer);
          const headers = new Headers();
          for (const [k, v] of Object.entries(req.headers)) if (typeof v === "string") headers.set(k, v);
          const response = await handler(new Request(url, {
            method: req.method, headers, body: req.method === "GET" || req.method === "HEAD" ? undefined : Buffer.concat(chunks),
          }));
          res.statusCode = response.status;
          response.headers.forEach((v, k) => res.setHeader(k, v));
          res.end(Buffer.from(await response.arrayBuffer()));
        } catch (err) {
          server.config.logger.error(`[api] ${file}: ${err instanceof Error ? err.message : err}`);
          res.statusCode = 500; res.end("Server error");
        }
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  // API handlers read process.env (as on Vercel): load every .env key, not only VITE_*. Never exposed to the browser.
  Object.assign(process.env, loadEnv(mode, process.cwd(), ""));
  return {
    plugins: [react(), apiRoutes()],
    server: {
      port: 5173,
      // Optional Python agents service (agents/, local first). When it is not running the app falls back to its
      // existing paths; the browser only ever calls /agents/* through src/api.ts.
      proxy: { "/agents": { target: process.env.AGENTS_URL || "http://127.0.0.1:8787", ws: true, changeOrigin: true } },
      // cloud annotation workers reach the local queue through a Cloudflare quick tunnel (scripts/photos.mjs)
      allowedHosts: [".trycloudflare.com"],
      // Watch only the app. Other files in the repo (reference images, agents' scratch JSON, screenshots) are written
      // while the dev server runs, and a locked file there (EBUSY) used to crash it.
      watch: {
        ignored: (file: string) => {
          const rel = relative(process.cwd(), file).replace(/\\/g, "/");
          if (!rel || rel.startsWith("..")) return false;
          const top = rel.split("/")[0];
          if (["src", "api", "lib", "public", "media", "design", "node_modules"].includes(top)) return false; // the folders themselves too
          if (rel.includes("/")) return true;
          return !/^(index\.html|vite\.config\.ts|package\.json|tsconfig.*\.json|middleware\.ts|\.env.*)$/.test(rel);
        },
      },
    },
  };
});
