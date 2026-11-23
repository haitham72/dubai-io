// Vercel Routing Middleware: a private-link gate for the investor demo (no OAuth).
// When DEMO_KEY is set, visitors need ?key=<DEMO_KEY> once; it is remembered in a cookie for 30 days.
// Keeps strangers from spending the OpenAI / SerpAPI / Tavily credits behind /api.
declare const process: { env: Record<string, string | undefined> };

export const config = { matcher: ["/((?!assets/|favicon.png|mirsal-logo.png|manifest.webmanifest).*)"] };

const COOKIE = "mirsal_demo";

export default function middleware(request: Request): Response | undefined {
  const key = process.env.DEMO_KEY;
  if (!key) return undefined; // gate off
  const url = new URL(request.url);
  const cookie = request.headers.get("cookie") ?? "";
  if (cookie.split(/;\s*/).includes(`${COOKIE}=${key}`)) return undefined;

  if (url.searchParams.get("key") === key) {
    url.searchParams.delete("key");
    return new Response(null, {
      status: 302,
      headers: {
        Location: url.pathname + (url.search || ""),
        "Set-Cookie": `${COOKIE}=${key}; Path=/; Max-Age=2592000; HttpOnly; Secure; SameSite=Lax`,
      },
    });
  }

  if (url.pathname.startsWith("/api/")) return new Response("Private demo", { status: 401 });
  return new Response(
    `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mirsal</title><style>body{margin:0;min-height:100dvh;display:grid;place-items:center;font-family:-apple-system,system-ui,sans-serif;background:#eef3fa;color:#101828}
main{text-align:center;padding:24px}img{width:72px;height:72px}h1{font-size:22px;margin:16px 0 6px}p{color:#667085;margin:0}</style></head>
<body><main><img src="/mirsal-logo.png" alt=""><h1>Mirsal</h1><p>This is a private demo. Please use the link you were sent.</p></main></body></html>`,
    { status: 401, headers: { "Content-Type": "text/html; charset=utf-8" } },
  );
}
