import { build } from "esbuild";
import path from "node:path";
await build({
  entryPoints: ["tests/photo-window/entry.ts"],
  bundle: true,
  platform: "node",
  format: "esm",
  outfile: "tests/photo-window/bundle.mjs",
  logLevel: "error",
  plugins: [{
    name: "videos-stub",
    setup(b) {
      b.onResolve({ filter: /^\.\.?\/videos$/ }, () => ({ path: path.resolve("tests/photo-window/videos-stub.ts") }));
    },
  }],
});
console.log("BUNDLED");
