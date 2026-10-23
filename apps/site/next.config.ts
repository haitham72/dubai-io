import type { NextConfig } from "next";

const apiOrigin = process.env.DUBAIIO_API_ORIGIN ?? "http://127.0.0.1:8030";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // The API has no CORS; calling it same-origin through this rewrite keeps the
  // anonymous session cookie on the site's own origin.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
};

export default nextConfig;
