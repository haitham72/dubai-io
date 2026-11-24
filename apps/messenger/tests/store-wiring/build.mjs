import { build } from "esbuild";
import path from "node:path";

await build({
  entryPoints: ["tests/store-wiring/entry.ts"],
  bundle: true,
  platform: "node",
  format: "esm",
  outfile: "tests/store-wiring/bundle.mjs",
  logLevel: "error",
  plugins: [
    {
      name: "videos-stub",
      setup(b) {
        b.onResolve({ filter: /^\.\.?\/videos$/ }, () => ({
          path: path.resolve("tests/photo-window/videos-stub.ts"),
        }));
      },
    },
  ],
});
console.log("BUNDLED STORE-WIRING");
